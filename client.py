import socket
import threading
import sys

# サーバの設定
SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345
BUFFER_SIZE = 4096

# UDPクライアントソケットの作成
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_message(username):
    try:
        while True:  # 無限ループ
            msg = input("あなた: ")
            if msg == "quit":
                break  # ユーザーが 'quit' を入力したら終了
            # メッセージの構成: "ユーザー名: メッセージ内容"
            message = f"{username}: {msg}".encode('utf-8')
            if len(message) > BUFFER_SIZE:
                print("メッセージが大きすぎます。")
                continue
            client_socket.sendto(message, (SERVER_IP, SERVER_PORT))
    finally:
        client_socket.close()
        print("ソケットを閉じました。")
        sys.exit()

def receive_message():
    while True:
        try:
            message, _ = client_socket.recvfrom(BUFFER_SIZE)
            print(f"\n{message.decode('utf-8')}\nあなた: ", end='', flush=True)
        except Exception as e:
            print(f"受信中にエラーが発生しました: {e}")
            break

# ユーザー名の入力とバリデーションチェクう
username = input("ユーザー名を入力してください: ")
username_bytes = username.encode('utf-8')

if not username or len(username_bytes) > 255:
    error_message = "ユーザー名が空です。" if not username else "ユーザー名は255バイト以下である必要があります。"
    print(error_message)
    client_socket.close()
    sys.exit()

# メッセージ受信スレッドの開始
recv_thread = threading.Thread(target=receive_message)
recv_thread.daemon = True
recv_thread.start()

# メッセージ送信処理の開始
send_message(username)
