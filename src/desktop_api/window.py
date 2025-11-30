"""Utilities for discovering and interacting with native application windows."""
from __future__ import annotations

import sys
import importlib
from dataclasses import dataclass
from typing import Any, List

import pyautogui

try:  # pygetwindow raises at import time on unsupported platforms
    import pygetwindow as gw  # type: ignore[import]
except (ImportError, NotImplementedError):  # pragma: no cover - optional dependency
    gw = None  # type: ignore[assignment]

X = None
Xatom = None
xdisplay = None
xerror = None
protocol = None

if sys.platform.startswith("linux"):  # pragma: no cover - platform-specific
    try:
        X = importlib.import_module("Xlib.X")
        Xatom = importlib.import_module("Xlib.Xatom")
        xdisplay = importlib.import_module("Xlib.display")
        xerror = importlib.import_module("Xlib.error")
        protocol = importlib.import_module("Xlib.protocol")
    except Exception:
        X = None  # type: ignore[assignment]
        Xatom = None  # type: ignore[assignment]
        xdisplay = None  # type: ignore[assignment]
        xerror = None  # type: ignore[assignment]
        protocol = None  # type: ignore[assignment]

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
_IS_LINUX = sys.platform.startswith("linux")
_HAS_NATIVE_ENUM = bool(gw and hasattr(gw, "getAllWindows"))
_LINUX_DISPLAY = None


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
    if _IS_LINUX:
        return _list_windows_linux(min_title_length)
    raise RuntimeError(
        "Window enumeration is not supported on this platform. "
        "macOS requires pyobjc; Linux requires python-xlib/X11."
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

    if _IS_MAC:
        refreshed = _mac_resolve_window(target)
        if refreshed is None:
            raise WindowNotFoundError(str(target))
        _mac_activate_pid(refreshed.pid)
        return refresh_window(refreshed)

    if _IS_LINUX:
        refreshed = _linux_resolve_window(target)
        if refreshed is None:
            raise WindowNotFoundError(str(target))
        _linux_activate_handle(refreshed.handle)
        return refresh_window(refreshed)

    raise RuntimeError("activate_window is not implemented on this platform.")


def refresh_window(target: WindowHandle | str) -> WindowHandle:
    """Return a fresh snapshot of the window geometry."""

    if _HAS_NATIVE_ENUM:
        window_obj = _resolve_window_object(target)
        if window_obj is None:
            raise WindowNotFoundError(str(target))
        return _to_handle(window_obj)

    if _IS_MAC:
        refreshed = _mac_resolve_window(target)
        if refreshed is None:
            raise WindowNotFoundError(str(target))
        return refreshed

    if _IS_LINUX:
        refreshed = _linux_resolve_window(target)
        if refreshed is None:
            raise WindowNotFoundError(str(target))
        return refreshed

    raise RuntimeError("refresh_window is not implemented on this platform.")


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


def _list_windows_linux(min_title_length: int) -> List[WindowHandle]:
    handles: List[WindowHandle] = []
    for snapshot in _iter_linux_windows():
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


def _iter_linux_windows():
    _ensure_linux_support()
    disp = _linux_display()
    root = disp.screen().root
    active_handle = _linux_active_window()

    candidates = _linux_client_list(disp, root)
    if not candidates:
        candidates = _linux_collect_reparented_clients(root)

    for window_id in candidates:
        snapshot = _linux_snapshot_window(disp, root, window_id, active_handle)
        if snapshot is not None:
            yield snapshot


def _linux_client_list(disp, root):
    candidate_atoms = (
        "_NET_CLIENT_LIST_STACKING",
        "_NET_CLIENT_LIST",
    )
    for atom_name in candidate_atoms:
        atom = disp.intern_atom(atom_name, True)
        if not atom:
            continue
        try:
            prop = root.get_full_property(atom, Xatom.WINDOW)
        except Exception:
            continue
        if prop and getattr(prop, "value", None):
            values = list(prop.value)
            if values:
                return list(dict.fromkeys(int(window_id) for window_id in values))

    fallback = _linux_collect_reparented_clients(root)
    if fallback:
        return fallback
    return []


def _linux_collect_reparented_clients(root):
    collected: list[int] = []
    visited: set[int] = {int(root.id)}
    stack: list[Any] = [root]

    while stack:
        window = stack.pop()
        try:
            children = window.query_tree().children
        except Exception:
            continue
        for child in children:
            child_id = int(child.id)
            if child_id in visited:
                continue
            visited.add(child_id)
            collected.append(child_id)
            stack.append(child)
    return collected


def _linux_snapshot_window(disp, root, window_id, active_handle):
    try:
        window = disp.create_resource_object("window", window_id)
    except Exception:
        return None
    for candidate in _linux_iter_window_candidates(window):
        if not _linux_is_window_visible(candidate):
            continue
        title = _linux_window_title(disp, candidate)
        if not title:
            continue
        geometry = _linux_window_geometry(candidate, root, disp)
        if geometry is None:
            continue
        left, top, width, height = geometry
        if width <= 1 or height <= 1:
            continue
        return WindowHandle(
            title=title,
            left=left,
            top=top,
            width=width,
            height=height,
            is_active=(active_handle is not None and int(candidate.id) == int(active_handle)),
            handle=int(candidate.id),
            platform="linux",
            pid=_linux_window_pid(disp, candidate),
        )
    return None


def _linux_iter_window_candidates(window):
    stack = [window]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        wid = int(getattr(current, "id", 0))
        if wid in seen:
            continue
        seen.add(wid)
        yield current
        try:
            children = current.query_tree().children
        except Exception:
            continue
        for child in children or []:
            stack.append(child)


def _linux_window_title(disp, window) -> str:
    atom_utf8 = disp.intern_atom("UTF8_STRING", True)
    name_atoms = ("_NET_WM_VISIBLE_NAME", "_NET_WM_NAME", "WM_NAME")

    for atom_name in name_atoms:
        atom = disp.intern_atom(atom_name, True)
        if not atom:
            continue
        try:
            if atom_name == "WM_NAME":
                target_type = Xatom.STRING
            else:
                target_type = atom_utf8 or Xatom.STRING
            prop = window.get_full_property(atom, target_type)
        except Exception:
            continue
        if prop and prop.value:
            decoded = _linux_decode_property(prop.value)
            decoded = decoded.strip()
            if decoded:
                return decoded

    fallback = _linux_fallback_wm_name(window)
    if fallback:
        return fallback

    class_name = _linux_window_class(window)
    if class_name:
        return class_name
    return ""


def _linux_decode_property(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        try:
            return bytes(value).decode("utf-8", errors="ignore")
        except Exception:
            pass
    if hasattr(value, "tolist"):
        try:
            data = bytes(value.tolist())
            return data.decode("utf-8", errors="ignore")
        except Exception:
            pass
    return ""


def _linux_fallback_wm_name(window) -> str:
    try:
        name = window.get_wm_name()
    except Exception:
        return ""
    if not name:
        return ""
    if isinstance(name, bytes):
        return name.decode("utf-8", errors="ignore").strip()
    return str(name).strip()


def _linux_window_class(window) -> str:
    try:
        wm_class = window.get_wm_class()
    except Exception:
        return ""
    if not wm_class:
        return ""
    parts: list[str] = []
    for entry in wm_class:
        if not entry:
            continue
        if isinstance(entry, bytes):
            parts.append(entry.decode("utf-8", errors="ignore"))
        else:
            parts.append(str(entry))
    return " ".join(part for part in parts if part).strip()


def _linux_window_geometry(window, root, disp=None):
    if disp is None:
        disp = _linux_display()

    # Get frame extents - these affect how we interpret geometry
    net_extents = _linux_get_property_extents(disp, window, "_NET_FRAME_EXTENTS")
    gtk_extents = _linux_get_property_extents(disp, window, "_GTK_FRAME_EXTENTS")

    try:
        geom = window.get_geometry()
    except Exception:
        return None

    width = int(geom.width)
    height = int(geom.height)
    border_width = int(getattr(geom, "border_width", 0))

    # Get absolute position of the window
    try:
        result = window.translate_coords(root, 0, 0)
        # translate_coords returns an object with x, y attributes (not a tuple)
        left = int(-result.x)
        top = int(-result.y)
    except Exception:
        # Fallback: walk up the window tree to accumulate position
        left, top = 0, 0
        current = window
        visited: set[int] = set()
        while True:
            wid = int(getattr(current, "id", 0))
            if wid in visited:
                break
            visited.add(wid)
            try:
                g = current.get_geometry()
            except Exception:
                break
            left += int(g.x)
            top += int(g.y)
            try:
                tree = current.query_tree()
            except Exception:
                break
            parent = getattr(tree, "parent", None)
            if parent is None or int(getattr(parent, "id", 0)) == int(getattr(root, "id", 0)):
                break
            current = parent

    # Handle _GTK_FRAME_EXTENTS (CSD shadows)
    # GTK frame extents indicate shadow area INCLUDED in the geometry
    # We SUBTRACT them to get the actual visible content
    if gtk_extents != (0, 0, 0, 0):
        gtk_left, gtk_right, gtk_top, gtk_bottom = gtk_extents
        left += gtk_left
        top += gtk_top
        width -= gtk_left + gtk_right
        height -= gtk_top + gtk_bottom
    # Handle _NET_FRAME_EXTENTS (SSD decorations) only if no GTK extents
    # NET frame extents indicate decorations OUTSIDE the geometry
    # We ADD them to include title bar/borders
    elif net_extents != (0, 0, 0, 0):
        net_left, net_right, net_top, net_bottom = net_extents
        left -= net_left
        top -= net_top
        width += net_left + net_right
        height += net_top + net_bottom

    # Account for border width
    width += 2 * border_width
    height += 2 * border_width

    return left, top, width, height


def _linux_get_property_extents(disp, window, atom_name: str) -> tuple[int, int, int, int]:
    """Get window extents (left, right, top, bottom) from an X property."""
    atom = disp.intern_atom(atom_name, True)
    if not atom:
        return (0, 0, 0, 0)
    try:
        prop = window.get_full_property(atom, Xatom.CARDINAL)
    except Exception:
        return (0, 0, 0, 0)
    if prop and prop.value and len(prop.value) >= 4:
        try:
            return (int(prop.value[0]), int(prop.value[1]), int(prop.value[2]), int(prop.value[3]))
        except Exception:
            pass
    return (0, 0, 0, 0)


def _linux_window_pid(disp, window) -> int | None:
    atom = disp.intern_atom("_NET_WM_PID", True)
    if not atom:
        return None
    try:
        prop = window.get_full_property(atom, Xatom.CARDINAL)
    except Exception:
        return None
    if prop and prop.value:
        try:
            return int(prop.value[0])
        except Exception:
            return None
    return None


def _linux_is_window_visible(window) -> bool:
    try:
        attrs = window.get_attributes()
    except Exception:
        return True
    return attrs.map_state != getattr(X, "IsUnmapped", 0)


def _linux_resolve_window(target: WindowHandle | str) -> WindowHandle | None:
    desired_handle = target.handle if isinstance(target, WindowHandle) else None
    desired_title = target.title if isinstance(target, WindowHandle) else str(target)
    normalized_title = desired_title.lower() if desired_title else None

    candidates = _list_windows_linux(min_title_length=1)
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


def _linux_activate_handle(handle: int | None) -> None:
    if handle is None:
        return
    try:
        disp = _linux_display()
    except RuntimeError:
        return
    if protocol is None or X is None:
        return
    root = disp.screen().root
    window = disp.create_resource_object("window", handle)
    atom = disp.intern_atom("_NET_ACTIVE_WINDOW", True)
    if not atom:
        return
    event = protocol.event.ClientMessage(
        window=window,
        client_type=atom,
        data=(32, [1, X.CurrentTime, handle, 0, 0]),
    )
    mask = X.SubstructureRedirectMask | X.SubstructureNotifyMask
    try:
        root.send_event(event, event_mask=mask)
        disp.flush()
    except Exception:
        pass


def _linux_active_window() -> int | None:
    if not _IS_LINUX or xdisplay is None:
        return None
    try:
        disp = _linux_display()
    except RuntimeError:
        return None
    atom = disp.intern_atom("_NET_ACTIVE_WINDOW", True)
    if not atom:
        return None
    root = disp.screen().root
    try:
        prop = root.get_full_property(atom, Xatom.WINDOW)
    except Exception:
        return None
    if prop and prop.value:
        try:
            return int(prop.value[0])
        except Exception:
            return None
    return None


def _linux_display():
    global _LINUX_DISPLAY
    _ensure_linux_support()
    if _LINUX_DISPLAY is None:
        try:
            _LINUX_DISPLAY = xdisplay.Display()  # type: ignore[call-arg]
        except Exception as exc:
            raise RuntimeError(
                "Unable to connect to the X server. Ensure DISPLAY is set and "
                "you are running under X11 or XWayland."
            ) from exc
    return _LINUX_DISPLAY


def _ensure_linux_support() -> None:
    if not _IS_LINUX:
        raise RuntimeError("Linux window enumeration requested on a different platform.")
    if xdisplay is None or X is None or Xatom is None or protocol is None:
        raise RuntimeError(
            "Linux window enumeration requires python-xlib (python3-xlib package) "
            "and an X11 session."
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
