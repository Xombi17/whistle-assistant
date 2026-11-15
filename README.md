# Whistle Assistant 🎙️

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-brightgreen.svg)](pyproject.toml)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux%20(Wayland%20%26%20X11)-orange.svg)](docs/ARCHITECTURE.md)
[![Tests: Passing](https://img.shields.io/badge/Tests-Passing-success.svg)](tests/)

An ultra-low latency, privacy-first voice dictation assistant and WhisperFlow alternative tailored for Linux (Ubuntu, Fedora, Arch on Wayland/X11).

Built for software engineers, developers, and bilingual speakers with **phonetic technical auto-correction** and **native Latin-script Hinglish preservation**.

---

## ⚡ Features

- 🏎️ **Ultra-Low Latency ASR**: Tier 1 Groq Whisper-large-v3-turbo with initial prompt biasing for instantaneous, highly accurate transcripts; Tier 2 local offline Cactus Whistle engine.
- 🛠️ **Phonetic Tech Auto-Correction**: Intelligently fixes acoustic mishearings in developer jargon (`"crawl configuration"` $\rightarrow$ `"Groq configuration"`, `"pipe wire"` $\rightarrow$ `"PipeWire"`, `"way land"` $\rightarrow$ `"Wayland"`).
- 🇮🇳 **Native Hinglish Support**: First-class handling of Hindi written in the English alphabet (e.g. *"theek hai bhai, Groq configuration add kar diya hai"*). Never translates Hindi words into English or transliterates into Devanagari script.
- 🪶 **Minimalist Glassmorphic UI**: High-contrast, borderless desktop interface built with Inter typography, clean sidebar history, and ambient depth.
- 🪄 **Floating Spring HUD**: A compact $360\times 52\text{ px}$ floating pill that springs up organically when holding your dictation hotkey and glides away on release.
- ⌨️ **Native Wayland & X11 Typing**: Injects finalized text directly into the focused application via `wtype` and synchronizes to your system clipboard (`wl-copy`).
- 🔒 **Privacy-First & Self-Contained**: Local SQLite history cache and full fallback support for offline local inference and local Ollama models.

---

## 🚀 Quick Start

### 1. One-Command Installation (Ubuntu / Debian)

Clone the repository and run the automated installer:

```bash
git clone https://github.com/Xombi17/whistle-assistant.git
cd whistle-assistant
chmod +x install.sh
./install.sh
```

The installer verifies system utilities (`alsa-utils`, `wl-clipboard`, `wtype`), provisions the Python virtual environment, installs the package, registers the custom squircle desktop icons, and configures the GNOME application launcher.

### 2. Configure Your API Key (Optional for Cloud Speed)

Copy the sample environment file or configure via the desktop UI:

```bash
cp .env.example .env
# Edit .env and supply your GROQ_API_KEY
```

---

## 🖥️ Usage

### Launch Desktop Interface
Launch via your desktop application menu by pressing `Super` and searching for **Whistle**, or run:
```bash
./launch.sh
# Or using the package CLI entry point:
whistle
```

### Launch Voice Dictation HUD
Trigger the floating voice dictation HUD:
```bash
whistle-hud
```

Bind `whistle-hud` to a global keyboard shortcut (e.g. `Super+Shift+J` or `F8`) in your desktop settings. Hold the key to speak, release to instantly inject the polished text into your active window.

---

## 🏗️ Architecture

```
Microphone (PipeWire / ALSA)
        │
        ▼
Speech Recognition (Groq Whisper-turbo / Local Cactus Whistle)
        │ (Raw transcript with keyword bias)
        ▼
WhisperFlow Normalization Pipeline (LLM / Phonetic Tech Rules / Hinglish Engine)
        │ (Polished punctuation & capitalization)
        ▼
Window Injection (Wayland wtype) + Clipboard (wl-copy) + Local SQLite History
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for deep technical details.

---

## ⚙️ Configuration & Customization

Whistle supports Groq Cloud, local Ollama, xAI (Grok), and local deterministic rules.

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for full configuration parameters, environment variables, and window manager integration (GNOME, Sway, Hyprland).

---

## 🧪 Testing

Run the automated test suite using `pytest`:

```bash
source .venv/bin/activate
pytest tests/ -v
```

All 13 tests verify phonetic tech repair, self-corrections, spoken punctuation cues, Hinglish normalization, config persistence, and SQLite history operations.

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding vocabulary rules, running tests, and opening pull requests.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
