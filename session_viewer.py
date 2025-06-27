# --- session_viewer.py ---
import os, sys, json
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
from PyQt6 import QtWidgets, QtGui, QtCore
from pynput.mouse import Controller
import math

USE_TKINTER = "--tk" in sys.argv

class SessionData:
    def __init__(self, session_dir):
        self.session_dir = session_dir
        self.frames = sorted([
            f for f in os.listdir(session_dir)
            if f.startswith("frame_") and f.endswith((".jpg", ".png"))
        ])
        with open(os.path.join(session_dir, "inputs.jsonl")) as f:
            self.inputs = [json.loads(line) for line in f]

    def get_frame_path(self, index):
        return os.path.join(self.session_dir, self.frames[index])

    def get_inputs(self, index):
        return self.inputs[index] if index < len(self.inputs) else None

    def __len__(self):
        return len(self.frames)

# ----- TKINTER VERSION -----
def run_tkinter_gui(session_data):
    root = tk.Tk()
    root.title("OSRS Session Viewer (tkinter)")

    canvas = tk.Canvas(root, width=800, height=600)
    canvas.pack()

    index = [0]
    image_id = [None]

    def show_frame(i):
        img = Image.open(session_data.get_frame_path(i))
        img = img.resize((800, 600))
        tk_img = ImageTk.PhotoImage(img)
        canvas.img = tk_img
        if image_id[0] is not None:
            canvas.delete(image_id[0])
        image_id[0] = canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

        # Draw mouse overlay
        canvas.delete("cursor")
        inputs = session_data.get_inputs(i)
        for event in inputs.get("inputs", []):
            if event["type"] == "move":
                x = int(event["position"][0] * 800)
                y = int(event["position"][1] * 600)
                canvas.create_oval(x-3, y-3, x+3, y+3, fill="red", tags="cursor")

    def next_frame(event=None):
        index[0] = min(index[0] + 1, len(session_data)-1)
        show_frame(index[0])

    def prev_frame(event=None):
        index[0] = max(index[0] - 1, 0)
        show_frame(index[0])

    root.bind("<Right>", next_frame)
    root.bind("<Left>", prev_frame)

    show_frame(index[0])
    root.mainloop()

# ---------- PyQt6 player --------------------
class QtSessionViewer(QtWidgets.QWidget):
    def __init__(self, session_data, speed: float = 0.20):
        super().__init__()
        self.data          = session_data
        self.speed         = speed        # playback multiplier (0.20 = 1/5 real-time)
        self.timing_exact  = True         # True: real Δt, False: evenly spaced
        self.cursor_follow = False
        self.playing       = False

        self.index     = 0                # current frame
        self.move_list = []               # [(delay_ms, norm_pos), …]
        self.move_i    = 0                # index in move_list

        # --- UI --------------------------------------------------------
        self.setWindowTitle("OSRS Session Viewer")
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedSize(1344, 756)

        self.prev_btn = QtWidgets.QPushButton("← Prev"); self.prev_btn.clicked.connect(self.prev_frame)
        self.next_btn = QtWidgets.QPushButton("Next →"); self.next_btn.clicked.connect(self.next_frame)
        for b in (self.prev_btn, self.next_btn):
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)   # let key-events reach widget

        btn_row = QtWidgets.QHBoxLayout(); btn_row.addWidget(self.prev_btn); btn_row.addWidget(self.next_btn)
        self.status = QtWidgets.QLabel(styleSheet="color: grey;")

        lay = QtWidgets.QVBoxLayout(self); lay.addWidget(self.label); lay.addLayout(btn_row); lay.addWidget(self.status)

        # --- timer & mouse controller ---------------------------------
        self.timer       = QtCore.QTimer(self); self.timer.timeout.connect(self._advance_move)
        self.mouse_ctrl  = Controller()

        self._prep_frame(first=True)       # paint first frame
    # ==================================================================
    #  Frame preparation
    # ==================================================================
    def _prep_frame(self, first=False):
        rec  = self.data.get_inputs(self.index)
        path = self.data.get_frame_path(self.index)

        # Build move_list = [(delay_ms, pos_norm), …]
        moves = [ev for ev in rec.get("inputs", []) if ev["type"] == "move"]
        self.move_list = []
        prev_t = moves[0]["timestamp"] if moves else 0.0
        for ev in moves:
            dt = (ev["timestamp"] - prev_t) * self.speed
            prev_t = ev["timestamp"]
            self.move_list.append([dt*1000.0, ev["position"]])  # ms
        # if equal-spacing mode requested -> overwrite delays
        if not self.timing_exact and self.move_list:
            avg = sum(d for d, _ in self.move_list)/len(self.move_list)
            for m in self.move_list: m[0] = avg

        self.move_i = 0
        last_pos = self.move_list[-1][1] if self.move_list else self._last_mouse_pos_norm(self.index)
        self._render_pixmap(path, last_pos)

        if first: self._update_status()
    # ------------------------------------------------------------------
    def _render_pixmap(self, img_path, norm_pos):
        pm = QtGui.QPixmap.fromImage(QtGui.QImage(img_path)).scaled(
            self.label.width(), self.label.height(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        if norm_pos:
            painter = QtGui.QPainter(pm)
            x = int(norm_pos[0]*pm.width()); y = int(norm_pos[1]*pm.height())
            painter.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.red))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawEllipse(QtCore.QPoint(x,y), 4, 4)
            painter.end()
        self.label.setPixmap(pm)

        if self.cursor_follow and norm_pos:
            self._move_system_cursor(norm_pos)
    # ------------------------------------------------------------------
    def _last_mouse_pos_norm(self, idx):
        for ev in reversed(self.data.get_inputs(idx).get("inputs", [])):
            if ev["type"] == "move": return ev["position"]
        return None
    # ------------------------------------------------------------------
    def _move_system_cursor(self, norm_pos):
        target = self.label.mapToGlobal(QtCore.QPoint(
            int(norm_pos[0]*self.label.width()),
            int(norm_pos[1]*self.label.height())))
        cur_x, cur_y = self.mouse_ctrl.position
        dx, dy = target.x() - cur_x, target.y() - cur_y
        if dx or dy:
            self.mouse_ctrl.move(dx, dy)          # relative move (incremental)
    # ==================================================================
    #  Timer-driven move playback
    # ==================================================================
    def _advance_move(self):
        if self.move_i >= len(self.move_list):            # done with this frame
            if self.index >= len(self.data)-1:
                self.playing = False; self.timer.stop(); self._update_status(); return
            self.index += 1; self._prep_frame(); self.move_i = 0
        else:
            delay_ms, pos = self.move_list[self.move_i]
            self._render_pixmap(self.data.get_frame_path(self.index), pos)
            self.move_i += 1
            if self.playing and self.move_i < len(self.move_list):
                self.timer.start(max(1,int(self.move_list[self.move_i][0])))
    # ==================================================================
    #  Navigation helpers
    # ==================================================================
    def next_frame(self,*_): self._step(+1)
    def prev_frame(self,*_): self._step(-1)
    def _step(self, d):
        self.playing = False; self.timer.stop()
        self.index = max(0, min(len(self.data)-1, self.index+d)); self._prep_frame()

    # ==================================================================
    #  Key handling
    # ==================================================================
    def keyPressEvent(self, e):
        k = e.key()
        if   k==QtCore.Qt.Key.Key_P:      self.toggle_play()
        elif k==QtCore.Qt.Key.Key_F1:     self.cursor_follow ^= True; self._update_status()
        elif k==QtCore.Qt.Key.Key_T:      self.timing_exact ^= True;  self._prep_frame()
        elif k in (QtCore.Qt.Key.Key_Plus, QtCore.Qt.Key.Key_Equal):
            self._change_speed(1.1)
        elif k in (QtCore.Qt.Key.Key_Minus, QtCore.Qt.Key.Key_Underscore):
            self._change_speed(1/1.1)
        elif k==QtCore.Qt.Key.Key_Right:  self.next_frame()
        elif k==QtCore.Qt.Key.Key_Left:   self.prev_frame()
        elif k==QtCore.Qt.Key.Key_Escape: self.playing=False; self.timer.stop(); self.cursor_follow=False; self._update_status()

    def toggle_play(self):
        self.playing ^= True
        if self.playing and self.move_list:
            self.move_i = 0
            self.timer.start(max(1,int(self.move_list[0][0])))
        else:
            self.timer.stop()
        self._update_status()

    def _change_speed(self, factor):
        self.speed = max(0.02, min(10.0, self.speed*factor))
        # rebuild move_list with new speed
        self._prep_frame()
        self._update_status()
    # ==================================================================
    def _update_status(self):
        state = "▶" if self.playing else "❚❚"
        cur   = "CURSOR ON" if self.cursor_follow else "cursor off"
        mode  = "exact" if self.timing_exact else "even"
        spd   = f"{self.speed:.2f}×"

        self.status.setText(
            f"[P] play/pause  |  [+ / -] speed  |  [T] timing  |  [F1] cursor  |  [←/→] step  |  [Esc] stop"
            f"     ||  mode: {mode}   speed: {spd}   {cur}"
        )
        self.setWindowTitle(
            f"OSRS Session Viewer  –  frame {self.index+1}/{len(self.data)}   {state}   {cur}   mode={mode}   speed={spd}"
        )

def run_pyqt_gui(session_data):
    app = QtWidgets.QApplication(sys.argv)
    viewer = QtSessionViewer(session_data)
    viewer.resize(1364, 816)
    viewer.show()
    sys.exit(app.exec())

# ----- MAIN -----
def main():
    session_dir = filedialog.askdirectory(title="Select session directory")
    if not session_dir:
        print("No directory selected.")
        return

    data = SessionData(session_dir)
    if USE_TKINTER:
        run_tkinter_gui(data)
    else:
        run_pyqt_gui(data)

if __name__ == "__main__":
    main()