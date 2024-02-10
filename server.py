import select
import socket
import time

# サーバー設定
SERVER_IP = "0.0.0.0"
SERVER_PORT = 9090
BUFFER_SIZE = 4096
MAX_MESSAGE_LENGTH = 1024  # メッセージの最大長
RATE_LIMIT_PERIOD = 1  # レート制限を適用する期間（秒）
MAX_MESSAGES_PER_PERIOD = 5  # 許容される最大メッセージ数（期間あたり）

# クライアント情報を追跡するための辞書
# 各クライアントのアドレスをキーとし、タプル（最後のアクティビティ時刻, その期間内のメッセージ送信回数）を値として持つ
clients = {}

# クライアントからのメッセージを処理する関数
def handle_message(message, client_address):
    # 現在時刻を取得
    current_time = time.time()
    # クライアントのレート制限情報を取得（存在しない場合はデフォルト値を設定）
    last_time, count = clients.get(client_address, (0, 0))
    
    # レート制限のチェック
    # 前回のメッセージ送信からの経過時間がRATE_LIMIT_PERIOD内であればカウントアップし、制限を超えていたらメッセージを拒否
    if current_time - last_time < RATE_LIMIT_PERIOD:
        if count >= MAX_MESSAGES_PER_PERIOD:
            print(f"Rate limit exceeded for {client_address}")
            return  # このメッセージは処理しない
        else:
            count += 1
    else:
        count = 1  # 期間が過ぎたらカウントをリセット
    
    # クライアントの情報を更新
    clients[client_address] = (current_time, count)

    # メッセージ長のチェック
    # 受信したメッセージの長さが設定した最大値を超えている場合は処理を中止し、警告を出力
    if len(message) > MAX_MESSAGE_LENGTH:
        print(f"Message from {client_address} is too long")
        return
    
    try:
        # メッセージのデコードと検証
        # 形式が不正な場合はエラーを出力し、処理を中止
        decoded_message = message.decode('utf-8')
        if ':' not in decoded_message: # 想定されたメッセージ形式かのエラーハンドリング
            raise ValueError("Invalid message format")
        username, message_body = decoded_message.split(':', 1)
        username = username.strip()
        message_body = message_body.strip()
        print(f"User {username} says: {message_body}")

        # 受信したメッセージを他の全クライアントにリレー
        for client in clients.keys():
            if client != client_address:  # メッセージの送信元には送り返さない
                server_socket.sendto(message, client)
    except (UnicodeDecodeError, ValueError) as e:
        print(f"Error processing message from {client_address}: {e}")

# UDPソケットの初期化
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # IPv4とUDPを使用
server_socket.bind((SERVER_IP, SERVER_PORT))
server_socket.setblocking(0)

print(f"サーバーが起動しました。{SERVER_IP}:{SERVER_PORT} で待機中...")

try:
    while True:
        read_sockets, _, exception_sockets = select.select([server_socket], [], [server_socket], 1)
        for notified_socket in read_sockets:
            message, client_address = notified_socket.recvfrom(BUFFER_SIZE)
            handle_message(message, client_address)
except KeyboardInterrupt:
    print("サーバーを終了します...")
finally:
    server_socket.close()
