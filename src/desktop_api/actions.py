"""High-level wrappers around pyautogui for basic desktop automation."""
from __future__ import annotations

import pyautogui

from .window import WindowHandle


def move_mouse(
    x: int,
    y: int,
    *,
    duration: float = 0.0,
    relative_to: WindowHandle | None = None,
) -> None:
    target_x, target_y = _resolve_coordinates(x, y, relative_to)
    pyautogui.moveTo(target_x, target_y, duration=duration)


def mouse_down(
    x: int,
    y: int,
    *,
    button: str = "left",
    duration: float = 0.0,
    relative_to: WindowHandle | None = None,
) -> None:
    target_x, target_y = _resolve_coordinates(x, y, relative_to)
    pyautogui.moveTo(target_x, target_y, duration=duration)
    pyautogui.mouseDown(x=target_x, y=target_y, button=button)


def mouse_up(
    x: int,
    y: int,
    *,
    button: str = "left",
    duration: float = 0.0,
    relative_to: WindowHandle | None = None,
) -> None:
    target_x, target_y = _resolve_coordinates(x, y, relative_to)
    pyautogui.moveTo(target_x, target_y, duration=duration)
    pyautogui.mouseUp(x=target_x, y=target_y, button=button)


def click(
    x: int,
    y: int,
    *,
    button: str = "left",
    clicks: int = 1,
    interval: float = 0.1,
    duration: float = 0.0,
    relative_to: WindowHandle | None = None,
) -> None:
    target_x, target_y = _resolve_coordinates(x, y, relative_to)
    pyautogui.click(
        x=target_x,
        y=target_y,
        button=button,
        clicks=clicks,
        interval=interval,
        duration=duration,
    )


def double_click(
    x: int,
    y: int,
    *,
    button: str = "left",
    interval: float = 0.1,
    relative_to: WindowHandle | None = None,
) -> None:
    click(
        x,
        y,
        button=button,
        clicks=2,
        interval=interval,
        relative_to=relative_to,
    )


def drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    *,
    button: str = "left",
    duration: float = 0.2,
    relative_to: WindowHandle | None = None,
) -> None:
    sx, sy = _resolve_coordinates(start_x, start_y, relative_to)
    ex, ey = _resolve_coordinates(end_x, end_y, relative_to)
    pyautogui.moveTo(sx, sy)
    pyautogui.dragTo(ex, ey, button=button, duration=duration)


def scroll(
    clicks: int,
    *,
    x: int | None = None,
    y: int | None = None,
    relative_to: WindowHandle | None = None,
) -> None:
    if x is not None or y is not None:
        current_x, current_y = pyautogui.position()
        relative_x = x if x is not None else current_x - (relative_to.left if relative_to else 0)
        relative_y = y if y is not None else current_y - (relative_to.top if relative_to else 0)
        target_x, target_y = _resolve_coordinates(relative_x, relative_y, relative_to)
        pyautogui.moveTo(target_x, target_y)
    pyautogui.scroll(clicks)


def type_text(text: str, *, interval: float = 0.0) -> None:
    pyautogui.write(text, interval=interval)


def send_hotkey(*keys: str, interval: float = 0.0) -> None:
    pyautogui.hotkey(*keys, interval=interval)


def _resolve_coordinates(
    x: int,
    y: int,
    relative_to: WindowHandle | None,
) -> tuple[int, int]:
    if relative_to is None:
        return int(x), int(y)
    return int(relative_to.left + x), int(relative_to.top + y)
