# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate synthetic animation comparisons, never read sensors, USB, or user media."""
import argparse
import math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from fx240.focus import Focus
from fx240.telemetry import Metric


def metrics():
    return [Metric('ct','CPU synthetic',45.2,'C','synthetic'),Metric('cf','CPU synthetic',3800,'MHz','synthetic'),
            Metric('gt','GPU synthetic',38.1,'C','synthetic'),Metric('gf','GPU synthetic',1600,'MHz','synthetic')]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    backdrops=[]
    for index in range(48):
        image=Image.new('RGB',(240,240),(5,7,20));draw=ImageDraw.Draw(image)
        for band in range(12):
            y=band*25-30+int(22*math.sin(index*math.tau/48+band*.3))
            draw.ellipse((-75,y,310,y+70),outline=(30+band*4,45,105+band*9),width=7)
        backdrops.append(image.filter(ImageFilter.GaussianBlur(4)))
    background=args.output_dir/'synthetic-waves.gif'
    backdrops[0].save(background,save_all=True,append_images=backdrops[1:],duration=50,loop=0)
    font_path=Path(__file__).resolve().parents[1]/'src/fx240/assets/fonts/Outfit.ttf'
    face=ImageFont.truetype(str(font_path),20)
    small=ImageFont.truetype(str(font_path),14)
    themes=[Focus(provider=metrics,animation=effect,temperature_decimals=1,
                  background_path=str(background) if effect=='comet' else None,
                  background_dim=.4) for effect in ('orbit','pulse','comet')]
    labels=[('ORBIT','Two moving points'),('PULSE','Soft brightness cycle'),('COMET + GIF','Live readings over motion')]
    frames=[]
    for index in range(60):
        image=Image.new('RGB',(840,340),'#0e1216');draw=ImageDraw.Draw(image)
        for column,(theme,(title,description)) in enumerate(zip(themes,labels)):
            draw.rounded_rectangle((column*280+8,8,column*280+272,332),radius=16,fill='#182027')
            # Start after the initial temperature arc ramp.
            theme(0) if index==0 else None
            frame,_=theme(1+index/20)
            image.paste(frame,(column*280+20,56))
            draw.text((column*280+140,30),title,font=face,fill='#e8eef1',anchor='mm')
            draw.text((column*280+140,313),description,font=small,fill='#abb8c0',anchor='mm')
        frames.append(image)
    frames[0].save(args.output_dir/'effects-comparison.gif',save_all=True,append_images=frames[1:],duration=50,loop=0)
    frames[18].save(args.output_dir/'effects-comparison.png')
    print('Synthetic comparison generated; no sensors, user files, or USB accessed.')


if __name__=='__main__':main()
