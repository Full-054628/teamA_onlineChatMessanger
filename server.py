import socket
import threading
import json
import random
import string
import struct

class ChatServer:
    def __init__(self, host="0.0.0.0", tcp_port=12346, udp_port=12345):
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.clients = {}  # クライアントのトークンと情報のマッピング
        self.rooms = {}  # ルーム名と参加しているクライアントのトークンのリスト
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host, self.udp_port))
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.tcp_socket.listen(5)
        print(f"チャットサーバーがTCP {self.tcp_port}番ポートとUDP {self.udp_port}番ポートで待機しています。")

    def handle_tcp_connection(self, client_socket, addr):
        try:
            # ヘッダーの受信
            header = client_socket.recv(32)
            if not header:
                print(f"{addr} からヘッダーが受信されませんでした。")
                return
            
            room_name_size, operation, _, operation_payload_size_bytes = struct.unpack('!B B B 29s', header)
            operation_payload_size = int.from_bytes(operation_payload_size_bytes.strip(b'\x00'), 'big')
            
            # ルーム名と操作ペイロードの受信
            room_name = client_socket.recv(room_name_size).decode('utf-8')
            operation_payload = client_socket.recv(operation_payload_size).decode('utf-8')
            request = json.loads(operation_payload)

            if operation == 1:  # ルーム作成
                response = self.create_room(room_name, request["username"])
            elif operation == 2:  # ルーム参加
                response = self.join_room(room_name, request["username"])
            else:
                response = {"status": "error", "message": "不正な操作です"}
            
            # クライアントへの応答送信
            response_payload = json.dumps(response).encode("utf-8")
            client_socket.sendall(response_payload)
        except Exception as e:
            print(f"{addr} からのTCP接続処理中にエラーが発生しました: {e}")
        finally:
            client_socket.close()

    def create_room(self, room_name, username):
        if room_name in self.rooms:
            return {"status": "error", "message": "ルームは既に存在します"}
        token = self.generate_token()
        self.rooms[room_name] = [token]
        self.clients[token] = (username, self.host, self.udp_port)
        return {"status": "ok", "token": token}

    def join_room(self, room_name, username):
        if room_name not in self.rooms:
            return {"status": "error", "message": "ルームが存在しません"}
        token = self.generate_token()
        self.rooms[room_name].append(token)
        self.clients[token] = (username, self.host, self.udp_port)
        return {"status": "ok", "token": token}

    def generate_token(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    def listen_udp(self):
        while True:
            message, client_addr = self.udp_socket.recvfrom(4096)
            threading.Thread(target=self.handle_udp_message, args=(message, client_addr)).start()

    def handle_udp_message(self, message, client_addr):
        try:
            message_json = json.loads(message.decode("utf-8"))
            token = message_json.get("token")
            msg = message_json.get("message")

            if token in self.clients:
                username, _, _ = self.clients[token]
                self.clients[token] = (username, client_addr[0], client_addr[1])
                self.relay_message(token, username, msg)
            else:
                print(f"無効なトークンまたはIPの不一致: {client_addr}")
        except Exception as e:
            print(f"{client_addr} からのUDPメッセージ処理中にエラーが発生しました: {e}")

    def relay_message(self, sender_token, username, message):
        for room_name, tokens in self.rooms.items():
            if sender_token in tokens:
                for token in tokens:
                    if token != sender_token:
                        _, client_ip, client_port = self.clients[token]
                        send_msg = json.dumps({"username": username, "message": message})
                        self.udp_socket.sendto(send_msg.encode("utf-8"), (client_ip, client_port))

    def start(self):
        threading.Thread(target=self.listen_udp, daemon=True).start()
        self.listen_tcp()

    def listen_tcp(self):
        while True:
            client_socket, addr = self.tcp_socket.accept()
            threading.Thread(target=self.handle_tcp_connection, args=(client_socket, addr)).start()

    def run(self):
        print("サーバーを起動しています...")
        self.start()

if __name__ == "__main__":
    server = ChatServer()
    server.run()
