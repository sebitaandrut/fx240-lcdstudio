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
from PIL import Image


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
    def ink_bounds(fragment):
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="300"><g font-family="Outfit, sans-serif">{fragment}</g></svg>'
        image=QImage(1280,300,QImage.Format.Format_RGBA8888)
        image.fill(Qt.GlobalColor.transparent)
        painter=QPainter(image)
        QSvgRenderer(QByteArray(svg.encode())).render(painter)
        painter.end()
        return Image.frombytes('RGBA',(1280,300),image.constBits().tobytes()).getchannel('A').getbbox()

    def place(fragment, *, center_x=None, center_y=None, left=None, top=None):
        x0,y0,x1,y1=ink_bounds(fragment)
        dx=center_x-(x0+x1)/2 if center_x is not None else left-x0 if left is not None else 0
        dy=center_y-(y0+y1)/2 if center_y is not None else top-y0 if top is not None else 0
        return f'<g transform="translate({dx} {dy})">{fragment}</g>'

    def stack(first,second,gap, *, center_x=None,left=None):
        a=ink_bounds(first);b=ink_bounds(second)
        height_a=a[3]-a[1];height_b=b[3]-b[1]
        top=150-(height_a+gap+height_b)/2
        return (place(first,center_x=center_x,left=left,top=top)+
                place(second,center_x=center_x,left=left,top=top+height_a+gap))

    # Align painted glyph bounds, not baselines or the SVG's nominal view box.
    brand=stack('<text x="100" y="100" fill="#e8eef1" font-size="67" font-weight="400">FX240</text>',
                '<text x="100" y="100" fill="#73dfc1" font-size="26" font-weight="400" letter-spacing="7">LCD STUDIO</text>',22,center_x=422)
    description=stack('<text x="100" y="100" fill="#becbd2" font-size="27" font-weight="400">Live telemetry. Custom visuals.</text>',
                      '<text x="100" y="100" fill="#9aadb8" font-size="24" font-weight="400">Built for Linux.</text>',14,left=685)
    stacked=place(mark(150,76,136,'#e8eef1'),center_y=150)+brand+'<path d="M630 102V198" stroke="#34434d" stroke-width="1"/>'+description
    stacked=place(stacked,center_x=640)
    variants={
        'a-dark':('#0e1418',mark(200,94,112,'#73dfc1')+'<text x="344" y="173" fill="#e8eef1" font-size="57" font-weight="400" letter-spacing="1">FX240 LCD STUDIO</text>'),
        'b-stacked':('#151e24',stacked),
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
