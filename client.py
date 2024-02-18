import socket
import threading
import sys
# #3作り始めます
class UDPClient:

    # クライアントの初期化
    def __init__(self, server_ip='127.0.0.1', server_port=12345, buffer_size=4096):
        self.server_ip = server_ip
        self.server_port = server_port
        self.buffer_size = buffer_size
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.username = self.prompt_username()

    # クライアントにユーザーネームを入力させ、バリデーションチェックを行う
    def prompt_username(self):
        username = input("ユーザー名を入力してください: ")
        username_bytes = username.encode('utf-8')
        if not username or len(username_bytes) > 255:
            error_message = "ユーザー名が空です。" if not username else "ユーザー名は255バイト以下である必要があります。"
            print(error_message)
            self.close()
            sys.exit()
        return username

    # ユーザーが入力したメッセージをサーバーに送信。"quit"と入力されたらソケットをクローズしてからプログラムを終了する
    def send_message(self):
        try:
            while True:
                msg = input("あなた: ")
                if msg == "quit":
                    break
                message = f"{self.username}: {msg}".encode('utf-8')
                if len(message) > self.buffer_size:
                    print("メッセージが大きすぎます。")
                    continue
                self.client_socket.sendto(message, (self.server_ip, self.server_port))
        finally:
            self.close()

    # サーバーからのメッセージを受信し、デコーードして表示する
    def receive_message(self):
        while True:
            try:
                message, _ = self.client_socket.recvfrom(self.buffer_size)
                print(f"\n{message.decode('utf-8')}\nあなた: ", end='', flush=True)
            except Exception as e:
                print(f"受信中にエラーが発生しました: {e}")
                break

    # receive_messageメソッドをデーモンスレッドで開始し、send_messageも開始
    def run(self):
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
    client.run()
