"""Utilities for discovering and interacting with native application windows."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, List

import pyautogui
import pygetwindow as gw

try:  # macOS-only dependencies
    import Quartz
except Exception:  # pragma: no cover - platform-specific
    Quartz = None  # type: ignore[assignment]

try:  # pragma: no cover - platform-specific
    from AppKit import (
        NSApplicationActivateIgnoringOtherApps,
        NSRunningApplication,
        NSWorkspace,
    )
except Exception:  # pragma: no cover - platform-specific
    NSApplicationActivateIgnoringOtherApps = 0  # type: ignore[assignment]
    NSRunningApplication = None  # type: ignore[assignment]
    NSWorkspace = None  # type: ignore[assignment]

_IS_MAC = sys.platform == "darwin"
_HAS_NATIVE_ENUM = hasattr(gw, "getAllWindows")


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
    pid: int | None = None

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

    if _HAS_NATIVE_ENUM:
        return _list_windows_via_pygetwindow(min_title_length)
    if _IS_MAC:
        return _list_windows_macos(min_title_length)
    raise RuntimeError(
        "pygetwindow does not expose getAllWindows() on this platform. "
        "Install the appropriate OS dependencies "
        "(pyobjc for macOS) or upgrade pygetwindow."
    )


def find_window(
    query: str,
    *,
    exact: bool = False,
    case_sensitive: bool = False,
    min_title_length: int = 1,
) -> WindowHandle:
    """Locate the first window that matches the provided query."""

    query_to_match = query if case_sensitive else query.lower()
    for handle in list_windows(min_title_length=min_title_length):
        title = handle.title if case_sensitive else handle.title.lower()
        if (exact and title == query_to_match) or (not exact and query_to_match in title):
            return handle
    raise WindowNotFoundError(f"No window found for query: {query}")


def activate_window(target: WindowHandle | str) -> WindowHandle:
    """Bring the selected window to the foreground and return its updated handle."""

    if _HAS_NATIVE_ENUM:
        window_obj = _resolve_window_object(target)
        if window_obj is None:
            raise WindowNotFoundError(str(target))
        window_obj.activate()
        return _to_handle(window_obj)

    refreshed = _mac_resolve_window(target)
    if refreshed is None:
        raise WindowNotFoundError(str(target))
    _mac_activate_pid(refreshed.pid)
    return refresh_window(refreshed)


def refresh_window(target: WindowHandle | str) -> WindowHandle:
    """Return a fresh snapshot of the window geometry."""

    if _HAS_NATIVE_ENUM:
        window_obj = _resolve_window_object(target)
        if window_obj is None:
            raise WindowNotFoundError(str(target))
        return _to_handle(window_obj)

    refreshed = _mac_resolve_window(target)
    if refreshed is None:
        raise WindowNotFoundError(str(target))
    return refreshed


def _list_windows_via_pygetwindow(min_title_length: int) -> List[WindowHandle]:
    windows: List[WindowHandle] = []
    active = gw.getActiveWindow()
    active_handle = _extract_handle(active) if active else None

    for win in gw.getAllWindows():
        if not win.title or len(win.title.strip()) < min_title_length:
            continue
        if win.isMinimized:
            continue
        windows.append(_to_handle(win, active_handle))
    return windows


def _list_windows_macos(min_title_length: int) -> List[WindowHandle]:
    handles: List[WindowHandle] = []
    for snapshot in _iter_macos_windows():
        if len(snapshot.title.strip()) >= min_title_length:
            handles.append(snapshot)
    return handles


def _iter_macos_windows():
    _ensure_mac_support()
    options = Quartz.kCGWindowListExcludeDesktopElements | Quartz.kCGWindowListOptionOnScreenOnly
    info_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID) or []
    screen_height = pyautogui.size().height
    active_pid = _mac_frontmost_pid()
    seen: set[tuple[int, int]] = set()

    for info in info_list:
        if info.get("kCGWindowLayer", 0) != 0:
            continue
        title = _mac_window_title(info)
        if not title:
            continue
        bounds = info.get("kCGWindowBounds", {})
        width = int(bounds.get("Width", 0))
        height = int(bounds.get("Height", 0))
        left = int(bounds.get("X", 0))
        # Quartz coordinates origin is bottom-left; convert to top-left.
        raw_y = int(bounds.get("Y", 0))
        top = int(screen_height - (raw_y + height))

        handle = int(info.get("kCGWindowNumber", 0))
        pid = int(info.get("kCGWindowOwnerPID", 0))
        key = (pid, handle)
        if key in seen:
            continue
        seen.add(key)

        yield WindowHandle(
            title=title,
            left=left,
            top=top,
            width=max(0, width),
            height=max(0, height),
            is_active=(active_pid is not None and pid == active_pid),
            handle=handle,
            platform="mac",
            pid=pid,
        )


def _mac_window_title(info: Any) -> str:
    owner = info.get(Quartz.kCGWindowOwnerName, "") if Quartz else ""
    name = info.get(Quartz.kCGWindowName, "") if Quartz else ""
    title = f"{owner} {name}".strip()
    return title


def _mac_resolve_window(target: WindowHandle | str) -> WindowHandle | None:
    desired_handle = target.handle if isinstance(target, WindowHandle) else None
    desired_title = target.title if isinstance(target, WindowHandle) else str(target)
    normalized_title = desired_title.lower() if desired_title else None

    candidates = _list_windows_macos(min_title_length=1)
    if desired_handle is not None:
        for candidate in candidates:
            if candidate.handle == desired_handle:
                return candidate

    if normalized_title:
        for candidate in candidates:
            if candidate.title.lower() == normalized_title:
                return candidate
        for candidate in candidates:
            if normalized_title in candidate.title.lower():
                return candidate
    return None


def _mac_activate_pid(pid: int | None) -> None:
    if pid is None or NSRunningApplication is None:
        return
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app is not None:
        app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)


def _mac_frontmost_pid() -> int | None:
    if NSWorkspace is None:
        return None
    workspace = NSWorkspace.sharedWorkspace()
    active_app = workspace.frontmostApplication()
    if active_app is None:
        return None
    return active_app.processIdentifier()


def _ensure_mac_support() -> None:
    if not _IS_MAC:
        raise RuntimeError("macOS-specific window enumeration requested on a different platform.")
    if Quartz is None or NSWorkspace is None or NSRunningApplication is None:
        raise RuntimeError(
            "macOS window enumeration requires pyobjc-core, pyobjc-framework-Quartz, "
            "and pyobjc-framework-Cocoa. Install them in your virtual environment."
        )


def _to_handle(window: Any, active_handle: int | None = None) -> WindowHandle:
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
    if not _HAS_NATIVE_ENUM:
        return None
    if isinstance(target, WindowHandle):
        if target.handle is not None:
            for win in gw.getAllWindows():
                if _extract_handle(win) == target.handle:
                    return win
        target_title = target.title
    else:
        target_title = target

    matches = gw.getWindowsWithTitle(target_title)
    return matches[0] if matches else None
