# --- session_recorder.py ---
import os, json, time
from datetime import datetime
import threading
import concurrent.futures

class SessionRecorder:
    def __init__(self, screen_cap, input_cap, frame_queue, start_time, save_dir="data/raw"):
        self.screen_cap = screen_cap
        self.input_cap = input_cap
        timestamp = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(save_dir, timestamp)
        os.makedirs(self.session_dir, exist_ok=True)
        self.inputs_file = open(os.path.join(self.session_dir, "inputs.jsonl"), "w")
        self.last_frame_time = time.time()
        self.frame_queue = frame_queue
        self.running = True
        self.start_time = start_time
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)  # Async file saving
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
        events = self.input_cap.get_events_since_last_frame(self.last_frame_time)
        frame = self.screen_cap.get_latest_frame()

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
            "abs_timestamp": round(timestamp, 4),
            "timestamp": round(timestamp - self.start_time, 4),
            "inputs": events
        }

        if frame:
            #path = os.path.join(self.session_dir, f"frame_{frame_id:06}.png")
            path = os.path.join(self.session_dir, f"frame_{frame_id:06}.jpg")
            frame.save(path, format="JPEG", quality=95, optimize=True)
            # Async file save + JSON write
            self.executor.submit(self._save_frame_and_log, frame, path, record)

        self.last_frame_time = timestamp

    def _save_frame_and_log(self, frame, path, record):
        try:
            frame.save(path)
            self.inputs_file.write(json.dumps(record) + "\n")
            self.inputs_file.flush()
        except Exception as e:
            print(f"Error saving frame/log: {e}")

    def close(self):
        self.running = False
        self.worker.join()
        self.executor.shutdown(wait=True)
        self.inputs_file.close()
