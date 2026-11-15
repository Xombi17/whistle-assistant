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

# DeepSeek Hardware Design Tokens
C_CHASSIS = "#070a12"        # Deep Obsidian
C_PANEL = "#0e1320"          # Compute Module Panel
C_BORDER = "#1b253b"         # Laser-cut hairline
C_CYAN_ACCENT = "#00d2ff"    # DeepSeek Electric Cyan
C_COBALT = "#3b82f6"         # Primary Cobalt Blue
C_EMERALD = "#10b981"        # System Status Green
C_ROSE = "#f43f5e"           # Record / Alert Red
C_TEXT_MAIN = "#f1f5f9"      # High contrast readout
C_TEXT_MUTED = "#64748b"     # Telemetry gray
C_TEXT_SUB = "#94a3b8"       # Secondary text
C_KEYCAP_BG = "#161f33"      # Tactile keycap background


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


def get_pressed_key_codes():
    pressed = set()
    for dev in ["/dev/input/event2", "/dev/input/event7"]:
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


class DeepSeekVoiceHUD:
    def __init__(self, root: tk.Tk, mode: str = "transcribe"):
        self.root = root
        self.mode = mode
        self.root.title("DEEPSEEK // JARVIS")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=C_CHASSIS)

        self.width = 520
        self.height = 175
        self.root.geometry(f"{self.width}x{self.height}")
        self.root.update_idletasks()
        x = (root.winfo_screenwidth() - self.width) // 2
        y = root.winfo_screenheight() - 235
        root.geometry(f"+{x}+{y}")

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
        self.peak_levels = [0.0] * 32
        self.result_queue = queue.Queue()
        self.stop_recording_event = threading.Event()
        self.pending_command = None
        self.is_destroyed = False

        self.draw_hardware_chassis()
        self.root.after(35, self.animate_spectrum)
        self.root.after(60, self.check_result)

    def safe_destroy(self):
        if not self.is_destroyed:
            self.is_destroyed = True
            try:
                self.root.destroy()
            except Exception:
                pass

    def draw_hardware_chassis(self):
        self.canvas.delete("all")
        is_transcribe = (self.mode == "transcribe")

        # 1. Outer Chassis Frame with laser-cut chamfer corners
        self.canvas.create_rectangle(1, 1, self.width - 2, self.height - 2, fill=C_PANEL, outline=C_BORDER, width=1)
        # Laser-cut accent corner brackets
        accent_col = C_CYAN_ACCENT if is_transcribe else "#c084fc"
        self.canvas.create_line(1, 14, 1, 1, 14, 1, fill=accent_col, width=2)
        self.canvas.create_line(self.width - 15, 1, self.width - 2, 1, self.width - 2, 14, fill=accent_col, width=2)
        self.canvas.create_line(1, self.height - 15, 1, self.height - 2, 14, self.height - 2, fill=accent_col, width=2)
        self.canvas.create_line(self.width - 15, self.height - 2, self.width - 2, self.height - 2, self.width - 2, self.height - 15, fill=accent_col, width=2)

        # 2. Header Telemetry Bar
        self.led_indicator = self.canvas.create_oval(18, 16, 26, 24, fill=C_ROSE if self.phase == "listening" else C_CYAN_ACCENT, outline="")
        self.canvas.create_text(34, 20, text="DEEPSEEK // VOICE CORE", anchor="w", fill=C_TEXT_MAIN, font=("Monospace", 9, "bold"))
        self.canvas.create_text(220, 20, text="16kHz · RAW PCM", anchor="w", fill=C_TEXT_MUTED, font=("Monospace", 8))

        # Mode Badge / Tactile Switch (Top Right)
        mode_str = "DICTATION [TAB]" if is_transcribe else "COMMAND [TAB]"
        btn_tag = "mode_switch"
        self.canvas.create_rectangle(self.width - 146, 11, self.width - 16, 30, fill=C_KEYCAP_BG, outline=C_BORDER, tags=btn_tag)
        self.canvas.create_text(self.width - 81, 20, text=f"⇄ {mode_str}", fill=accent_col, font=("Monospace", 8, "bold"), tags=btn_tag)
        self.canvas.tag_bind(btn_tag, "<Button-1>", lambda e: self.toggle_mode_live())

        # Hairline separator
        self.canvas.create_line(16, 36, self.width - 16, 36, fill=C_BORDER, width=1)

        # 3. Primary Status & Text Console
        initial_status = "RECORDING // SPEAK NOW (HOLD HOTKEY)" if self.phase == "listening" else "PROCESSING..."
        self.status = self.canvas.create_text(18, 56, text=initial_status, anchor="w", fill=C_TEXT_MAIN, font=("Monospace", 10, "bold"))

        # 4. Digital Spectrum Analyzer VU-Meter (32 Hardware Bars)
        self.bars = []
        bar_count = 32
        start_x = 18
        bar_spacing = (self.width - 36) / bar_count
        base_y = 132

        for i in range(bar_count):
            x = start_x + i * bar_spacing + 3
            bar = self.canvas.create_line(x, base_y, x, base_y - 2, fill=C_CYAN_ACCENT if is_transcribe else "#a855f7", width=5, capstyle="projecting")
            self.bars.append(bar)

        # dB Scale readout
        self.db_label = self.canvas.create_text(self.width - 18, 126, text="-48 dBFS", anchor="e", fill=C_TEXT_MUTED, font=("Monospace", 8))

        # 5. Footer Telemetry & Keycaps
        self.canvas.create_line(16, 144, self.width - 16, 144, fill=C_BORDER, width=1)
        self.footer = self.canvas.create_text(18, 158, text="RELEASE HOTKEY / RETURN: FINISH  ·  ESC: ABORT", anchor="w", fill=C_TEXT_MUTED, font=("Monospace", 8))

        # Hardware Engine Badge
        cfg = load_config()
        provider_name = cfg.get("provider", "GROQ").upper()
        self.canvas.create_text(self.width - 18, 158, text=f"AI // {provider_name}", anchor="e", fill=C_COBALT, font=("Monospace", 8, "bold"))

    def set_status_threadsafe(self, text, phase=None, fill=None):
        def _update():
            if self.is_destroyed:
                return
            if phase:
                self.phase = phase
                dot_fill = C_ROSE if phase == "listening" else C_CYAN_ACCENT
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
        self.draw_hardware_chassis()

    def on_return_pressed(self):
        if self.phase == "listening":
            self.stop_recording_event.set()
        elif self.phase == "confirm":
            self.confirm_action()

    def on_space_released(self):
        if self.phase == "listening":
            self.stop_recording_event.set()

    def on_mouse_released(self, event):
        if self.phase == "listening" and event.y > 38:
            self.stop_recording_event.set()

    def animate_spectrum(self):
        if self.is_destroyed:
            return
        self.tick += 1
        is_transcribe = (self.mode == "transcribe")
        base_color = C_CYAN_ACCENT if is_transcribe else "#c084fc"

        base_y = 132
        max_height = 54

        if self.phase == "listening":
            # Real RMS volume drives the spectrum analyzer
            norm_rms = min(1.0, max(0.0, self.current_rms / 2800.0))
            db_val = max(-60, int(20 * math.log10(norm_rms + 1e-4)))
            self.canvas.itemconfigure(self.db_label, text=f"{db_val} dBFS")

            # Pulse the LED
            led_glow = C_ROSE if (self.tick // 6) % 2 == 0 else "#9f1239"
            self.canvas.itemconfigure(self.led_indicator, fill=led_glow)

            for i, bar in enumerate(self.bars):
                # Frequency-like distribution curve (center weighted)
                freq_weight = math.sin((i / len(self.bars)) * math.pi)
                jitter = (math.sin(self.tick * 0.35 + i * 0.75) + 1.0) * 0.5
                h = max(2, int((norm_rms * 0.85 + jitter * 0.15) * freq_weight * max_height))

                # Color gradient: Cyan/Blue -> Intense Neon
                bar_color = base_color if h < 35 else "#38bdf8" if h < 46 else "#ffffff"
                x = 18 + i * ((self.width - 36) / len(self.bars)) + 3
                self.canvas.coords(bar, x, base_y, x, base_y - h)
                self.canvas.itemconfigure(bar, fill=bar_color)

        elif self.phase == "processing":
            self.canvas.itemconfigure(self.led_indicator, fill=C_CYAN_ACCENT)
            self.canvas.itemconfigure(self.db_label, text="NEURAL // INFERENCE")
            for i, bar in enumerate(self.bars):
                wave = abs(math.sin(self.tick * 0.28 + i * 0.42))
                h = max(3, int(wave * 30))
                x = 18 + i * ((self.width - 36) / len(self.bars)) + 3
                self.canvas.coords(bar, x, base_y, x, base_y - h)
                self.canvas.itemconfigure(bar, fill=C_COBALT)

        self.root.after(35, self.animate_spectrum)

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
            self.canvas.itemconfigure(self.status, text=f"ERROR // {error.upper()}", fill=C_ROSE)
            self.root.after(2200, self.safe_destroy)
            return

        if item_type == "transcribe":
            text = payload
            self.phase = "done"
            display_text = (text[:40] + "…") if len(text) > 42 else text
            self.canvas.itemconfigure(self.status, text=f'DICTATED: "{display_text}"', fill=C_CYAN_ACCENT)
            self.canvas.itemconfigure(self.footer, text="INJECTING TEXT TO ACTIVE APPLICATION...", fill=C_EMERALD)

            def finish_dictation():
                try:
                    self.root.withdraw()
                except Exception:
                    pass
                threading.Thread(target=paste_text, args=(text,), daemon=True).start()
                self.root.after(800, self.safe_destroy)

            self.root.after(300, finish_dictation)

        elif item_type == "command":
            app_name, desktop_path, transcript = payload
            self.pending_command = (app_name, desktop_path)
            self.phase = "confirm"
            self.canvas.itemconfigure(self.status, text=f"EXECUTE // LAUNCH {app_name.upper()}?", fill="#c084fc")
            self.canvas.itemconfigure(self.footer, text="PRESS [ENTER] TO EXECUTE  ·  [ESC] TO ABORT", fill=C_EMERALD)
            self.root.after(6000, lambda: self.safe_destroy() if self.phase == "confirm" else None)

    def confirm_action(self):
        if self.phase == "confirm" and self.pending_command:
            app_name, desktop_path = self.pending_command
            subprocess.Popen(["gio", "launch", desktop_path])
            subprocess.run(["notify-send", "JARVIS // EXEC", f"Launched {app_name}"], check=False)
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
    for kbd in ["/dev/input/event17", "/dev/input/event2", "/dev/input/event7"]:
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
        subprocess.run(["notify-send", "WhisperFlow", f"Inserted: {text[:45]}"], check=False)
    else:
        subprocess.run(["notify-send", "WhisperFlow", f'Copied: "{text[:45]}" (Ctrl+V)'], check=False)


def monitor_key_release(stop_event):
    initial_modifiers = {42, 54, 125, 126}
    initial_pressed = get_pressed_key_codes() & initial_modifiers
    was_holding = bool(initial_pressed)

    time.sleep(0.5)
    if not was_holding:
        return

    while not stop_event.is_set():
        current_pressed = get_pressed_key_codes()
        if not (current_pressed & initial_modifiers):
            stop_event.set()
            return
        time.sleep(0.04)


def audio_recorder(overlay, stop_event, pcm_chunks):
    cmd = ["arecord", "-D", "default", "-q", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    chunk_size = 1600
    start_time = time.time()
    max_duration = 35.0

    try:
        while not stop_event.is_set():
            data = proc.stdout.read(chunk_size)
            if not data:
                break
            pcm_chunks.append(data)
            rms = compute_rms(data)
            overlay.current_rms = rms

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
        if len(all_pcm) < 9600:
            raise ValueError("Recording too short — hold key while speaking.")

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
                pid = int(f.read().strip())
            os.kill(pid, 0)
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
        subprocess.run(["notify-send", "JARVIS Mode", f"Active mode: {mode}"], check=False)
        return 0

    if signal_existing_process():
        return 0

    my_pid = os.getpid()
    with open(PID_FILE, "w") as f:
        f.write(str(my_pid))

    active_mode = args.mode or get_stored_mode()
    root = tk.Tk()
    overlay = DeepSeekVoiceHUD(root, mode=active_mode)

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


if __name__ == "__main__":
    sys.exit(main())
