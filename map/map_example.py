import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

class MapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interactive Map with Pins (Qt6)")
        self.setGeometry(100, 100, 1000, 700)

        # Web view for map
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        # Example coordinates (lat, lon, name)
        pins = [
            (40.1772, 44.5035, "Yerevan"),
            (40.7894, 43.8476, "Gyumri"),
            (39.762, 45.333, "Goris"),
            (40.15, 45.0, "Sevan Lake"),
        ]

        # Create HTML with Leaflet
        html = self.generate_map_html(pins)
        self.browser.setHtml(html, QUrl("https://leafletjs.com/"))

    def generate_map_html(self, pins):
        # JS array of markers
        markers_js = ""
        for lat, lon, name in pins:
            markers_js += f"""
            var marker = L.marker([{lat}, {lon}]).addTo(map);
            marker.bindPopup("{name}");
            marker.on('click', function(e) {{
                clickedPins.push("{name}");
                updateOrder();
            }});
            """

        # Full HTML
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Leaflet Map</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
            <style>
                body, html {{ height: 100%; margin: 0; }}
                #map {{ height: 90%; width: 100%; }}
                #orderBox {{
                    height: 10%; padding: 5px; overflow-x: auto;
                    background: #f0f0f0; font-family: Arial;
                }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <div id="orderBox"><b>Click order:</b> <span id="order"></span></div>

            <script>
                var map = L.map('map').setView([40.1772, 44.5035], 8);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    maxZoom: 19
                }}).addTo(map);

                var clickedPins = [];

                function updateOrder() {{
                    document.getElementById("order").innerHTML = clickedPins.join(" → ");
                }}

                {markers_js}
            </script>
        </body>
        </html>
        """

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapApp()
    window.show()
    sys.exit(app.exec())

