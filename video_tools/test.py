import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal, Qt, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self, pipeline):
        super().__init__()
        self.pipeline = pipeline
        self._is_running = True

    def run(self):
        # Open the GStreamer pipeline
        # Note the cv2.CAP_GSTREAMER flag
        cap = cv2.VideoCapture(self.pipeline, cv2.CAP_GSTREAMER)

        if not cap.isOpened():
            print("Error: Could not open GStreamer pipeline.")
            return

        while self._is_running:
            ret, cv_img = cap.read()
            if ret:
                self.change_pixmap_signal.emit(cv_img)
                print(cv_img.shape)
            else:
                # If ret is False, the stream might have ended or failed
                print("Stream ended or frame capture failed.")
                break
        
        cap.release()
        print("Video thread stopped.")

    def stop(self):
        self._is_running = False
        self.wait()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GStreamer UDP Stream")
        self.resize(1280, 720)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")

        vbox = QVBoxLayout()
        vbox.addWidget(self.image_label)
        self.setLayout(vbox)

        # -----------------------------------------------------------------
        # MODIFICATION 1: Define the GStreamer pipeline string for OpenCV
        #
        # - We removed "gst-launch-1.0"
        # - We replaced "autovideosink" with:
        #   "videoconvert ! video/x-raw, format=BGR ! appsink drop=1"
        # -----------------------------------------------------------------
        GSTREAMER_PIPELINE = (
            'udpsrc port=5000 caps="application/x-rtp, media=video, encoding-name=H264, '
            'clock-rate=90000, payload=96" ! rtph264depay ! avdec_h264 ! '
            'videoconvert ! video/x-raw, format=BGR ! appsink drop=1'
        )

        # Setup Video Thread
        self.thread = VideoThread(GSTREAMER_PIPELINE)
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.start()

    def closeEvent(self, event):
        self.thread.stop()
        event.accept()

    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        """Updates the image_label with a new opencv image"""
        # Note: cv_img is already in BGR format from the pipeline
        # We just convert it to RGB for Qt
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        p = convert_to_Qt_format.scaled(self.image_label.width(), self.image_label.height(), Qt.AspectRatioMode.KeepAspectRatio)
        self.image_label.setPixmap(QPixmap.fromImage(p))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())