import socket
import sys
import threading

def receive_message(sock):
    """サーバーからのメッセージを受信して表示する関数"""
    while True:
        try:
            message, _ = sock.recvfrom(4096)  # 4096バイトまでのデータを受信
            print(f"\n{message.decode('utf-8')}\nあなた: ", end='', flush=True)
        except OSError:
            break  # ソケットが閉じられた場合、受信を終了

# サーバーの設定
SERVER_IP = "127.0.0.1"  # サーバーのIPアドレスを指定 ローカルホストでテストする場合の設定
SERVER_PORT = 9090       # 使用するサーバーのポート番号

# UDPクライアントソケットの作成
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # IPv4とUDPを使用するソケットを作成。

# ユーザー名の入力処理
username = input("ユーザー名を入力してください: ").strip()  # ユーザー名の入力
if len(username.encode('utf-8')) > 255:
    # ユーザー名が255バイトを超える場合はエラーを出力し、プログラムを終了
    print("ユーザー名は255バイト以下である必要があります。")
    client_socket.close()  
    sys.exit()  # プログラムを終了

# 受信スレッドの開始
recv_thread = threading.Thread(target=receive_message, args=(client_socket,))
recv_thread.daemon = True  # メインスレッドが終了したら受信スレッドも終了するように設定
recv_thread.start()

try:
    while True:
        # ユーザーにメッセージの入力を求める
        msg = input("あなた: ")
        if msg:
            # ユーザー名とメッセージを組み合わせ、エンコードしてサーバに送信
            data = f"{username}: {msg}"
            client_socket.sendto(data.encode('utf-8'), (SERVER_IP, SERVER_PORT))
except KeyboardInterrupt:
    # ユーザーがCtrl+Cを押した場合、チャットを終了するメッセージを表示
    print("\nチャットを終了します...")
finally:
    # 最終的にソケットを閉じてリソースを解放します。
    client_socket.close()
    sys.exit()


