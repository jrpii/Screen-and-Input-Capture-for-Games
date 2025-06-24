# --- input_capture.py ---
from pynput import mouse, keyboard
import time
import threading
import queue
from capture.config import CONFIG

# Helper to reduce data precision to small yet meaningful amount.
def round_tuple(tup):
    return tuple(round(v, CONFIG["round_precision"]) for v in tup)

class InputLogger:
    def __init__(self, start_time):
        self.events = queue.Queue()
        self.current_state = {
            "mouse_pos": (0, 0),
            "mouse_left": False,
            "mouse_right": False,
            "mouse_middle": False,
            "scroll": (0, 0),
            "keys": set()
        }
        self.scroll_active = False
        self.last_scroll_time = 0
        self.scroll_ticks = 0
        self.scroll_ticks_up = 0
        self.scroll_ticks_down = 0
        self.last_scroll_direction = None
        self.mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll)
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.lock = threading.Lock()

        self.window_offset = (0, 0)
        self.window_size = (1, 1)  # Prevent divide-by-zero
        self.start_time = start_time

    def set_window_bounds(self, offset, size):
        self.window_offset = offset
        self.window_size = size

    # Normalize position to captured screen, clamp if flagged. Ouputs a percentage (0-1.0).
    def normalize_pos(self, x, y, clamp=True):
        ox, oy = self.window_offset
        w, h = self.window_size
        local_x = (x - ox) / w
        local_y = (y - oy) / h
        if clamp:
            local_x = max(0.0, min(1.0, local_x))
            local_y = max(0.0, min(1.0, local_y))
        return (local_x, local_y)

    def on_move(self, x, y):
        with self.lock:
            dt = time.time()
            if self.start_time is None:
                return  # Ignore inputs until start_time is set
            is_mmb_down = self.current_state.get("mouse_middle", False)

            # Normalized positions, clamp depending on middle mouse state (like when panning camera off screen)
            new_pos = self.normalize_pos(x, y, clamp=not is_mmb_down)
            old_pos = self.current_state['mouse_pos']
            dx = new_pos[0] - old_pos[0]
            dy = new_pos[1] - old_pos[1]

            # Skip redundant movement
            if new_pos == old_pos:
                return

            # Update current state
            self.current_state['mouse_pos'] = new_pos

            self.events.put({
                "type": "move",
                "timestamp": round(dt - self.start_time, CONFIG["round_precision"]),
                "position": round_tuple(new_pos),
                "velocity": round_tuple((dx, dy))
            })

    def on_click(self, x, y, button, pressed):
        with self.lock:
            dt = time.time()
            if self.start_time is None:
                return  # Ignore inputs until start_time is set
            name = f"mouse_{button.name}"
            self.current_state[name] = pressed

            # Track active modifiers (Shift, Ctrl, etc.) on click down.
            modifiers = []
            if pressed and button.name != "middle":
                if "Key.shift" in self.current_state["keys"] or "Key.shift_r" in self.current_state["keys"]:
                    modifiers.append("shift")
                if "Key.ctrl" in self.current_state["keys"] or "Key.ctrl_r" in self.current_state["keys"]:
                    modifiers.append("ctrl")
                if "Key.alt" in self.current_state["keys"] or "Key.alt_r" in self.current_state["keys"]:
                    modifiers.append("alt")

            self.events.put({
                "type": "click",
                "timestamp": round(dt - self.start_time, CONFIG["round_precision"]),
                "position": round_tuple(self.normalize_pos(x, y)),
                "button": button.name,
                "pressed": pressed,
                "modifiers": modifiers
            })

    def on_press(self, key):
        with self.lock:
            dt = time.time()
            if self.start_time is None:
                return  # Ignore inputs until start_time is set
            key_name = self._key_to_str(key)
            if key_name and key_name not in self.current_state["keys"]:
                self.current_state["keys"].add(key_name)
                self.events.put({
                    "type": "key_press",
                    "timestamp": round(dt - self.start_time, CONFIG["round_precision"]),
                    "key": key_name
                })

    def on_release(self, key):
        with self.lock:
            dt = time.time()
            if self.start_time is None:
                return  # Ignore inputs until start_time is set
            key_name = self._key_to_str(key)
            if key_name:
                self.current_state["keys"].discard(key_name)
                self.events.put({
                    "type": "key_release",
                    "timestamp": round(dt - self.start_time, CONFIG["round_precision"]),
                    "key": key_name
                })

    def on_scroll(self, x, y, dx, dy):
        now = time.time()
        if self.start_time is None:
            return  # Ignore inputs until start_time is set
        direction = "up" if dy > 0 else "down"
        is_direction_change = (direction != self.last_scroll_direction)

        if not self.scroll_active:
            self.scroll_active = True
            self.scroll_start_time = now
            self.scroll_ticks_up = 0
            self.scroll_ticks_down = 0
            self.scroll_ticks = 1
            self.events.put({
                "type": "scroll_start",
                "timestamp": round(now - self.start_time, CONFIG["round_precision"]),
                "direction": direction
            })
        else:
            if direction == "up":
                self.scroll_ticks_up += 1
            else:
                self.scroll_ticks_down += 1

            self.events.put({
                "type": "scroll_tick",
                "timestamp": round(now - self.start_time, CONFIG["round_precision"]),
                "direction": direction,
                "direction_change": is_direction_change
            })
        self.last_scroll_direction = direction
        self.last_scroll_time = now

    def _key_to_str(self, key):
        try:
            return key.char if hasattr(key, 'char') and key.char else str(key)
        except:
            return str(key)

    def start(self):
        self.mouse_listener.start()
        self.keyboard_listener.start()
        threading.Thread(target=self._scroll_monitor, daemon=True).start()

    def get_events_since_last_frame(self, since_time):
        now = time.time()
        new_events = []
        since_time -= now

         # If start_time isn't set, return held state only
        if self.start_time is None:
            return [{
                "type": "held",
                "timestamp": 0.0,
                "held": {
                    "mouse_middle": self.current_state["mouse_middle"],
                    "mouse_left": self.current_state["mouse_left"],
                    "mouse_right": self.current_state["mouse_right"],
                    "keys": list(self.current_state["keys"])
                }
            }]

        with self.lock:
            tmp = []
            while not self.events.empty():
                event = self.events.get()
                tmp.append(event)

            for event in tmp:
                if event["timestamp"] >= since_time:
                    new_events.append(event)

            # Re-add the unused older events back to the queue
            for event in tmp:
                if event["timestamp"] < since_time:
                    self.events.put(event)

        new_events.append({
            "type": "held",
            "timestamp": round(now - self.start_time, CONFIG["round_precision"]),
            "held": {
                "mouse_middle": self.current_state["mouse_middle"],
                "mouse_left": self.current_state["mouse_left"],
                "mouse_right": self.current_state["mouse_right"],
                "keys": list(self.current_state["keys"])
            }
        })

        return new_events

    def _scroll_monitor(self):
        if self.start_time is None:
            return  # Ignore inputs until start_time is set
        while True:
            time.sleep(0.01)
            timeout = CONFIG.get("scroll_stop_timeout", 0.15)
            if self.scroll_active and time.time() - self.last_scroll_time > timeout: # lower to increase scroll tracking percision
                self.events.put({
                    "type": "scroll_stop",
                    "timestamp": round(time.time() - self.start_time, CONFIG["round_precision"]),
                    "duration": self.last_scroll_time - self.scroll_start_time,
                    "total_ticks": self.scroll_ticks_up + self.scroll_ticks_down,
                    "ticks_up": self.scroll_ticks_up,
                    "ticks_down": self.scroll_ticks_down
                })
                self.scroll_active = False
