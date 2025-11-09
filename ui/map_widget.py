#!/usr/bin/env python3
import json
import socket
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
# Import QUrl, QTimer, AND pyqtSlot
from PyQt6.QtCore import QUrl, QTimer, pyqtSlot

class MapWidget(QWidget):
    def __init__(self, parent=None, udp_port=6007):
        super().__init__(parent)
        self.udp_port = udp_port

        layout = QVBoxLayout(self)
        # Remove margins for a cleaner look
        layout.setContentsMargins(0, 0, 0, 0)
        self.browser = QWebEngineView(self)
        layout.addWidget(self.browser)
        self.setLayout(layout)

        self.load_map_html()

        # UDP socket for receiving pin coordinates
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.bind(("", self.udp_port))
        self.udp_sock.setblocking(False)
        print(f"[MapWidget] Listening for UDP on port {self.udp_port}")

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll_udp_socket)
        self.poll_timer.start(200)  # check every 200 ms

    def load_map_html(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Leaflet Map</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
            <style>
                body, html { height: 100%; margin: 0; padding: 0; }
                #map { height: 100%; width: 100%; }
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([40.1772, 44.5035], 8); // Default view
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                }).addTo(map);

                var markers = [];
                var droneMarker = null;
                var followDrone = true; // Flag to control map panning

                // Function to add a static pin (from UDP)
                function addMarker(lat, lon, name) {
                    try {
                        var marker = L.marker([lat, lon]).addTo(map);
                        marker.bindPopup(name);
                        markers.push(marker);
                    } catch (e) {
                        console.error("addMarker error:", e);
                    }
                }
                
                // Function to update the drone's position
                function updateDrone(lat, lon) {
                    try {
                        var pos = [lat, lon];
                        if (!droneMarker) {
                            // Create a blue circle marker for the drone
                            droneMarker = L.circleMarker(pos, { 
                                radius: 7, 
                                color: '#0000ff',
                                weight: 2,
                                fillColor: '#3388ff', 
                                fillOpacity: 0.8 
                            }).addTo(map);
                            droneMarker.bindPopup('<b>Drone</b>');
                            // Set initial view to drone
                            map.setView(pos, 16);
                        } else {
                            droneMarker.setLatLng(pos);
                        }
                        
                        // Pan map to follow drone if flag is set
                        if (followDrone) {
                            map.panTo(pos);
                        }
                    } catch (e) {
                        console.error("updateDrone error:", e);
                    }
                }

                function clearMarkers() {
                    markers.forEach(function(m) { map.removeLayer(m); });
                    markers = [];
                }
                
                // Optional: Stop following if user drags map
                map.on('dragstart', function() {
                    followDrone = false;
                });
                
                // You could add a button in HTML to re-enable following
                // e.g., map.on('click', function() { followDrone = true; });

            </script>
        </body>
        </html>
        """
        # Using a base URL is good practice for web engines
        self.browser.setHtml(html, QUrl("https://base.example.com/"))

    def add_pin(self, lat, lon, name="pin"):
        # Use json.dumps for safe JS string quoting
        try:
            js = f"addMarker({float(lat)}, {float(lon)}, {json.dumps(str(name))});"
            self.browser.page().runJavaScript(js)
            print(f"[MapWidget] Added pin: {lat}, {lon}, {name}")
        except Exception as e:
            print(f"[MapWidget] Error adding pin: {e}")

    @pyqtSlot(float, float)
    def update_drone_position(self, lat, lon):
        """
        Public slot to be called from other widgets (like AutopilotControlPanel).
        Updates the drone's position marker on the map.
        """
        try:
            js = f"updateDrone({lat}, {lon});"
            self.browser.page().runJavaScript(js)
        except Exception as e:
            print(f"[MapWidget] Error updating drone position: {e}")

    def poll_udp_socket(self):
        try:
            while True:
                data, addr = self.udp_sock.recvfrom(4096)
                try:
                    payload = json.loads(data.decode('utf-8'))
                except Exception as e:
                    print(f"[MapWidget] JSON decode error from {addr}: {e}")
                    continue

                # Accept either single pin or list under "pins"
                if isinstance(payload, dict):
                    if "pins" in payload and isinstance(payload["pins"], list):
                        for p in payload["pins"]:
                            try:
                                # Allow [lat, lon, name] or [lat, lon]
                                lat, lon = p[0], p[1]
                                name = p[2] if len(p) > 2 else "Pin"
                                self.add_pin(lat, lon, name)
                            except Exception:
                                continue
                    elif "lat" in payload and "lon" in payload:
                        name = payload.get("name", payload.get("label", "pin"))
                        self.add_pin(payload["lat"], payload["lon"], name)
                    else:
                        # try a list-of-lists payload shaped like [ [lat,lon,name], ... ]
                        if isinstance(payload.get("data"), list):
                            for p in payload["data"]:
                                if len(p) >= 2:
                                    self.add_pin(p[0], p[1], p[2] if len(p) > 2 else "pin")
                elif isinstance(payload, list):
                    for p in payload:
                        if isinstance(p, (list, tuple)) and len(p) >= 2:
                            self.add_pin(p[0], p[1], p[2] if len(p) > 2 else "pin")

        except BlockingIOError:
            pass # No data available, perfectly normal
        except Exception as e:
            print(f"[MapWidget] UDP poll error: {e}")
