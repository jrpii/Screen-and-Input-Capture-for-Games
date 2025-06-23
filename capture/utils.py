import win32gui

def get_runelite_window_rect():
    target_hwnd = None

    def enum_handler(hwnd, _):
        nonlocal target_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "RuneLite" in title:
                target_hwnd = hwnd
                return False  # Stop enumerating once found

    win32gui.EnumWindows(enum_handler, None)

    if not target_hwnd:
        raise RuntimeError("RuneLite window not found")

    rect = win32gui.GetWindowRect(target_hwnd)
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    return left, top, width, height