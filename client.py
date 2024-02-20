import socket
import threading
import sys
import json

class UDPClient:

    # クライアントの初期化
    def __init__(self, server_ip="127.0.0.1", server_port=12345, tcp_port=12346, buffer_size=4096):
        self.server_ip = server_ip  # サーバーのIPアドレス
        self.server_port = server_port  # UDP通信用のポート
        self.tcp_port = tcp_port  # TCP通信用のポート
        self.buffer_size = buffer_size  # 受信バッファのサイズ
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDPソケットの作成
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCPソケットの作成
        self.username = self.prompt_username()  # ユーザー名の入力と取得
        self.token = self.get_token()  # サーバーからトークンの取得

    # クライアントにユーザーネームを入力させ、バリデーションチェックを行う
    def prompt_username(self):
        username = input("ユーザー名を入力してください: ")
        username_bytes = username.encode("utf-8")
        if not username or len(username_bytes) > 255:
            print("ユーザー名が空、または長すぎます。")
            sys.exit()
        return username

    # サーバーからユニークなトークンを取得するためのTCP接続
    def get_token(self):
        self.tcp_socket.connect((self.server_ip, self.tcp_port))  # TCP接続の確立
        self.tcp_socket.sendall(json.dumps({"username": self.username}).encode("utf-8"))  # ユーザー名をJSON形式で送信
        token = self.tcp_socket.recv(self.buffer_size).decode("utf-8")  # サーバーからトークンの受信
        self.tcp_socket.close()  # TCPソケットのクローズ
        return token

    # メッセージ送信処理
    def send_message(self):
        try:
            while True:
                msg = input("あなた: ")
                if msg == "quit":
                    break
                message = f"{self.token}:{msg}".encode("utf-8") 
                if len(message) > self.buffer_size:
                    print("メッセージが大きすぎます。")
                    continue
                self.client_socket.sendto(message, (self.server_ip, self.server_port))  # UDPでメッセージ送信
        finally:
            self.close()

    # メッセージ受信処理
    def receive_message(self):        
        while True:
            try:
                message, _ = self.client_socket.recvfrom(self.buffer_size)
                print(f"\n{message.decode('utf-8')}\nあなた: ", end="", flush=True)
            except Exception as e:
                print(f"受信中にエラーが発生しました: {e}")
                break

    # 受信処理と送信処理の開始
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
