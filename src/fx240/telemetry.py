# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only sysfs providers. Missing data stays unavailable, never zero."""
from dataclasses import dataclass, asdict
import math
from pathlib import Path


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    value: float | None
    unit: str
    source: str

    def record(self):
        return asdict(self)


def read(path):
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def number(path, scale):
    try:
        value = float(read(path)) / scale
        return value if math.isfinite(value) else None
    except ValueError:
        return None


def collect(sysroot=Path("/sys")):
    root = Path(sysroot)
    metrics = []
    # Restrict temperature conversion to drivers with standard temperature units.
    cpu = {"coretemp", "k10temp", "zenpower"}
    gpu = {"amdgpu", "radeon", "nouveau"}
    for hw in sorted((root / "class/hwmon").glob("hwmon*")):
        driver = read(hw / "name")
        group = "CPU" if driver in cpu else "GPU" if driver in gpu else None
        if group is None:
            continue
        for kind, unit, scale in (("temp", "C", 1000), ("freq", "MHz", 1000000)):
            for path in sorted(hw.glob(f"{kind}[0-9]*_input")):
                channel = path.name.removesuffix("_input")
                label = read(hw / (channel + "_label")) or channel
                value = number(path, scale)
                if read(hw / (channel + "_fault")) == "1" or read(hw / (channel + "_enable")) == "0":
                    value = None
                metrics.append(Metric(f"{hw.name}/{channel}", f"{group} {driver} {label}", value, unit, str(path)))
    for policy in sorted((root / "devices/system/cpu/cpufreq").glob("policy*")):
        path = policy / "scaling_cur_freq"
        metrics.append(Metric(f"cpu/{policy.name}", f"CPU {policy.name}", number(path, 1000), "MHz", str(path)))
    return metrics
