# --- session_recorder.py ---
import os, json, time
from datetime import datetime, timezone
import threading
import concurrent.futures
from capture.config import CONFIG

class SessionRecorder:
    def __init__(self, screen_cap, input_cap, frame_queue, start_time, save_dir=None):
        self.screen_cap = screen_cap
        self.input_cap = input_cap
        self.frame_queue = frame_queue
        self.start_time = start_time
        self.running = True
        self.last_frame_time = time.time()

        # File format
        self.save_format = CONFIG.get("save_format", "jpg").lower()
        self.image_ext = "jpg" if self.save_format == "jpg" else "png"
        self.max_workers = CONFIG.get("max_workers", 8)

        # Base save directory from param or config
        if save_dir is None:
            save_dir = CONFIG.get("save_dir", "data/raw")
        self.save_dir = save_dir

        # Add subfolder for capture window name (e.g., 'RuneLite')
        window_name = CONFIG.get("capture_window", "RuneLite")
        self.window_dir = os.path.join(self.save_dir, window_name)
        os.makedirs(self.window_dir, exist_ok=True)

        # Session folder
        timestamp = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(self.window_dir, timestamp)
        os.makedirs(self.session_dir, exist_ok=True)

        # Session metadata
        tick_rate = CONFIG["tick_rate"]
        frames_per_tick = CONFIG["frames_per_tick"]
        resolution = screen_cap.get_resolution()

        self.meta = {
            "capture_window": window_name,
            "session_id": os.path.basename(self.session_dir),
            "start_time_utc": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "tick_rate": tick_rate,
            "frames_per_tick": frames_per_tick,
            "frame_interval": round(tick_rate / frames_per_tick, CONFIG["round_precision"]),
            "resolution": resolution,
            "aspect_ratio": self._compute_aspect_ratio(*resolution),
            "crop_box": CONFIG.get("crop_box", None),
            "save_format": self.save_format,
            "scroll_stop_timeout": CONFIG.get("scroll_stop_timeout"),
            "session_tags": CONFIG.get("session_tags", []),
            "notes": CONFIG.get("notes", ""),
        }

        with open(os.path.join(self.session_dir, "session_meta.json"), "w") as f:
            json.dump(self.meta, f, indent=2)

        self.inputs_file = open(os.path.join(self.session_dir, "inputs.jsonl"), "w")

        # Worker thread
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        self.worker = threading.Thread(target=self._worker_loop)
        self.worker.start()

    def _worker_loop(self):
        while self.running:
            try:
                req = self.frame_queue.get(timeout=1)
                self._handle_frame(**req)
            except:
                continue  # Timeout, try again

    def _handle_frame(self, frame_id, tick_number, frame_number, timestamp):
        frame, frame_time = self.screen_cap.get_latest_frame()
        if frame is None:
            return
        epsilon = CONFIG.get("frame_event_safety_margin", 0.001)  # .00X = Xms safety buffer to align frames and inputs
        events = self.input_cap.get_events_since_last_frame(self.last_frame_time, frame_time - epsilon)

        for event in events:
            if event["type"] == "held":
                event["frame_id"] = frame_id
                event["tick_number"] = tick_number
                event["frame_number"] = frame_number
                #event["timestamp"] = round(event["timestamp"] - self.start_time, 4)

        record = {
            "frame_id": frame_id,
            "tick_number": tick_number,
            "frame_number": frame_number,
            "abs_timestamp": round(frame_time, CONFIG["round_precision"]),
            "timestamp": round(frame_time - self.start_time, CONFIG["round_precision"]),
            "inputs": events
        }

        if frame:
            path = os.path.join(self.session_dir, f"frame_{frame_id:06}.{self.image_ext}")
            # Async file save + JSON write
            self.executor.submit(self._save_frame_and_log, frame, path, record)

        self.last_frame_time = frame_time

    def _save_frame_and_log(self, frame, path, record):
        try:
            if self.save_format == "jpg":
                frame.save(path, format="JPEG", quality=95, optimize=True)
            else:
                frame.save(path, format="PNG")
            self.inputs_file.write(json.dumps(record) + "\n")
            self.inputs_file.flush()
        except Exception as e:
            print(f"Error saving frame/log: {e}")

    def _compute_aspect_ratio(self, width, height):
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a
        g = gcd(width, height)
        return f"{width // g}:{height // g}"

    def close(self):
        self.running = False
        self.worker.join()
        self.executor.shutdown(wait=True)
        self.inputs_file.close()

        print("Postprocessing inputs.jsonl file...", flush=True)
        self.sort_jsonl(os.path.join(self.session_dir, "inputs.jsonl"))

    @staticmethod
    def sort_jsonl(path):
        try:
            with open(path, "r") as f:
                lines = [json.loads(line) for line in f]

            lines.sort(key=lambda x: x["frame_id"])

            with open(path, "w") as f:
                for entry in lines:
                    f.write(json.dumps(entry) + "\n")

            print(f"Sorted {len(lines)} input records.", flush=True)
        except Exception as e:
            print(f"Failed to sort JSONL file: {e}", flush=True)
