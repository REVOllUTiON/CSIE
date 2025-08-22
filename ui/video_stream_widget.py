#!/usr/bin/env python3
import random
import socket
import json
import threading
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QGraphicsView, QSizePolicy, QGraphicsScene
from PyQt6.QtCore import QTimer, QRectF
from PyQt6.QtGui import QBrush, QColor

from bounding_box_item import BoundingBoxItem

class VideoStreamWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Create scene and set default background color
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setSceneRect(0, 0, 640, 480)
        self.setBackgroundBrush(QBrush(QColor("black")))
        
        self.current_bbox_id = 0
        self.bbox_items = {}

        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rpi_ip = "127.0.0.1"  # ← Set your Pi IP
        self.rpi_port = 5005           # ← RPi receiving port
        self.rpi_port_s = 5006          # ← RPi sending port
        self.start_udp_listener()

    def set_rtsp_address(self, rtsp_address):
        # Here you would add code to open the RTSP stream using GStreamer or similar.
        print(f"RTSP Address set to: {rtsp_address}")
        # For simulation, we just clear and reset the scene background.
        self.scene.clear()
        self.setBackgroundBrush(QBrush(QColor("darkGray")))

    def update_bounding_boxes(self, object_list):
        # Clear old bounding boxes
        for item in self.bbox_items.values():
            self.scene.removeItem(item)
        self.bbox_items.clear()

        # Draw new ones
        for obj in object_list:
            try:
                x = float(obj["x"])
                y = float(obj["y"])
                size = float(obj["size"])
                label = obj.get("label", "")
                obj_id = obj.get("id", self.current_bbox_id)
                rect = QRectF(x, y, size, size)
                bbox = BoundingBoxItem(obj, rect, on_click_callback=self.send_control_packet)


                self.scene.addItem(bbox)
                self.bbox_items[obj_id] = bbox
                self.current_bbox_id += 1
            except Exception as e:
                print(f"[UI] Error parsing object: {e}")

    def start_udp_listener(self):
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind(("", self.rpi_port))
        self.udp_sock.setblocking(False)  # non-blocking socket
        print(f"[UI] Listening for UDP on port {self.rpi_port}")

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_udp_socket)
        self.poll_timer.start(100)  # check every 100ms

    def poll_udp_socket(self):
        try:
            while True:
                data, _ = self.udp_sock.recvfrom(2048)
                payload = json.loads(data.decode('utf-8'))
                if "objects" in payload:
                    self.update_bounding_boxes(payload["objects"])
        except BlockingIOError:
            pass  # No data available
        except Exception as e:
            print(f"[UI] UDP error: {e}")
    def remove_bbox(self, bbox_item):
        # Remove the bounding box if it's still present in the scene
        if bbox_item.scene() is not None:
            self.scene.removeItem(bbox_item)
            print(f"Removed BoundingBox ID {bbox_item.bbox_id}")
    
    def send_control_packet(self, metadata):
        packet = {
            "id": metadata.get("id", -1),
            "data": metadata.get("data", "selected"),
            "camera_mode": 1,       # ← You can wire this from UI later
            "tracking_mode": 1      # ← Set from state or default
        }
        try:
            msg = json.dumps(packet).encode('utf-8')
            self.send_sock.sendto(msg, (self.rpi_ip, self.rpi_port_s))
            print(f"[UI] Sent control: {packet}")
        except Exception as e:
            print(f"[UI] Error sending control: {e}")
