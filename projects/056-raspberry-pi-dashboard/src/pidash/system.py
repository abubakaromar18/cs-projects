"""Read-only system vitals: CPU temperature, load average, uptime, memory.

On a Pi these come from the Linux pseudo-filesystems (/sys and /proc). Each
reader degrades gracefully to ``None`` so the dashboard still works on macOS
or Windows during development. The root paths are injectable for tests.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def cpu_temp_c(sys_root: Path = Path("/sys")) -> float | None:
    """Kernel reports millidegrees Celsius in thermal_zone0/temp."""
    raw = _read(sys_root / "class/thermal/thermal_zone0/temp")
    try:
        return round(int(raw) / 1000, 1) if raw else None
    except ValueError:
        return None


def uptime_seconds(proc_root: Path = Path("/proc")) -> float | None:
    raw = _read(proc_root / "uptime")
    try:
        return float(raw.split()[0]) if raw else None
    except (ValueError, IndexError):
        return None


def memory_mb(proc_root: Path = Path("/proc")) -> dict[str, int] | None:
    """Parse MemTotal / MemAvailable (values are in kB) from /proc/meminfo."""
    raw = _read(proc_root / "meminfo")
    if not raw:
        return None
    fields: dict[str, int] = {}
    for line in raw.splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts and parts[0].isdigit():
            fields[key] = int(parts[0])
    if "MemTotal" not in fields or "MemAvailable" not in fields:
        return None
    return {"total": fields["MemTotal"] // 1024, "available": fields["MemAvailable"] // 1024}


def load_average() -> list[float] | None:
    try:
        return [round(x, 2) for x in os.getloadavg()]
    except (AttributeError, OSError):
        return None


def vitals(sys_root: Path = Path("/sys"), proc_root: Path = Path("/proc")) -> dict[str, Any]:
    return {
        "hostname": platform.node(),
        "cpu_temp_c": cpu_temp_c(sys_root),
        "uptime_s": uptime_seconds(proc_root),
        "load": load_average(),
        "memory_mb": memory_mb(proc_root),
    }
