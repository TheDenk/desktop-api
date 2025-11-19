"""Utilities for discovering and interacting with native application windows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

import pygetwindow as gw


class WindowNotFoundError(RuntimeError):
    """Raised when a window cannot be located by the provided query."""


@dataclass(frozen=True)
class WindowHandle:
    """Lightweight snapshot of a native window's geometry and state."""

    title: str
    left: int
    top: int
    width: int
    height: int
    is_active: bool
    handle: int | None = None
    platform: str | None = None

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def as_region(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


def list_windows(min_title_length: int = 1) -> List[WindowHandle]:
    """Return visible windows whose titles satisfy the length requirement."""

    windows: List[WindowHandle] = []
    active = gw.getActiveWindow()
    active_handle = _extract_handle(active) if active else None

    for window in gw.getAllWindows():
        if not window.title or len(window.title.strip()) < min_title_length:
            continue
        if window.isMinimized:
            continue
        windows.append(_to_handle(window, active_handle))
    return windows


def find_window(
    query: str,
    *,
    exact: bool = False,
    case_sensitive: bool = False,
    min_title_length: int = 1,
) -> WindowHandle:
    """Locate the first window that matches the provided query."""

    query_to_match = query if case_sensitive else query.lower()
    for window in list_windows(min_title_length=min_title_length):
        title = window.title if case_sensitive else window.title.lower()
        if (exact and title == query_to_match) or (not exact and query_to_match in title):
            return window
    raise WindowNotFoundError(f"No window found for query: {query}")


def activate_window(target: WindowHandle | str) -> WindowHandle:
    """Bring the selected window to the foreground and return its updated handle."""

    window_obj = _resolve_window_object(target)
    if window_obj is None:
        raise WindowNotFoundError(str(target))
    window_obj.activate()
    return _to_handle(window_obj)


def refresh_window(target: WindowHandle | str) -> WindowHandle:
    """Return a fresh snapshot of the window geometry."""

    window_obj = _resolve_window_object(target)
    if window_obj is None:
        raise WindowNotFoundError(str(target))
    return _to_handle(window_obj)


def _to_handle(window: Any, active_handle: int | None = None) -> WindowHandle:
    # pygetwindow shares the same class name on every platform.
    left, top, right, bottom = window.left, window.top, window.right, window.bottom
    width = max(0, right - left)
    height = max(0, bottom - top)
    resolved_active = active_handle
    if resolved_active is None:
        resolved_active = _extract_handle(gw.getActiveWindow())
    window_handle = _extract_handle(window)

    return WindowHandle(
        title=window.title,
        left=left,
        top=top,
        width=width,
        height=height,
        is_active=window_handle == resolved_active,
        handle=window_handle,
        platform=_detect_platform(window),
    )


def _extract_handle(window: Any | None) -> int | None:
    if window is None:
        return None
    for attr in ("_hWnd", "_nsWindowNumber", "_xid"):
        handle = getattr(window, attr, None)
        if handle:
            return int(handle)
    return None


def _detect_platform(window: Any) -> str | None:
    if hasattr(window, "_hWnd"):
        return "windows"
    if hasattr(window, "_nsWindowNumber"):
        return "mac"
    if hasattr(window, "_xid"):
        return "linux"
    return None


def _resolve_window_object(target: WindowHandle | str):
    if isinstance(target, WindowHandle):
        if target.handle is not None:
            for window in gw.getAllWindows():
                if _extract_handle(window) == target.handle:
                    return window
        target_title = target.title
    else:
        target_title = target

    matches = gw.getWindowsWithTitle(target_title)
    return matches[0] if matches else None
