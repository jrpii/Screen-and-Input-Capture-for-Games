# --- screen_capture.py ---
from windows_capture import WindowsCapture
import numpy as np
from PIL import Image
import threading
import time
from capture.utils import get_specified_window_rect
from capture.config import CONFIG

class ScreenCapture:
    def __init__(self, window_name=None):
        print("ScreenCapture initializing...")
        self.window_name = window_name or CONFIG.get("capture_window", "RuneLite")
        self.frame = None
        self.lock = threading.Lock()
        self.capture = WindowsCapture(window_name=self.window_name)
        self.capture.event(self.on_frame_arrived)
        self.capture.event(self.on_closed)
        self.thread = None  # <== store thread
        self.frame_count = 0
        self.last_frame_time = time.time()
        print(f"Handlers registered for window: {self.window_name}")

    def on_frame_arrived(self, frame, control):
        self.frame_count += 1
        now = time.time()
        #print(f"Frame arrived! Total: {self.frame_count}, (delta)t: {now - self.last_frame_time:.4f}s")
        self.last_frame_time = now

        bgr_frame = frame.frame_buffer[:, :, :3][:, :, ::-1]  # BGRA -> RGB
        img = Image.fromarray(bgr_frame, mode="RGB")
        #img = Image.fromarray(frame.frame_buffer)
        with self.lock:
            self.frame = (img.copy(), now)

    def get_frame_count(self):
        return self.frame_count

    def on_closed(self):
        print("Capture session closed.")

    def start(self):
        # Start capture in its own thread
        def run_capture():
            try:
                self.capture.start()
            except Exception as e:
                print(f"Capture error: {e}")
        self.thread = threading.Thread(target=run_capture, daemon=True)
        self.thread.start()

    def stop(self):
        # Gracefully stop the native capture thread
        if hasattr(self.capture, "capture") and hasattr(self.capture.capture, "stop"):
            self.capture.capture.stop()
        if self.thread:
            self.thread.join(timeout=2.0)

    def get_latest_frame(self):
        #if self.lock.acquire(timeout=0.01):  # Slight wait to avoid blocking, replace below line if needed
        with self.lock:
            if not self.frame:
                return None, None
            try:
                img, ts = self.frame
                crop_box = CONFIG.get("crop_box")  # e.g., (left, top, right, bottom)
                if crop_box:
                    img = img.crop(crop_box)
                return img, ts
            except Exception as e:
                print(f"Error copying frame: {e}")
                return None

    def get_resolution(self):
        try:
            _, _, width, height = get_specified_window_rect()
            return width, height
        except Exception as e:
            print(f"Failed to get capture window resolution: {e}", flush=True)
            return None, None
