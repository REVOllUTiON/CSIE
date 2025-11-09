# raspberry_pi_udp.py
import socket
import json
import time
import random

LAPTOP_IP = "127.0.0.1"  # ← Change to your laptop IP
SEND_PORT = 5005
RECEIVE_PORT = 5006

send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind(("", RECEIVE_PORT))
recv_sock.settimeout(0.5)

labels = ["car", "person", "bicycle", "dog", "tree"]

def generate_random_objects():
    objects = []
    for i in range(random.randint(1, 4)):
        obj = {
            "x": random.randint(0, 640),
            "y": random.randint(0, 480),
            "size": random.randint(10, 100),
            "label": random.choice(labels),
            "id": i + 1,
            "data": random.choice(["moving", "static", "lost"])
        }
        objects.append(obj)
    return {"objects": objects}

def send_objects():
    packet = generate_random_objects()
    msg = json.dumps(packet).encode('utf-8')
    send_sock.sendto(msg, (LAPTOP_IP, SEND_PORT))
    print(f"[Raspberry Pi] Sent: {packet}")

def receive_control():
    try:
        data, _ = recv_sock.recvfrom(2048)
        command = json.loads(data.decode('utf-8'))
        print(f"[Raspberry Pi] Received control: {command}")
    except socket.timeout:
        pass

if __name__ == "__main__":
    while True:
        send_objects()
        receive_control()
        time.sleep(1)  # 1 Hz
