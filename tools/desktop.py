"""
Desktop control tools — screen capture + mouse/keyboard automation.

Adapted from Mark XXXIX (FatihMakes/Mark-XXXIX):
  actions/screen_processor.py  — screen/camera capture
  actions/computer_control.py  — PyAutoGUI action dispatch

Key differences from the original:
  - Gemini Live audio session replaced by base64 image returned to Claude
  - screen_find/screen_click removed (Claude sees the screenshot directly)
  - Config reads from JARVIS env vars, not config/api_keys.json
  - No long_term.json memory; user_data falls back to random_data
"""

from __future__ import annotations

import base64
import io
import random
import string
import subprocess
import sys
import time
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

try:
    import mss
    import mss.tools
    _MSS = True
except ImportError:
    _MSS = False

try:
    import PIL.Image
    _PIL = True
except ImportError:
    _PIL = False

try:
    import cv2
    import numpy as np
    _CV2 = True
except ImportError:
    _CV2 = False

_IMG_MAX_W = 1280
_IMG_MAX_H = 720
_JPEG_Q    = 70


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")


def _compress(img_bytes: bytes) -> tuple[bytes, str]:
    if not _PIL:
        return img_bytes, "image/png"
    img = PIL.Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=_JPEG_Q, optimize=False)
    return buf.getvalue(), "image/jpeg"


def _capture_screen() -> tuple[bytes, str]:
    if _MSS:
        with mss.mss() as sct:
            target = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            shot   = sct.grab(target)
            png    = mss.tools.to_png(shot.rgb, shot.size)
        return _compress(png)

    if _PYAUTOGUI:
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return _compress(buf.getvalue())

    raise RuntimeError("No screenshot backend available. Run: pip install mss")


def _capture_camera() -> tuple[bytes, str]:
    if not _CV2:
        raise RuntimeError("OpenCV not installed. Run: pip install opencv-python")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open camera at index 0.")
    for _ in range(5):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise RuntimeError("Camera returned no frame.")
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = PIL.Image.fromarray(rgb)
    img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=_JPEG_Q)
    return buf.getvalue(), "image/jpeg"


def _type(text: str, interval: float = 0.03) -> str:
    _require_pyautogui()
    time.sleep(0.3)
    pyautogui.typewrite(text, interval=interval)
    return f"Typed: {text[:60]}{'…' if len(text) > 60 else ''}"


def _smart_type(text: str, clear_first: bool = True) -> str:
    _require_pyautogui()
    if clear_first:
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.press("delete")
        time.sleep(0.1)
    if len(text) > 20 and _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")
        return f"Smart-typed (clipboard): {text[:60]}{'…' if len(text) > 60 else ''}"
    pyautogui.typewrite(text, interval=0.04)
    return f"Smart-typed: {text[:60]}{'…' if len(text) > 60 else ''}"


def _click(x=None, y=None, button: str = "left", clicks: int = 1) -> str:
    _require_pyautogui()
    if x is not None and y is not None:
        pyautogui.click(x, y, button=button, clicks=clicks)
        return f"{'Double-c' if clicks == 2 else 'C'}licked ({x}, {y}) [{button}]"
    pyautogui.click(button=button, clicks=clicks)
    return "Clicked at current position"


def _focus_window(title: str) -> str:
    try:
        script = f'(New-Object -ComObject WScript.Shell).AppActivate("{title}")'
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, timeout=5,
        )
        time.sleep(0.3)
        return f"Focused window: {title}"
    except Exception as e:
        return f"focus_window failed: {e}"


_FIRST_NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn"]
_LAST_NAMES  = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
_DOMAINS     = ["gmail.com", "yahoo.com", "outlook.com", "proton.me"]


def _random_data(data_type: str) -> str:
    dt = data_type.lower().strip()
    if dt == "first_name": return random.choice(_FIRST_NAMES)
    if dt == "last_name":  return random.choice(_LAST_NAMES)
    if dt == "name":       return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"
    if dt == "email":
        return f"{random.choice(_FIRST_NAMES).lower()}.{random.choice(_LAST_NAMES).lower()}{random.randint(10,999)}@{random.choice(_DOMAINS)}"
    if dt == "username":   return f"{random.choice(_FIRST_NAMES).lower()}{random.randint(100,9999)}"
    if dt == "password":
        chars = string.ascii_letters + string.digits + "!@#$%"
        raw = random.choice(string.ascii_uppercase) + random.choice(string.digits) + random.choice("!@#$%") + "".join(random.choices(chars, k=9))
        return "".join(random.sample(raw, len(raw)))
    if dt == "phone":    return f"+1{random.randint(200,999)}{random.randint(1_000_000,9_999_999)}"
    if dt == "birthday":
        return f"{random.randint(1,12):02d}/{random.randint(1,28):02d}/{random.randint(1980,2000)}"
    return f"random_{data_type}_{random.randint(1000,9999)}"


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

def _handle_capture_screen(args: dict) -> list:
    source = args.get("source", "screen").lower()
    try:
        if source == "camera":
            image_bytes, mime_type = _capture_camera()
        else:
            image_bytes, mime_type = _capture_screen()
    except Exception as e:
        return f"Capture failed: {e}"

    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    w, h = (_PYAUTOGUI and pyautogui.size()) or ("?", "?")
    return [
        {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64}},
        {"type": "text",  "text": f"Screenshot captured ({w}×{h}). Describe what you see or specify a target to click."},
    ]


def _handle_computer_control(args: dict) -> str:
    action = args.get("action", "").lower().strip()
    if not action:
        return "No action specified."

    try:
        if action == "type":
            return _type(args.get("text", ""))

        if action == "smart_type":
            return _smart_type(args.get("text", ""), clear_first=args.get("clear_first", True))

        if action in ("click", "left_click"):
            return _click(args.get("x"), args.get("y"), "left", 1)

        if action == "double_click":
            return _click(args.get("x"), args.get("y"), "left", 2)

        if action == "right_click":
            return _click(args.get("x"), args.get("y"), "right", 1)

        if action == "move":
            _require_pyautogui()
            pyautogui.moveTo(int(args["x"]), int(args["y"]), duration=0.3)
            return f"Mouse → ({args['x']}, {args['y']})"

        if action == "drag":
            _require_pyautogui()
            pyautogui.moveTo(int(args["x1"]), int(args["y1"]), duration=0.2)
            pyautogui.dragTo(int(args["x2"]), int(args["y2"]), duration=0.5, button="left")
            return f"Dragged ({args['x1']},{args['y1']}) → ({args['x2']},{args['y2']})"

        if action == "hotkey":
            _require_pyautogui()
            raw  = args.get("keys", "")
            keys = [k.strip() for k in raw.split("+")] if isinstance(raw, str) else raw
            pyautogui.hotkey(*keys)
            return f"Hotkey: {'+'.join(keys)}"

        if action == "press":
            _require_pyautogui()
            key = args.get("key", "enter")
            pyautogui.press(key)
            return f"Pressed: {key}"

        if action == "scroll":
            _require_pyautogui()
            direction = args.get("direction", "down")
            amount    = int(args.get("amount", 3))
            clicks    = amount if direction in ("up", "right") else -amount
            pyautogui.scroll(clicks)
            return f"Scrolled {direction} ×{amount}"

        if action == "copy":
            if _PYPERCLIP: return pyperclip.paste()
            _require_pyautogui()
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.2)
            return "(copied — pyperclip unavailable for read)"

        if action == "paste":
            if _PYPERCLIP:
                pyperclip.copy(args.get("text", ""))
                time.sleep(0.1)
                _require_pyautogui()
                pyautogui.hotkey("ctrl", "v")
                return f"Pasted: {args.get('text','')[:60]}"
            return "pyperclip not available"

        if action == "screenshot":
            _require_pyautogui()
            path = Path.home() / "Desktop" / "jarvis_screenshot.png"
            pyautogui.screenshot().save(str(path))
            return f"Screenshot saved: {path}"

        if action == "wait":
            secs = min(float(args.get("seconds", 1.0)), 30.0)
            time.sleep(secs)
            return f"Waited {secs}s"

        if action == "clear_field":
            _require_pyautogui()
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.press("delete")
            return "Field cleared"

        if action == "focus_window":
            return _focus_window(args.get("title", ""))

        if action == "random_data":
            return _random_data(args.get("type", "name"))

        return f"Unknown action: '{action}'"

    except Exception as e:
        return f"computer_control '{action}' failed: {e}"


# ---------------------------------------------------------------------------
# JARVIS tool registry
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "capture_screen",
        "description": (
            "Capture the current screen (or webcam) and return the image to Claude for visual analysis. "
            "Use this before clicking UI elements to see what's on screen and determine coordinates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["screen", "camera"],
                    "description": "What to capture: 'screen' (default) or 'camera' for webcam"
                }
            },
            "required": []
        }
    },
    {
        "name": "computer_control",
        "description": (
            "Execute mouse and keyboard actions on the desktop. "
            "Actions: type, smart_type, click, double_click, right_click, move, drag, "
            "hotkey, press, scroll, copy, paste, screenshot, wait, clear_field, "
            "focus_window, random_data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform (see tool description for full list)"
                },
                "text":      {"type": "string",  "description": "Text to type or paste"},
                "x":         {"type": "number",  "description": "Screen X coordinate"},
                "y":         {"type": "number",  "description": "Screen Y coordinate"},
                "x1":        {"type": "number",  "description": "Drag start X"},
                "y1":        {"type": "number",  "description": "Drag start Y"},
                "x2":        {"type": "number",  "description": "Drag end X"},
                "y2":        {"type": "number",  "description": "Drag end Y"},
                "button":    {"type": "string",  "description": "'left' or 'right'"},
                "keys":      {"type": "string",  "description": "Hotkey string e.g. 'ctrl+c'"},
                "key":       {"type": "string",  "description": "Single key name e.g. 'enter'"},
                "direction": {"type": "string",  "description": "'up', 'down', 'left', 'right'"},
                "amount":    {"type": "integer", "description": "Scroll amount (default: 3)"},
                "seconds":   {"type": "number",  "description": "Wait duration in seconds"},
                "title":     {"type": "string",  "description": "Window title fragment for focus_window"},
                "type":      {"type": "string",  "description": "Data type for random_data (name, email, phone, etc.)"},
                "clear_first": {"type": "boolean", "description": "Clear field before smart_type (default: true)"}
            },
            "required": ["action"]
        }
    },
]

TOOL_HANDLERS = {
    "capture_screen":    _handle_capture_screen,
    "computer_control":  _handle_computer_control,
}
