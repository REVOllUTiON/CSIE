#!/usr/bin/env python3
import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from pymavlink import mavutil


# Worker class to handle MAVLink communication in a separate thread
class MavlinkConnectionWorker(QObject):
    """
    Handles MAVLink communication in a non-blocking way.
    Runs in a separate QThread.
    """
    # Signal emits a dictionary with drone telemetry data
    drone_data_updated = pyqtSignal(dict)
    # Signal emits connection status updates
    connection_status = pyqtSignal(str)
    # Signal to tell the thread to finish
    finished = pyqtSignal()

    def __init__(self, connection_string, parent=None):
        super().__init__(parent)
        self.connection_string = connection_string
        self.running = False
        self.mavlink_connection = None

    def connect_and_run(self):
        """
        Connects to the MAVLink device and starts the message loop.
        This runs in the QThread.
        """
        if not mavutil:
            self.connection_status.emit("Error: pymavlink not found")
            self.finished.emit()
            return

        try:
            print(f"[Mavlink] Attempting to connect to {self.connection_string}")
            # Establish connection
            self.mavlink_connection = mavutil.mavlink_connection(self.connection_string, autoreconnect=True, baud=57600)
            self.mavlink_connection.wait_heartbeat()
            print(f"[Mavlink] Heartbeat received! System {self.mavlink_connection.target_system} Component {self.mavlink_connection.target_component}")
            self.connection_status.emit(f"Connected to SYSID {self.mavlink_connection.target_system}")
            self.running = True
        except Exception as e:
            print(f"[Mavlink] Connection error: {e}")
            self.connection_status.emit(f"Connection Failed: {e}")
            self.finished.emit()
            return

        # Request necessary data streams from the autopilot
        self.request_data_streams()

        telemetry_data = {
            'lat': 0.0,
            'lon': 0.0,
            'alt': 0.0,
            'speed': 0.0,
            'battery_v': 0.0,
            'battery_remaining': 0,
            'mode': 'Unknown',
            'armed': False
        }

        # Main loop to receive messages
        while self.running:
            try:
                # Wait for a message, blocking for up to 1 second
                msg = self.mavlink_connection.recv_match(
                    type=['GLOBAL_POSITION_INT', 'VFR_HUD', 'HEARTBEAT', 'SYS_STATUS'],
                    blocking=True,
                    timeout=1.0 
                )
                if not msg:
                    # Timeout occurred, loop again to check self.running
                    continue

                msg_type = msg.get_type()

                # Parse known message types
                if msg_type == 'GLOBAL_POSITION_INT':
                    telemetry_data['lat'] = msg.lat / 1e7
                    telemetry_data['lon'] = msg.lon / 1e7
                    telemetry_data['alt'] = msg.relative_alt / 1000.0  # Relative altitude in meters
                
                elif msg_type == 'VFR_HUD':
                    telemetry_data['speed'] = msg.groundspeed # Groundspeed in m/s

                elif msg_type == 'HEARTBEAT':
                    telemetry_data['armed'] = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) > 0
                    # Try to get the mode name from ArduPilot mapping
                    mode_name = mavutil.mode_mapping_apm.get(msg.custom_mode, str(msg.custom_mode))
                    telemetry_data['mode'] = mode_name
                
                elif msg_type == 'SYS_STATUS':
                    telemetry_data['battery_v'] = msg.voltage_battery / 1000.0
                    telemetry_data['battery_remaining'] = msg.battery_remaining

                # Emit the updated data dictionary
                self.drone_data_updated.emit(telemetry_data)

            except Exception as e:
                print(f"[Mavlink] Error in message loop: {e}")
                time.sleep(1) # Don't spam errors
        
        print("[Mavlink] Worker loop stopped.")
        self.finished.emit()

    def request_data_streams(self):
        """Requests standard data streams from the autopilot."""
        if not self.mavlink_connection:
            return
            
        # Request streams at 2 Hz
        rate = 2
        for stream in [mavutil.mavlink.MAV_DATA_STREAM_EXTENDED_STATUS, 
                       mavutil.mavlink.MAV_DATA_STREAM_POSITION, 
                       mavutil.mavlink.MAV_DATA_STREAM_EXTRA1]:
            self.mavlink_connection.mav.request_data_stream_send(
                self.mavlink_connection.target_system,
                self.mavlink_connection.target_component,
                stream,
                rate,
                1   # Start
            )

    def get_connection(self):
        """Allows the main thread to get the connection object for sending commands."""
        return self.mavlink_connection

    def stop(self):
        """
        Stops the MAVLink message loop.
        """
        print("[Mavlink] Stopping worker...")
        self.running = False


class AutopilotControlPanel(QWidget):
    # Signal to send drone position to other widgets (like the map)
    drone_position_updated = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout()
        
        self.mavlink_connection = None
        self.mavlink_thread = None
        self.mavlink_worker = None

        # Autopilot connection group
        connection_group = QGroupBox("Autopilot Connection")
        conn_layout = QFormLayout()
        self.autopilot_path_field = QLineEdit()
        # Set a common default for SITL
        self.autopilot_path_field.setPlaceholderText("e.g., udp:127.0.0.1:14550")
        self.autopilot_path_field.setText("udp:127.0.0.1:14550")
        conn_layout.addRow("Autopilot Path:", self.autopilot_path_field)
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_autopilot)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self.disconnect_autopilot)
        self.disconnect_button.setEnabled(False)
        
        conn_button_layout = QHBoxLayout()
        conn_button_layout.addWidget(self.connect_button)
        conn_button_layout.addWidget(self.disconnect_button)
        conn_layout.addRow(conn_button_layout)
        
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
        # Standard ArduPilot modes
        for mode in ["GUIDED", "LOITER", "RTL", "AUTO", "STABILIZE"]:
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
        info_layout.addRow("Position (Lat, Lon, Alt):", self.position_label)
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

    def connect_autopilot(self):
        if not mavutil:
            self.current_mode_label.setText("Error: pymavlink missing")
            return
            
        if self.mavlink_thread and self.mavlink_thread.isRunning():
            print("[Autopilot] Already connected or connecting.")
            return

        autopilot_path = self.autopilot_path_field.text()
        if not autopilot_path:
            self.current_mode_label.setText("Error: Autopilot path is empty")
            return

        self.connect_button.setEnabled(False)
        self.connect_button.setText("Connecting...")

        # Create thread and worker
        self.mavlink_thread = QThread()
        self.mavlink_worker = MavlinkConnectionWorker(autopilot_path)
        self.mavlink_worker.moveToThread(self.mavlink_thread)

        # Connect signals from worker to slots in this class
        self.mavlink_worker.drone_data_updated.connect(self.update_drone_display)
        self.mavlink_worker.connection_status.connect(self.on_connection_status)
        
        # Connect thread management signals
        self.mavlink_thread.started.connect(self.mavlink_worker.connect_and_run)
        self.mavlink_worker.finished.connect(self.mavlink_thread.quit)
        self.mavlink_worker.finished.connect(self.mavlink_worker.deleteLater)
        self.mavlink_thread.finished.connect(self.mavlink_thread.deleteLater)
        self.mavlink_thread.finished.connect(self.on_thread_finished)

        # Start the thread
        self.mavlink_thread.start()

    def disconnect_autopilot(self):
        print("[Autopilot] Disconnecting...")
        if self.mavlink_worker:
            self.mavlink_worker.stop() # Tell worker loop to stop
        # Thread will quit and clean up via connected signals
        
        # Reset UI
        self.on_connection_status("Disconnected")
        self.mavlink_connection = None
        self.mavlink_thread = None
        self.mavlink_worker = None

    def on_thread_finished(self):
        print("[Autopilot] MAVLink thread finished.")
        # Clean up references
        self.mavlink_connection = None
        self.mavlink_thread = None
        self.mavlink_worker = None
        # Reset UI
        self.connect_button.setEnabled(True)
        self.connect_button.setText("Connect")
        self.disconnect_button.setEnabled(False)
        self.on_connection_status("Disconnected")

    @pyqtSlot(str)
    def on_connection_status(self, status):
        print(f"[Autopilot] Status: {status}")
        self.current_mode_label.setText(status)
        
        if "Connected" in status:
            self.connect_button.setText("Connected")
            self.disconnect_button.setEnabled(True)
            # Retrieve the connection object from the worker for sending commands
            if self.mavlink_worker:
                self.mavlink_connection = self.mavlink_worker.get_connection()
        elif "Failed" in status or "Error" in status:
            self.connect_button.setEnabled(True)
            self.connect_button.setText("Connect")
            self.disconnect_button.setEnabled(False)
        elif "Disconnected" in status:
            # Clear info labels on disconnect
            self.position_label.setText("N/A")
            self.speed_label.setText("N/A")
            self.battery_label.setText("N/A")

    @pyqtSlot(dict)
    def update_drone_display(self, data):
        """
        Slot to receive drone data from the MAVLink worker thread.
        """
        # Update labels
        self.position_label.setText(f"{data['lat']:.6f}, {data['lon']:.6f} @ {data['alt']:.1f}m")
        self.speed_label.setText(f"{data['speed']:.1f} m/s")
        self.battery_label.setText(f"{data['battery_remaining']}% ({data['battery_v']:.1f}V)")
        self.current_mode_label.setText(f"{data['mode']} ({'ARMED' if data['armed'] else 'DISARMED'})")

        # Emit signal for the map, only if position is valid
        if data['lat'] != 0.0 or data['lon'] != 0.0:
             self.drone_position_updated.emit(data['lat'], data['lon'])

    def send_arm(self):
        if self.mavlink_connection:
            print("Sending ARM command")
            self.mavlink_connection.mav.command_long_send(
                self.mavlink_connection.target_system,
                self.mavlink_connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,  # confirmation
                1,  # 1 to arm, 0 to disarm
                0, 0, 0, 0, 0, 0  # params 2-7 not used
            )
        else:
            print("[Autopilot] Not connected, cannot arm.")

    def send_disarm(self):
        if self.mavlink_connection:
            print("Sending DISARM command")
            self.mavlink_connection.mav.command_long_send(
                self.mavlink_connection.target_system,
                self.mavlink_connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,  # confirmation
                0,  # 0 to disarm
                0, 0, 0, 0, 0, 0  # params 2-7 not used
            )
        else:
            print("[Autopilot] Not connected, cannot disarm.")

    def send_mode(self, mode_name):
        if self.mavlink_connection:
            print(f"Changing mode to {mode_name}")
            
            # Find mode ID from string using the connection's mapping
            mode_id = self.mavlink_connection.mode_mapping().get(mode_name.upper())
            
            if mode_id is None:
                print(f"[Autopilot] Unknown mode: {mode_name}")
                return

            self.mavlink_connection.mav.set_mode_send(
                self.mavlink_connection.target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                mode_id
            )
        else:
            print(f"[Autopilot] Not connected, cannot change mode to {mode_name}.")

    def change_camera_mode(self):
        print("Camera mode changed (Simulation)")
        
    def closeEvent(self, event):
        # Ensure the thread is stopped when the widget (or window) closes
        self.disconnect_autopilot()
        super().closeEvent(event)
