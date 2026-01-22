"""Tests for screenshot capture functionality."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from desktop_api.capture import (
    _clamp_region_to_screen,
    capture_region,
    capture_window,
)
from desktop_api.window import WindowHandle


class TestClampRegionToScreen:
    """Tests for _clamp_region_to_screen function."""

    @patch("desktop_api.capture.pyautogui.size")
    def test_clamp_normal_region(self, mock_size):
        """Test that normal regions within screen bounds are unchanged."""
        mock_size.return_value = (1920, 1080)
        left, top, width, height = _clamp_region_to_screen(100, 100, 800, 600)
        assert left == 100
        assert top == 100
        assert width == 800
        assert height == 600

    @patch("desktop_api.capture.pyautogui.size")
    def test_clamp_negative_coordinates(self, mock_size):
        """Test that negative coordinates are clamped to 0."""
        mock_size.return_value = (1920, 1080)
        left, top, width, height = _clamp_region_to_screen(-50, -30, 800, 600)
        assert left == 0
        assert top == 0
        assert width == 750  # Adjusted because left was moved from -50 to 0
        assert height == 570  # Adjusted because top was moved from -30 to 0

    @patch("desktop_api.capture.pyautogui.size")
    def test_clamp_fullscreen_window_exceeds_right(self, mock_size):
        """Test fullscreen window that extends beyond right edge."""
        mock_size.return_value = (1920, 1080)
        # Window reports bounds that exceed screen width
        left, top, width, height = _clamp_region_to_screen(0, 0, 2000, 1080)
        assert left == 0
        assert top == 0
        assert width == 1920  # Clamped to screen width
        assert height == 1080

    @patch("desktop_api.capture.pyautogui.size")
    def test_clamp_fullscreen_window_exceeds_bottom(self, mock_size):
        """Test fullscreen window that extends beyond bottom edge."""
        mock_size.return_value = (1920, 1080)
        # Window reports bounds that exceed screen height
        left, top, width, height = _clamp_region_to_screen(0, 0, 1920, 1200)
        assert left == 0
        assert top == 0
        assert width == 1920
        assert height == 1080  # Clamped to screen height

    @patch("desktop_api.capture.pyautogui.size")
    def test_clamp_fullscreen_window_exceeds_both(self, mock_size):
        """Test fullscreen window that exceeds both width and height."""
        mock_size.return_value = (1920, 1080)
        # Window reports bounds larger than screen
        left, top, width, height = _clamp_region_to_screen(0, 0, 2560, 1440)
        assert left == 0
        assert top == 0
        assert width == 1920  # Clamped to screen width
        assert height == 1080  # Clamped to screen height

    @patch("desktop_api.capture.pyautogui.size")
    def test_clamp_window_offset_beyond_screen(self, mock_size):
        """Test window that starts beyond screen bounds."""
        mock_size.return_value = (1920, 1080)
        # Window starts at position beyond screen
        left, top, width, height = _clamp_region_to_screen(2000, 1200, 800, 600)
        assert left == 1920  # Clamped to screen edge
        assert top == 1080  # Clamped to screen edge
        assert width == 1  # Minimum width
        assert height == 1  # Minimum height

    @patch("desktop_api.capture.pyautogui.size")
    def test_clamp_ensures_minimum_size(self, mock_size):
        """Test that clamped region always has at least 1x1 size."""
        mock_size.return_value = (1920, 1080)
        # Region that would result in zero or negative size
        left, top, width, height = _clamp_region_to_screen(2000, 1200, 100, 50)
        assert width >= 1
        assert height >= 1

    @patch("desktop_api.capture.pyautogui.size")
    def test_clamp_partial_overlap(self, mock_size):
        """Test window that partially overlaps screen bounds."""
        mock_size.return_value = (1920, 1080)
        # Window partially extends beyond screen
        left, top, width, height = _clamp_region_to_screen(1800, 1000, 500, 300)
        assert left == 1800
        assert top == 1000
        assert width == 120  # Clamped: 1800 + 500 = 2300, but screen is 1920
        assert height == 80  # Clamped: 1000 + 300 = 1300, but screen is 1080


class TestCaptureRegion:
    """Tests for capture_region function."""

    @patch("desktop_api.capture.mss.mss")
    @patch("desktop_api.capture.pyautogui.size")
    def test_capture_region_normal(self, mock_size, mock_mss_class):
        """Test normal region capture."""
        mock_size.return_value = (1920, 1080)
        mock_sct = MagicMock()
        mock_mss_class.return_value.__enter__.return_value = mock_sct
        mock_grab = MagicMock()
        mock_grab.size = (800, 600)
        mock_grab.rgb = b"\x00" * (800 * 600 * 3)
        mock_sct.grab.return_value = mock_grab

        result = capture_region({"left": 100, "top": 100, "width": 800, "height": 600})
        assert isinstance(result, Image.Image)
        assert result.size == (800, 600)
        mock_sct.grab.assert_called_once_with(
            {"left": 100, "top": 100, "width": 800, "height": 600}
        )

    @patch("desktop_api.capture.mss.mss")
    @patch("desktop_api.capture.pyautogui.size")
    def test_capture_region_fullscreen_clamped(self, mock_size, mock_mss_class):
        """Test that fullscreen regions are clamped before capture."""
        mock_size.return_value = (1920, 1080)
        mock_sct = MagicMock()
        mock_mss_class.return_value.__enter__.return_value = mock_sct
        mock_grab = MagicMock()
        mock_grab.size = (1920, 1080)
        mock_grab.rgb = b"\x00" * (1920 * 1080 * 3)
        mock_sct.grab.return_value = mock_grab

        # Try to capture region larger than screen
        result = capture_region({"left": 0, "top": 0, "width": 2560, "height": 1440})
        assert isinstance(result, Image.Image)
        # Should be clamped to screen size
        mock_sct.grab.assert_called_once_with(
            {"left": 0, "top": 0, "width": 1920, "height": 1080}
        )

    @patch("desktop_api.capture.mss.mss")
    @patch("desktop_api.capture.pyautogui.size")
    def test_capture_region_negative_coords(self, mock_size, mock_mss_class):
        """Test that negative coordinates are clamped."""
        mock_size.return_value = (1920, 1080)
        mock_sct = MagicMock()
        mock_mss_class.return_value.__enter__.return_value = mock_sct
        mock_grab = MagicMock()
        mock_grab.size = (700, 500)
        mock_grab.rgb = b"\x00" * (700 * 500 * 3)
        mock_sct.grab.return_value = mock_grab

        result = capture_region({"left": -50, "top": -30, "width": 800, "height": 600})
        assert isinstance(result, Image.Image)
        # Should clamp negative coords and adjust size
        call_args = mock_sct.grab.call_args[0][0]
        assert call_args["left"] >= 0
        assert call_args["top"] >= 0
        assert call_args["width"] > 0
        assert call_args["height"] > 0


class TestCaptureWindow:
    """Tests for capture_window function."""

    @patch("desktop_api.capture.refresh_window")
    @patch("desktop_api.capture.mss.mss")
    @patch("desktop_api.capture.pyautogui.size")
    def test_capture_window_fullscreen_fallback(
        self, mock_size, mock_mss_class, mock_refresh_window
    ):
        """Test that fullscreen windows use region-based capture with clamping."""
        mock_size.return_value = (1920, 1080)
        # Create a window handle with bounds larger than screen (fullscreen scenario)
        window = WindowHandle(
            title="Test Fullscreen",
            left=0,
            top=0,
            width=2560,  # Larger than screen width
            height=1440,  # Larger than screen height
            is_active=True,
            handle=12345,
            platform="mac",
            pid=1234,
        )
        mock_refresh_window.return_value = window

        mock_sct = MagicMock()
        mock_mss_class.return_value.__enter__.return_value = mock_sct
        mock_grab = MagicMock()
        mock_grab.size = (1920, 1080)
        mock_grab.rgb = b"\x00" * (1920 * 1080 * 3)
        mock_sct.grab.return_value = mock_grab

        result = capture_window(window, activate=False, padding=0)
        assert isinstance(result, Image.Image)

        # Should clamp to screen bounds
        call_args = mock_sct.grab.call_args[0][0]
        assert call_args["width"] <= 1920
        assert call_args["height"] <= 1080
        assert call_args["left"] >= 0
        assert call_args["top"] >= 0

    @patch("desktop_api.capture.refresh_window")
    @patch("desktop_api.capture.mss.mss")
    @patch("desktop_api.capture.pyautogui.size")
    def test_capture_window_with_padding_clamped(
        self, mock_size, mock_mss_class, mock_refresh_window
    ):
        """Test that padding doesn't cause out-of-bounds capture."""
        mock_size.return_value = (1920, 1080)
        # Window at edge of screen with padding
        window = WindowHandle(
            title="Test Edge Window",
            left=1900,
            top=1000,
            width=20,
            height=80,
            is_active=True,
            handle=12345,
            platform="mac",
            pid=1234,
        )
        mock_refresh_window.return_value = window

        mock_sct = MagicMock()
        mock_mss_class.return_value.__enter__.return_value = mock_sct
        mock_grab = MagicMock()
        mock_grab.size = (100, 200)
        mock_grab.rgb = b"\x00" * (100 * 200 * 3)
        mock_sct.grab.return_value = mock_grab

        # Add padding that would extend beyond screen
        result = capture_window(window, activate=False, padding=50)
        assert isinstance(result, Image.Image)

        # Should clamp padded region to screen bounds
        call_args = mock_sct.grab.call_args[0][0]
        assert call_args["left"] >= 0
        assert call_args["top"] >= 0
        assert call_args["left"] + call_args["width"] <= 1920
        assert call_args["top"] + call_args["height"] <= 1080

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    @patch("desktop_api.capture.Quartz")
    @patch("desktop_api.capture.refresh_window")
    @patch("desktop_api.capture.mss.mss")
    @patch("desktop_api.capture.pyautogui.size")
    def test_capture_window_quartz_fallback_on_error(
        self, mock_size, mock_mss_class, mock_refresh_window, mock_quartz
    ):
        """Test that Quartz API failure falls back to region-based capture."""
        mock_size.return_value = (1920, 1080)
        window = WindowHandle(
            title="Test Window",
            left=0,
            top=0,
            width=800,
            height=600,
            is_active=True,
            handle=12345,
            platform="mac",
            pid=1234,
        )
        mock_refresh_window.return_value = window

        # Make Quartz API fail
        mock_quartz.CGWindowListCreateImage.return_value = None

        mock_sct = MagicMock()
        mock_mss_class.return_value.__enter__.return_value = mock_sct
        mock_grab = MagicMock()
        mock_grab.size = (800, 600)
        mock_grab.rgb = b"\x00" * (800 * 600 * 3)
        mock_sct.grab.return_value = mock_grab

        result = capture_window(window, activate=False, padding=0)
        assert isinstance(result, Image.Image)
        # Should have fallen back to region-based capture
        mock_sct.grab.assert_called_once()
