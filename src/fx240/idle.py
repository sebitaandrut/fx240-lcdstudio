"""Programmatically recreated standby artwork; not a firmware reset command."""
from PIL import Image, ImageDraw
from .focus import font, resolve_font, SCALE


def render_idle():
    image = Image.new('RGB', (240*SCALE,240*SCALE), '#050609')
    draw = ImageDraw.Draw(image)
    points = [(76,43),(164,43),(183,58),(209,147),(201,164),
              (135,207),(120,211),(105,207),(39,164),(31,147),(57,58)]
    # Quadratic corner rounding, drawn at renderer resolution.
    path=[]
    for i,p in enumerate(points):
        prev,nxt=points[i-1],points[(i+1)%len(points)]
        a=tuple(p[j]*.7+prev[j]*.3 for j in (0,1))
        b=tuple(p[j]*.7+nxt[j]*.3 for j in (0,1))
        for k in range(13):
            t=k/12
            path.append(tuple(((1-t)**2*a[j]+2*(1-t)*t*p[j]+t*t*b[j])*SCALE for j in (0,1)))
    draw.line(path+[path[0]],fill='#edf4ff',width=5*SCALE,joint='curve')
    face=font(resolve_font(),12,650)
    for text,y in [('THIS IS YOUR',102),('WORLD!',123),('BE CREATIVE!',144)]:
        draw.text((120*SCALE,y*SCALE),text,font=face,anchor='mm',fill='#edf4ff')
    return image.resize((240,240),Image.Resampling.LANCZOS)
