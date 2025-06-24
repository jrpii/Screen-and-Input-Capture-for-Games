import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env

def get_env_float(key, default):
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default

def get_env_int(key, default):
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default

def get_env_list(key, default):
    val = os.getenv(key)
    if val:
        return [x.strip() for x in val.split(",")]
    return default

def get_env_bool(key, default=False):
    val = os.getenv(key)
    if val is not None:
        return val.lower() in ("1", "true", "yes")
    return default

def get_env_tuple(key, default):
    val = os.getenv(key)
    if val:
        try:
            parts = [int(x.strip()) for x in val.split(",")]
            return tuple(parts)
        except:
            pass
    return default

CONFIG = {
    "capture_window": os.getenv("CAPTURE_WINDOW", "RuneLite"),
    "tick_rate": get_env_float("TICK_RATE", 0.6),
    "frames_per_tick": get_env_int("FRAMES_PER_TICK", 3),
    "save_format": os.getenv("SAVE_FORMAT", "jpg"),
    "crop_box": get_env_tuple("CROP_BOX", None),
    "session_tags": get_env_list("SESSION_TAGS", []),
    "notes": os.getenv("NOTES", ""),
    "round_precision": get_env_int("ROUND_PRECISION", 4),
    "scroll_stop_timeout": get_env_float("SCROLL_STOP_TIMEOUT", 0.15),
    "max_workers": get_env_int("MAX_WORKERS", 8),
    "save_dir": os.getenv("SAVE_DIR", "data/raw"),
}