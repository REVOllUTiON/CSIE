#!/usr/bin/env python3
from datetime import datetime
from PyQt6.QtWidgets import QGraphicsRectItem
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPen, QColor, QBrush
from PyQt6.QtCore import pyqtSignal

class BoundingBoxItem(QGraphicsRectItem):
    def __init__(self, metadata: dict, rect: QRectF, on_click_callback=None, *args, **kwargs):
        super().__init__(rect, *args, **kwargs)
        self.metadata = metadata
        self.bbox_id = metadata.get("id", -1)
        self.on_click_callback = on_click_callback

        pen = QPen(QColor("red"))
        pen.setWidth(2)
        self.setPen(pen)
        self.setBrush(QBrush(QColor(255, 0, 0, 50)))

        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

        self.setToolTip(f"{metadata.get('label', '')} - ID: {self.bbox_id} - {metadata.get('data', '')}")

    def mousePressEvent(self, event):
        center = self.rect().center()
        print(f"Clicked bbox {self.bbox_id} @ ({center.x():.1f}, {center.y():.1f})")
        if self.on_click_callback:
            self.on_click_callback(self.metadata)
        super().mousePressEvent(event)
