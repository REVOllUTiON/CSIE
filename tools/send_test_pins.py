#!/usr/bin/env python3
import socket
import json
import time
import random
import argparse

lat_f = -35.3632
lon_f = 149.1652

def make_single_pin():
    lat = lat_f + random.uniform(-0.1, 0.1)
    lon = lon_f + random.uniform(-0.1, 0.1)
    return {"lat": round(lat, 6), "lon": round(lon, 6), "name": "test_pin"}

def make_multiple_pins():
    pins = []
    for i in range(3):
        lat = lat_f + random.uniform(-0.1, 0.1)
        lon = lon_f + random.uniform(-0.1, 0.1)
        pins.append([round(lat,6), round(lon,6), f"pin_{i}"])
    return {"pins": pins}

def make_list_of_lists():
    pins = []
    for i in range(2):
        lat = lat_f + random.uniform(-0.1, 0.1)
        lon = lon_f + random.uniform(-0.1, 0.1)
        pins.append([round(lat,6), round(lon,6), f"lot_{i}"])
    return pins  # top-level list

def send_udp(sock, addr, payload):
    b = json.dumps(payload).encode("utf-8")
    sock.sendto(b, addr)
    print("sent:", payload)

def main():
    p = argparse.ArgumentParser(description="Send test pin coordinates via UDP every 5s")
    p.add_argument("--host", default="127.0.0.1", help="Target host (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=6007, help="Target UDP port (default 6007)")
    args = p.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = (args.host, args.port)

    try:
        i = 0
        while True:
            mode = i % 3
            if mode == 0:
                send_udp(sock, addr, make_single_pin())
            elif mode == 1:
                send_udp(sock, addr, make_multiple_pins())
            else:
                send_udp(sock, addr, make_list_of_lists())
            i += 1
            time.sleep(5)
    except KeyboardInterrupt:
        print("stopped by user")
    finally:
        sock.close()

if __name__ == "__main__":
    main()