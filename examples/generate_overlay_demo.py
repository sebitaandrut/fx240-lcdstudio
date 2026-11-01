"""Generate original motion centered between the telemetry overlay bands."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    frames = []
    for i in range(20):
        image = Image.new('RGB', (240,240), (16, 32, 48))
        draw = ImageDraw.Draw(image)
        x = 48 + i*7
        draw.ellipse((x-12, 94, x+12, 118), fill=(80,220,205))
        draw.text((103,132), f'{i:02d}', fill='white')
        frames.append(image)
    frames[0].save(args.directory/'overlay-background.png')
    frames[0].save(args.directory/'overlay-motion.gif', save_all=True,
                   append_images=frames[1:], duration=200, loop=0)
    print('Generated overlay-background.png and overlay-motion.gif')


if __name__ == '__main__':
    main()
