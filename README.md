## desktop-api

Cross-platform helper for capturing native application windows and performing simple GUI automation (click, double-click, press/release, drag, key presses, etc.). It is built on top of `pyautogui`, `pygetwindow`, and `mss`, so the same Python API works on macOS, Windows, and Linux.

## Features
- Enumerate, search, and activate native desktop windows
- Capture the entire screen, individual monitors, arbitrary regions, or a specific application window
- Perform mouse actions (move, click, double-click, drag, scroll) with optional coordinates relative to a target window
- Send keyboard input (text typing and hotkeys)
- Simple facade (`DesktopController`) for common automation workflows

## Installation
```bash
python -m venv .venv
source .venv/bin/activate  # (Linux/macOS)
# .venv\\Scripts\\activate.bat  # (Windows)
pip install -e .
```

### Platform requirements
- **macOS**: Install the app via `pip`, then grant *Input Monitoring* and *Screen Recording* permissions when prompted. Window enumeration also needs PyObjC bindings:
  ```bash
  pip install pyobjc-core pyobjc-framework-Quartz pyobjc-framework-Cocoa
  ```
- **Windows**: No additional dependencies. Run the terminal as Administrator if the target app is elevated.
- **Linux**: Requires X11 (Wayland is not supported by pyautogui yet). Install `scrot`, `python3-xlib`, and enable screen recording permissions if your desktop environment requires it.

## Quick start
```python
from desktop_api import DesktopController, WindowNotFoundError

controller = DesktopController(fail_safe=True, pause=0.1)

try:
    notes_window = controller.find_window("Notes")  # auto-activates by default
except WindowNotFoundError:
    raise SystemExit("Notes app must be opened")

# Capture to a PIL.Image
image = controller.capture_window(notes_window)
image.save("notes.png")

# Click 100x80 pixels relative to the Notes window
controller.click(100, 80, relative_to=notes_window)
controller.double_click(120, 120, relative_to=notes_window)
controller.type_text("Automated input!\n")
controller.send_hotkey("command", "s")  # Ctrl+S on Windows/Linux

# Draw a short diagonal stroke inside the Notes window
controller.mouse_down(60, 120, relative_to=notes_window)
controller.move_mouse(140, 200, relative_to=notes_window, duration=0.2)
controller.mouse_up(140, 200, relative_to=notes_window)
```

The controller automatically activates any window it finds so the UI is visible while your agent moves the cursor. Pass `activate=False` if you only need metadata.

## API overview
- `DesktopController.list_windows()` – list visible windows with geometry metadata
- `DesktopController.find_window(query, activate=True)` – fuzzy-search by title (exact or substring) and optionally bring it to the foreground
- `DesktopController.capture_window(target, activate=False, padding=0)` – capture an app window as `PIL.Image`
- `DesktopController.capture_screen(monitor=0)` and `capture_region((left, top, width, height))`
- `DesktopController.mouse_down(...)`, `mouse_up(...)`, `click(...)`, `double_click(...)`, `drag(...)`, `scroll(...)`
- `DesktopController.type_text(text)` and `send_hotkey(*keys)`

Every mouse method accepts a `relative_to` argument so you can provide coordinates within a specific window instead of global screen positions.

## Example scripts
`examples/demo.py` shows how to list windows, capture one, and perform a click. Run it with
```bash
python examples/demo.py --window "Safari"
```  

`examples/clicker.py` is a lightweight hotkey-based auto-clicker. Hold the configured key (default: `shift`) to emit clicks at the current cursor location; optionally supply `--toggle-hotkey` to flip continuous clicking on/off with a single press:
```bash
python examples/clicker.py --cps 15 --hotkey shift --toggle-hotkey space
```  

`examples/dummy_agent_loop.py` demonstrates an agent-style loop of capture → click → type → click → wait → capture.  
Replace the provided actions with calls into your AI agent (e.g., send every screenshot to a model, parse the response, and map its plan back to mouse/keyboard commands).

Press Ctrl+C to quit at any time.

## Safety tips
- Keep `fail_safe=True` (default) so moving the mouse to the top-left corner aborts automation
- Use short pauses (`pause` argument) to give GUIs time to update between actions
- When scripting destructive actions, add explicit confirmation logic around them
