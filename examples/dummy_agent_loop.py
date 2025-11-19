"""Agent-style loop that captures, acts, and waits repeatedly."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from desktop_api import DesktopController, WindowHandle, WindowNotFoundError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", required=True, help="Window title to automate")
    parser.add_argument(
        "--focus-click",
        type=int,
        nargs=2,
        metavar=("X", "Y"),
        default=(40, 40),
        help="Relative coords for the first click (e.g., focus input field)",
    )
    parser.add_argument(
        "--submit-click",
        type=int,
        nargs=2,
        metavar=("X", "Y"),
        default=(80, 80),
        help="Relative coords for the second click (e.g., submit button)",
    )
    parser.add_argument(
        "--text",
        default="Automated message",
        help="Text to type after the first click",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="How many times to run the capture-act loop",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.5,
        help="Seconds to wait between iterations",
    )
    parser.add_argument(
        "--output-dir",
        default="captures",
        help="Directory to store screenshots for each iteration",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.05,
        help="pyautogui pause between low-level actions",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    controller = DesktopController(pause=args.pause)

    try:
        target_window = controller.find_window(args.window)
    except WindowNotFoundError as exc:  # pragma: no cover - example script
        print(exc)
        return 1

    controller.activate_window(target_window)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(args.iterations):
        print(f"=== Iteration {idx + 1}/{args.iterations} ===")
        target_window = controller.refresh_window(target_window)
        image = controller.capture_window(target_window)

        image_path = output_dir / f"iteration_{idx:03d}.png"
        image.save(image_path)
        print(f"Saved screenshot to {image_path.resolve()}")

        # Replace the actions below with calls into your AI agent's plan.
        # ...
        # _focus_and_type(controller, target_window, args.focus_click, args.text)
        # _submit(controller, target_window, args.submit_click)

        if idx < args.iterations - 1:
            time.sleep(args.interval)

    return 0


def _focus_and_type(
    controller: DesktopController,
    target_window: WindowHandle,
    coords: tuple[int, int],
    text: str,
) -> None:
    controller.click(*coords, relative_to=target_window)
    if text:
        controller.type_text(text)


def _submit(
    controller: DesktopController,
    target_window: WindowHandle,
    coords: tuple[int, int],
) -> None:
    controller.click(*coords, relative_to=target_window)


if __name__ == "__main__":
    raise SystemExit(main())
