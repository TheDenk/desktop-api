"""Screenshot helpers."""
from __future__ import annotations

from typing import Tuple

import mss
from PIL import Image

from .window import WindowHandle, activate_window, refresh_window

Region = Tuple[int, int, int, int]


def capture_screen(monitor: int = 0) -> Image.Image:
    """Capture a screenshot of the selected monitor (0 = virtual full screen)."""

    with mss.mss() as sct:
        monitor_index = max(0, min(monitor, len(sct.monitors) - 1))
        monitor_area = sct.monitors[monitor_index]
        raw = sct.grab(monitor_area)
    return Image.frombytes("RGB", raw.size, raw.rgb)


def capture_region(region: Region | dict[str, int]) -> Image.Image:
    """Capture an arbitrary region defined by (left, top, width, height)."""

    left, top, width, height = _normalize_region(region)
    width = max(1, width)
    height = max(1, height)
    with mss.mss() as sct:
        raw = sct.grab({"left": left, "top": top, "width": width, "height": height})
    return Image.frombytes("RGB", raw.size, raw.rgb)


def capture_window(
    target: WindowHandle | str,
    *,
    activate: bool = False,
    padding: int = 0,
) -> Image.Image:
    """Capture the contents of a native window."""

    window = activate_window(target) if activate else refresh_window(target)
    if padding < 0:
        raise ValueError("padding must be >= 0")

    region = window.as_region()
    if padding:
        region["left"] -= padding
        region["top"] -= padding
        region["width"] += padding * 2
        region["height"] += padding * 2
    return capture_region(region)


def _normalize_region(region: Region | dict[str, int]) -> Region:
    if isinstance(region, tuple):
        return region
    return (
        region["left"],
        region["top"],
        region["width"],
        region["height"],
    )
