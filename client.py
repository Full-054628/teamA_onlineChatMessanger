import socket
import threading
import sys
import json
import struct

class ChatClient:
    def __init__(self, server_ip="127.0.0.1", server_port=12345, tcp_port=12346, buffer_size=4096):
        self.server_ip = server_ip
        self.server_port = server_port
        self.tcp_port = tcp_port
        self.buffer_size = buffer_size
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = ""
        self.token = ""

    def prompt_and_connect(self):
        self.username = input("ユーザー名を入力してください: ")
        if not self.username or len(self.username.encode("utf-8")) > 255:
            print("ユーザー名が空、または長すぎます。")
            sys.exit()
        
        self.tcp_socket.connect((self.server_ip, self.tcp_port))
        
        operation = input("チャットルームを作成するには 'create'、参加するには 'join' と入力してください: ")
        room_name = input("チャットルーム名を入力してください: ")
        # ヘッダー情報を構築
        room_name_encoded = room_name.encode('utf-8')
        room_name_size = len(room_name_encoded)
        operation_payload = json.dumps({
            "operation": operation,
            "username": self.username,
            "room_name": room_name
        }).encode('utf-8')
        operation_payload_size = len(operation_payload)

        # ヘッダーの構築と送信
        header = struct.pack('!B B B 29s', room_name_size, 1 if operation == 'create' else 2, 0, operation_payload_size.to_bytes(29, 'big'))
        self.tcp_socket.sendall(header + room_name_encoded + operation_payload)
        
        # サーバーからの応答の受信
        response_header = self.tcp_socket.recv(32)
        if not response_header:
            print("サーバーからの応答がありません。")
            self.tcp_socket.close()
            sys.exit()
        
        # サーバーからの応答を解析
        room_name_size, operation, state, operation_payload_size_bytes = struct.unpack('!B B B 29s', response_header)
        operation_payload_size = int.from_bytes(operation_payload_size_bytes.strip(b'\x00'), 'big')

        response_room_name = self.tcp_socket.recv(room_name_size).decode('utf-8')
        response_payload = self.tcp_socket.recv(operation_payload_size).decode('utf-8')

        print(f"サーバーからの応答: Room Name: {response_room_name}, Operation: {operation}, State: {state}, Payload: {response_payload}")
        
        self.tcp_socket.close()

    def send_message(self):
        while True:
            msg = input("あなた: ")
            if msg == "quit":
                self.close()
                break
            message = {"token": self.token, "message": msg}
            self.udp_socket.sendto(json.dumps(message).encode('utf-8'), (self.server_ip, self.server_port))

    def receive_message(self):
        while True:
            try:
                message, _ = self.udp_socket.recvfrom(self.buffer_size)
                data = json.loads(message.decode('utf-8'))
                # 受信メッセージを表示し、改行を挿入
                print(f"\r{data['username']}: {data['message']}\nあなた: ", end="")
                sys.stdout.flush()
            except Exception as e:
                print(f"\r受信中にエラーが発生しました: {e}\nあなた: ", end="")
                sys.stdout.flush()

    def start(self):
        receiver_thread = threading.Thread(target=self.receive_message, daemon=True)
        receiver_thread.start()
        self.send_message()

    def close(self):
        self.udp_socket.close()
        print("\nソケットを閉じました。")
        sys.exit()

if __name__ == "__main__":
    client = ChatClient()
    client.prompt_and_connect()
    client.start()