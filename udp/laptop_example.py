# laptop_udp.py
import socket
import json
import time
import random

RASPBERRY_IP = "127.0.0.1"  # ← Change to your Pi IP
SEND_PORT = 5006
RECEIVE_PORT = 5005

send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind(("", RECEIVE_PORT))
recv_sock.settimeout(0.5)

def generate_random_control():
    return {
        "id": random.randint(100, 200),
        "data": random.choice(["zoom in", "zoom out", "focus", "scan"]),
        "camera_mode": random.choice([0, 1, 2]),
        "tracking_mode": random.choice([0, 1])
    }

def send_control():
    packet = generate_random_control()
    msg = json.dumps(packet).encode('utf-8')
    send_sock.sendto(msg, (RASPBERRY_IP, SEND_PORT))
    print(f"[Laptop] Sent: {packet}")

def receive_objects():
    try:
        data, _ = recv_sock.recvfrom(2048)
        objects = json.loads(data.decode('utf-8'))
        print(f"[Laptop] Received: {objects}")
    except socket.timeout:
        pass

if __name__ == "__main__":
    while True:
        receive_objects()
        send_control()
        time.sleep(1)  # 1 Hz
