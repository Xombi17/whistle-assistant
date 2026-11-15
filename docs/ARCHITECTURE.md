# Whistle Assistant: System Architecture

Whistle Assistant is an ultra-low-latency, privacy-first voice dictation and desktop assistant designed specifically for Linux desktop environments (Wayland and X11).

```
 ┌──────────────┐      ┌─────────────────────────┐      ┌──────────────────────────┐
 │  Microphone  │ ---> │     Audio Capture       │ ---> │ Speech Recognition (ASR) │
 │ (ALSA/PipeW) │      │ (arecord / PipeWire /   │      │ - Groq Whisper-v3-turbo  │
 └──────────────┘      │  WirePlumber / Pulse)   │      │ - Local Cactus Whistle   │
                       └─────────────────────────┘      └────────────┬─────────────┘
                                                                     │ Raw Transcript
                                                                     ▼
 ┌──────────────┐      ┌─────────────────────────┐      ┌──────────────────────────┐
 │ Target App / │ <--- │  System Text Injection  │ <--- │ WhisperFlow Normalization│
 │ Input Field  │      │ - Wayland (wtype)       │      │ - Multi-Provider LLM     │
 └──────────────┘      │ - Clipboard (wl-copy)   │      │ - Phonetic Tech Repair   │
                       └─────────────────────────┘      │ - Native Latin Hinglish  │
                                                        │ - Self-Correction Engine │
                                                        └────────────┬─────────────┘
                                                                     │
                                                                     ▼
                                                        ┌──────────────────────────┐
                                                        │ SQLite History & Cache   │
                                                        │ (~/.local/share/jarvis)  │
                                                        └──────────────────────────┘
```

---

## 1. Audio Capture & Hardware Integration

- **Subsystem**: Integrated with Linux audio stacks via `arecord`, with runtime device discovery querying `wpctl status` and `pactl get-default-source`.
- **Format**: High-fidelity 16kHz mono 16-bit linear PCM (`S16_LE`), standard for state-of-the-art transformer acoustic models.
- **Trigger Mechanisms**:
  - **Press-and-Hold Dictation**: The lightweight HUD (`whistle-hud`) captures audio continuously while the user holds the hotkey (e.g. `Super+Shift+J` or `F8`), terminating capture immediately on key release.
  - **Single-Key Toggle**: Tap to begin recording, tap to conclude.

---

## 2. ASR Engine (Speech-to-Text)

Whistle employs a tiered, fault-tolerant transcription strategy:

1. **Tier 1 (Ultra-Fast Cloud Inference)**:
   - Powered by Groq Cloud (`whisper-large-v3-turbo`).
   - Inference latency typically under 150ms.
   - **Prompt Biasing**: Injects domain-specific developer terminology (e.g. `Groq`, `Grok`, `DeepSeek`, `Ollama`, `PipeWire`, `Wayland`, `Vite`, `PyTorch`) directly into Whisper's initial decoder prompt to suppress homophone misrecognitions at the acoustic level.

2. **Tier 2 (Fully Offline Local Fallback)**:
   - Powered by Cactus Compute (`cactus.Whistle` / `whistle.cact`).
   - 100% offline, zero network egress, fully private.

---

## 3. WhisperFlow Normalization & Post-Processing

Raw speech from acoustic decoders lacks punctuation, contains hesitation artifacts, and often misinterprets developer jargon or bilingual phrasing. Whistle runs a hybrid normalization pipeline:

### A. Cloud / Local LLM Formatter (`jarvis.formatter`)
- Connects to Groq (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`), Ollama, or xAI (Grok).
- Applies temperature `0.1` deterministic formatting guided by the WhisperFlow prompt contract.
- Fixes spoken punctuation ("period", "comma", "new line").
- Strips filler tokens ("um", "uh", "er", "you know").
- Preserves native bilingual **Hinglish** in English Latin script (e.g., `"theek hai bhai, Groq configuration add ho gaya"`), preventing unwanted English translation or Devanagari script transliteration.

### B. Deterministic Rule Pipeline (`jarvis.writing`)
- Used as an instantaneous, zero-latency local fallback if network connectivity drops or no LLM provider is configured.
- Regex-driven phonetic homophone repair (`crawl configuration` $\rightarrow$ `Groq configuration`, `deep sick` $\rightarrow$ `DeepSeek`).
- Spoken punctuation translation.
- Mid-sentence self-correction resolution (`"Monday, no, Tuesday"` $\rightarrow$ `"Tuesday"`).

---

## 4. Text Injection & Desktop Integration

- **Wayland Native Injection**: Uses `wtype` to simulate direct keypresses into the active focused window.
- **Clipboard Sync**: Transcripts are automatically copied to the primary Wayland clipboard via `wl-copy`.
- **Desktop Application Portal**: Registered in `~/.local/share/applications/whistle.desktop` with `StartupWMClass=WhistleApp` so that GNOME, KDE, and modern Wayland compositors correctly index, group, and display the app under running applications.

---

## 5. Storage & History

- Local SQLite database stored at `~/.local/share/jarvis/history.sqlite3`.
- Stores raw transcripts, formatted outputs, audio duration, and timestamps.
- Indexed for real-time full-text search across past dictation sessions.
