# JARVIS (Whistle Assistant)

A privacy-first, fully offline voice assistant and WhisperFlow dictation alternative for Ubuntu Linux (Wayland/X11), powered by local models via [Cactus Compute](https://cactus.compute).

## Modes: Dictation (WhisperFlow) vs Command (JARVIS)

The assistant features dual operating modes with instant switching:

### 1. WhisperFlow Dictation Mode (`transcribe`)
- Captures audio and transcribes speech locally using Whistle (`whistle.cact`).
- Injects typed text directly into your currently focused window via `wtype` (Wayland).
- Backs up transcripts straight to the system clipboard via `wl-copy`.

### 2. JARVIS Command Assistant Mode (`command`)
- Transcribes your command.
- Passes intent to Needle 3 (`needle3.cact`) for structured tool proposal.
- Enforces strict schema and safety validation.
- Presents an interactive confirmation dialog with `Enter` to execute (e.g. launching verified desktop applications via `gio launch`).

## How to Switch Modes

- **In the Overlay**: Click the **⇄ Switch (Tab)** button on the top-right of the HUD or press `Tab` / `M` while it's open.
- **Global Toggle**: Run `python3 jarvis/hotkey.py --toggle` (bind to a keyboard shortcut like `Super+Shift+Space`) to flip between modes with desktop notifications.
- **Direct Mode Hotkeys**:
  - Dictation: `python3 jarvis/hotkey.py --mode transcribe` (bind to `Super+D`)
  - Command: `python3 jarvis/hotkey.py --mode command` (bind to `Super+J`)
- **Check Status**: `python3 jarvis/hotkey.py --status`

## Setup & Prerequisites

```bash
sudo apt install python3 python3-venv python3-tk alsa-utils espeak-ng libglib2.0-bin xdg-utils wl-clipboard wtype
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Download local model weights:
```bash
env CACTUS_TELEMETRY=0 cactus fetch
env CACTUS_TELEMETRY=0 cactus download needle3
env CACTUS_TELEMETRY=0 cactus download whistle
```

## Running

```bash
python3 jarvis/hotkey.py
```

## License

MIT
