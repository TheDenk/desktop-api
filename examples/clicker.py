"""Simple hotkey-driven auto-clicker example."""
from __future__ import annotations

import argparse
import threading
import time
from typing import Optional

import pyautogui
from pynput import keyboard

from desktop_api import DesktopController

SPECIAL_KEYS = {
    "shift": keyboard.Key.shift,
    "ctrl": keyboard.Key.ctrl,
    "control": keyboard.Key.ctrl,
    "alt": keyboard.Key.alt,
    "option": keyboard.Key.alt,
    "cmd": keyboard.Key.cmd,
    "command": keyboard.Key.cmd,
    "space": keyboard.Key.space,
    "tab": keyboard.Key.tab,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cps",
        type=float,
        default=10.0,
        help="Clicks per second while the hotkey is held (default: 10)",
    )
    parser.add_argument(
        "--button",
        choices=["left", "right", "middle"],
        default="left",
        help="Mouse button to click",
    )
    parser.add_argument(
        "--hotkey",
        "--hold-hotkey",
        dest="hold_hotkey",
        default="shift",
        help="Key that must be held to emit clicks (special keys: shift, ctrl, alt, cmd, space, tab)",
    )
    parser.add_argument(
        "--toggle-hotkey",
        help="Optional key that toggles continuous clicking on/off when pressed (no need to hold)",
    )
    parser.add_argument(
        "--fail-safe",
        action="store_true",
        help="Enable pyautogui fail-safe (move mouse to top-left to abort). Off by default for smoother clicking.",
    )
    return parser.parse_args()


class HotkeyClicker:
    def __init__(
        self,
        cps: float,
        button: str,
        hold_hotkey: keyboard.Key | keyboard.KeyCode,
        toggle_hotkey: keyboard.Key | keyboard.KeyCode | None = None,
    ) -> None:
        if cps <= 0:
            raise ValueError("cps must be positive")
        self.interval = 1.0 / cps
        self.button = button
        self.hold_hotkey = hold_hotkey
        self.toggle_hotkey = toggle_hotkey
        self.controller = DesktopController(fail_safe=False, pause=0.0)
        self._active = False
        self._hold_engaged = False
        self._toggled = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        with keyboard.Listener(on_press=self._on_press, on_release=self._on_release) as listener:
            parts = [f"Hold {self._format_hotkey(self.hold_hotkey)} to click"]
            if self.toggle_hotkey:
                parts.append(f"press {self._format_hotkey(self.toggle_hotkey)} to toggle auto-click")
            print(", ".join(parts) + ". Ctrl+C to exit.")
            listener.join()

    def _format_hotkey(self, hotkey: keyboard.Key | keyboard.KeyCode) -> str:
        if isinstance(hotkey, keyboard.Key):
            return f"<{hotkey.name}>"
        if isinstance(hotkey, keyboard.KeyCode):
            return repr(hotkey.char)
        return str(hotkey)

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if key == self.hold_hotkey:
            self._hold_engaged = True
            self._update_state()
        elif self.toggle_hotkey and key == self.toggle_hotkey:
            self._toggled = not self._toggled
            state = "ON" if self._toggled else "OFF"
            print(f"Toggled auto-click: {state}")
            self._update_state()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if key == self.hold_hotkey:
            self._hold_engaged = False
            self._update_state()

    def _update_state(self) -> None:
        should_run = self._hold_engaged or self._toggled
        if should_run and not self._active:
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._click_loop, daemon=True)
            self._thread.start()
            self._active = True
        elif not should_run and self._active:
            self._stop_event.set()
            self._active = False

    def _click_loop(self) -> None:
        print("Auto-clicking...")
        try:
            while not self._stop_event.is_set():
                x, y = pyautogui.position()
                self.controller.click(x, y, button=self.button)
                time.sleep(self.interval)
        finally:
            print("Stopped.")


def parse_hotkey(token: str) -> keyboard.Key | keyboard.KeyCode:
    key = token.lower()
    if key in SPECIAL_KEYS:
        return SPECIAL_KEYS[key]
    if len(key) == 1:
        return keyboard.KeyCode.from_char(key)
    raise ValueError(f"Unsupported hotkey: {token}")


def main() -> int:
    args = parse_args()
    hold_hotkey = parse_hotkey(args.hold_hotkey)
    toggle_hotkey = parse_hotkey(args.toggle_hotkey) if args.toggle_hotkey else None

    if args.fail_safe:
        pyautogui.FAILSAFE = True

    clicker = HotkeyClicker(
        cps=args.cps,
        button=args.button,
        hold_hotkey=hold_hotkey,
        toggle_hotkey=toggle_hotkey,
    )
    try:
        clicker.start()
    except KeyboardInterrupt:
        print("Exiting auto-clicker")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
