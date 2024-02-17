# TODO TCPの接続が成功した際に、発行されるトークンとルーム名を受け取る必要がある

import socket
import threading
import sys


class UDPClient:
    def __init__(
        self, server_ip="127.0.0.1", server_port=12345, tcp_port=12346, buffer_size=4096
    ):
        self.server_ip = server_ip
        self.server_port = server_port
        self.tcp_port = tcp_port
        self.buffer_size = buffer_size
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = self.prompt_username()
        self.token = self.get_token()

    def prompt_username(self):
        username = input("ユーザー名を入力してください: ")
        username_bytes = username.encode("utf-8")
        if not username or len(username_bytes) > 255:
            error_message = (
                "ユーザー名が空です。"
                if not username
                else "ユーザー名は255バイト以下である必要があります。"
            )
            print(error_message)
            self.close()
        return username

    def get_token(self):
        # # TCP接続を通じてサーバーからトークンを受け取る
        # self.tcp_socket.connect((self.server_ip, self.tcp_port))
        # self.tcp_socket.sendall("TOKEN_REQUEST".encode("utf-8"))
        # token = self.tcp_socket.recv(self.buffer_size).decode("utf-8")
        # self.tcp_socket.close()
        # return token

        # テスト用: ユーザー名に応じて異なるダミートークンを返す
        if self.username == "user1":
            # return "dummytoken1234567890abcdefg"
            return "b"
        elif self.username == "user2":
            # return "dummytoken0987654321abcdefg"
            return "c"
        else:
            # デフォルトのダミートークン
            # return "defaultdummytokenabcdef123456"
            return "d"

    def send_message(self):
        # トークンとルーム名をメッセージに含めてサーバーに送信
        try:
            while True:
                msg = input("あなた: ")
                if msg == "quit":
                    break
                # ルーム名（ここでは例として 'a'）とトークンをメッセージに含める
                room_name = "a"  # 仮のルーム名
                # トークンとユーザー名をメッセージに含める
                message = f"{room_name}{self.token}:{self.username}: {msg}".encode(
                    "utf-8"
                )
                if len(message) > self.buffer_size:
                    print("メッセージが大きすぎます。")
                    continue
                self.client_socket.sendto(message, (self.server_ip, self.server_port))
        finally:
            self.close()

    def receive_message(self):
        while True:
            try:
                message, _ = self.client_socket.recvfrom(self.buffer_size)
                print(f"\n{message.decode('utf-8')}\nあなた: ", end="", flush=True)
            except Exception as e:
                print(f"受信中にエラーが発生しました: {e}")
                break

    def start(self):
        recv_thread = threading.Thread(target=self.receive_message)
        recv_thread.daemon = True
        recv_thread.start()
        self.send_message()

    def close(self):
        self.client_socket.close()
        print("ソケットを閉じました。")
        sys.exit()


if __name__ == "__main__":
    client = UDPClient()
    client.start()
