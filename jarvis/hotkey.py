"""JARVIS dictation overlay for GNOME Wayland."""
import os
import sys
import queue
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jarvis.model import LocalModels


class DictationOverlay:
    def __init__(self, root):
        self.root = root
        self.root.title('JARVIS')
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#11131b')
        self.root.geometry('440x156')
        self.root.update_idletasks()
        x = (root.winfo_screenwidth() - 440) // 2
        y = root.winfo_screenheight() - 210
        root.geometry(f'+{x}+{y}')
        self.canvas = tk.Canvas(root, width=440, height=156, bg='#11131b', highlightthickness=0)
        self.canvas.pack()
        self.canvas.create_rectangle(1, 1, 439, 155, fill='#171a25', outline='#34384a', width=2)
        self.canvas.create_oval(24, 24, 40, 40, fill='#f45b75', outline='')
        self.canvas.create_text(55, 32, text='JARVIS  ·  DICTATION', anchor='w', fill='#f4f5fb', font=('Sans', 12, 'bold'))
        self.status = self.canvas.create_text(24, 66, text='Starting microphone…', anchor='w', fill='#b8bfd4', font=('Sans', 11))
        self.bars = []
        for i in range(27):
            px = 26 + i * 14
            self.bars.append(self.canvas.create_line(px, 108, px, 126, fill='#7b83ff', width=4, capstyle='round'))
        self.canvas.create_text(24, 142, text='Super + Shift + J again to dictate another phrase', anchor='w', fill='#777f96', font=('Sans', 9))
        self.phase = 'listening'
        self.tick = 0
        self.result_queue = queue.Queue()
        self.root.after(80, self.animate)
        self.root.after(100, self.check_result)

    def animate(self):
        import math
        self.tick += 1
        for i, item in enumerate(self.bars):
            strength = 7 + abs(math.sin(self.tick * 0.22 + i * 0.62)) * (25 if self.phase == 'listening' else 9)
            mid = 117
            color = '#ff6683' if self.phase == 'listening' else '#8187ff'
            self.canvas.coords(item, 26 + i * 14, mid - strength / 2, 26 + i * 14, mid + strength / 2)
            self.canvas.itemconfigure(item, fill=color)
        self.root.after(80, self.animate)

    def check_result(self):
        try:
            text, error = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self.check_result)
            return
        if error:
            self.canvas.itemconfigure(self.status, text=error, fill='#ff8599')
            self.root.after(2200, self.root.destroy)
            return
        self.phase = 'done'
        self.canvas.itemconfigure(self.status, text='Dictated: ' + text[:48], fill='#d7dcf0')
        threading.Thread(target=self.paste_text, args=(text,), daemon=True).start()
        self.root.after(1500, self.root.destroy)

    def paste_text(self, text):
        try:
            subprocess.run(['wtype', '--', text], check=True, timeout=5)
        except Exception:
            subprocess.run(['wl-copy', '--', text], check=False)
            self.root.after(0, lambda: self.canvas.itemconfigure(self.status, text='Copied to clipboard — press Ctrl+V', fill='#ffd68a'))


def main():
    root = tk.Tk()
    overlay = DictationOverlay(root)

    def transcribe():
        try:
            with tempfile.TemporaryDirectory(prefix='jarvis-') as directory:
                wav = os.path.join(directory, 'speech.wav')
                subprocess.run(['arecord', '-q', '-d', '5', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'wav', wav], check=True, timeout=7)
                overlay.phase = 'processing'
                overlay.canvas.itemconfigure(overlay.status, text='Transcribing locally…')
                text = LocalModels([]).transcribe(wav).strip()
                if not text:
                    raise ValueError('No speech detected')
                overlay.result_queue.put((text, None))
        except Exception as exc:
            overlay.result_queue.put((None, str(exc)))

    threading.Thread(target=transcribe, daemon=True).start()
    root.mainloop()


if __name__ == '__main__':
    main()
