# JARVIS (Whistle Assistant)

A privacy-first, fully offline voice assistant for Ubuntu Linux powered by local models via [Cactus Compute](https://cactus.compute).

## Architecture & Features

- **Offline Speech-to-Text**: Captures 16 kHz audio via ALSA (`arecord`) and transcribes locally using Whistle (`whistle.cact`).
- **Structured Tool Calling**: Maps user intent to structured JSON tool proposals using Needle 3 (`needle3.cact`).
- **Strict Allowlist & Boundaries**:
  - `open_app(name)`: Discovers verified `.desktop` files and launches them securely via `gio launch`.
  - `find_files(query)`: Sandboxed path searches.
  - `open_file(path)`: Safe file opening without arbitrary execution.
  - `create_reminder(title, when)`, `list_reminders()`, `modify_reminder(...)`, `cancel_reminder(id)`: Local reminder management.
- **Safety First**: Zero autonomous execution—every action proposal must be explicitly confirmed by the user.

## Setup & Prerequisites

```bash
sudo apt install python3 python3-venv python3-tk alsa-utils espeak-ng libglib2.0-bin xdg-utils
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Download model weights offline:
```bash
env CACTUS_TELEMETRY=0 cactus fetch
env CACTUS_TELEMETRY=0 cactus download needle3
env CACTUS_TELEMETRY=0 cactus download whistle
```

## License

MIT
