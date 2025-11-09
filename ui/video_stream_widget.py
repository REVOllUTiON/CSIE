#!/usr/bin/env python3
import socket
import json
import sys
import numpy as np
import cv2
from PyQt6.QtCore import QTimer, QRectF, Qt, QThread, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, 
    QGraphicsScene, QSizePolicy, QLineEdit, QPushButton, QLabel, QGraphicsPixmapItem,
    QDoubleSpinBox, QFrame, QGroupBox
)
from PyQt6.QtGui import QBrush, QColor, QPainter, QImage, QPixmap, QResizeEvent

from bounding_box_item import BoundingBoxItem

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self, pipeline):
        super().__init__()
        self.pipeline = pipeline
        self._is_running = True

    def run(self):
        print(f"[VideoThread] Opening pipeline: {self.pipeline}")
        cap = cv2.VideoCapture(self.pipeline, cv2.CAP_GSTREAMER)
        if not cap.isOpened():
            print("[VideoThread] Error: Could not open GStreamer pipeline.")
            return
        while self._is_running:
            ret, cv_img = cap.read()
            if ret: self.change_pixmap_signal.emit(cv_img)
            else: self.msleep(1000)
        cap.release()
        print("[VideoThread] Stopped.")

    def stop(self):
        self._is_running = False
        self.wait()

class ResizingGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if self.scene():
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

class GimbalAxisControl(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, name, min_val, max_val, initial_val=0.0, step=1.0, parent=None):
        super().__init__(parent)
        self.value = initial_val; self.min_val = min_val; self.max_val = max_val
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2) # Tight margins

        top_layout = QHBoxLayout()
        self.name_label = QLabel(f"<b>{name}</b>")
        self.value_label = QLabel(f"{self.value:.1f}")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_layout.addWidget(self.name_label)
        top_layout.addStretch()
        top_layout.addWidget(self.value_label)
        layout.addLayout(top_layout)

        control_layout = QHBoxLayout()
        self.minus_btn = QPushButton("-")
        self.minus_btn.setFixedWidth(25)
        self.minus_btn.clicked.connect(self.decrease_value)
        self.plus_btn = QPushButton("+")
        self.plus_btn.setFixedWidth(25)
        self.plus_btn.clicked.connect(self.increase_value)
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.1, 90.0); self.step_spin.setValue(step); self.step_spin.setSingleStep(0.5); self.step_spin.setDecimals(1)
        # Hide spinbox buttons to save space if desired, or keep them small
        self.step_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons) 
        self.step_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)

        control_layout.addWidget(self.minus_btn)
        control_layout.addWidget(self.step_spin)
        control_layout.addWidget(self.plus_btn)
        layout.addLayout(control_layout)

    def increase_value(self):
        self.value = min(self.max_val, self.value + self.step_spin.value())
        self.update_display(); self.valueChanged.emit(self.value)
    def decrease_value(self):
        self.value = max(self.min_val, self.value - self.step_spin.value())
        self.update_display(); self.valueChanged.emit(self.value)
    def update_display(self): self.value_label.setText(f"{self.value:.1f}")
    def get_value(self): return self.value

class VideoStreamWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Control Bar
        control_layout = QHBoxLayout()
        self.rpi_ip_input = QLineEdit()
        self.rpi_ip_input.setPlaceholderText("Enter Raspberry Pi IP")
        self.rpi_ip_input.setText("192.168.0.195")
        self.set_ip_button = QPushButton("Set RPi IP")
        self.set_ip_button.clicked.connect(self.update_rpi_ip)
        control_layout.addWidget(QLabel("RPi IP:"))
        control_layout.addWidget(self.rpi_ip_input)
        control_layout.addWidget(self.set_ip_button)
        main_layout.addLayout(control_layout)

        # Graphics View
        self.scene = QGraphicsScene(self)
        self.VIDEO_WIDTH = 1920; self.VIDEO_HEIGHT = 1080
        self.scene.setSceneRect(0, 0, self.VIDEO_WIDTH, self.VIDEO_HEIGHT)
        self.view = ResizingGraphicsView(self.scene, self)
        self.view.setBackgroundBrush(QBrush(QColor("black")))
        self.view.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.view.setMinimumSize(640, 360)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        main_layout.addWidget(self.view)

        # Video Item
        self.video_pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.video_pixmap_item)
        self.video_pixmap_item.setZValue(0)

        # --- Gimbal Control Section ---
        gimbal_group = QGroupBox("Gimbal Control")
        # Make it compact vertically
        gimbal_group.setMaximumHeight(100) 
        gimbal_layout = QHBoxLayout()
        gimbal_layout.setContentsMargins(5, 5, 5, 5)

        self.roll_ctrl = GimbalAxisControl("Roll", -180, 180, initial_val=0, step=5.0)
        self.pitch_ctrl = GimbalAxisControl("Pitch", -90, 90, initial_val=0, step=5.0)
        self.yaw_ctrl = GimbalAxisControl("Yaw", -180, 180, initial_val=0, step=5.0)
        self.zoom_ctrl = GimbalAxisControl("Zoom", 1.0, 30.0, initial_val=1.0, step=1.0)

        for ctrl in [self.roll_ctrl, self.pitch_ctrl, self.yaw_ctrl, self.zoom_ctrl]:
            ctrl.valueChanged.connect(lambda _: self.send_gimbal_command())
            gimbal_layout.addWidget(ctrl)
            # Add separators between controls
            if ctrl != self.zoom_ctrl:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.VLine)
                line.setFrameShadow(QFrame.Shadow.Sunken)
                gimbal_layout.addWidget(line)

        gimbal_group.setLayout(gimbal_layout)
        main_layout.addWidget(gimbal_group)

        self.current_bbox_id = 0
        self.bbox_items = {}
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.gimbal_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rpi_ip = self.rpi_ip_input.text()
        self.rpi_port = 5005; self.rpi_port_s = 5006; self.gimbal_port = 6010
        self.start_udp_listener()
        self.video_thread = None

    def send_gimbal_command(self):
        cmd_str = f"{self.roll_ctrl.get_value():.1f}, {self.pitch_ctrl.get_value():.1f}, {self.yaw_ctrl.get_value():.1f}, {self.zoom_ctrl.get_value():.1f}"
        try:
            print(f"[Gimbal] Sending to {self.rpi_ip}:{self.gimbal_port} -> {cmd_str}")
            self.gimbal_sock.sendto(cmd_str.encode('utf-8'), (self.rpi_ip, self.gimbal_port))
        except Exception as e: print(f"[Gimbal] Error: {e}")

    def update_rpi_ip(self):
        new_ip = self.rpi_ip_input.text()
        if new_ip:
            self.rpi_ip = new_ip
            print(f"[UI] Raspberry Pi IP updated to: {self.rpi_ip}")

    def set_video_source(self, source=""):
        if self.video_thread and self.video_thread.isRunning(): self.video_thread.stop()
        if not source.strip():
            source = ('udpsrc port=5000 caps="application/x-rtp, media=video, encoding-name=H264, clock-rate=90000, payload=96" ! rtph264depay ! avdec_h264 ! videoconvert ! video/x-raw, format=BGR ! appsink drop=1')
        self.video_thread = VideoThread(source)
        self.video_thread.change_pixmap_signal.connect(self.update_video_frame)
        self.video_thread.start()

    @pyqtSlot(np.ndarray)
    def update_video_frame(self, cv_img):
        try:
            cv_img = np.ascontiguousarray(cv_img)
            rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.video_pixmap_item.setPixmap(QPixmap.fromImage(qt_image))
        except Exception as e: print(f"[UI] Error updating video frame: {e}")

    def update_bounding_boxes(self, object_list):
        for item in self.bbox_items.values():
            if item.scene(): self.scene.removeItem(item)
        self.bbox_items.clear()
        for arr in object_list:
            try:
                x_min, y_min, x_max, y_max, conf, obj_id = arr
                rect = QRectF(x_min, y_min, x_max - x_min, y_max - y_min)
                obj_dict = {"id": obj_id, "label": f"obj_{obj_id}", "data": f"Conf: {conf:.2f}"}
                bbox = BoundingBoxItem(obj_dict, rect, on_click_callback=self.send_control_packet)
                bbox.setZValue(1); self.scene.addItem(bbox); self.bbox_items[obj_id] = bbox
            except: pass

    def start_udp_listener(self):
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: self.udp_sock.bind(("0.0.0.0", self.rpi_port))
        except: return
        self.udp_sock.setblocking(False)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_udp_socket)
        self.poll_timer.start(100)

    def poll_udp_socket(self):
        try:
            while True:
                data, _ = self.udp_sock.recvfrom(4096)
                payload = json.loads(data.decode('utf-8'))
                if "objects" in payload: self.update_bounding_boxes(payload["objects"])
        except: pass
    
    def send_control_packet(self, metadata):
        packet = {"id": metadata.get("id", -1), "camera_mode": 1, "tracking_mode": 1}
        try: self.send_sock.sendto(json.dumps(packet).encode('utf-8'), (self.rpi_ip, self.rpi_port_s))
        except: pass
    
    def closeEvent(self, event):
        if self.video_thread: self.video_thread.stop()
        super().closeEvent(event)