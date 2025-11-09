#!/usr/bin/env python3
import os
import sys
# ensure parent dir is on path so we can import map.map_widget
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import sys as _sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QLineEdit, QPushButton, QSizePolicy, QSplitter
)
from PyQt6.QtCore import Qt
from autopilot_control import AutopilotControlPanel
from video_stream_widget import VideoStreamWidget
from map_widget import MapWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modular Drone Control UI")
        
        # Use a QSplitter as the central widget's main layout mechanism
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left Panel Container ---
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0) # Tight layout

        self.rtsp_field = QLineEdit()
        self.rtsp_field.setPlaceholderText("Enter video source (RTSP URL or GStreamer pipeline)")
        self.rtsp_set_button = QPushButton("Set Video Source")
        self.rtsp_set_button.clicked.connect(self.set_video_source)
        rtsp_layout = QHBoxLayout()
        rtsp_layout.addWidget(self.rtsp_field)
        rtsp_layout.addWidget(self.rtsp_set_button)
        
        left_layout.addLayout(rtsp_layout)

        self.video_widget = VideoStreamWidget()
        # Use 'Ignored' instead of 'Ignoring' for compatibility
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        left_layout.addWidget(self.video_widget)

        # --- Right Panel Container ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0) # Tight layout

        self.map_widget = MapWidget()
        self.map_widget.setMinimumHeight(400) 
        right_layout.addWidget(self.map_widget)

        self.autopilot_panel = AutopilotControlPanel()
        right_layout.addWidget(self.autopilot_panel)

        # Connect signals
        self.autopilot_panel.drone_position_updated.connect(self.map_widget.update_drone_position)

        # Add containers to splitter
        self.splitter.addWidget(left_container)
        self.splitter.addWidget(right_container)

        # Set initial sizes for splitter (approx 3:1 ratio, favoring video)
        # Total width approx 1600, so maybe 1200 for video, 400 for side panel
        self.splitter.setSizes([1280, 420])
        
        # Prevent the video widget from completely collapsing
        self.splitter.setCollapsible(0, False)

        # Set specific stretch factors: index 0 (left) gets stretch 1, index 1 (right) gets stretch 0
        # This means when window is resized, mostly the left side (video) will grow.
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)

        self.setCentralWidget(self.splitter)

    def set_video_source(self):
        source = self.rtsp_field.text()
        self.video_widget.set_video_source(source)

    def closeEvent(self, event):
        print("Main window closing...")
        self.autopilot_panel.disconnect_autopilot()
        self.video_widget.close() 
        event.accept()

def main():
    app = QApplication(_sys.argv)
    window = MainWindow()
    # Set a generous default size
    window.resize(2480, 900)
    window.show()
    _sys.exit(app.exec())

if __name__ == "__main__":
    main()