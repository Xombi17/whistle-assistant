"""JARVIS unified voice overlay with mode switching (WhisperFlow Dictation vs Command Assistant)."""
import argparse
import configparser
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jarvis.model import LocalModels
from jarvis.validation import validate

CONFIG_DIR = Path.home() / '.config' / 'jarvis'
MODE_FILE = CONFIG_DIR / 'mode'

TOOL_SCHEMAS = [
    {
        'name': 'open_app',
        'description': 'Open an installed application',
        'parameters': {
            'type': 'object',
            'properties': {'name': {'type': 'string'}},
            'required': ['name']
        }
    }
]


def get_stored_mode():
    try:
        if MODE_FILE.is_file():
            mode = MODE_FILE.read_text(encoding='utf-8').strip().lower()
            if mode in ('transcribe', 'dictate', 'whisperflow'):
                return 'transcribe'
            if mode in ('command', 'assistant'):
                return 'command'
    except Exception:
        pass
    return 'transcribe'


def set_stored_mode(mode):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MODE_FILE.write_text(mode, encoding='utf-8')


def toggle_stored_mode():
    current = get_stored_mode()
    new_mode = 'command' if current == 'transcribe' else 'transcribe'
    set_stored_mode(new_mode)
    label = 'Command Mode (JARVIS)' if new_mode == 'command' else 'Dictation Mode (WhisperFlow)'
    subprocess.run(['notify-send', 'JARVIS Mode Switched', f'Current mode: {label}'], check=False)
    return new_mode


def resolve_app(name):
    paths = [Path.home() / '.local/share/applications'] + [
        Path(x) / 'applications' for x in os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
    ]
    matches = []
    for folder in paths:
        if not folder.is_dir():
            continue
        for path in folder.glob('*.desktop'):
            parser = configparser.ConfigParser(interpolation=None)
            try:
                parser.read(path, encoding='utf-8')
                entry = parser['Desktop Entry']
                label = entry.get('Name', '')
                if (
                    entry.get('Type') == 'Application'
                    and not entry.getboolean('Hidden', fallback=False)
                    and not entry.getboolean('NoDisplay', fallback=False)
                    and (label.casefold() == name.casefold() or path.stem.casefold() == name.casefold())
                ):
                    matches.append(str(path.resolve(strict=True)))
            except Exception:
                continue
    unique = list(dict.fromkeys(matches))
    return unique[0] if unique else None


class VoiceOverlay:
    def __init__(self, root, mode='transcribe'):
        self.root = root
        self.mode = mode
        self.root.title('JARVIS')
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#11131b')

        self.width = 460
        self.height = 160
        self.root.geometry(f'{self.width}x{self.height}')
        self.root.update_idletasks()
        x = (root.winfo_screenwidth() - self.width) // 2
        y = root.winfo_screenheight() - 220
        root.geometry(f'+{x}+{y}')

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, bg='#11131b', highlightthickness=0)
        self.canvas.pack()

        # Keybindings
        self.root.bind('<Escape>', lambda e: self.root.destroy())
        self.root.bind('<Tab>', lambda e: self.toggle_mode_live())
        self.root.bind('<m>', lambda e: self.toggle_mode_live())
        self.root.bind('<M>', lambda e: self.toggle_mode_live())
        self.root.bind('<Return>', lambda e: self.confirm_action())

        self.phase = 'listening'
        self.tick = 0
        self.result_queue = queue.Queue()
        self.pending_command = None

        self.draw_ui()
        self.root.after(80, self.animate)
        self.root.after(100, self.check_result)

    def draw_ui(self):
        self.canvas.delete('all')
        is_transcribe = (self.mode == 'transcribe')

        # Frame border
        border_color = '#38bdf8' if is_transcribe else '#a855f7'
        self.canvas.create_rectangle(1, 1, self.width - 1, self.height - 1, fill='#171a25', outline=border_color, width=2)

        # Mode Indicator Dot
        dot_color = '#38bdf8' if is_transcribe else '#c084fc'
        self.canvas.create_oval(24, 22, 38, 36, fill=dot_color, outline='')

        # Title
        title_text = 'WHISPERFLOW  ·  DICTATION' if is_transcribe else 'JARVIS  ·  COMMAND'
        self.canvas.create_text(48, 29, text=title_text, anchor='w', fill='#f4f5fb', font=('Sans', 11, 'bold'))

        # Clickable Mode Switch Button (Top Right)
        btn_bg = '#1e293b' if is_transcribe else '#2e1065'
        btn_tag = 'mode_btn'
        self.canvas.create_rectangle(self.width - 145, 16, self.width - 20, 42, fill=btn_bg, outline='#475569', tags=btn_tag)
        self.canvas.create_text(self.width - 82, 29, text='⇄ Switch (Tab)', fill='#e2e8f0', font=('Sans', 8, 'bold'), tags=btn_tag)
        self.canvas.tag_bind(btn_tag, '<Button-1>', lambda e: self.toggle_mode_live())

        # Status text
        default_status = 'Listening (speak now)…' if self.phase == 'listening' else 'Processing…'
        self.status = self.canvas.create_text(24, 66, text=default_status, anchor='w', fill='#b8bfd4', font=('Sans', 11))

        # Animated waveform bars
        self.bars = []
        bar_count = 28
        bar_color = '#38bdf8' if is_transcribe else '#c084fc'
        for i in range(bar_count):
            px = 26 + i * 14
            bar = self.canvas.create_line(px, 105, px, 123, fill=bar_color, width=4, capstyle='round')
            self.bars.append(bar)

        # Footer Hint
        hint = 'Tab: toggle mode  ·  Esc: cancel'
        self.footer = self.canvas.create_text(24, 144, text=hint, anchor='w', fill='#777f96', font=('Sans', 9))

    def toggle_mode_live(self):
        self.mode = 'command' if self.mode == 'transcribe' else 'transcribe'
        set_stored_mode(self.mode)
        self.draw_ui()

    def animate(self):
        import math
        self.tick += 1
        if self.phase in ('listening', 'processing'):
            is_transcribe = (self.mode == 'transcribe')
            color = ('#38bdf8' if is_transcribe else '#c084fc') if self.phase == 'listening' else '#818cf8'
            for i, item in enumerate(self.bars):
                strength = 6 + abs(math.sin(self.tick * 0.22 + i * 0.58)) * (26 if self.phase == 'listening' else 10)
                mid = 114
                self.canvas.coords(item, 26 + i * 14, mid - strength / 2, 26 + i * 14, mid + strength / 2)
                self.canvas.itemconfigure(item, fill=color)
        self.root.after(80, self.animate)

    def check_result(self):
        try:
            item_type, payload, error = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self.check_result)
            return

        if error:
            self.phase = 'error'
            self.canvas.itemconfigure(self.status, text=f'Error: {error}', fill='#f87171')
            self.root.after(2600, self.root.destroy)
            return

        if item_type == 'transcribe':
            text = payload
            self.phase = 'done'
            display_text = (text[:42] + '…') if len(text) > 45 else text
            self.canvas.itemconfigure(self.status, text=f'Dictated: "{display_text}"', fill='#38bdf8')
            threading.Thread(target=self.paste_text, args=(text,), daemon=True).start()
            self.root.after(1400, self.root.destroy)

        elif item_type == 'command':
            app_name, desktop_path, transcript = payload
            self.pending_command = (app_name, desktop_path)
            self.phase = 'confirm'
            self.canvas.itemconfigure(self.status, text=f'Launch {app_name}?', fill='#c084fc')
            self.canvas.itemconfigure(self.footer, text='Press Enter to launch  ·  Esc to cancel', fill='#a78bfa')
            # Auto-timeout after 6 seconds if unconfirmed
            self.root.after(6000, lambda: self.root.destroy() if self.phase == 'confirm' else None)

    def confirm_action(self):
        if self.phase == 'confirm' and self.pending_command:
            app_name, desktop_path = self.pending_command
            subprocess.Popen(['gio', 'launch', desktop_path])
            subprocess.run(['notify-send', 'JARVIS', f'Launched {app_name}'], check=False)
            self.root.destroy()

    def paste_text(self, text):
        # WhisperFlow text injection: try typing into focused window, copy to clipboard as backup
        try:
            subprocess.run(['wtype', '--', text], check=True, timeout=5)
        except Exception:
            subprocess.run(['wl-copy', '--', text], check=False)
            self.root.after(0, lambda: self.canvas.itemconfigure(self.status, text='Copied to clipboard (Ctrl+V)', fill='#facc15'))


def run_pipeline(overlay):
    try:
        with tempfile.TemporaryDirectory(prefix='jarvis-') as directory:
            wav = os.path.join(directory, 'recording.wav')
            subprocess.run(['arecord', '-q', '-d', '4', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'wav', wav], check=True, timeout=6)
            overlay.phase = 'processing'
            overlay.canvas.itemconfigure(overlay.status, text='Transcribing speech locally…')

            model = LocalModels(TOOL_SCHEMAS)
            transcript = model.transcribe(wav).strip()
            if not transcript:
                raise ValueError('No speech detected')

            if overlay.mode == 'transcribe':
                overlay.result_queue.put(('transcribe', transcript, None))
            else:
                overlay.canvas.itemconfigure(overlay.status, text='Interpreting command…')
                response = model.propose(transcript)
                calls = validate(response)
                if not calls or calls[0]['name'] != 'open_app':
                    raise ValueError('Only "open <app>" is currently supported in command mode.')
                app_name = calls[0]['arguments']['name']
                desktop_file = resolve_app(app_name)
                if not desktop_file:
                    raise ValueError(f'No installed application found for "{app_name}"')
                overlay.result_queue.put(('command', (app_name, desktop_file, transcript), None))

    except Exception as exc:
        overlay.result_queue.put((None, None, str(exc)))


def main():
    parser = argparse.ArgumentParser(description='JARVIS / WhisperFlow Voice Overlay')
    parser.add_argument('--mode', choices=['transcribe', 'command'], help='Force specific mode')
    parser.add_argument('--toggle', action='store_true', help='Toggle between transcription and command modes')
    parser.add_argument('--status', action='store_true', help='Print and notify active mode')
    args = parser.parse_args()

    if args.toggle:
        new_mode = toggle_stored_mode()
        print(f'Mode switched to: {new_mode}')
        return 0

    if args.status:
        mode = get_stored_mode()
        print(f'Current mode: {mode}')
        subprocess.run(['notify-send', 'JARVIS Mode', f'Active mode: {mode}'], check=False)
        return 0

    active_mode = args.mode or get_stored_mode()
    root = tk.Tk()
    overlay = VoiceOverlay(root, mode=active_mode)
    threading.Thread(target=run_pipeline, args=(overlay,), daemon=True).start()
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
