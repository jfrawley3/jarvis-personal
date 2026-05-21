import base64
import pytest
from unittest.mock import patch, MagicMock


def _make_jpeg_bytes():
    """Minimal valid JPEG bytes for mocking."""
    import io
    try:
        from PIL import Image
        img = Image.new("RGB", (10, 10), color=(100, 100, 100))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except ImportError:
        return b"\xff\xd8\xff\xe0" + b"\x00" * 100  # fake JPEG header


class TestCaptureScreen:
    def test_returns_image_and_text_blocks(self):
        from tools.desktop import _handle_capture_screen
        fake_bytes = _make_jpeg_bytes()

        with patch("tools.desktop._capture_screen", return_value=(fake_bytes, "image/jpeg")):
            result = _handle_capture_screen({"source": "screen"})

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["type"] == "image"
        assert result[1]["type"] == "text"

    def test_image_block_is_valid_base64(self):
        from tools.desktop import _handle_capture_screen
        fake_bytes = _make_jpeg_bytes()

        with patch("tools.desktop._capture_screen", return_value=(fake_bytes, "image/jpeg")):
            result = _handle_capture_screen({})

        b64 = result[0]["source"]["data"]
        decoded = base64.b64decode(b64)
        assert decoded == fake_bytes

    def test_capture_error_returns_error_string(self):
        from tools.desktop import _handle_capture_screen

        with patch("tools.desktop._capture_screen", side_effect=RuntimeError("no display")):
            result = _handle_capture_screen({"source": "screen"})

        assert isinstance(result, str)
        assert "Capture failed" in result

    def test_camera_source_calls_capture_camera(self):
        from tools.desktop import _handle_capture_screen
        fake_bytes = _make_jpeg_bytes()

        with patch("tools.desktop._capture_camera", return_value=(fake_bytes, "image/jpeg")) as mock_cam:
            _handle_capture_screen({"source": "camera"})

        mock_cam.assert_called_once()


class TestComputerControl:
    def test_type_action(self):
        from tools.desktop import _handle_computer_control

        with patch("tools.desktop._type", return_value="Typed: hello") as mock_type:
            result = _handle_computer_control({"action": "type", "text": "hello"})

        mock_type.assert_called_once_with("hello")
        assert "Typed" in result

    def test_click_action(self):
        from tools.desktop import _handle_computer_control

        with patch("tools.desktop._click", return_value="Clicked (100, 200) [left]") as mock_click:
            result = _handle_computer_control({"action": "click", "x": 100, "y": 200})

        mock_click.assert_called_once_with(100, 200, "left", 1)
        assert "Clicked" in result

    def test_hotkey_action(self):
        from tools.desktop import _handle_computer_control

        with patch("tools.desktop._PYAUTOGUI", True), \
             patch("tools.desktop.pyautogui") as mock_pg:
            result = _handle_computer_control({"action": "hotkey", "keys": "ctrl+c"})

        assert "Hotkey" in result

    def test_wait_action_capped_at_30s(self):
        from tools.desktop import _handle_computer_control

        with patch("tools.desktop.time") as mock_time:
            mock_time.sleep = MagicMock()
            result = _handle_computer_control({"action": "wait", "seconds": 999})

        mock_time.sleep.assert_called_once_with(30.0)
        assert "30" in result

    def test_unknown_action_returns_error_string(self):
        from tools.desktop import _handle_computer_control
        result = _handle_computer_control({"action": "fly_to_moon"})
        assert "Unknown action" in result

    def test_missing_action_returns_error(self):
        from tools.desktop import _handle_computer_control
        result = _handle_computer_control({})
        assert "No action" in result

    def test_random_data_name(self):
        from tools.desktop import _handle_computer_control
        result = _handle_computer_control({"action": "random_data", "type": "name"})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_random_data_email_contains_at(self):
        from tools.desktop import _handle_computer_control
        result = _handle_computer_control({"action": "random_data", "type": "email"})
        assert "@" in result

    def test_double_click_action(self):
        from tools.desktop import _handle_computer_control

        with patch("tools.desktop._click", return_value="Double-clicked (50, 50) [left]") as mock_click:
            result = _handle_computer_control({"action": "double_click", "x": 50, "y": 50})

        mock_click.assert_called_once_with(50, 50, "left", 2)
