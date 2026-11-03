# SPDX-License-Identifier: GPL-3.0-or-later
"""Circular Qt image provider shared by output and isolated editor previews."""
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage,QPainter,QPainterPath
from PySide6.QtQuick import QQuickImageProvider

class FrameProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.image = QImage(240,240,QImage.Format.Format_RGB888)
        self.image.fill('#080b0e')

    def update(self, image):
        rgb = image.convert('RGB')
        frame = QImage(rgb.tobytes(),rgb.width,rgb.height,rgb.width*3,QImage.Format.Format_RGB888).copy()
        self.image = QImage(rgb.width,rgb.height,QImage.Format.Format_ARGB32_Premultiplied)
        self.image.fill(0)
        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addEllipse(QRectF(3,3,234,234))
        painter.setClipPath(clip)
        painter.drawImage(0,0,frame)
        painter.end()

    def requestImage(self, identifier, size, requested_size):
        size.setWidth(self.image.width())
        size.setHeight(self.image.height())
        return self.image.copy()
