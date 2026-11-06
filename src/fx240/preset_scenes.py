# SPDX-License-Identifier: GPL-3.0-or-later
"""Translate the active built-in design into a local, editable scene."""
from .scene import layer


def builtin_scene(settings):
    design = settings.layout_mode
    accent = settings.accent if design == 'focus' else getattr(settings, design + '_accent')
    layers = []

    def effect(identifier, shape, color, animation='none', style='accent', **geometry):
        bounds = {'x': 0, 'y': 0, 'width': 240, 'height': 240, **geometry}
        layers.append(layer(identifier, 'effect', effect=shape, color=color,
                            animation=animation, effect_style=style, **bounds))

    def label(identifier, x, y, width, size, color='#edf4f5', *, text='', metric=None,
              prefix='', unit=False, degree_only=False):
        height = max(16, size + 10)
        layers.append(layer(
            identifier, 'metric' if metric else 'text', x=x-width//2, y=y-height//2,
            width=width, height=height, size=size, weight=settings.font_weight,
            font_path=settings.font_path, color=color, vertical_align='center',
            text=text, metric=metric or 'cpu_temp', label=prefix, unit_suffix=unit,
            degree_only=degree_only,
        ))

    if settings.background_path:
        layers.append(layer('background', 'media', path=settings.background_path, x=0, y=0,
                            width=240, height=240, opacity=1-settings.background_dim))
    else:
        effect('disc', 'disc', '#080b0e' if design == 'focus' else '#090f12')

    motion = settings.preset_animation
    if design == 'dual':
        gpu = settings.dual_gpu_accent
        effect('cpu-arc', 'dual_cpu', accent, motion, settings.comet_style)
        effect('gpu-arc', 'dual_gpu', gpu, motion, settings.dual_gpu_effect_style)
        effect('divider', 'divider', '#2d4149', x=114, y=78, width=12, height=82)
        for name, x, color in (('cpu', 74, accent), ('gpu', 166, gpu)):
            label(name+'-label', x, 79, 80, 15, color, text=name.upper())
            label(name+'-temp', x, 116, 83, 31, metric=name+'_temp', degree_only=True)
            label(name+'-clock', x, 146, 83, 13, '#a5b6bb', metric=name+'_clock')
        label('units', 120, 181, 58, 14, '#a5b6bb', unit=True)
    elif design == 'trace':
        effect('trace', 'trace', accent, motion, settings.comet_style)
        label('cpu-label', 120, 49, 112, 14, accent, text='CPU · ', unit=True)
        label('cpu-temp', 120, 88, 140, 47, metric='cpu_temp', degree_only=True)
        label('history-label', 120, 178, 62, 13, '#a5b6bb', text='60 s')
        label('gpu-temp', 120, 201, 135, 14, metric='gpu_temp', prefix='GPU', degree_only=True)
    elif design == 'halo':
        effect('halo', 'halo', accent, motion, settings.comet_style)
        label('cpu-label', 120, 69, 112, 14, accent, text='CPU · ', unit=True)
        label('cpu-temp', 120, 111, 150, 49, metric='cpu_temp', degree_only=True)
        label('cpu-clock', 120, 148, 136, 16, '#a5b6bb', metric='cpu_clock')
        label('gpu-temp', 120, 177, 140, 14, metric='gpu_temp', prefix='GPU', degree_only=True)
    else:
        layers.append(layer('focus-arc', 'arc', x=0, y=0, width=240, height=240, color=accent,
                            animation=settings.animation, effect_style=settings.comet_style))
        label('cpu-label', 120, 49, 80, 14, '#a5b6bb', text='CPU')
        label('cpu-temp', 120, 99, 185, 64, metric='cpu_temp')
        label('cpu-clock', 120, 146, 140, 18, accent, metric='cpu_clock')
        label('gpu-temp', 120, 183, 150, 18, metric='gpu_temp', prefix='GPU')
        label('gpu-clock', 120, 204, 115, 14, '#a5b6bb', metric='gpu_clock')
    return {'version': 1, 'temperature_unit': settings.temperature_unit,
            'temperature_decimals': settings.temperature_decimals, 'motion_speed': settings.comet_speed,
            'layers': layers}
