# --- session_viewer.py ---
import os, sys, json
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
from PyQt6 import QtWidgets, QtGui, QtCore

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

# ----- PYQT6 VERSION -----
class QtSessionViewer(QtWidgets.QWidget):
    def __init__(self, session_data):
        super().__init__()
        self.session_data = session_data
        self.index = 0
        self.setWindowTitle("OSRS Session Viewer (PyQt6)")

        self.label = QtWidgets.QLabel(self)
        self.label.setFixedSize(1344, 756)

        self.prev_btn = QtWidgets.QPushButton("← Prev")
        self.next_btn = QtWidgets.QPushButton("Next →")
        self.prev_btn.clicked.connect(self.prev_frame)
        self.next_btn.clicked.connect(self.next_frame)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        self.setLayout(layout)

        self.show_frame()

    def show_frame(self):
        path = self.session_data.get_frame_path(self.index)
        img = QtGui.QImage(path)
        pixmap = QtGui.QPixmap.fromImage(img).scaled(1344, 756)
        painter = QtGui.QPainter(pixmap)

        inputs = self.session_data.get_inputs(self.index)
        for event in inputs.get("inputs", []):
            if event["type"] == "move":
                x = int(event["position"][0] * 1344)
                y = int(event["position"][1] * 756)
                painter.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.red))
                painter.drawEllipse(QtCore.QPoint(x, y), 4, 4)

        painter.end()
        self.label.setPixmap(pixmap)

    def next_frame(self):
        self.index = min(self.index + 1, len(self.session_data) - 1)
        self.show_frame()

    def prev_frame(self):
        self.index = max(self.index - 1, 0)
        self.show_frame()

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