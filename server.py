import socket #Pythonでネットワーク接続を扱うための標準ライブラリ
import threading #複数のスレッドを同時に実行するために使用する（サーバが同時に複数クライアントからのメッセージを処理できるようになる）
import time
import sys

# サーバの設定
SERVER_IP = '0.0.0.0'
SERVER_PORT = 12345
BUFFER_SIZE = 4096
INACTIVITY_TIMEOUT = 30  # クライアントのタイムアウト時間（秒）

# クライアントのリストと最終アクティブ時間を追跡するための辞書
clients = {}

# UDPソケットの作成
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # AF_INETはIPv4ベースのアドレスを使用。SOCK_DGRAMはUDPプロトコル。
server_socket.bind((SERVER_IP, SERVER_PORT)) # 作成したソケットを、指定したIPアドレスとポートにバインド

# クライアントから受け取ったメッセージを、送信もとアドレス以外の全クライアントに転送
def relay_message(message, sender_address):
    for client in list(clients.keys()):
        if client != sender_address:
            try:
                server_socket.sendto(message, client)
            except Exception as e:
                print(f"メッセージの転送中にエラーが発生しました: {e}")

# クライアントからのメッセージを受信し、リレーする
def handle_client():
    while True:
        try:
            message, client_address = server_socket.recvfrom(BUFFER_SIZE)
            # クライアントのアドレスと最終アクティブ時間を記録
            clients[client_address] = time.time()
            relay_message(message, client_address)
        except Exception as e:
            print(f"クライアントからのメッセージ受信中にエラーが発生しました: {e}")
            break

# 非アクティブクライアントを削除する
def cleanup_inactive_clients():
    while True:
        try:
            current_time = time.time()
            inactive_clients = [client for client, last_seen in clients.items() if current_time - last_seen > INACTIVITY_TIMEOUT]
            
            for client in inactive_clients:
                print(f"非アクティブクライアント {client} を削除しました。")
                del clients[client]
        except Exception as e:
            print(f"非アクティブクライアントのクリーンアップ中にエラーが発生しました: {e}")
        finally:
            time.sleep(INACTIVITY_TIMEOUT)

def main():
    threading.Thread(target=handle_client).start()
    threading.Thread(target=cleanup_inactive_clients, daemon=True).start() # デーモンスレッド。サーバーが終了するときに自動終了する
    print(f"サーバーが起動しました。{SERVER_IP}:{SERVER_PORT}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nサーバーを終了します...")
    finally:
        server_socket.close()
        print("サーバーソケットをクローズしました。")
        sys.exit(0)

if __name__ == "__main__":
    main()