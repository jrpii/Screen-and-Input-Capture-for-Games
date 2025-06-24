# --- utils.py ---
import win32gui
import time
import threading
from capture.config import CONFIG

def get_specified_window_rect():
    target_hwnd = None

    def enum_handler(hwnd, _):
        nonlocal target_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if CONFIG["capture_window"] in title:
                target_hwnd = hwnd
                return False  # Stop enumerating once found

    win32gui.EnumWindows(enum_handler, None)

    if not target_hwnd:
        raise RuntimeError(f'Capture window "{CONFIG["capture_window"]}" not found.')

    # Get full window rect
    rect = win32gui.GetWindowRect(target_hwnd)
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    
    # Apply crop if defined
    crop = CONFIG.get("crop_box", None)
    if crop:
        crop_left, crop_top, crop_right, crop_bottom = crop
        # Validate crop dimensions
        if crop_right <= crop_left or crop_bottom <= crop_top:
            raise ValueError("Invalid crop_box: right must be > left and bottom > top")

        # Compute cropped region relative to the original window
        left += crop_left
        top += crop_top
        width = crop_right - crop_left
        height = crop_bottom - crop_top
    
    return left, top, width, height
