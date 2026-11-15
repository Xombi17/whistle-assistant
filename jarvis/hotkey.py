"""JARVIS Voice Overlay with DeepSeek Hardware aesthetic.
Features an industrial compute chassis, precision VU spectrum analyzer, telemetry badges, and hold-to-talk."""

import argparse
import array
import configparser
import fcntl
import glob
import math
import os
import queue
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
from jarvis.formatter import load_config, polish_transcript
from jarvis.history import save_history_item
from jarvis.model import LocalModels
from jarvis.validation import validate

CONFIG_DIR = Path.home() / ".config" / "jarvis"
MODE_FILE = CONFIG_DIR / "mode"
PID_FILE = os.path.join(os.environ.get("XDG_RUNTIME_DIR", tempfile.gettempdir()), "jarvis.pid")
HELD_FLAG = Path(tempfile.gettempdir()) / "whistle_held.flag"

TOOL_SCHEMAS = [
    {
        "name": "open_app",
        "description": "Open an installed application",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    }
]

# Modern Minimalist Design Tokens (Whistle)
C_CHASSIS = "#0e1015"
C_PANEL = "#131620"
C_BORDER = "#232a3b"
C_BLUE = "#3b82f6"
C_ROSE = "#ef4444"
C_EMERALD = "#10b981"
C_TEXT_MAIN = "#f1f5f9"
C_TEXT_MUTED = "#94a3b8"


def get_stored_mode():
    try:
        if MODE_FILE.is_file():
            mode = MODE_FILE.read_text(encoding="utf-8").strip().lower()
            if mode in ("transcribe", "dictate", "whisperflow"):
                return "transcribe"
            if mode in ("command", "assistant"):
                return "command"
    except Exception:
        pass
    return "transcribe"


def set_stored_mode(mode):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MODE_FILE.write_text(mode, encoding="utf-8")


def toggle_stored_mode():
    current = get_stored_mode()
    new_mode = "command" if current == "transcribe" else "transcribe"
    set_stored_mode(new_mode)
    label = "Command Mode (JARVIS)" if new_mode == "command" else "Dictation Mode (WhisperFlow)"
    subprocess.run(["notify-send", "JARVIS Mode Switched", f"Active: {label}"], check=False)
    return new_mode


def resolve_app(name):
    paths = [Path.home() / ".local/share/applications"] + [
        Path(x) / "applications" for x in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")
    ]
    matches = []
    for folder in paths:
        if not folder.is_dir():
            continue
        for path in folder.glob("*.desktop"):
            parser = configparser.ConfigParser(interpolation=None)
            try:
                parser.read(path, encoding="utf-8")
                entry = parser["Desktop Entry"]
                label = entry.get("Name", "")
                if (
                    entry.get("Type") == "Application"
                    and not entry.getboolean("Hidden", fallback=False)
                    and not entry.getboolean("NoDisplay", fallback=False)
                    and (label.casefold() == name.casefold() or path.stem.casefold() == name.casefold())
                ):
                    matches.append(str(path.resolve(strict=True)))
            except Exception:
                continue
    unique = list(dict.fromkeys(matches))
    return unique[0] if unique else None


def pcm_to_wav(pcm_data, sample_rate=16000, channels=1, sampwidth=2):
    data_size = len(pcm_data)
    byte_rate = sample_rate * channels * sampwidth
    block_align = channels * sampwidth
    bits_per_sample = sampwidth * 8
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + pcm_data


def compute_rms(pcm_bytes):
    if not pcm_bytes:
        return 0
    count = len(pcm_bytes) // 2
    if count == 0:
        return 0
    try:
        shorts = struct.unpack(f"<{count}h", pcm_bytes[: count * 2])
        sum_sq = sum(s * s for s in shorts)
        return int((sum_sq / count) ** 0.5)
    except Exception:
        return 0


def find_physical_keyboards():
    """Finds physical keyboard input devices, prioritizing real hardware keyboards."""
    hardware_kbds = []
    virtual_kbds = []
    for dev in sorted(glob.glob("/dev/input/event*")):
        try:
            with open(dev, "rb") as f:
                buf = array.array("B", [0] * 256)
                fcntl.ioctl(f.fileno(), 2 << 30 | (len(buf) << 16) | (ord("E") << 8) | 0x06, buf)
                name = buf.tobytes().split(b"\x00")[0].decode("utf-8", errors="ignore").lower()
                if "keyboard" in name:
                    if "virtual" in name or "snippet" in name:
                        virtual_kbds.append(dev)
                    else:
                        hardware_kbds.append(dev)
        except Exception:
            pass
    return hardware_kbds or virtual_kbds or ["/dev/input/event2", "/dev/input/event7"]


def get_pressed_key_codes():
    pressed = set()
    for dev in find_physical_keyboards():
        try:
            fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
            buf = array.array("B", [0] * 64)
            EVIOCGKEY = 2 << 30 | (len(buf) << 16) | (ord("E") << 8) | 0x18
            fcntl.ioctl(fd, EVIOCGKEY, buf, True)
            for code in range(len(buf) * 8):
                if (buf[code // 8] >> (code % 8)) & 1:
                    pressed.add(code)
            os.close(fd)
        except Exception:
            pass
    return pressed


class WhistleVoiceHUD:
    def __init__(self, root: tk.Tk, mode: str = "transcribe"):
        self.root = root
        self.mode = mode
        self.root.title("Whistle")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=C_CHASSIS)

        self.width = 360
        self.height = 52
        self.target_x = (root.winfo_screenwidth() - self.width) // 2
        self.target_y = root.winfo_screenheight() - 110
        self.current_y = self.target_y + 35

        self.root.geometry(f"{self.width}x{self.height}+{self.target_x}+{self.current_y}")
        self.root.update_idletasks()

        self.canvas = tk.Canvas(root, width=self.width, height=self.height, bg=C_CHASSIS, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Bindings
        self.root.bind("<Escape>", lambda e: self.safe_destroy())
        self.root.bind("<Tab>", lambda e: self.toggle_mode_live())
        self.root.bind("<m>", lambda e: self.toggle_mode_live())
        self.root.bind("<Return>", lambda e: self.on_return_pressed())
        self.root.bind("<KeyRelease-space>", lambda e: self.on_space_released())
        self.root.bind("<ButtonRelease-1>", lambda e: self.on_mouse_released(e))

        self.phase = "listening"
        self.tick = 0
        self.current_rms = 0.0
        self.result_queue = queue.Queue()
        self.stop_recording_event = threading.Event()
        self.pending_command = None
        self.is_destroyed = False

        self.draw_pill()
        self.animate_entrance()
        self.root.after(30, self.animate_spectrum)
        self.root.after(60, self.check_result)

    def animate_entrance(self):
        """Smooth spring-up entry animation from bottom."""
        if self.is_destroyed:
            return
        if self.current_y > self.target_y:
            step = max(2, (self.current_y - self.target_y) // 2)
            self.current_y -= step
            self.root.geometry(f"+{self.target_x}+{self.current_y}")
            self.root.after(16, self.animate_entrance)
        else:
            self.current_y = self.target_y
            self.root.geometry(f"+{self.target_x}+{self.target_y}")

    def safe_destroy(self):
        if not self.is_destroyed:
            self.is_destroyed = True
            try:
                self.root.destroy()
            except Exception:
                pass

    def draw_pill(self):
        self.canvas.delete("all")
        is_transcribe = (self.mode == "transcribe")

        # 1. Clean Pill Capsule Container
        self.canvas.create_rectangle(1, 1, self.width - 2, self.height - 2, fill=C_PANEL, outline=C_BORDER, width=1)

        # 2. Recording Status LED
        self.led_indicator = self.canvas.create_oval(18, 21, 28, 31, fill=C_ROSE, outline="")

        # 3. Status text
        status_text = "Listening..." if self.phase == "listening" else "Formatting..."
        self.status = self.canvas.create_text(38, 26, text=status_text, anchor="w", fill=C_TEXT_MAIN, font=("Sans", 10, "bold"))

        # 4. Voice Wave Bars (Centered vertically)
        self.bars = []
        bar_count = 8
        start_x = 180
        base_y = 26

        for i in range(bar_count):
            x = start_x + i * 8
            bar = self.canvas.create_line(x, base_y - 2, x, base_y + 2, fill=C_BLUE, width=3, capstyle="round")
            self.bars.append(bar)

        # 5. Right Mode / Shortcut hint
        mode_str = "Dictation" if is_transcribe else "Command"
        btn_tag = "mode_switch"
        self.canvas.create_text(self.width - 18, 26, text=f"{mode_str} (Tab)", anchor="e", fill=C_TEXT_MUTED, font=("Sans", 9), tags=btn_tag)
        self.canvas.tag_bind(btn_tag, "<Button-1>", lambda e: self.toggle_mode_live())

    def set_status_threadsafe(self, text, phase=None, fill=None):
        def _update():
            if self.is_destroyed:
                return
            if phase:
                self.phase = phase
                dot_fill = C_ROSE if phase == "listening" else C_BLUE
                try:
                    self.canvas.itemconfigure(self.led_indicator, fill=dot_fill)
                except Exception:
                    pass
            kwargs = {"text": text}
            if fill:
                kwargs["fill"] = fill
            try:
                self.canvas.itemconfigure(self.status, **kwargs)
            except Exception:
                pass
        self.root.after(0, _update)

    def toggle_mode_live(self):
        self.mode = "command" if self.mode == "transcribe" else "transcribe"
        set_stored_mode(self.mode)
        self.draw_pill()

    def on_return_pressed(self):
        if self.phase == "listening":
            self.stop_recording_event.set()
        elif self.phase == "confirm":
            self.confirm_action()

    def on_space_released(self):
        if self.phase == "listening":
            self.stop_recording_event.set()

    def on_mouse_released(self, event):
        if self.phase == "listening":
            self.stop_recording_event.set()

    def animate_spectrum(self):
        if self.is_destroyed:
            return
        self.tick += 1
        base_y = 26

        if self.phase == "listening":
            norm_rms = min(1.0, max(0.0, self.current_rms / 2500.0))
            led_glow = C_ROSE if (self.tick // 5) % 2 == 0 else "#991b1b"
            self.canvas.itemconfigure(self.led_indicator, fill=led_glow)

            for i, bar in enumerate(self.bars):
                freq_weight = math.sin(((i + 1) / (len(self.bars) + 1)) * math.pi)
                jitter = (math.sin(self.tick * 0.35 + i * 0.8) + 1.0) * 0.5
                h = max(2, int((norm_rms * 16 + jitter * 6) * freq_weight))
                x = 180 + i * 8
                self.canvas.coords(bar, x, base_y - h, x, base_y + h)
                self.canvas.itemconfigure(bar, fill=C_BLUE if h < 8 else "#60a5fa")

        elif self.phase == "processing":
            self.canvas.itemconfigure(self.led_indicator, fill=C_BLUE)
            for i, bar in enumerate(self.bars):
                wave = abs(math.sin(self.tick * 0.25 + i * 0.45))
                h = max(2, int(wave * 12))
                x = 180 + i * 8
                self.canvas.coords(bar, x, base_y - h, x, base_y + h)
                self.canvas.itemconfigure(bar, fill="#818cf8")

        self.root.after(30, self.animate_spectrum)

    def check_result(self):
        if self.is_destroyed:
            return
        try:
            item_type, payload, error = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(60, self.check_result)
            return

        if error:
            self.phase = "error"
            self.canvas.itemconfigure(self.status, text="Error", fill=C_ROSE)
            self.root.after(1800, self.safe_destroy)
            return

        if item_type == "transcribe":
            text = payload
            self.phase = "done"
            display_text = (text[:24] + "…") if len(text) > 26 else text
            self.canvas.itemconfigure(self.status, text=display_text, fill=C_TEXT_MAIN)
            self.canvas.itemconfigure(self.led_indicator, fill=C_EMERALD)

            def finish_dictation():
                try:
                    self.root.withdraw()
                except Exception:
                    pass
                threading.Thread(target=paste_text, args=(text,), daemon=True).start()
                self.root.after(600, self.safe_destroy)

            self.root.after(250, finish_dictation)

        elif item_type == "command":
            app_name, desktop_path, transcript = payload
            self.pending_command = (app_name, desktop_path)
            self.phase = "confirm"
            self.canvas.itemconfigure(self.status, text=f"Launch {app_name}?", fill="#a855f7")
            self.root.after(5000, lambda: self.safe_destroy() if self.phase == "confirm" else None)

    def confirm_action(self):
        if self.phase == "confirm" and self.pending_command:
            app_name, desktop_path = self.pending_command
            subprocess.Popen(["gio", "launch", desktop_path])
            subprocess.run(["notify-send", "Whistle", f"Launched {app_name}"], check=False)
            self.safe_destroy()


def paste_text(text):
    """Guarantees clipboard copy on Wayland, and simulates Ctrl+V into active application."""
    if not text:
        return

    try:
        subprocess.run(["wl-copy", "-n", "--", text], check=True, timeout=2)
        subprocess.run(["wl-copy", "-p", "-n", "--", text], check=False, timeout=2)
    except Exception:
        pass

    time.sleep(0.12)

    pasted = False
    for kbd in find_physical_keyboards():
        try:
            subprocess.run(["evemu-event", kbd, "--sync", "--type", "EV_KEY", "--code", "KEY_LEFTCTRL", "--value", "1"], check=True, timeout=1)
            subprocess.run(["evemu-event", kbd, "--sync", "--type", "EV_KEY", "--code", "KEY_V", "--value", "1"], check=True, timeout=1)
            time.sleep(0.02)
            subprocess.run(["evemu-event", kbd, "--sync", "--type", "EV_KEY", "--code", "KEY_V", "--value", "0"], check=True, timeout=1)
            subprocess.run(["evemu-event", kbd, "--sync", "--type", "EV_KEY", "--code", "KEY_LEFTCTRL", "--value", "0"], check=True, timeout=1)
            pasted = True
            break
        except Exception:
            continue

    if pasted:
        subprocess.run(["notify-send", "Whistle", f"Inserted: {text[:45]}"], check=False)
    else:
        subprocess.run(["notify-send", "Whistle", f'Copied: "{text[:45]}" (Ctrl+V)'], check=False)


def monitor_key_release(stop_event):
    """Detects when held hotkey shortcut is released."""
    time.sleep(0.08)
    initial_pressed = get_pressed_key_codes()
    held_keys = {k for k in initial_pressed if k < 256}

    if not held_keys:
        try:
            HELD_FLAG.unlink(missing_ok=True)
        except Exception:
            pass
        return

    time.sleep(0.15)
    while not stop_event.is_set():
        current = get_pressed_key_codes()
        if not (current & held_keys):
            try:
                HELD_FLAG.unlink(missing_ok=True)
            except Exception:
                pass
            stop_event.set()
            return
        time.sleep(0.04)


def audio_recorder(overlay, stop_event, pcm_chunks):
    cmd = ["arecord", "-D", "default", "-q", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    chunk_size = 1600
    start_time = time.time()
    max_duration = 35.0

    speech_detected = False
    speech_frames = 0
    silence_frames = 0
    SPEECH_THRESHOLD = 450
    SILENCE_LIMIT_FRAMES = 14  # ~1.4s silence after speech automatically stops recording

    try:
        while not stop_event.is_set():
            data = proc.stdout.read(chunk_size)
            if not data:
                break
            pcm_chunks.append(data)
            rms = compute_rms(data)
            overlay.current_rms = rms

            # Auto-VAD silence detection
            if rms >= SPEECH_THRESHOLD:
                speech_frames += 1
                if speech_frames >= 2:
                    speech_detected = True
                    silence_frames = 0
            elif speech_detected:
                silence_frames += 1
                if silence_frames >= SILENCE_LIMIT_FRAMES:
                    stop_event.set()
                    break

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

        key_thread = threading.Thread(target=monitor_key_release, args=(stop_event,), daemon=True)
        key_thread.start()

        audio_recorder(overlay, stop_event, pcm_chunks)

        overlay.set_status_threadsafe("NEURAL INFERENCE // TRANSCRIBING...", phase="processing")

        all_pcm = b"".join(pcm_chunks)
        if len(all_pcm) < 4800:
            raise ValueError("Recording too short — speak while holding key.")

        wav_bytes = pcm_to_wav(all_pcm)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
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
            raise ValueError("No speech detected. Check audio source.")

        if overlay.mode == "transcribe":
            overlay.set_status_threadsafe("NEURAL INFERENCE // FORMATTING WITH AI...", phase="processing")
            cfg = load_config()
            polished = polish_transcript(transcript)
            final_text = polished or transcript
            save_history_item(raw_text=transcript, formatted_text=final_text, mode="transcribe", provider=cfg.get("provider", "groq"))
            overlay.result_queue.put(("transcribe", final_text, None))
        else:
            overlay.set_status_threadsafe("NEURAL INFERENCE // INTERPRETING COMMAND...")
            save_history_item(raw_text=transcript, formatted_text=transcript, mode="command", provider="needle3")
            response = model.propose(transcript)
            calls = validate(response)
            if not calls or calls[0]["name"] != "open_app":
                raise ValueError('Only "open <app>" is currently supported in command mode.')
            app_name = calls[0]["arguments"]["name"]
            desktop_file = resolve_app(app_name)
            if not desktop_file:
                raise ValueError(f'No installed application found for "{app_name}"')
            overlay.result_queue.put(("command", (app_name, desktop_file, transcript), None))

    except Exception as exc:
        overlay.result_queue.put((None, None, str(exc)))


def signal_existing_process():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                content = f.read().strip().split()
                pid = int(content[0])

            os.kill(pid, 0)

            # If user is currently holding the key down, GNOME will auto-repeat launch.
            # While HELD_FLAG exists, NEVER abort or signal the existing recording!
            if HELD_FLAG.exists():
                return True

            # If HELD_FLAG does not exist, this is an intentional second press in toggle mode
            os.kill(pid, signal.SIGUSR1)
            return True
        except Exception:
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
    return False


def main():
    parser = argparse.ArgumentParser(description="JARVIS / WhisperFlow Voice Overlay")
    parser.add_argument("--mode", choices=["transcribe", "command"], help="Force specific mode")
    parser.add_argument("--toggle", action="store_true", help="Toggle between transcription and command modes")
    parser.add_argument("--status", action="store_true", help="Print and notify active mode")
    args = parser.parse_args()

    if args.toggle:
        new_mode = toggle_stored_mode()
        print(f"Mode switched to: {new_mode}")
        return 0

    if args.status:
        mode = get_stored_mode()
        print(f"Current mode: {mode}")
        subprocess.run(["notify-send", "Whistle Mode", f"Active mode: {mode}"], check=False)
        return 0

    if signal_existing_process():
        return 0

    my_pid = os.getpid()
    with open(PID_FILE, "w") as f:
        f.write(str(my_pid))

    # Mark HELD_FLAG if shortcut keys are physically held at launch
    initial_keys = {k for k in get_pressed_key_codes() if k < 256}
    if initial_keys:
        try:
            HELD_FLAG.touch()
        except Exception:
            pass

    active_mode = args.mode or get_stored_mode()
    root = tk.Tk()
    overlay = WhistleVoiceHUD(root, mode=active_mode)

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
        try:
            HELD_FLAG.unlink(missing_ok=True)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
