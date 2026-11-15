# Jarvis - Your Personal Assistant

## Installation

```sh
sudo apt install python3 python3-venv python3-tk alsa-utils espeak-ng libglib2.0-bin xdg-utils
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
env CACTUS_TELEMETRY=0 .venv/bin/cactus fetch
env CACTUS_TELEMETRY=0 .venv/bin/cactus download needle3
env CACTUS_TELEMETRY=0 .venv/bin/cactus download whistle
.venv/bin/python -m jarvis
```

## Usage

Run the assistant with `python -m jarvis`. The GUI will appear, and you can interact with it using the text input, send button, and record button.

## License

MIT License
