import socket
import threading
import json
import struct
import hashlib
import os
import random
import string

class ChatServer:
    def __init__(self, host="0.0.0.0", tcp_port=12346, udp_port=12345):
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.clients = {}
        self.rooms = {}

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host, self.udp_port))

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.tcp_socket.listen(5)

        print(f"チャットサーバーがTCP {self.tcp_port}番ポートとUDP {self.udp_port}番ポートで待機しています。")

    # 
    def listen_udp(self):
        while True:
            try:
                # UDPソケットからメッセージを受信。受信バッファの最大サイズは4096バイト
                message, client_addr = self.udp_socket.recvfrom(4096) 
                # 受信したメッセージを処理するために新しいスレッドを開始。
                # handle_udp_messageメソッドをターゲットとし、メッセージとクライアントのアドレスを引数として渡す
                threading.Thread(target=self.handle_udp_message, args=(message, client_addr)).start()
            except Exception as e:
                print(f"UDP listen error: {e}")


    def handle_udp_message(self, message, client_addr):
        try:
            # 受信したメッセージ（バイト列）をUTF-8でデコードし、JSON形式からPythonオブジェクトに変換
            decoded_message = json.loads(message.decode("utf-8"))
            # メッセージからトークンとメッセージ本文を取得
            token = decoded_message.get("token")
            msg = decoded_message.get("message")

            # 受信したメッセージに関するデバッグ情報を表示
            print(f"Received message from {client_addr}: {msg}")

            # トークンがクライアントリストに存在するか確認
            if token in self.clients:
                # トークンに対応するチャットルーム名とUDPポートを取得
                room_name, _ = self.clients[token]
                # そのチャットルームにいる全クライアントの情報を取得
                clients_to_relay = self.rooms[room_name]["clients"]

                # チャットルーム内の他の全クライアントにメッセージをリレーする
                for client_token, (client_ip, client_udp_port) in clients_to_relay.items():
                    if client_token != token:  # メッセージの送信者を除外
                        # 正しいクライアントのアドレス情報を使用してメッセージをリレー
                        self.udp_socket.sendto(message, (client_ip, client_udp_port))
                        # メッセージのリレーに関するデバッグ情報を表示
                        print(f"Relayed message to {client_ip}:{client_udp_port}")
            else:
                # 有効ではないトークンが受信された場合、エラーメッセージを表示
                print("Invalid token received from:", client_addr)
        except Exception as e:
            # メッセージ処理中にエラーが発生した場合、エラーメッセージを表示
            print(f"Error handling UDP message: {e}")



    def listen_tcp(self):
    # 無限ループでTCP接続を待機する
        while True:
            # クライアントからの接続を受け入れ、クライアントソケットとアドレスを取得
            client_socket, addr = self.tcp_socket.accept()
            # 新しいスレッドを開始して、受け取ったTCP接続を処理する
            threading.Thread(target=self.handle_tcp_connection, args=(client_socket, addr)).start()

    def handle_tcp_connection(self, client_socket, addr):
        try:
            # クライアントからのデータを受信（最大1024バイト）
            data = client_socket.recv(1024)
            # データが受信された場合、リクエストを処理
            if data:
                response = self.process_request(data, addr)
                # 処理結果をクライアントに送信
                client_socket.sendall(response)
        except Exception as e:
            # 接続処理中にエラーが発生した場合、エラーメッセージを表示
            print(f"Error handling TCP connection: {e}")
        finally:
            # 処理が完了したらクライアントソケットを閉じる
            client_socket.close()

    def process_request(self, data, addr):
            # リクエストデータからヘッダー情報を解析するためのフォーマット
            header_format = '>B B B I'
            # ヘッダーサイズを計算
            header_size = struct.calcsize(header_format)
            # ヘッダーデータを解析して、各種情報を取得
            room_name_length, operation, state, body_length = struct.unpack(header_format, data[:header_size])
            # ルーム名をデコード
            room_name = data[header_size:header_size+room_name_length].decode('utf-8')
            # ペイロード（本文データ）を取得してJSONオブジェクトに変換
            payload_raw = data[header_size+room_name_length:header_size+room_name_length+body_length]
            payload = json.loads(payload_raw.decode('utf-8'))
            
            # ペイロードからUDPポート情報を取得
            udp_port = payload["udp_port"]
            
            # オペレーションコードに応じた処理を分岐
            if operation == 1:  # ルーム作成のリクエスト
                return self.create_room(room_name, payload, addr, udp_port)
            elif operation == 2:  # ルーム参加のリクエスト
                return self.join_room(room_name, payload, addr, udp_port)
            else:  # 未知のオペレーションコードの場合、エラーメッセージを返す
                return json.dumps({"status": "error", "message": "Unknown operation"}).encode('utf-8')


    def create_room(self, room_name, payload, addr, udp_port):
        # 新しいトークンを生成
        token = self.generate_token()
        # 新しいチャットルームをrooms辞書に追加。
        # ルーム名をキーとし、ルームのパスワード（ハッシュ化されたもの）とクライアントのリストを値とする。
        self.rooms[room_name] = {"password": self.hash_password(payload["password"]), "clients": {token: (addr[0], udp_port)}}
        # クライアントをclients辞書に追加。
        # 生成したトークンをキーとし、ルーム名とクライアントのアドレス情報を値とする。
        self.clients[token] = (room_name, (addr[0], udp_port))
        # 成功レスポンスをJSON形式でエンコードして返す。
        return json.dumps({"status": "ok", "token": token}).encode('utf-8')

    def join_room(self, room_name, payload, addr, udp_port):
        provided_password = payload["password"]  # クライアントが提供したパスワード

        # チャットルームが存在し、提供されたパスワードが正しいか確認
        if room_name in self.rooms and self.verify_password(self.rooms[room_name]["password"], provided_password):
            # 新しいトークンを生成
            token = self.generate_token()
            # 指定されたルームにクライアントを追加
            self.rooms[room_name]["clients"][token] = (addr[0], udp_port)
            # クライアントをclients辞書に追加
            self.clients[token] = (room_name, (addr[0], udp_port))
            # 成功レスポンスを返す
            return json.dumps({"status": "ok", "token": token}).encode('utf-8')
        else:
            # パスワードが間違っている場合、エラーレスポンスを返す
            return json.dumps({"status": "error", "message": "Incorrect password or room does not exist"}).encode('utf-8')


    def hash_password(self, password):
        # パスワードのハッシュ化に使用するランダムなソルトを生成
        salt = os.urandom(32)
        # pbkdf2_hmacアルゴリズムを使用してパスワードをハッシュ化。
        # sha256ハッシュアルゴリズム、ソルト、100000回の反復を使用。
        pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        # ソルトとハッシュを結合して返す。
        return salt + pwdhash

    def verify_password(self, stored_password, provided_password):
        # 保存されたパスワードからソルトを抽出
        salt = stored_password[:32]
        # 保存されたハッシュを抽出
        stored_hash = stored_password[32:]
        # 提供されたパスワードを同じソルトと反復回数を使用してハッシュ化
        pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        # 生成されたハッシュと保存されたハッシュを比較
        return pwdhash == stored_hash

    def generate_token(self):
        # ランダムな文字列を生成してトークンとして返す。
        # 英大文字と数字を使用し、長さは26文字。
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=26))


    def start(self):
        threading.Thread(target=self.listen_udp, daemon=True).start() # listen_udpをデーモンスレッドで実行
        self.listen_tcp()

    def run(self):
        print("Starting server...")
        self.start()

if __name__ == "__main__":
    server = ChatServer()
    server.run()