#!/usr/bin/env python3
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, QSizePolicy
from autopilot_control import AutopilotControlPanel
from video_stream_widget import VideoStreamWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modular Drone Control UI")
        central_widget = QWidget()
        main_layout = QHBoxLayout()

        # Left panel: Video stream and RTSP address field
        left_panel = QVBoxLayout()
        self.rtsp_field = QLineEdit()
        self.rtsp_field.setPlaceholderText("Enter RTSP address")
        self.rtsp_set_button = QPushButton("Set RTSP Address")
        self.rtsp_set_button.clicked.connect(self.set_rtsp_address)
        rtsp_layout = QHBoxLayout()
        rtsp_layout.addWidget(self.rtsp_field)
        rtsp_layout.addWidget(self.rtsp_set_button)
        left_panel.addLayout(rtsp_layout)

        self.video_widget = VideoStreamWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_panel.addWidget(self.video_widget)

        # Right panel: Autopilot and drone controls
        right_panel = QVBoxLayout()
        self.autopilot_panel = AutopilotControlPanel()
        right_panel.addWidget(self.autopilot_panel)
        right_panel.addStretch()

        # Add both panels to the main layout
        main_layout.addLayout(left_panel, 3)  # left panel occupies more space
        main_layout.addLayout(right_panel, 1)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def set_rtsp_address(self):
        rtsp_address = self.rtsp_field.text()
        self.video_widget.set_rtsp_address(rtsp_address)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
