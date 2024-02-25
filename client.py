import socket
import threading
import sys
import json

class ChatClient:
    # クライアントの初期化
    def __init__(self, server_ip="127.0.0.1", server_tcp_port=12346, server_udp_port=12345):
        # サーバーのIPとポート設定
        self.server_ip = server_ip
        self.server_tcp_port = server_tcp_port
        self.server_udp_port = server_udp_port
        
        # UDPソケットの設定とバインド
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(("", 0))  # ランダムなローカルポートにバインド
        
        # TCPソケットの設定
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # ユーザー情報
        self.username = ""  # ユーザー名
        self.token = ""  # サーバーから受け取るトークン

    # サーバーへの接続とルーム操作の選択
    def prompt_and_connect(self):
        self.username = input("ユーザー名を入力してください: ")
        try:
            # サーバーへのTCP接続
            self.tcp_socket.connect((self.server_ip, self.server_tcp_port))
        except Exception as e:
            print(f"サーバーへの接続に失敗しました: {e}")
            sys.exit()

        # チャットルームの操作選択とリクエスト送信
        local_udp_port = self.udp_socket.getsockname()[1]  # UDPポートの取得
        operation = input("チャットルームを作成するには 'create'、参加するには 'join' と入力してください: ")
        room_name = input("チャットルーム名を入力してください: ")
        password = input("パスワード（任意、'create'の場合）: ") if operation == "create" else input("パスワード: ")
        request = {
            "operation": operation,
            "room_name": room_name,
            "password": password,
            "udp_port": local_udp_port  # UDPポート情報を含む
        }
        self.tcp_socket.sendall(json.dumps(request).encode('utf-8'))
        response = json.loads(self.tcp_socket.recv(1024).decode('utf-8'))
        
        # サーバーからのレスポンス処理
        if response["status"] == "ok":
            self.token = response["token"]
            print(f"トークン: {self.token} でルーム '{room_name}' に参加しました。")
        else:
            print(f"エラー: {response['message']}")
            self.tcp_socket.close()
            sys.exit()

        self.tcp_socket.close()

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

                try:
                    message = json.loads(data.decode('utf-8'))
                    print(f"\r{message['message']}\nあなた: ", end="")
                except json.JSONDecodeError:
                    print("\nReceived data is not a valid JSON.\nあなた: ", end="")
                    continue

                sys.stdout.flush()
            except Exception as e:
                print(f"\nメッセージの受信中にエラーが発生しました: {e}\nあなた: ", end="")
                break

    # 通信の開始
    def start(self):
        receiver_thread = threading.Thread(target=self.receive_message, daemon=True)
        receiver_thread.start()
        self.send_message()

    # クライアントの終了処理
    def close(self):
        self.udp_socket.close()
        sys.exit()

if __name__ == "__main__":
    client = ChatClient()
    client.prompt_and_connect()
    client.start()
