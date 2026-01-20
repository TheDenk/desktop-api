# desktop-api

Cross-platform Python library for desktop automation: capture screens/windows and control mouse & keyboard. Works on **macOS**, **Windows**, and **Linux**.

Built on `pyautogui`, `pygetwindow`, and `mss`.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Examples](#examples)
  - [Creating a Controller](#creating-a-controller)
  - [Finding Windows](#finding-windows)
  - [Taking Screenshots](#taking-screenshots)
  - [Mouse Operations](#mouse-operations)
  - [Keyboard Operations](#keyboard-operations)
- [API Reference](#api-reference)
- [Example Scripts](#example-scripts)
- [Safety Tips](#safety-tips)

---

## Installation

```bash
# Install from PyPI
pip install desktop-api

# Or install from source
# Clone and install
git clone https://github.com/thedenk/desktop-api.git
cd desktop-api

python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -e .
```

### Platform-Specific Requirements

| Platform | Additional Setup |
|----------|------------------|
| **macOS** | Grant *Screen Recording* and *Input Monitoring* permissions when prompted. Install PyObjC: `pip install pyobjc-core pyobjc-framework-Quartz pyobjc-framework-Cocoa` |
| **Windows** | No extra dependencies. Run as Administrator if automating elevated apps. |
| **Linux** | X11 only (Wayland not supported). Install: `sudo apt install scrot python3-xlib` |

---

## Quick Start

```python
from desktop_api import DesktopController, WindowNotFoundError

# Create a controller
controller = DesktopController()

# Find and capture a window
try:
    window = controller.find_window("Safari")
    screenshot = controller.capture_window(window)
    screenshot.save("safari.png")
except WindowNotFoundError:
    print("Safari is not open!")
```

---

## Examples

### Creating a Controller

The `DesktopController` is your main entry point for all automation tasks.

```python
from desktop_api import DesktopController

# Basic usage
controller = DesktopController()

# With safety options
controller = DesktopController(
    fail_safe=True,   # Move mouse to top-left corner to abort (default: True)
    pause=0.1         # Wait 0.1s between actions (default: 0.0)
)
```

**Tip:** Use `pause=0.1` to give GUIs time to respond between actions.

---

### Finding Windows

#### List All Open Windows

```python
from desktop_api import DesktopController

controller = DesktopController()

# Get all visible windows
windows = controller.list_windows()

for win in windows:
    print(f"{win.title}")
    print(f"  Position: ({win.left}, {win.top})")
    print(f"  Size: {win.width}x{win.height}")
    print(f"  Active: {win.is_active}")
    print()
```

#### Find a Specific Window

```python
from desktop_api import DesktopController, WindowNotFoundError

controller = DesktopController()

# Find by partial title match (case-insensitive)
try:
    window = controller.find_window("Chrome")
    print(f"Found: {window.title}")
except WindowNotFoundError:
    print("Window not found!")

# Find with exact title match
window = controller.find_window("Google Chrome", exact=True)

# Find without auto-activating the window
window = controller.find_window("Chrome", activate=False)

# Case-sensitive search
window = controller.find_window("Chrome", case_sensitive=True)
```

#### Activate and Refresh Windows

```python
# Bring window to foreground
controller.activate_window(window)

# Refresh window geometry (after resize/move)
window = controller.refresh_window(window)
print(f"New position: ({window.left}, {window.top})")
```

---

### Taking Screenshots

#### Capture Entire Screen

```python
from desktop_api import DesktopController

controller = DesktopController()

# Capture primary monitor (full virtual screen)
screenshot = controller.capture_screen()
screenshot.save("fullscreen.png")

# Capture specific monitor (0 = all, 1 = first, 2 = second, etc.)
monitor1 = controller.capture_screen(monitor=1)
monitor1.save("monitor1.png")
```

#### Capture a Window

```python
from desktop_api import DesktopController, WindowNotFoundError

controller = DesktopController()

try:
    window = controller.find_window("Notes")
    
    # Basic window capture
    screenshot = controller.capture_window(window)
    screenshot.save("notes.png")
    
    # Capture with padding around the window
    screenshot_padded = controller.capture_window(window, padding=20)
    screenshot_padded.save("notes_with_border.png")
    
    # Activate window before capturing (ensures it's visible)
    screenshot = controller.capture_window(window, activate=True)
    
except WindowNotFoundError:
    print("Notes app is not open!")
```

#### Capture a Region

```python
from desktop_api import DesktopController

controller = DesktopController()

# Capture specific area: (left, top, width, height)
region = controller.capture_region((100, 100, 800, 600))
region.save("region.png")

# Using dict format
region = controller.capture_region({
    "left": 100,
    "top": 100,
    "width": 800,
    "height": 600
})
```

---

### Mouse Operations

All mouse methods accept `relative_to` parameter for window-relative coordinates.

#### Click

```python
from desktop_api import DesktopController

controller = DesktopController()
window = controller.find_window("Notes")

# Click at absolute screen position
controller.click(500, 300)

# Click relative to window (100px right, 80px down from top-left)
controller.click(100, 80, relative_to=window)

# Right click
controller.click(100, 80, button="right", relative_to=window)

# Triple click (select paragraph)
controller.click(100, 80, clicks=3, relative_to=window)

# Double click
controller.double_click(100, 80, relative_to=window)
```

#### Move Mouse

```python
# Move instantly
controller.move_mouse(500, 300)

# Move with animation
controller.move_mouse(500, 300, duration=0.5)

# Move relative to window
controller.move_mouse(100, 100, relative_to=window)
```

#### Drag

```python
# Drag from point A to point B
controller.drag(
    start_x=100, start_y=100,
    end_x=300, end_y=200,
    duration=0.3,
    relative_to=window
)

# Draw a line in a drawing app
controller.drag(50, 50, 200, 200, relative_to=window)
```

#### Low-Level Mouse Control

```python
# Manual press and release (for custom drag operations)
controller.mouse_down(100, 100, relative_to=window)
controller.move_mouse(200, 200, relative_to=window, duration=0.5)
controller.mouse_up(200, 200, relative_to=window)
```

#### Scroll

```python
# Scroll down (negative = down, positive = up)
controller.scroll(-3)

# Scroll up
controller.scroll(5)

# Scroll at specific position
controller.scroll(-3, x=100, y=100, relative_to=window)
```

---

### Keyboard Operations

#### Type Text

```python
from desktop_api import DesktopController

controller = DesktopController()

# Type text instantly
controller.type_text("Hello, World!")

# Type with delay between characters
controller.type_text("Slow typing...", interval=0.05)

# Type with newline
controller.type_text("Line 1\nLine 2\n")
```

#### Send Hotkeys

```python
# Save file (Cmd+S on Mac, Ctrl+S on Windows/Linux)
controller.send_hotkey("command", "s")  # macOS
controller.send_hotkey("ctrl", "s")     # Windows/Linux

# Select all
controller.send_hotkey("command", "a")

# Copy
controller.send_hotkey("command", "c")

# Paste
controller.send_hotkey("command", "v")

# Undo
controller.send_hotkey("command", "z")

# Multiple modifiers
controller.send_hotkey("command", "shift", "s")  # Save As
```

---

## API Reference

### DesktopController Methods

| Method | Description |
|--------|-------------|
| `list_windows()` | List all visible windows |
| `find_window(query, exact=False, case_sensitive=False, activate=True)` | Find window by title |
| `activate_window(target)` | Bring window to foreground |
| `refresh_window(target)` | Get updated window geometry |
| `capture_screen(monitor=0)` | Screenshot of monitor |
| `capture_window(target, activate=False, padding=0)` | Screenshot of window |
| `capture_region(region)` | Screenshot of area |
| `click(x, y, button="left", clicks=1, relative_to=None)` | Mouse click |
| `double_click(x, y, relative_to=None)` | Double click |
| `move_mouse(x, y, duration=0.0, relative_to=None)` | Move cursor |
| `drag(start_x, start_y, end_x, end_y, duration=0.2, relative_to=None)` | Drag operation |
| `mouse_down(x, y, button="left", relative_to=None)` | Press mouse button |
| `mouse_up(x, y, button="left", relative_to=None)` | Release mouse button |
| `scroll(clicks, x=None, y=None, relative_to=None)` | Scroll wheel |
| `type_text(text, interval=0.0)` | Type string |
| `send_hotkey(*keys, interval=0.0)` | Send key combination |

### WindowHandle Properties

| Property | Description |
|----------|-------------|
| `title` | Window title |
| `left`, `top` | Position (top-left corner) |
| `width`, `height` | Dimensions |
| `right`, `bottom` | Computed edges |
| `is_active` | Whether window is focused |
| `handle` | Native window handle |
| `pid` | Process ID |

---

## Example Scripts

### `examples/demo.py`
Basic window capture and click demo:
```bash
python examples/demo.py --window "Safari" --output screenshot.png
```

### `examples/clicker.py`
Hotkey-based auto-clicker (requires `pip install pynput`):
```bash
# Hold Shift to click at 15 CPS
python examples/clicker.py --cps 15 --hotkey shift

# Toggle mode with Space key
python examples/clicker.py --cps 10 --toggle-hotkey space
```

### `examples/dummy_agent_loop.py`
Template for AI agent automation loops:
```bash
python examples/dummy_agent_loop.py --window "Notes" --iterations 5
```

---

## Complete Example: Automate Notes App

```python
"""Full example: Open Notes, type text, save file."""
from desktop_api import DesktopController, WindowNotFoundError
import time

controller = DesktopController(fail_safe=True, pause=0.1)

try:
    # Find the Notes window
    notes = controller.find_window("Notes")
    print(f"Found: {notes.title} at ({notes.left}, {notes.top})")
    
    # Take a "before" screenshot
    before = controller.capture_window(notes)
    before.save("before.png")
    
    # Click to focus the text area (adjust coordinates for your app)
    controller.click(200, 200, relative_to=notes)
    time.sleep(0.2)
    
    # Type some text
    controller.type_text("Hello from desktop-api!\n")
    controller.type_text("This is automated input.\n")
    
    # Save with Cmd+S (or Ctrl+S on Windows/Linux)
    controller.send_hotkey("command", "s")
    time.sleep(0.5)
    
    # Take an "after" screenshot
    after = controller.capture_window(notes)
    after.save("after.png")
    
    print("Done! Check before.png and after.png")
    
except WindowNotFoundError:
    print("Please open the Notes app first!")
```

---

## Safety Tips

1. **Keep `fail_safe=True`** – Moving mouse to top-left corner aborts automation
2. **Use `pause` parameter** – Gives GUIs time to respond between actions
3. **Test with non-destructive actions first** – Verify coordinates before automating
4. **Add confirmation logic** – For destructive operations, add explicit checks
5. **Use `activate=False`** – When you only need window metadata, not focus

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `WindowNotFoundError` | Check if window is open and title matches |
| Permission denied (macOS) | Grant Screen Recording & Input Monitoring in System Preferences |
| Wayland not working (Linux) | Use X11 or XWayland session |
| Clicks going to wrong position | Use `refresh_window()` to update geometry after window moves |
| Typing not working | Ensure target window has keyboard focus |
