import socket
import threading
import sys
import json
import struct

class ChatClient:
    # クライアントの初期化
    def __init__(self, server_ip="127.0.0.1", server_tcp_port=12346, server_udp_port=12345):
        self.server_ip = server_ip
        self.server_tcp_port = server_tcp_port
        self.server_udp_port = server_udp_port
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(("", 0))
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = ""
        self.token = ""

    # サーバーへのTCP接続
    def connect_to_server(self):
        try:
            self.tcp_socket.connect((self.server_ip, self.server_tcp_port))
            print("サーバーへの接続に成功しました。")
            return True
        except Exception as e:
            print(f"サーバーへの接続に失敗しました: {e}")
            return False

    # ユーザー情報の入力とバリデーション
    def prompt_user_info(self):
        while True:
            self.username = input("ユーザー名を入力してください: ")
            username_bytes = self.username.encode('utf-8')

            if not self.username or len(username_bytes) > 255:
                print("ユーザー名が空です。" if not self.username else "ユーザー名は255バイト以下である必要があります。")
                continue
            break

        operation = input("チャットルームを作成するには '1'、参加するには '2' と入力してください: ")
        room_name = input("チャットルーム名を入力してください: ")
        password = input("パスワードを入力してください: ")

        return operation, room_name, password

    # TCPメッセージの送信とレスポンスの処理
    def send_tcp_message(self, operation, room_name, password=""):
        udp_port = self.udp_socket.getsockname()[1]  # 実際にバインドされたUDPポートを取得
        body = json.dumps({"username": self.username, "password": password, "udp_port": udp_port})
        body_bytes = body.encode('utf-8')
        room_name_bytes = room_name.encode('utf-8')
        header = struct.pack('>B B B I', len(room_name_bytes), operation, 0, len(body_bytes))
        message = header + room_name_bytes + body_bytes

        self.tcp_socket.sendall(message)
        response = self.tcp_socket.recv(1024)
        return json.loads(response.decode('utf-8')) if response else {"status": "error", "message": "No response from server"}

    # チャットクライアントの開始
    def start(self):
        if not self.connect_to_server():
            print("サーバーへの接続に失敗しました。")
            sys.exit()

        operation, room_name, password = self.prompt_user_info()
        operation_code = 1 if operation == "1" else 2
        response = self.send_tcp_message(operation_code, room_name, password)

        if response.get("status") == "ok":
            self.token = response["token"]
            print(f"トークン: {self.token} でルーム '{room_name}' に参加しました。")
            self.receive_and_send_messages()
        else:
            print(f"エラー: {response.get('message', 'Unknown error')}")
            self.tcp_socket.close()
            sys.exit()

    # メッセージの受信と送信の処理を開始
    def receive_and_send_messages(self):
        receiver_thread = threading.Thread(target=self.receive_message, daemon=True)
        receiver_thread.start()
        self.send_message()

    # メッセージの送信
    def send_message(self):
        while True:
            message = input("あなた：")
            if message.lower() == "quit":
                print("チャットから退出します。")
                self.close()
                break
            packet = {"token": self.token, "message": f"{self.username}: {message}"}
            self.udp_socket.sendto(json.dumps(packet).encode('utf-8'), (self.server_ip, self.server_udp_port))

    # メッセージの受信と表示
    def receive_message(self):
        while True:
            try:
                data, _ = self.udp_socket.recvfrom(4096)
                if not data:
                    continue
                message = json.loads(data.decode('utf-8'))
                print(f"\r{message['message']}\nあなた: ", end="")
            except json.JSONDecodeError:
                print("\nReceived data is not a valid JSON.\nあなた: ", end="")
                continue
            except Exception as e:
                print(f"\nメッセージの受信中にエラーが発生しました: {e}\nあなた: ", end="")
                break

    # クライアントの終了処理
    def close(self):
        self.udp_socket.close()
        self.tcp_socket.close()
        sys.exit()

if __name__ == "__main__":
    client = ChatClient()
    client.start()
