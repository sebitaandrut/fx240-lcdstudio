# SPDX-License-Identifier: GPL-3.0-or-later
"""Circular Qt image provider shared by output and isolated editor previews."""
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage,QPainter,QPainterPath
from PySide6.QtQuick import QQuickImageProvider


def circular_image(image):
    rgb = image.convert('RGB')
    frame = QImage(rgb.tobytes(), rgb.width, rgb.height, rgb.width*3, QImage.Format.Format_RGB888).copy()
    result = QImage(rgb.width, rgb.height, QImage.Format.Format_ARGB32_Premultiplied)
    result.fill(0)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    margin = rgb.width * 3 / 240
    clip.addEllipse(QRectF(margin, margin, rgb.width - 2*margin, rgb.height - 2*margin))
    painter.setClipPath(clip)
    painter.drawImage(0, 0, frame)
    painter.end()
    return result


class FrameProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.image = QImage(240,240,QImage.Format.Format_ARGB32_Premultiplied)
        self.image.fill(0)

    def update(self, image):
        self.image = circular_image(image)

    def requestImage(self, identifier, size, requested_size):
        size.setWidth(self.image.width())
        size.setHeight(self.image.height())
        return self.image.copy()


class ThumbnailProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.images = {}
        self.empty = QImage(1, 1, QImage.Format.Format_ARGB32_Premultiplied)
        self.empty.fill(0)

    def requestImage(self, identifier, size, requested_size):
        image = self.images.get(identifier, self.empty)
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image.copy()
