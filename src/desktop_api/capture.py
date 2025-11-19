"""Screenshot helpers."""
from __future__ import annotations

import sys
from typing import Tuple

import mss
from PIL import Image

from .window import WindowHandle, activate_window, refresh_window

try:  # pragma: no cover - platform-specific
    import Quartz
except Exception:  # pragma: no cover - platform-specific
    Quartz = None  # type: ignore[assignment]

_IS_MAC = sys.platform == "darwin"

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

    if (
        _IS_MAC
        and Quartz is not None
        and window.platform == "mac"
        and window.handle is not None
        and padding == 0
    ):
        mac_image = _capture_window_macos(window)
        return mac_image.convert("RGB")

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


def _capture_window_macos(window: WindowHandle) -> Image.Image:
    if Quartz is None:  # pragma: no cover - platform-specific
        raise RuntimeError("Quartz is required for macOS window capture")
    if window.handle is None:
        raise RuntimeError("Cannot capture macOS window without a handle")

    image_ref = Quartz.CGWindowListCreateImage(
        Quartz.CGRectNull,
        Quartz.kCGWindowListOptionIncludingWindow,
        window.handle,
        Quartz.kCGWindowImageBoundsIgnoreFraming | Quartz.kCGWindowImageShouldBeOpaque,
    )
    if image_ref is None:
        raise RuntimeError("Unable to capture window via Quartz")

    width = Quartz.CGImageGetWidth(image_ref)
    height = Quartz.CGImageGetHeight(image_ref)
    if width == 0 or height == 0:
        raise RuntimeError("Captured window has zero size")

    data_provider = Quartz.CGImageGetDataProvider(image_ref)
    data = Quartz.CGDataProviderCopyData(data_provider)
    pixel_bytes = bytes(data)
    bytes_per_row = Quartz.CGImageGetBytesPerRow(image_ref)

    image = Image.frombuffer(
        "RGBA",
        (width, height),
        pixel_bytes,
        "raw",
        "BGRA",
        bytes_per_row,
        1,
    )
    return image
