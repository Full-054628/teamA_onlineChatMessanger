import socket
import threading
import json
import random
import string

# パスワードをハッシュ化し、ソルトを生成する
import hashlib
import os


class ChatServer:
    # サーバーの設定を初期化
    def __init__(self, host="0.0.0.0", tcp_port=12346, udp_port=12345):

        self.host = host  # サーバーのホストアドレス
        self.tcp_port = tcp_port  # TCP通信用のポート
        self.udp_port = udp_port  # UDP通信用のポート
        self.clients = {}  # クライアントのトークンとアドレスを保持する辞書
        self.rooms = {}  # チャットルームとその参加者を保持する辞書

        # UDPソケットの設定
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host, self.udp_port))

        # TCPソケットの設定
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.tcp_socket.listen(5)  # 接続待ちの最大クライアント数を設定

        print(
            f"チャットサーバーがTCP {self.tcp_port}番ポートとUDP {self.udp_port}番ポートで待機しています。"
        )

    # TCP接続を処理
    def handle_tcp_connection(self, client_socket, addr):
        try:
            data = client_socket.recv(1024).decode(
                "utf-8"
            )  # クライアントからのデータを受信
            request = json.loads(data)  # JSON形式のデータを辞書に変換

            # リクエストの種類に応じて処理を分岐
            if request["operation"] == "create":
                # チャットルーム作成リクエスト
                response = self.create_room(request, addr)
            elif request["operation"] == "join":
                # チャットルーム参加リクエスト
                response = self.join_room(request, addr)
            else:
                # 不正な操作
                response = {"status": "error", "message": "Invalid operation"}

            # レスポンスをクライアントに送信
            client_socket.sendall(json.dumps(response).encode("utf-8"))
        except Exception as e:
            print(f"Error handling TCP connection: {e}")
        finally:
            client_socket.close()  # 接続を閉じる

    def hash_password(self, password):
        # ソルトを生成（32バイトのランダムなデータ）
        salt = os.urandom(32)
        # パスワードとソルトを組み合わせてハッシュ化
        pwdhash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        # ハッシュ化されたパスワードとソルトを返す
        return salt + pwdhash

    # チャットルームを作成
    def create_room(self, request, addr):
        room_name = request["room_name"]
        password = request.get("password", "")
        if room_name in self.rooms:
            # 既に存在するルーム名の場合はエラー
            return {"status": "error", "message": "ルームは既に存在します"}

        # パスワードをハッシュ化
        hashed_password = self.hash_password(password)

        token = self.generate_token()  # トークンを生成
        self.rooms[room_name] = {
            "password": hashed_password,
            "clients": [token],
        }  # ルームを追加
        self.clients[token] = (addr[0], self.udp_port)  # トークンとアドレスを関連付け
        return {"status": "ok", "token": token}  # トークンを含むレスポンスを返す

    def verify_password(self, stored_password, provided_password):
        # 保存されたパスワードからソルトを抽出（最初の32バイト）
        salt = stored_password[:32]
        # 保存されたパスワードのハッシュ部分を抽出
        stored_hash = stored_password[32:]
        # 提供されたパスワードを同じソルトでハッシュ化
        pwdhash = hashlib.pbkdf2_hmac(
            "sha256", provided_password.encode("utf-8"), salt, 100000
        )
        # ハッシュ化されたパスワードを比較
        return pwdhash == stored_hash

    # チャットルームに参加
    def join_room(self, request, addr):
        room_name = request["room_name"]
        provided_password = request.get("password", "")
        if room_name not in self.rooms:
            # ルームが存在しない場合はエラー
            return {"status": "error", "message": "無効なルーム名です"}

        # ルームのパスワードを取得
        stored_password = self.rooms[room_name]["password"]
        # パスワードを検証
        if not self.verify_password(stored_password, provided_password):
            return {"status": "error", "message": "無効なパスワードです"}

        token = self.generate_token()  # トークンを生成
        self.rooms[room_name]["clients"].append(
            token
        )  # ルームの参加者リストにトークンを追加
        self.clients[token] = (addr[0], self.udp_port)  # トークンとアドレスを関連付け
        return {"status": "ok", "token": token}  # トークンを含むレスポンスを返す

    # トークンを生成
    def generate_token(self):
        return "".join(random.choices(string.ascii_letters + string.digits, k=16))

    def listen_udp(self):
        # UDPでのメッセージ受信を待機するメソッド
        while True:
            message, client_addr = self.udp_socket.recvfrom(4096)
            threading.Thread(
                target=self.handle_udp_message, args=(message, client_addr)
            ).start()

    # UDPメッセージを処理
    def handle_udp_message(self, message, client_addr):
        try:
            # メッセージをJSON形式でデコード
            decoded_message = json.loads(message.decode("utf-8"))
            # トークンとメッセージ本文を抽出
            token = decoded_message["token"]
            msg = decoded_message["message"]

            if token in self.clients:
                # トークンが有効な場合、メッセージをリレー
                for room_name, room_info in self.rooms.items():
                    if token in room_info["clients"]:
                        self.relay_message(room_name, token, msg.encode("utf-8"))
                        break
            else:
                print(f"Invalid token or IP mismatch: {client_addr}")
        except Exception as e:
            print(f"Error handling UDP message: {e}")

    # メッセージをリレー
    def relay_message(self, room_name, sender_token, message):
        for token in self.rooms[room_name]["clients"]:
            if token != sender_token:
                client_ip, client_udp_port = self.clients[token]
                self.udp_socket.sendto(message, (client_ip, client_udp_port))

    def start(self):
        threading.Thread(
            target=self.listen_udp, daemon=True
        ).start()  # UDPリスニングを開始
        self.listen_tcp()  # メインスレッドでTCPリスニングを開始

    # TCPでの接続要求を待機
    def listen_tcp(self):
        while True:
            client_socket, addr = self.tcp_socket.accept()
            threading.Thread(
                target=self.handle_tcp_connection, args=(client_socket, addr)
            ).start()

    def run(self):
        print("Starting server...")
        self.start()


if __name__ == "__main__":
    server = ChatServer()
    server.run()
