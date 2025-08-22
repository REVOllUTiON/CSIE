#!/usr/bin/env python3
import random
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import QTimer

class AutopilotControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout()

        # Autopilot connection group
        connection_group = QGroupBox("Autopilot Connection")
        conn_layout = QFormLayout()
        self.autopilot_path_field = QLineEdit()
        conn_layout.addRow("Autopilot Path:", self.autopilot_path_field)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_autopilot)
        conn_layout.addRow(self.connect_button)
        connection_group.setLayout(conn_layout)
        main_layout.addWidget(connection_group)

        # Drone commands group
        commands_group = QGroupBox("Drone Commands")
        cmd_layout = QHBoxLayout()
        self.arm_button = QPushButton("Arm")
        self.arm_button.clicked.connect(self.send_arm)
        self.disarm_button = QPushButton("Disarm")
        self.disarm_button.clicked.connect(self.send_disarm)
        cmd_layout.addWidget(self.arm_button)
        cmd_layout.addWidget(self.disarm_button)
        commands_group.setLayout(cmd_layout)
        main_layout.addWidget(commands_group)

        # Mode change buttons
        mode_group = QGroupBox("Change Mode")
        mode_layout = QHBoxLayout()
        self.mode_buttons = {}
        for mode in ["Loiter", "Auto", "RTL", "Guided"]:
            btn = QPushButton(mode)
            btn.clicked.connect(lambda checked, m=mode: self.send_mode(m))
            self.mode_buttons[mode] = btn
            mode_layout.addWidget(btn)
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)

        # Drone information display
        info_group = QGroupBox("Drone Information")
        info_layout = QFormLayout()
        self.position_label = QLabel("N/A")
        self.speed_label = QLabel("N/A")
        self.battery_label = QLabel("N/A")
        self.current_mode_label = QLabel("N/A")
        info_layout.addRow("Position:", self.position_label)
        info_layout.addRow("Speed:", self.speed_label)
        info_layout.addRow("Battery:", self.battery_label)
        info_layout.addRow("Current Mode:", self.current_mode_label)
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        self.camera_mode_button = QPushButton("Change Camera Mode")
        self.camera_mode_button.clicked.connect(self.change_camera_mode)
        main_layout.addWidget(self.camera_mode_button)

        main_layout.addStretch()
        self.setLayout(main_layout)

        # Timer to simulate updating drone information
        self.info_timer = QTimer(self)
        self.info_timer.timeout.connect(self.simulate_drone_info)
        self.info_timer.start(2000)  # update every 2 seconds

    def connect_autopilot(self):
        autopilot_path = self.autopilot_path_field.text()
        # Here you would add code to start the MAVProxy/pymavlink connection using the provided path.
        print(f"Connecting to autopilot using path: {autopilot_path}")
        # For simulation, we assume connection is successful.
        self.current_mode_label.setText("Connected")

    def send_arm(self):
        print("Sending ARM command")
        # Add code to send arm command via pymavlink
        self.current_mode_label.setText("Armed")

    def send_disarm(self):
        print("Sending DISARM command")
        # Add code to send disarm command via pymavlink
        self.current_mode_label.setText("Disarmed")

    def send_mode(self, mode):
        print(f"Changing mode to {mode}")
        # Add code to send mode change command via pymavlink
        self.current_mode_label.setText(mode)

    def change_camera_mode(self):
        print("Camera mode changed (Simulation)")  
        
    def simulate_drone_info(self):
        # Simulate updating drone information (position, speed, battery, etc.)
        pos_x = random.uniform(-100, 100)
        pos_y = random.uniform(-100, 100)
        speed = random.uniform(0, 20)
        battery = random.randint(20, 100)
        self.position_label.setText(f"({pos_x:.1f}, {pos_y:.1f})")
        self.speed_label.setText(f"{speed:.1f} m/s")
        self.battery_label.setText(f"{battery}%")
