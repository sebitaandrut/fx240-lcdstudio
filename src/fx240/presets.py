# SPDX-License-Identifier: GPL-3.0-or-later
"""Built-in LCD compositions with bounded, local animation state."""
from collections import deque
from colorsys import hsv_to_rgb
import math

from PIL import Image, ImageDraw

from .background import Background
from .focus import MUTED, WHITE, accent_rgb, arc_point, frequency, readings, round_arc, temperature
from .typography import SCALE, font, resolve_font

DESIGNS = {'focus': 'Focus', 'dual': 'Dual', 'trace': 'Trace', 'halo': 'Halo'}
PRESET_ACCENTS = {'dual': '#73dfc1', 'trace': '#c6a3fa', 'halo': '#ffc082'}
DEFAULT_GPU_ACCENT = '#83bcfa'


EFFECT_TITLES = {
    'disc': 'Background disc', 'divider': 'Divider', 'dual_cpu': 'CPU arc',
    'dual_gpu': 'GPU arc', 'trace': 'Temperature history', 'halo': 'Radial pulse',
    'segments': 'Segmented ring', 'radar': 'Radar sweep',
}

EDITOR_EFFECTS = {
    'arc': ('Temperature arc', '#73dfc1'),
    'dual_cpu': ('CPU arc (Dual)', PRESET_ACCENTS['dual']),
    'dual_gpu': ('GPU arc (Dual)', DEFAULT_GPU_ACCENT),
    'trace': (EFFECT_TITLES['trace'], PRESET_ACCENTS['trace']),
    'halo': (EFFECT_TITLES['halo'], PRESET_ACCENTS['halo']),
    'segments': (EFFECT_TITLES['segments'], '#ff83b5'),
    'radar': (EFFECT_TITLES['radar'], '#73dfc1'),
}

SEGMENT_ANGLES = tuple((start + 4, start + 24) for start in range(0, 360, 30))


def dim(color, amount):
    return tuple(round(channel * amount) for channel in color)


def radar_box(radius):
    return tuple(value * SCALE for value in (120-radius, 120-radius, 120+radius, 120+radius))


def motion_color(accent, clock, style, offset=0):
    if style == 'accent':
        return accent
    return tuple(round(channel * 255) for channel in hsv_to_rgb((clock / 6 + offset) % 1, .65, 1))


def update_trace(history, elapsed, value):
    if history and (elapsed < history[-1][0] or elapsed - history[-1][0] > 2.5):
        history.clear()
    if history and elapsed - history[-1][0] < 1:
        history.pop()
    history.append((elapsed, value))
    while history and elapsed - history[0][0] >= 60:
        history.popleft()
    temperatures = [value for _, value in history if value is not None]
    if not temperatures:
        return []
    low, high = min(temperatures), max(temperatures)
    padding = max(2, (10 - (high - low)) / 2)
    low -= padding
    high += padding
    if not math.isfinite(high - low) or high <= low:
        return []
    return [
        None if value is None else (
            (198 - (elapsed - at) * 156 / 60) * SCALE,
            (156 - 34 * (value - low) / (high - low)) * SCALE,
        )
        for at, value in history
    ]


def draw_effect_base(draw, shape, color, trace=()):
    if shape == 'disc':
        draw.ellipse((2 * SCALE, 2 * SCALE, 238 * SCALE, 238 * SCALE), fill=color)
    elif shape == 'divider':
        draw.line((120 * SCALE, 0, 120 * SCALE, 240 * SCALE), fill=color, width=20 * SCALE)
    elif shape in ('dual_cpu', 'dual_gpu'):
        start = 106 if shape == 'dual_cpu' else 286
        round_arc(draw, start, start + 148, tuple(round(channel * .68) for channel in color))
    elif shape == 'trace':
        for y in (124, 155):
            draw.line((42 * SCALE, y * SCALE, 198 * SCALE, y * SCALE), fill=(39, 57, 65), width=SCALE)
        for left, right in zip(trace, trace[1:]):
            if left is not None and right is not None:
                draw.line((*left, *right), fill=color, width=3 * SCALE)
    elif shape == 'segments':
        for start, end in SEGMENT_ANGLES:
            round_arc(draw, start, end, dim(color, .26))
    elif shape == 'radar':
        for radius in (43, 72, 98):
            draw.ellipse(radar_box(radius), outline=dim(color, .28), width=SCALE)


def draw_effect_motion(draw, shape, color, clock, style='accent', trace=()):
    phase = (clock / 3) % 1
    sweep = (1 - math.cos(math.tau * phase)) / 2
    highlight = motion_color(color, clock, style, .5 if shape == 'dual_gpu' else 0)
    if shape in ('dual_cpu', 'dual_gpu'):
        angle = 254 - 148 * sweep if shape == 'dual_cpu' else 286 + 148 * sweep
        x, y = arc_point(angle)
        radius = 4 * SCALE
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=highlight)
    elif shape == 'trace' and trace:
        position = sweep * (len(trace) - 1)
        index = int(position)
        point = trace[index]
        if point is not None:
            x, y = point
            if index + 1 < len(trace) and trace[index + 1] is not None:
                next_x, next_y = trace[index + 1]
                fraction = position - index
                x += (next_x - x) * fraction
                y += (next_y - y) * fraction
            radius = 3 * SCALE
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=highlight)
    elif shape == 'halo':
        phase = (phase + .34) % 1
        radius = (82 + 23 * phase) * SCALE
        center = 120 * SCALE
        alpha = round(166 * math.sin(math.pi * phase))
        if alpha:
            draw.ellipse((center - radius, center - radius, center + radius, center + radius),
                         outline=(*highlight, alpha), width=3 * SCALE)
    elif shape == 'segments':
        head = (clock / 4 % 1) * len(SEGMENT_ANGLES)
        for index, (start, end) in enumerate(SEGMENT_ANGLES):
            distance = (head - index) % len(SEGMENT_ANGLES)
            if distance < 5:
                strength = (1 - distance / 5)**1.5
                tone = tuple(round(a + (b-a)*strength) for a, b in zip(dim(color, .26), highlight))
                round_arc(draw, start, end, tone)
    elif shape == 'radar':
        angle = (clock / 4 % 1) * 360 - 90
        box = radar_box(98)
        for index in range(8):
            end = angle - 48 + 6*(index+1)
            draw.pieslice(box, end-6, end, fill=(*highlight, 8+index*6))
        radians = math.radians(angle)
        x, y = (120 + 98*math.cos(radians))*SCALE, (120 + 98*math.sin(radians))*SCALE
        draw.line((120*SCALE, 120*SCALE, x, y), fill=(*highlight, 180), width=2*SCALE)
        draw.ellipse(box, outline=dim(color, .28), width=SCALE)


class PresetRenderer:
    def __init__(self, fps, *, design, provider, font_path, font_weight,
                 temperature_decimals, temperature_unit, comet_speed, accent,
                 animation, comet_style, background_path, background_dim,
                 gpu_accent=DEFAULT_GPU_ACCENT, gpu_effect_style='accent'):
        self.fps = fps
        self.design = design
        self.provider = provider
        self.font_path = resolve_font(font_path)
        self.weight = font_weight
        self.decimals = temperature_decimals
        self.temperature_unit = temperature_unit
        self.speed = comet_speed
        self.accent = accent_rgb(accent)
        self.gpu_accent = accent_rgb(gpu_accent)
        self.animated = animation != 'none'
        self.effect_style = comet_style
        self.gpu_effect_style = gpu_effect_style
        self.background = Background(background_path, background_dim)
        self.offset = 0
        self.sampled_at = None
        self.values = (None,) * 4
        self.history = deque(maxlen=60)
        self.trace = []
        self.base = None

    def close(self):
        self.background.close()
        self.history.clear()
        self.trace.clear()

    def comet_time(self, elapsed):
        return elapsed * self.speed + self.offset

    def inherit_motion(self, other, elapsed):
        self.offset = -elapsed * self.speed
        if isinstance(other, PresetRenderer) and other.design == self.design:
            self.offset += other.comet_time(elapsed)
            self.history.extend(other.history)

    def arc_value(self, elapsed):
        value = self.values[0]
        return 0 if value is None else max(0, min(1, value / 100))

    def text(self, draw, x, y, value, size, color=WHITE, max_width=170):
        face = font(self.font_path, size, self.weight)
        while size > 12 and face.getlength(value) > max_width * SCALE:
            size -= 1
            face = font(self.font_path, size, self.weight)
        if face.getlength(value) > max_width * SCALE:
            value = 'N/A'
        draw.text((x * SCALE, y * SCALE), value, fill=color, font=face, anchor='mm')

    def temp(self, value):
        if value is None:
            return 'N/A'
        return temperature(value, self.decimals, self.temperature_unit) + '°'

    def sample(self, elapsed):
        self.values = readings(self.provider())
        self.sampled_at = elapsed
        size = (240 * SCALE, 240 * SCALE)
        if self.background.enabled:
            self.base = Image.new('RGBA', size)
        else:
            self.base = Image.new('RGB', size, (5, 8, 10))
        draw = ImageDraw.Draw(self.base)
        if not self.background.enabled:
            draw.ellipse((2 * SCALE, 2 * SCALE, 238 * SCALE, 238 * SCALE), fill=(9, 15, 18))
        if self.design == 'dual':
            self.draw_dual(draw)
        elif self.design == 'trace':
            self.draw_trace(draw, elapsed)
        else:
            self.draw_halo(draw)

    def draw_dual(self, draw):
        cpu_temp, cpu_clock, gpu_temp, gpu_clock = self.values
        draw_effect_base(draw, 'dual_cpu', self.accent)
        draw_effect_base(draw, 'dual_gpu', self.gpu_accent)
        draw.line((120 * SCALE, 78 * SCALE, 120 * SCALE, 160 * SCALE), fill=(45, 65, 73), width=SCALE)
        for x, name, temp, clock, color in (
            (74, 'CPU', cpu_temp, cpu_clock, self.accent),
            (166, 'GPU', gpu_temp, gpu_clock, self.gpu_accent),
        ):
            self.text(draw, x, 79, name, 15, color)
            self.text(draw, x, 116, self.temp(temp), 31, max_width=83)
            self.text(draw, x, 146, frequency(clock), 13, MUTED, max_width=83)
        self.text(draw, 120, 181, '°' + self.temperature_unit, 14, MUTED)

    def draw_trace(self, draw, elapsed):
        cpu_temp, _, gpu_temp, _ = self.values
        self.trace = update_trace(self.history, elapsed, cpu_temp)
        draw_effect_base(draw, 'trace', self.accent, self.trace)
        self.text(draw, 120, 49, 'CPU · °' + self.temperature_unit, 14, self.accent)
        self.text(draw, 120, 88, self.temp(cpu_temp), 47, max_width=140)
        self.text(draw, 120, 178, '60 s', 13, MUTED)
        self.text(draw, 120, 201, f'GPU  {self.temp(gpu_temp)}', 14, max_width=135)

    def draw_halo(self, draw):
        cpu_temp, cpu_clock, gpu_temp, _ = self.values
        self.text(draw, 120, 69, 'CPU · °' + self.temperature_unit, 14, self.accent)
        self.text(draw, 120, 111, self.temp(cpu_temp), 49, max_width=150)
        self.text(draw, 120, 148, frequency(cpu_clock), 16, MUTED)
        self.text(draw, 120, 177, f'GPU  {self.temp(gpu_temp)}', 14, max_width=140)

    def __call__(self, elapsed):
        if self.sampled_at is None or elapsed < self.sampled_at or elapsed - self.sampled_at >= 1:
            self.sample(elapsed)
        if self.background.enabled:
            image = self.background.frame(elapsed).convert('RGB').resize(self.base.size, Image.Resampling.LANCZOS)
            image.paste(self.base, (0, 0), self.base)
        else:
            image = self.base.copy()
        if self.animated:
            self.draw_motion(image, elapsed)
        return image.resize((240, 240), Image.Resampling.LANCZOS), 1 / self.fps

    def draw_motion(self, image, elapsed):
        draw = ImageDraw.Draw(image, 'RGBA')
        clock = self.comet_time(elapsed)
        if self.design == 'dual':
            draw_effect_motion(draw, 'dual_cpu', self.accent, clock, self.effect_style)
            draw_effect_motion(draw, 'dual_gpu', self.gpu_accent, clock, self.gpu_effect_style)
        else:
            draw_effect_motion(draw, self.design, self.accent, clock, self.effect_style, self.trace)
