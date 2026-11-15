"""JARVIS unified voice overlay with hold-to-talk release detection, live audio reactivity,
and seamless mode switching (WhisperFlow Dictation vs Command Assistant)."""

import argparse
import configparser
import glob
import os
import queue
import select
import signal
import struct
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
PID_FILE = os.path.join(os.environ.get('XDG_RUNTIME_DIR', tempfile.gettempdir()), 'jarvis.pid')

TOOL_SCHEMAS = [
    {
        'name': 'open_app',
        'description': 'Open an installed application',
        'parameters': {
            'type': 'object',
            'properties': {'name': {'type': 'string'}},
            'required': ['name'],
        },
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
    subprocess.run(['notify-send', 'JARVIS Mode Switched', f'Active: {label}'], check=False)
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


def pcm_to_wav(pcm_data, sample_rate=16000, channels=1, sampwidth=2):
    """Generate a standard 44-byte RIFF WAV header for raw 16-bit PCM."""
    data_size = len(pcm_data)
    byte_rate = sample_rate * channels * sampwidth
    block_align = channels * sampwidth
    bits_per_sample = sampwidth * 8
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,
        b'WAVE',
        b'fmt ',
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b'data',
        data_size,
    )
    return header + pcm_data


def compute_rms(pcm_bytes):
    """Compute RMS volume level from 16-bit signed PCM data."""
    if not pcm_bytes:
        return 0
    count = len(pcm_bytes) // 2
    if count == 0:
        return 0
    try:
        shorts = struct.unpack(f'<{count}h', pcm_bytes[: count * 2])
        sum_sq = sum(s * s for s in shorts)
        return int((sum_sq / count) ** 0.5)
    except Exception:
        return 0


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

        # Keyboard & Mouse events
        self.root.bind('<Escape>', lambda e: self.root.destroy())
        self.root.bind('<Tab>', lambda e: self.toggle_mode_live())
        self.root.bind('<m>', lambda e: self.toggle_mode_live())
        self.root.bind('<M>', lambda e: self.toggle_mode_live())
        self.root.bind('<Return>', lambda e: self.on_return_pressed())
        self.root.bind('<KeyRelease-space>', lambda e: self.on_space_released())
        self.root.bind('<ButtonRelease-1>', lambda e: self.on_mouse_released(e))

        self.phase = 'listening'
        self.tick = 0
        self.audio_level = 0.0
        self.result_queue = queue.Queue()
        self.stop_recording_event = threading.Event()
        self.pending_command = None

        self.draw_ui()
        self.root.after(40, self.animate)
        self.root.after(80, self.check_result)

    def draw_ui(self):
        self.canvas.delete('all')
        is_transcribe = (self.mode == 'transcribe')

        border_color = '#38bdf8' if is_transcribe else '#a855f7'
        self.canvas.create_rectangle(1, 1, self.width - 1, self.height - 1, fill='#171a25', outline=border_color, width=2)

        dot_color = '#38bdf8' if is_transcribe else '#c084fc'
        self.canvas.create_oval(24, 22, 38, 36, fill=dot_color, outline='')

        title_text = 'WHISPERFLOW  ·  DICTATION' if is_transcribe else 'JARVIS  ·  COMMAND'
        self.canvas.create_text(48, 29, text=title_text, anchor='w', fill='#f4f5fb', font=('Sans', 11, 'bold'))

        btn_bg = '#1e293b' if is_transcribe else '#2e1065'
        btn_tag = 'mode_btn'
        self.canvas.create_rectangle(self.width - 145, 16, self.width - 20, 42, fill=btn_bg, outline='#475569', tags=btn_tag)
        self.canvas.create_text(self.width - 82, 29, text='⇄ Switch (Tab)', fill='#e2e8f0', font=('Sans', 8, 'bold'), tags=btn_tag)
        self.canvas.tag_bind(btn_tag, '<Button-1>', lambda e: self.toggle_mode_live())

        status_msg = 'Holding hotkey… speak now' if self.phase == 'listening' else 'Processing…'
        self.status = self.canvas.create_text(24, 66, text=status_msg, anchor='w', fill='#b8bfd4', font=('Sans', 11))

        self.bars = []
        bar_count = 28
        bar_color = '#38bdf8' if is_transcribe else '#c084fc'
        for i in range(bar_count):
            px = 26 + i * 14
            bar = self.canvas.create_line(px, 105, px, 123, fill=bar_color, width=4, capstyle='round')
            self.bars.append(bar)

        hint = 'Release hotkey to transcribe  ·  Esc: cancel'
        self.footer = self.canvas.create_text(24, 144, text=hint, anchor='w', fill='#777f96', font=('Sans', 9))

    def toggle_mode_live(self):
        self.mode = 'command' if self.mode == 'transcribe' else 'transcribe'
        set_stored_mode(self.mode)
        self.draw_ui()

    def on_return_pressed(self):
        if self.phase == 'listening':
            self.stop_recording_event.set()
        elif self.phase == 'confirm':
            self.confirm_action()

    def on_space_released(self):
        if self.phase == 'listening':
            self.stop_recording_event.set()

    def on_mouse_released(self, event):
        # If user clicked and held anywhere except mode toggle, releasing triggers transcription
        if self.phase == 'listening' and event.y > 45:
            self.stop_recording_event.set()

    def animate(self):
        import math
        self.tick += 1
        if self.phase == 'listening':
            is_transcribe = (self.mode == 'transcribe')
            color = '#38bdf8' if is_transcribe else '#c084fc'
            # Combine wave with real live audio energy
            boost = min(38.0, self.audio_level * 0.015)
            for i, item in enumerate(self.bars):
                sin_wave = math.sin(self.tick * 0.24 + i * 0.65)
                strength = 5 + abs(sin_wave) * (12 + boost)
                mid = 114
                self.canvas.coords(item, 26 + i * 14, mid - strength / 2, 26 + i * 14, mid + strength / 2)
                self.canvas.itemconfigure(item, fill=color)
        elif self.phase == 'processing':
            for i, item in enumerate(self.bars):
                mid = 114
                strength = 7 + abs(math.sin(self.tick * 0.35 + i * 0.45)) * 14
                self.canvas.coords(item, 26 + i * 14, mid - strength / 2, 26 + i * 14, mid + strength / 2)
                self.canvas.itemconfigure(item, fill='#818cf8')
        self.root.after(40, self.animate)

    def check_result(self):
        try:
            item_type, payload, error = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(60, self.check_result)
            return

        if error:
            self.phase = 'error'
            self.canvas.itemconfigure(self.status, text=f'Error: {error}', fill='#f87171')
            self.root.after(2200, self.root.destroy)
            return

        if item_type == 'transcribe':
            text = payload
            self.phase = 'done'
            display_text = (text[:38] + '…') if len(text) > 40 else text
            self.canvas.itemconfigure(self.status, text=f'Dictated: "{display_text}"', fill='#38bdf8')
            self.canvas.itemconfigure(self.footer, text='Injecting text into active window…', fill='#94a3b8')

            # Hide window after brief visual confirmation, then type into target window
            def finish_dictation():
                time.sleep(0.3)
                self.root.withdraw()
                self.paste_text(text)
                self.root.destroy()

            threading.Thread(target=finish_dictation, daemon=True).start()

        elif item_type == 'command':
            app_name, desktop_path, transcript = payload
            self.pending_command = (app_name, desktop_path)
            self.phase = 'confirm'
            self.canvas.itemconfigure(self.status, text=f'Launch {app_name}?', fill='#c084fc')
            self.canvas.itemconfigure(self.footer, text='Press Enter to launch  ·  Esc to cancel', fill='#a78bfa')
            self.root.after(6000, lambda: self.root.destroy() if self.phase == 'confirm' else None)

    def confirm_action(self):
        if self.phase == 'confirm' and self.pending_command:
            app_name, desktop_path = self.pending_command
            subprocess.Popen(['gio', 'launch', desktop_path])
            subprocess.run(['notify-send', 'JARVIS', f'Launched {app_name}'], check=False)
            self.root.destroy()

    def paste_text(self, text):
        # 1. Guarantee clipboard persistence first
        subprocess.run(['wl-copy', '--', text], check=False)

        # 2. Give window manager time to return focus to target application
        time.sleep(0.08)

        # 3. Inject text using wtype directly into active text input
        typed = False
        try:
            res = subprocess.run(['wtype', '--', text], check=True, timeout=5)
            typed = (res.returncode == 0)
        except Exception:
            typed = False

        if not typed:
            subprocess.run(['notify-send', 'WhisperFlow', 'Copied text to clipboard (Press Ctrl+V)'], check=False)


def monitor_key_release(stop_event):
    """Monitors accessible keyboard devices for key release events (Super/Shift/J or space)."""
    # Keycodes: J=36, LeftMeta=125, RightMeta=126, LeftShift=42, RightShift=54, Space=57
    watch_keys = {36, 125, 126, 42, 54, 57}
    fds = []
    for dev in sorted(glob.glob('/dev/input/event*')):
        try:
            fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
            fds.append(fd)
        except Exception:
            continue

    if not fds:
        return

    # Give small grace period (0.25s) so initial key-press down events settle
    time.sleep(0.25)

    try:
        while not stop_event.is_set():
            r, _, _ = select.select(fds, [], [], 0.05)
            for fd in r:
                while True:
                    try:
                        data = os.read(fd, 24)
                        if not data or len(data) < 24:
                            break
                        _, _, ev_type, code, value = struct.unpack('qqHHi', data)
                        # ev_type 1 == EV_KEY; value 0 == Key Release
                        if ev_type == 1 and value == 0 and code in watch_keys:
                            stop_event.set()
                            return
                    except (BlockingIOError, OSError):
                        break
    finally:
        for fd in fds:
            try:
                os.close(fd)
            except Exception:
                pass


def audio_recorder(overlay, stop_event, pcm_chunks):
    """Captures 16 kHz raw audio stream and computes real-time volume RMS for GUI animation."""
    cmd = ['arecord', '-q', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-t', 'raw']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    chunk_size = 1600  # 0.05 seconds of audio per read
    start_time = time.time()
    max_duration = 30.0  # safety timeout

    try:
        while not stop_event.is_set():
            data = proc.stdout.read(chunk_size)
            if not data:
                break
            pcm_chunks.append(data)
            rms = compute_rms(data)
            overlay.audio_level = overlay.audio_level * 0.4 + rms * 0.6

            if time.time() - start_time > max_duration:
                stop_event.set()
                break
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=1)
        except Exception:
            proc.kill()


def run_pipeline(overlay):
    try:
        pcm_chunks = []
        stop_event = overlay.stop_recording_event

        # Start key-release monitor in background thread
        key_thread = threading.Thread(target=monitor_key_release, args=(stop_event,), daemon=True)
        key_thread.start()

        # Record until key release or stop trigger
        audio_recorder(overlay, stop_event, pcm_chunks)

        overlay.phase = 'processing'
        overlay.canvas.itemconfigure(overlay.status, text='Transcribing with Whistle…')

        all_pcm = b''.join(pcm_chunks)
        # Require at least 0.25 seconds of audio
        if len(all_pcm) < 8000:
            raise ValueError('Recording too short, please speak clearly.')

        wav_bytes = pcm_to_wav(all_pcm)

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav_path = f.name
            f.write(wav_bytes)

        try:
            model = LocalModels(TOOL_SCHEMAS)
            transcript = model.transcribe(wav_path).strip()
        finally:
            try:
                os.unlink(wav_path)
            except Exception:
                pass

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


def signal_existing_process():
    """If another JARVIS instance is running, signal it to stop recording and exit this instance."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Check if PID is alive
            os.kill(pid, 0)
            # Send SIGUSR1 to trigger immediate transcription on the running instance
            os.kill(pid, signal.SIGUSR1)
            return True
        except Exception:
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
    return False


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

    # If already running, signal running instance to stop & transcribe (toggle behavior)
    if signal_existing_process():
        return 0

    # Write current PID
    my_pid = os.getpid()
    with open(PID_FILE, 'w') as f:
        f.write(str(my_pid))

    active_mode = args.mode or get_stored_mode()
    root = tk.Tk()
    overlay = VoiceOverlay(root, mode=active_mode)

    # Listen for SIGUSR1 to stop recording if user presses hotkey again
    def handle_sigusr1(signum, frame):
        overlay.stop_recording_event.set()

    signal.signal(signal.SIGUSR1, handle_sigusr1)

    threading.Thread(target=run_pipeline, args=(overlay,), daemon=True).start()

    try:
        root.mainloop()
    finally:
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass

    return 0


if __name__ == '__main__':
    sys.exit(main())
