# --- main.py --- (For starting session capture.)
import time
from capture.screen_capture import ScreenCapture
from capture.input_capture import InputLogger
from capture.session_recorder import SessionRecorder
from capture.utils import get_runelite_window_rect
from queue import Queue

if __name__ == "__main__":
    # Tracking Config
    tick_rate = 0.6
    frames_per_tick = 3 #3, 6, are good and match tick rate of 0.6 best
    frame_interval = tick_rate / frames_per_tick  # Ideal = 0.12s for 5 fpt, 0.1 for 6 fpt, 0.2 for 3fpt

    # State
    start_time = None
    frame_id = 0
    frame_queue = Queue(maxsize=frames_per_tick * 2)

    # Init
    screen = ScreenCapture()
    inputs = InputLogger(start_time=start_time)

    offset_x, offset_y, width, height = get_runelite_window_rect()
    inputs.set_window_bounds((offset_x, offset_y), (width, height))

    # Start
    screen.start()
    inputs.start()
    recorder = SessionRecorder(screen, inputs, frame_queue, start_time=start_time)

    print("Waiting for first frame...")
    while screen.get_latest_frame() is None:
        time.sleep(0.01)
    print("First frame received. Starting capture...")

    try:
        while True:
            now = time.time()

            if start_time is None:
                tick_number = 0  # Default
                frame_number = 0
                # Wait for a stable frame and a valid tick
                if screen.get_frame_count() > 0:
                    start_time = now
                    recorder.start_time = now
                    inputs.start_time = now
                    next_frame_time = start_time
                    frame_id = 0
                    print("Start time set. Beginning capture loop.")
                else:
                    continue
            else:
                # Schedule time for this frame
                next_frame_time = start_time + frame_id * frame_interval
                sleep_duration = next_frame_time - now
                if sleep_duration > 0:
                    time.sleep(sleep_duration)

                actual_time = time.time()
                drift = actual_time - next_frame_time
                print(f"Drift: {drift:.6f} sec", flush=True)

                elapsed = actual_time - start_time
                tick_number = int(elapsed // tick_rate)
                frame_number = frame_id % frames_per_tick

                try: 
                    frame_queue.put({
                        "frame_id": frame_id,
                        "tick_number": tick_number,
                        "frame_number": frame_number,
                        "timestamp": actual_time,
                    }, timeout=0.01)
                    frame_id += 1
                except queue.Full:
                    print("WARNING: Frame queue full! Dropping frame to avoid delay.")
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received. Stopping capture...")
    finally:
        screen.stop()
        recorder.close()
        print("Recording stopped.")
