# Whistle Assistant: Configuration Guide

Whistle Assistant is configured through environment variables or via a JSON configuration file located at:

```
~/.config/whistle/config.json
```
*(Also falls back to `~/.config/jarvis/config.json` for backward compatibility)*

---

## 1. Configuration File Format (`config.json`)

```json
{
  "provider": "groq",
  "groq_api_key": "gsk_...",
  "groq_model": "openai/gpt-oss-120b",
  "xai_api_key": "",
  "xai_model": "grok-beta",
  "ollama_url": "http://localhost:11434",
  "ollama_model": "qwen2.5-coder:7b"
}
```

### Parameter Reference

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `provider` | string | `"groq"` | Active LLM formatting provider (`"groq"`, `"ollama"`, `"xai"`). |
| `groq_api_key` | string | `""` | Groq Cloud API key for ultra-fast Whisper ASR & LLM formatting. |
| `groq_model` | string | `"openai/gpt-oss-120b"` | LLM model identifier on Groq (fallback to `qwen/qwen3.8-27b`). |
| `xai_api_key` | string | `""` | xAI / Grok API key. |
| `xai_model` | string | `"grok-beta"` | Model name for xAI provider. |
| `ollama_url` | string | `"http://localhost:11434"` | Local Ollama base URL. |
| `ollama_model` | string | `"qwen2.5-coder:7b"` | Model tag for local Ollama formatting. |

---

## 2. Environment Variables

All settings can be overridden via environment variables in your shell or `.env` file:

```bash
# Provider Selection
export JARVIS_LLM_PROVIDER=groq

# Groq Cloud API Credentials
export GROQ_API_KEY="gsk_your_key_here"
export GROQ_MODEL="openai/gpt-oss-120b"

# xAI / Grok Credentials
export XAI_API_KEY="xai_your_key_here"
export XAI_MODEL="grok-beta"

# Local Ollama Settings
export OLLAMA_URL="http://localhost:11434"
export OLLAMA_MODEL="qwen2.5-coder:7b"
```

---

## 3. Desktop Hotkey Setup

Whistle is designed to be triggered with a global system hotkey.

### GNOME Settings (Ubuntu / Fedora)
1. Open **Settings** $\rightarrow$ **Keyboard** $\rightarrow$ **Keyboard Shortcuts** $\rightarrow$ **Custom Shortcuts**.
2. Click **+** (Add Shortcut):
   - **Name**: `Whistle Voice Dictation`
   - **Command**: `/path/to/whistle assistant/.venv/bin/whistle-hud`
   - **Shortcut**: `Super+Shift+J` (or `F8`)

### Sway / Hyprland Config
Add to your `~/.config/hypr/hyprland.conf`:
```conf
bind = SUPER SHIFT, J, exec, /path/to/whistle assistant/.venv/bin/whistle-hud
```

Or Sway `~/.config/sway/config`:
```conf
bindsym Mod4+Shift+j exec /path/to/whistle assistant/.venv/bin/whistle-hud
```

---

## 4. Audio Input Device Configuration

Whistle automatically detects your default PipeWire / PulseAudio recording device. To override or inspect:

```bash
# View active sources
wpctl status
pactl get-default-source

# Test microphone recording directly
arecord -f S16_LE -r 16000 -c 1 -d 3 test.wav && aplay test.wav
```
