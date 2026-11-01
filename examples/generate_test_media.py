# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate original synthetic media for physical LCD validation."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw


def frame(index=0):
    image = Image.new('RGB', (240, 240), (12, 18, 28))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 239, 239), outline='white', width=2)
    draw.text((85, 10), 'TOP / UP', fill='white')
    draw.text((80, 218), 'BOTTOM', fill='white')
    draw.text((12, 28), 'LEFT', fill='white')
    draw.text((194, 28), 'RIGHT', fill='white')
    for x, color, label in ((12, 'red', 'R'), (88, 'lime', 'G'), (164, 'blue', 'B')):
        draw.rectangle((x, 52, x+63, 106), fill=color)
        draw.text((x+28, 112), label, fill='white')
    draw.text((45, 140), 'FX240 LINUX TEST', fill='white')
    draw.text((90, 161), f'{index:02d}', fill='white')
    x = 18 + index * 10
    draw.rectangle((12, 185, 227, 202), outline='white')
    draw.rectangle((x, 188, x+12, 199), fill=(80, 220, 205))
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    frame().save(args.directory / 'test-pattern.png')
    frames = [frame(i) for i in range(20)]
    frames[0].save(args.directory / 'test-animation.gif', save_all=True,
                   append_images=frames[1:], duration=100, loop=0)
    print('Generated test-pattern.png and test-animation.gif')


if __name__ == '__main__':
    main()
