# Game Session Recorder (High-Resolution Input + Frame Capture)

This tool captures high-resolution screen frames and detailed human input data (mouse, scroll, keyboard) in real-time from the specified window. 
It is designed to support data collection for vision-based AI systems, machine learning datasets, and offline agent training.


AI Generated README file.
---

## 🔧 Features

- 🔁 Multi-threaded **screen capture** via `WindowsCapture`
- 🖱️ High-precision **input logging** (mouse movement, buttons, scroll, keys)
- 🧠 Frame-aligned **input grouping** per game tick and sub-frame
- 📸 Supports **multiple frames per tick** (e.g. 2–6) for smooth temporal resolution
- 🧪 Input events include:
  - Mouse velocity + normalized position (0–1)
  - Button press/release
  - Scroll detection (start, tick, stop)
  - Held state tracking for keys + buttons
- 🧱 Modular structure:
  - `screen_capture.py` - Window screen grabber (with crop support)
  - `input_capture.py` - Input event recorder with timing + state tracking
  - `session_recorder.py` - Frame logger + input/event synchronizer
- 📝 Stores:
  - Frames as `.jpg` or `.png`
  - Input events in `inputs.jsonl`
  - Metadata in `session_meta.json`

---

## 🧪 Usage

To record sessions:
```bash
python main.py
```
Press Ctrl + C to stop recording. A new session folder will be created with timestamped data.

To review sessions:
```bash
python session_viewer.py
```
Then select the session folder you want to replay. Currently must manually step through and only mouse move inputs visualized.

📁 Output Structure
data/raw/WindowName/session_YYYYMMDD_HHMMSS/
│
├── frame_000000.jpg
├── frame_000001.jpg
├── ...
│
├── inputs.jsonl           # Input events grouped by frame
├── session_meta.json      # Session config + metadata

⚙️ Configuration
Edit capture/config.py to adjust:

tick_rate (default: 0.6)

frames_per_tick

save_format ("jpg" or "png")

round_precision

capture_window (e.g., "RuneLite")

crop_box if needed

💻 Dependencies
This system uses Python 3.10+ and several packages including:

pynput - for keyboard/mouse capture

numpy

Pillow

opencv-python

windows-capture (custom/native)

📦 Setup
Create Environment
```bash
conda create -n screen-capture python=3.10
conda activate screen-capture
pip install -r requirements.txt
```