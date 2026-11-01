# SPDX-License-Identifier: GPL-3.0-or-later
"""Render original SVG banner concepts using the existing GUI mark and Outfit."""
from pathlib import Path
import os
import re

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QByteArray,Qt
from PySide6.QtGui import QFontDatabase,QImage,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


def main():
    root=Path(__file__).resolve().parents[1]
    app=QApplication.instance() or QApplication([])
    QFontDatabase.addApplicationFont(str(root/'src/fx240/assets/fonts/Outfit.ttf'))
    source=(root/'src/fx240/assets/branding/tray-lcd-dark.svg').read_text()
    geometry=re.search(r'(<path.*)</svg>',source).group(1)
    destination=root/'docs/assets/banners'
    destination.mkdir(parents=True,exist_ok=True)
    def mark(x,y,size,color):
        return f'<g transform="translate({x} {y}) scale({size/24})" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{geometry}</g>'
    variants={
        'a-dark':('#0e1418',mark(200,94,112,'#73dfc1')+'<text x="344" y="173" fill="#e8eef1" font-size="57" font-weight="400" letter-spacing="1">FX240 LCD STUDIO</text>'),
        'b-stacked':('#151e24',mark(150,76,136,'#e8eef1')+'<text x="324" y="139" fill="#e8eef1" font-size="67" font-weight="400">FX240</text><text x="328" y="189" fill="#73dfc1" font-size="26" font-weight="400" letter-spacing="7">LCD STUDIO</text><path d="M630 102V198" stroke="#34434d" stroke-width="1"/><text x="685" y="145" fill="#becbd2" font-size="27" font-weight="400">Live telemetry. Custom visuals.</text><text x="685" y="182" fill="#9aadb8" font-size="24" font-weight="400">Built for Linux.</text>'),
        'c-light':('#f2f5f7',mark(200,94,112,'#1e373c')+'<text x="344" y="173" fill="#20313b" font-size="57" font-weight="400" letter-spacing="1">FX240 LCD STUDIO</text>'),
    }
    for name,(background,content) in variants.items():
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="300" viewBox="0 0 1280 300"><rect width="1280" height="300" fill="{background}"/><g font-family="Outfit, sans-serif">{content}</g></svg>\n'
        (destination/f'{name}.svg').write_text(svg)
        image=QImage(1280,300,QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter=QPainter(image)
        renderer=QSvgRenderer(QByteArray(svg.encode()))
        assert renderer.isValid()
        renderer.render(painter);painter.end()
        assert image.save(str(destination/f'{name}.png'))
    print('Rendered three SVG/PNG banner concepts from the original GUI mark.')


if __name__=='__main__':main()
