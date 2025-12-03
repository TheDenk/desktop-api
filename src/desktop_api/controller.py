"""Facade class that ties together window management, capture, and actions."""
from __future__ import annotations

import pyautogui
from PIL import Image

from . import actions, capture, window
from .window import WindowHandle


class DesktopController:
    """Convenient entry point for cross-platform desktop automation."""

    def __init__(self, *, fail_safe: bool = True, pause: float = 0.0) -> None:
        pyautogui.FAILSAFE = fail_safe
        pyautogui.PAUSE = pause

    # Window discovery -------------------------------------------------
    def list_windows(self, *, min_title_length: int = 1) -> list[WindowHandle]:
        return window.list_windows(min_title_length=min_title_length)

    def find_window(
        self,
        query: str,
        *,
        exact: bool = False,
        case_sensitive: bool = False,
        min_title_length: int = 1,
        activate: bool = True,
    ) -> WindowHandle:
        handle = window.find_window(
            query,
            exact=exact,
            case_sensitive=case_sensitive,
            min_title_length=min_title_length,
        )
        if activate:
            return window.activate_window(handle)
        return handle

    def activate_window(self, target: WindowHandle | str) -> WindowHandle:
        return window.activate_window(target)

    def refresh_window(self, target: WindowHandle | str) -> WindowHandle:
        return window.refresh_window(target)

    # Capture ----------------------------------------------------------
    def capture_screen(self, monitor: int = 0) -> Image.Image:
        return capture.capture_screen(monitor=monitor)

    def capture_window(
        self,
        target: WindowHandle | str,
        *,
        activate: bool = False,
        padding: int = 0,
    ) -> Image.Image:
        return capture.capture_window(target, activate=activate, padding=padding)

    def capture_region(self, region: capture.Region | dict[str, int]) -> Image.Image:
        return capture.capture_region(region)

    # Mouse ------------------------------------------------------------
    def move_mouse(
        self,
        x: int,
        y: int,
        *,
        duration: float = 0.0,
        relative_to: WindowHandle | None = None,
    ) -> None:
        actions.move_mouse(x, y, duration=duration, relative_to=relative_to)

    def mouse_down(
        self,
        x: int,
        y: int,
        *,
        button: str = "left",
        duration: float = 0.0,
        relative_to: WindowHandle | None = None,
    ) -> None:
        actions.mouse_down(
            x,
            y,
            button=button,
            duration=duration,
            relative_to=relative_to,
        )

    def mouse_up(
        self,
        x: int,
        y: int,
        *,
        button: str = "left",
        duration: float = 0.0,
        relative_to: WindowHandle | None = None,
    ) -> None:
        actions.mouse_up(
            x,
            y,
            button=button,
            duration=duration,
            relative_to=relative_to,
        )

    def click(
        self,
        x: int,
        y: int,
        *,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.1,
        duration: float = 0.0,
        relative_to: WindowHandle | None = None,
    ) -> None:
        actions.click(
            x,
            y,
            button=button,
            clicks=clicks,
            interval=interval,
            duration=duration,
            relative_to=relative_to,
        )

    def double_click(
        self,
        x: int,
        y: int,
        *,
        button: str = "left",
        interval: float = 0.1,
        relative_to: WindowHandle | None = None,
    ) -> None:
        actions.double_click(
            x,
            y,
            button=button,
            interval=interval,
            relative_to=relative_to,
        )

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        *,
        button: str = "left",
        duration: float = 0.2,
        relative_to: WindowHandle | None = None,
    ) -> None:
        actions.drag(
            start_x,
            start_y,
            end_x,
            end_y,
            button=button,
            duration=duration,
            relative_to=relative_to,
        )

    def scroll(
        self,
        clicks: int,
        *,
        x: int | None = None,
        y: int | None = None,
        relative_to: WindowHandle | None = None,
    ) -> None:
        if relative_to:
            x = x if x is not None else relative_to.left + relative_to.width // 2
            y = y if y is not None else relative_to.top + relative_to.height // 2
        actions.scroll(clicks, x=x, y=y, relative_to=relative_to)

    # Keyboard ---------------------------------------------------------
    def type_text(self, text: str, *, interval: float = 0.0) -> None:
        actions.type_text(text, interval=interval)

    def send_hotkey(self, *keys: str, interval: float = 0.0) -> None:
        actions.send_hotkey(*keys, interval=interval)
