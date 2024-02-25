import socket
import threading
import json
import struct
import hashlib
import os
import random
import string

class ChatServer:
    def __init__(self, host="0.0.0.0", tcp_port=12346, udp_port=12345):
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.clients = {}
        self.rooms = {}

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.host, self.udp_port))

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.tcp_socket.listen(5)

        print(f"チャットサーバーがTCP {self.tcp_port}番ポートとUDP {self.udp_port}番ポートで待機しています。")

    def listen_udp(self):
        while True:
            try:
                message, client_addr = self.udp_socket.recvfrom(4096)
                threading.Thread(target=self.handle_udp_message, args=(message, client_addr)).start()
            except Exception as e:
                print(f"UDP listen error: {e}")


    def handle_udp_message(self, message, client_addr):
        try:
            decoded_message = json.loads(message.decode("utf-8"))
            token = decoded_message.get("token")
            msg = decoded_message.get("message")

            # メッセージ受信のデバッグ情報を表示
            print(f"Received message from {client_addr}: {msg}")

            if token in self.clients:
                room_name, _ = self.clients[token]
                clients_to_relay = self.rooms[room_name]["clients"]

                # ルーム内の他の全クライアントにメッセージをリレー
                for client_token, (client_ip, client_udp_port) in clients_to_relay.items():
                    if client_token != token:  # メッセージ送信者を除外
                        # 正しいクライアントのアドレス情報を使用してメッセージをリレー
                        self.udp_socket.sendto(message, (client_ip, client_udp_port))
                        # メッセージリレーのデバッグ情報を表示
                        print(f"Relayed message to {client_ip}:{client_udp_port}")
            else:
                print("Invalid token received from:", client_addr)
        except Exception as e:
            print(f"Error handling UDP message: {e}")



    def listen_tcp(self):
        while True:
            client_socket, addr = self.tcp_socket.accept()
            threading.Thread(target=self.handle_tcp_connection, args=(client_socket, addr)).start()

    def handle_tcp_connection(self, client_socket, addr):
        try:
            data = client_socket.recv(1024)
            if data:
                response = self.process_request(data, addr)
                client_socket.sendall(response)
        except Exception as e:
            print(f"Error handling TCP connection: {e}")
        finally:
            client_socket.close()

    def process_request(self, data, addr):
        header_format = '>B B B I'
        header_size = struct.calcsize(header_format)
        room_name_length, operation, state, body_length = struct.unpack(header_format, data[:header_size])
        room_name = data[header_size:header_size+room_name_length].decode('utf-8')
        payload_raw = data[header_size+room_name_length:header_size+room_name_length+body_length]
        payload = json.loads(payload_raw.decode('utf-8'))
        
        udp_port = payload["udp_port"]  # UDPポート情報を取得
        
        if operation == 1:  # Create room
            return self.create_room(room_name, payload, addr, udp_port)
        elif operation == 2:  # Join room
            return self.join_room(room_name, payload, addr, udp_port)
        else:
            return json.dumps({"status": "error", "message": "Unknown operation"}).encode('utf-8')

    def create_room(self, room_name, payload, addr, udp_port):
        # ルーム作成処理、クライアント情報の保存
        token = self.generate_token()
        self.rooms[room_name] = {"password": self.hash_password(payload["password"]), "clients": {token: (addr[0], udp_port)}}
        self.clients[token] = (room_name, (addr[0], udp_port))
        return json.dumps({"status": "ok", "token": token}).encode('utf-8')

    def join_room(self, room_name, payload, addr, udp_port):
        # ルーム参加処理、クライアント情報の保存
        token = self.generate_token()
        self.rooms[room_name]["clients"][token] = (addr[0], udp_port)
        self.clients[token] = (room_name, (addr[0], udp_port))
        return json.dumps({"status": "ok", "token": token}).encode('utf-8')

    def hash_password(self, password):
        salt = os.urandom(32)
        pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return salt + pwdhash

    def verify_password(self, stored_password, provided_password):
        salt = stored_password[:32]
        stored_hash = stored_password[32:]
        pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return pwdhash == stored_hash

    def generate_token(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=26))

    def start(self):
        threading.Thread(target=self.listen_udp, daemon=True).start()
        self.listen_tcp()

    def run(self):
        print("Starting server...")
        self.start()

if __name__ == "__main__":
    server = ChatServer()
    server.run()