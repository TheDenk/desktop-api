"""Capture a screenshot from a chosen app window on left press and log click data to CSV."""
from __future__ import annotations

import argparse
import csv
import logging
from datetime import datetime
from pathlib import Path

from pynput import mouse

from desktop_api.capture import capture_window
from desktop_api.window import WindowHandle, activate_window, refresh_window

OUTPUT_DIR = Path(__file__).parent / "captures"
CSV_PATH = Path(__file__).parent / "captures.csv"

# Create output directories/files up front to keep the handler simple.
OUTPUT_DIR.mkdir(exist_ok=True)

press_pos: tuple[int, int] | None = None
current_image_path: Path | None = None
active_window: WindowHandle | None = None
press_window: WindowHandle | None = None


def init_csv() -> None:
    if not CSV_PATH.exists():
        with CSV_PATH.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["image_path", "press_x", "press_y", "release_x", "release_y", "reasoning"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--window",
        required=True,
        help="Substring match for the target window title (case-insensitive)",
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=0,
        help="Optional padding (pixels) around the window capture",
    )
    return parser.parse_args()


def _point_in_window(x: int, y: int, window: WindowHandle) -> bool:
    """Return True if the screen point (x, y) falls within the window bounds."""
    return window.left <= x <= window.right and window.top <= y <= window.bottom


def on_click(x: int, y: int, button: mouse.Button, pressed: bool) -> None:
    """Handle left-button press/release events."""
    global press_pos, current_image_path, active_window, press_window

    if button != mouse.Button.left:
        return

    if pressed:
        if active_window is None:
            return

        active_window = refresh_window(active_window)
        if not _point_in_window(x, y, active_window):
            logging.debug("Ignoring press outside target window at (%d, %d)", x, y)
            return

        press_window = active_window
        press_pos = (x - press_window.left, y - press_window.top)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        current_image_path = OUTPUT_DIR / f"snap_{ts}.png"

        image = capture_window(press_window, activate=False, padding=ARGS.padding)
        image.save(current_image_path)
        logging.info("Captured %s", current_image_path)
    else:
        if press_pos is None or current_image_path is None or press_window is None:
            return

        release_pos = (x - press_window.left, y - press_window.top)
        with CSV_PATH.open("a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    str(current_image_path),
                    press_pos[0],
                    press_pos[1],
                    release_pos[0],
                    release_pos[1],
                    "",  # reasoning reserved for future use
                ]
            )
        logging.info("Logged click to %s", CSV_PATH)
        press_pos = None
        current_image_path = None
        press_window = None


def main() -> int:
    init_csv()
    # Resolve and activate the target window once at startup, then refresh on every click.
    try:
        global active_window
        active_window = activate_window(ARGS.window)
        logging.info(
            "Tracking window: %r at (%d, %d)",
            active_window.title,
            active_window.left,
            active_window.top,
        )
    except Exception as exc:  # pragma: no cover - example script
        logging.error("Unable to activate window matching %r: %s", ARGS.window, exc)
        return 1

    with mouse.Listener(on_click=on_click) as listener:
        logging.info("Left press captures the target window; release logs CSV. Ctrl+C to exit.")
        listener.join()
    return 0


if __name__ == "__main__":
    ARGS = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    raise SystemExit(main())
