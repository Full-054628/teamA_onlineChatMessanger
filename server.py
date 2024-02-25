import socket
import threading
import json
import random
import string
import hashlib
import os

class ChatServer:
    # チャットサーバーの初期設定
    def __init__(self, host="0.0.0.0", tcp_port=12346, udp_port=12345):
        self.host = host  # サーバーのホストアドレス
        self.tcp_port = tcp_port  # TCP通信用ポート
        self.udp_port = udp_port  # UDP通信用ポート
        self.clients = {}  # クライアントのトークンと(IPアドレス, UDPポート)を保持
        self.rooms = {}  # チャットルームとその参加者を保持

        # UDPソケットの設定
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host, self.udp_port))

        # TCPソケットの設定
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.tcp_socket.listen(5)  # 同時に接続待ちするクライアントの数

        print(f"チャットサーバーがTCP {self.tcp_port}番ポートとUDP {self.udp_port}番ポートで待機しています。")

    # UDPメッセージのリスニング
    def listen_udp(self):
        while True:
            message, client_addr = self.udp_socket.recvfrom(4096)
            threading.Thread(target=self.handle_udp_message, args=(message, client_addr)).start()

    # UDPメッセージの処理
    def handle_udp_message(self, message, client_addr):
        try:
            if not message:
                print("Received an empty message.")
                return
            decoded_message = json.loads(message.decode("utf-8"))
            token = decoded_message["token"]
            msg = decoded_message["message"]
            print(f"Received message from {client_addr}: {msg}")

            # メッセージを適切なクライアントにリレー
            if token in self.clients:
                for room_name, room_info in self.rooms.items():
                    if token in room_info["clients"]:
                        self.relay_message(room_name, token, msg.encode("utf-8"))
                        break
            else:
                print(f"Invalid token or IP mismatch: {client_addr}")
        except Exception as e:
            print(f"Error handling UDP message: {e}")

    # メッセージのリレー処理
    def relay_message(self, room_name, sender_token, message):
        for token in self.rooms[room_name]["clients"]:
            if token != sender_token:
                client_ip, client_udp_port = self.clients[token]
                # メッセージをJSON形式にエンコードして送信
                message_dict = {"message": message.decode('utf-8')}
                message_json = json.dumps(message_dict)
                self.udp_socket.sendto(message_json.encode('utf-8'), (client_ip, client_udp_port))

    # TCP接続のリスニング
    def listen_tcp(self):
        while True:
            client_socket, addr = self.tcp_socket.accept()
            threading.Thread(target=self.handle_tcp_connection, args=(client_socket, addr)).start()

    # TCP接続の処理
    def handle_tcp_connection(self, client_socket, addr):
        try:
            data = client_socket.recv(1024).decode("utf-8")
            request = json.loads(data)

            # チャットルームの作成または参加処理
            if request["operation"] in ["create", "join"]:
                udp_port = request.get("udp_port", None)
                if udp_port is not None:
                    response = self.process_room_request(request, addr, udp_port)
                else:
                    response = {"status": "error", "message": "UDP port information is missing"}
            else:
                response = {"status": "error", "message": "Invalid operation"}

            client_socket.sendall(json.dumps(response).encode("utf-8"))
        except Exception as e:
            print(f"Error handling TCP connection: {e}")
        finally:
            client_socket.close()

    # チャットルームリクエストの処理
    def process_room_request(self, request, addr, udp_port):
        # チャットルームの作成または参加
        if request["operation"] == "create":
            response = self.create_room(request, addr, udp_port)
        elif request["operation"] == "join":
            response = self.join_room(request, addr, udp_port)
        return response

    # チャットルームの作成
    def create_room(self, request, addr, udp_port):
        room_name = request["room_name"]
        password = request.get("password", "")
        if room_name in self.rooms:
            return {"status": "error", "message": "ルームは既に存在します"}

        hashed_password = self.hash_password(password)
        token = self.generate_token()
        self.rooms[room_name] = {"password": hashed_password, "clients": [token]}
        self.clients[token] = (addr[0], udp_port)
        return {"status": "ok", "token": token}

    # チャットルームへの参加
    def join_room(self, request, addr, udp_port):
        room_name = request["room_name"]
        provided_password = request.get("password", "")
        if room_name not in self.rooms:
            return {"status": "error", "message": "無効なルーム名です"}

        stored_password = self.rooms[room_name]["password"]
        if not self.verify_password(stored_password, provided_password):
            return {"status": "error", "message": "無効なパスワードです"}

        token = self.generate_token()
        self.rooms[room_name]["clients"].append(token)
        self.clients[token] = (addr[0], udp_port)
        return {"status": "ok", "token": token}

    # パスワードのハッシュ化
    def hash_password(self, password):
        salt = os.urandom(32)
        pwdhash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return salt + pwdhash

    # パスワードの検証
    def verify_password(self, stored_password, provided_password):
        salt = stored_password[:32]
        stored_hash = stored_password[32:]
        pwdhash = hashlib.pbkdf2_hmac("sha256", provided_password.encode("utf-8"), salt, 100000)
        return pwdhash == stored_hash

    # トークンの生成
    def generate_token(self):
        return "".join(random.choices(string.ascii_letters + string.digits, k=16))

    # サーバーの起動
    def start(self):
        threading.Thread(target=self.listen_udp, daemon=True).start()
        self.listen_tcp()

    # サーバーの実行
    def run(self):
        print("Starting server...")
        self.start()

if __name__ == "__main__":
    server = ChatServer()
    server.run()
