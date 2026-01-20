"""Public API for the desktop_api package."""
from . import actions, capture, window
from .__version__ import __version__
from .controller import DesktopController
from .window import WindowHandle, WindowNotFoundError

__all__ = [
    "DesktopController",
    "WindowHandle",
    "WindowNotFoundError",
    "actions",
    "capture",
    "window",
  "__version__",
]
