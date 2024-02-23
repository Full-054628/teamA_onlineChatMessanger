import socket  # Pythonでネットワーク接続を扱うための標準ライブラリ
import threading  # 複数のスレッドを同時に実行するために使用する（サーバが同時に複数クライアントからのメッセージを処理できるようになる）
import time
import sys


class UDPServer:
    # クラスレベルで定数を定義
    SERVER_IP = "0.0.0.0"
    SERVER_PORT = 12345
    BUFFER_SIZE = 4096
    INACTIVITY_TIMEOUT = 30  # クライアントのタイムアウト時間（秒）
    ROOM_NAME_SIZE = 1  # ルーム名のサイズを1バイトに設定
    TOKEN_SIZE = 1  # トークンのサイズを1バイトに設定

    def __init__(
        self, ip="0.0.0.0", port=12345, buffer_size=4096, inactivity_timeout=30
    ):
        # サーバーの初期設定
        self.server_ip = ip
        self.server_port = port
        self.buffer_size = buffer_size
        self.inactivity_timeout = (
            inactivity_timeout  # クライアントのタイムアウト時間（秒）
        )
        self.clients = (
            {}
        )  # クライアントのリストと最終アクティブ時間を追跡するための辞書
        self.server_socket = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM
        )  # AF_INETはIPv4ベースのアドレスを使用。SOCK_DGRAMはUDPプロトコル。
        self.server_socket.bind(
            (self.server_ip, self.server_port)
        )  # 作成したソケットを、指定したIPアドレスとポートにバインド
        print(f"サーバーが起動しました。{self.server_ip}:{self.server_port}")

    def relay_message(self, message, sender_address):
        # クライアントから受け取ったメッセージを、送信もとアドレス以外の全クライアントに転送
        for client in list(self.clients.keys()):
            if client != sender_address:
                try:
                    self.server_socket.sendto(message, client)
                except Exception as e:
                    print(f"メッセージの転送中にエラーが発生しました: {e}")

    def validate_token_and_ip(self, token, client_address):
        # # トークンとIPアドレスの検証ロジックを実装
        # return token == client_address[0]

        # テスト用: ダミートークンのリスト
        dummy_tokens = [
            # "dummytoken1234567890abcdefg",
            # "dummytoken1234567890abcdefg",
            # "dummytoken1234567890abcdefg",
            "b",
            "c",
            "d",
        ]
        # トークンがダミートークンのリストに含まれているかチェック
        return token.decode("utf-8") in dummy_tokens

    def handle_client(self):
        # クライアントからのメッセージを受信し、リレーする
        while True:
            try:
                message, client_address = self.server_socket.recvfrom(self.buffer_size)
                # メッセージの長さをチェック
                if len(message) < UDPServer.ROOM_NAME_SIZE + UDPServer.TOKEN_SIZE:
                    print(f"不正なメッセージフォーマット: {client_address}")
                    continue  # 次のメッセージの処理に移る

                # メッセージからルーム名とトークンを抽出
                room_name = message[: UDPServer.ROOM_NAME_SIZE]
                token = message[
                    UDPServer.ROOM_NAME_SIZE : UDPServer.ROOM_NAME_SIZE
                    + UDPServer.TOKEN_SIZE
                ]

                # トークンとIPアドレスの検証
                if self.validate_token_and_ip(token, client_address):
                    self.clients[client_address] = (
                        time.time()
                    )  # クライアントのアドレスと最終アクティブ時間を記録
                    self.relay_message(message, client_address)
                else:
                    print(f"無効なトークンまたはIPアドレス: {client_address}")
            except Exception as e:
                print(f"クライアントからのメッセージ受信中にエラーが発生しました: {e}")
                break

    def cleanup_inactive_clients(self):
        # 非アクティブクライアントを定期的に削除する
        while True:
            try:
                current_time = time.time()
                inactive_clients = [
                    client
                    for client, last_seen in self.clients.items()
                    if current_time - last_seen > self.inactivity_timeout
                ]

                for client in inactive_clients:
                    # クライアントに通知メッセージを送信
                    notification_message = "規定の時間操作がなかったため、一時的にリストから削除されました。リストから削除されている間にルームで交わされたメッセージは確認できませんが、再度メッセージを送信することでいつでもルームに再参加できます。お待ちしています！".encode(
                        "utf-8"
                    )
                    self.server_socket.sendto(notification_message, client)
                    print(f"非アクティブクライアント {client} を削除しました。")
                    del self.clients[client]
            except Exception as e:
                print(
                    f"非アクティブクライアントのクリーンアップ中にエラーが発生しました: {e}"
                )
            finally:
                time.sleep(self.inactivity_timeout)

    def start(self):
        # サーバーのメインループを開始
        threading.Thread(target=self.handle_client).start()
        threading.Thread(
            target=self.cleanup_inactive_clients, daemon=True
        ).start()  # デーモンスレッド。サーバーが終了するときに自動終了する

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nサーバーを終了します...")
        finally:
            self.server_socket.close()
            print("サーバーソケットをクローズしました。")
            sys.exit(0)


if __name__ == "__main__":
    udp_server = UDPServer()
    udp_server.start()
