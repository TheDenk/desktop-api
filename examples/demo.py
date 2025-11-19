"""Minimal demo for the desktop_api API."""
from __future__ import annotations

import argparse
from pathlib import Path

from desktop_api import DesktopController, WindowNotFoundError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--window",
        required=True,
        help="Window title (exact match or substring) to target",
    )
    parser.add_argument(
        "--output",
        default="capture.png",
        help="Where to save the captured screenshot",
    )
    parser.add_argument(
        "--relative-click",
        type=int,
        nargs=2,
        metavar=("X", "Y"),
        default=(40, 40),
        help="Relative coordinates to click inside the target window",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    controller = DesktopController(pause=0.1)

    try:
        target_window = controller.find_window(args.window)
    except WindowNotFoundError as exc:  # pragma: no cover - demo script
        print(exc)
        return 1

    controller.activate_window(target_window)
    image = controller.capture_window(target_window)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(f"Saved screenshot to {output_path.resolve()}")

    rel_x, rel_y = args.relative_click
    controller.click(rel_x, rel_y, relative_to=target_window)
    controller.type_text("Hello from desktop-api!\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
