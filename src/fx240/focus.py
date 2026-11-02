# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal circular telemetry theme with time-based motion and cached typography."""
from functools import lru_cache
import io
import math
import colorsys
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .telemetry import collect
from .localfiles import read_regular

SCALE = 2
MINT = (115, 223, 193)
ARC_BASE = (52, 122, 104)
ARC_BOX = (17*SCALE,17*SCALE,223*SCALE,223*SCALE)
ARC_WIDTH = 8*SCALE
WHITE = (237, 244, 245)
MUTED = (165, 182, 187)
MAX_FONT_BYTES = 16 * 1024 * 1024


def load_font(path, size):
    # A saved/custom font is local input too: never hand a FIFO to FreeType.
    return ImageFont.truetype(io.BytesIO(read_regular(path,MAX_FONT_BYTES)),size)


def resolve_font(path=None):
    if path is not None:
        # Validate explicit choices instead of silently substituting another font.
        load_font(path, 12)
        return str(path)
    for candidate in (str(Path(__file__).parent/'assets/fonts/Outfit.ttf'),
                      '/usr/share/fonts/noto/NotoSans-Regular.ttf',
                      '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf'):
        if Path(candidate).is_file():
            return candidate
    return None


@lru_cache(maxsize=32)
def font(path, size, weight=400):
    face = load_font(path, size*SCALE) if path else ImageFont.load_default(size=size*SCALE)
    try:
        axes = face.get_variation_axes()
    except (OSError, AttributeError):
        return face
    values = []
    for axis in axes:
        name = axis['name']
        value = weight if name == b'Weight' else size if name == b'Optical size' else axis['default']
        values.append(max(axis['minimum'], min(axis['maximum'], value)))
    face.set_variation_by_axes(values)
    return face


def ease(value):
    t = max(0.0, min(1.0, value))
    return t*t*(3-2*t)


def accent_rgb(value):
    if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):
        raise ValueError('Accent must be a six-digit hex color')
    return tuple(int(value[i:i+2],16) for i in (1,3,5))


def arc_color(accent):
    return tuple(round(c*b/a) for c,b,a in zip(accent,ARC_BASE,MINT))


def comet_segments(elapsed, progress, accent=MINT, style="accent"):
    """A three-second sweep; clip its fading tail to the active temperature arc."""
    span = 270*max(0,min(1,progress))
    if span <= 0:
        return []
    trail = min(38,span*.6)
    head = ((elapsed % 3)/3)*(span+trail)
    segments = []
    for index in range(20):
        left = head-trail+trail*index/20
        right = left+trail/20
        left,right = max(0,left),min(span,right)
        if right-left <= 1e-9:
            continue
        strength = min(1, ((index+.5)/20)*1.5)**1.4
        highlight = (255,255,255)
        if style == 'rainbow':
            highlight = tuple(round(c*255) for c in colorsys.hsv_to_rgb((elapsed/3+index/20*.75)%1,.85,1))
        color = tuple(round(a+(b-a)*strength) for a,b in zip(arc_color(accent),highlight))
        segments.append((135+left,135+right,color))
    return segments


def arc_point(angle):
    """Pillow strokes extend inward from the arc box; use their actual centerline."""
    center = ((ARC_BOX[0]+ARC_BOX[2])/2,(ARC_BOX[1]+ARC_BOX[3])/2)
    radius = (ARC_BOX[2]-ARC_BOX[0]-(ARC_WIDTH-1))/2
    radians = math.radians(angle)
    return center[0]+radius*math.cos(radians),center[1]+radius*math.sin(radians)


def round_arc(draw, start, end, color):
    """Draw one curved stroke with circular caps of the same diameter."""
    if end <= start:
        return
    draw.arc(ARC_BOX,start,end,fill=color,width=ARC_WIDTH)
    radius = (ARC_WIDTH-1)/2
    for angle in (start,end):
        x,y = arc_point(angle)
        draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=color)


def active_arc_mask(size, progress):
    mask = Image.new('L',size)
    round_arc(ImageDraw.Draw(mask),135,135+270*progress,255)
    return mask


def draw_active_arc(image, elapsed, progress, accent=MINT, style="accent"):
    """Keep the round comet centered on the rounded active stroke."""
    mask = active_arc_mask(image.size,progress)
    layer = Image.new('RGB',image.size,arc_color(accent))
    draw = ImageDraw.Draw(layer)
    for left,right,color in comet_segments(elapsed,progress,accent,style):
        # Overlapping circular caps give the head and fading tail a soft silhouette.
        round_arc(draw,left,right,color)
    image.paste(layer,(0,0),mask)


def readings(metrics, keys=None):
    if keys:
        metrics = [metric for metric in metrics if metric.key in keys]
    result = []
    for group, unit in (('CPU','C'), ('CPU','MHz'), ('GPU','C'), ('GPU','MHz')):
        metric = next((m for m in metrics if m.label.startswith(group+' ') and m.unit == unit), None)
        value = metric.value if metric else None
        result.append(value if value is not None and math.isfinite(value) else None)
    return tuple(result)


def temperature(value, decimals=0, unit='C'):
    if unit not in ('C','F'):
        raise ValueError('Temperature unit must be C or F')
    converted = value if value is None or unit == 'C' else value*9/5+32
    return 'N/A' if converted is None else f'{converted:.{decimals}f}'


def frequency(value):
    return 'N/A' if value is None else f'{value/1000:.2f} GHz'


class Focus:
    def __init__(self, fps=24, keys=None, font_path=None, provider=None, arc_range=(0,100), font_weight=350, temperature_decimals=0, comet_speed=1.0, accent="#73dfc1", comet_style="accent", temperature_unit="C"):
        if not 0 < fps <= 24:
            raise ValueError('Focus FPS must be greater than zero and at most 24')
        if not all(math.isfinite(x) for x in arc_range) or arc_range[1] <= arc_range[0]:
            raise ValueError('Arc maximum must exceed its minimum')
        if not 100 <= font_weight <= 900:
            raise ValueError("Font weight must be between 100 and 900")
        if temperature_decimals not in (0,1):
            raise ValueError("Temperature decimals must be 0 or 1")
        if not math.isfinite(comet_speed) or not .25 <= comet_speed <= 3:
            raise ValueError('Comet speed must be between 0.25 and 3')
        self.accent = accent_rgb(accent)
        if comet_style not in ('accent','rainbow'):
            raise ValueError('Unknown comet style')
        self.comet_style = comet_style
        self.comet_speed = comet_speed
        self.comet_offset = 0.0
        if temperature_unit not in ('C','F'):
            raise ValueError('Temperature unit must be C or F')
        self.temperature_unit = temperature_unit
        self.temperature_decimals = temperature_decimals
        self.font_weight = font_weight
        self.fps = fps
        self.keys = keys
        self.font_path = resolve_font(font_path)
        self.provider = provider if provider is not None else collect
        self.arc_range = arc_range
        self.sampled_at = None
        self.changed_at = 0
        self.values = (None,)*4
        self.arc_from = 0
        self.arc_to = 0
        self.static = None

    def text(self, draw, xy, text, size, color, anchor='mm'):
        draw.text(tuple(v*SCALE for v in xy), text, font=font(self.font_path,size,self.font_weight),
                  fill=color, anchor=anchor)

    def draw_temperature(self, draw, value):
        if value is None:
            self.text(draw,(120,99),'N/A',45,WHITE)
            return
        text = temperature(value,self.temperature_decimals,self.temperature_unit)
        number_size = 64
        while number_size > 44:
            face = font(self.font_path,number_size,self.font_weight)
            bounds = face.getbbox(text,anchor='lt')
            if bounds[2]-bounds[0] <= 160*SCALE:
                break
            number_size -= 1
        number_font = font(self.font_path,number_size,self.font_weight)
        degree_font = font(self.font_path,24,self.font_weight)
        number_box = number_font.getbbox(text,anchor='lt')
        degree_box = degree_font.getbbox('°'+self.temperature_unit,anchor='lt')
        width = number_box[2]-number_box[0]
        height = number_box[3]-number_box[1]
        gap = 3*SCALE
        degree_width = degree_box[2]-degree_box[0]
        left = 120*SCALE-(width+gap+degree_width)/2
        top = 99*SCALE-height/2
        self.text(draw,((left-number_box[0])/SCALE,(top-number_box[1])/SCALE),text,number_size,WHITE,anchor='lt')
        self.text(draw,((left+width+gap-degree_box[0])/SCALE,(top+2*SCALE-degree_box[1])/SCALE),'°'+self.temperature_unit,24,self.accent,anchor='lt')

    def comet_time(self, elapsed):
        return elapsed*self.comet_speed+self.comet_offset

    def inherit_motion(self, other, elapsed):
        self.arc_from = self.arc_to = other.arc_value(elapsed)
        self.comet_offset = other.comet_time(elapsed)-elapsed*self.comet_speed

    def arc_value(self, elapsed):
        return self.arc_from+(self.arc_to-self.arc_from)*ease((elapsed-self.changed_at)/.6)

    def sample(self, elapsed):
        current_arc = self.arc_value(elapsed)
        new_values = readings(self.provider(), self.keys)
        self.values = new_values
        self.arc_from = current_arc
        low, high = self.arc_range
        self.arc_to = 0 if new_values[0] is None else max(0,min(1,(new_values[0]-low)/(high-low)))
        self.changed_at = elapsed
        self.sampled_at = elapsed
        self.static = Image.new('RGB', (240*SCALE,240*SCALE), 'black')
        draw = ImageDraw.Draw(self.static)
        draw.ellipse((3*SCALE,3*SCALE,237*SCALE,237*SCALE), fill=(8,11,14))
        round_arc(draw,135,405,(28,42,46))
        self.text(draw,(120,49),'CPU',14,MUTED)
        self.text(draw,(120,146),frequency(new_values[1]),18,self.accent)
        draw.line((75*SCALE,164*SCALE,165*SCALE,164*SCALE), fill=(37,50,56),width=SCALE)
        gpu_temp = 'N/A' if new_values[2] is None else temperature(new_values[2],self.temperature_decimals,self.temperature_unit)+'°'+self.temperature_unit
        # Two centered rows keep all four readings legible inside the circular inset.
        self.text(draw,(120,183),f'GPU  {gpu_temp}',18,WHITE)
        self.text(draw,(120,204),frequency(new_values[3]),14,MUTED)

    def __call__(self, elapsed):
        if self.sampled_at is None or elapsed < self.sampled_at:
            self.changed_at = elapsed
            self.arc_from = self.arc_to = 0
            self.sample(elapsed)
        elif elapsed-self.sampled_at >= 1:
            self.sample(elapsed)
        image = self.static.copy()
        draw = ImageDraw.Draw(image)
        progress = self.arc_value(elapsed)
        if self.values[0] is not None and progress > 0:
            draw_active_arc(image,self.comet_time(elapsed),progress,self.accent,self.comet_style)
            draw = ImageDraw.Draw(image)
        # Numeric readings switch atomically; only the decorative arc interpolates.
        self.draw_temperature(draw,self.values[0])
        return image.resize((240,240),Image.Resampling.LANCZOS),1/self.fps
