"""AI-powered writing formatter supporting Groq Cloud, Ollama, Grok (xAI), and local rule fallback."""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from jarvis.writing import WritingPipeline

CONFIG_DIR = Path.home() / ".config" / "jarvis"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_SYSTEM_PROMPT = """You are an expert voice-to-text dictation editor modeled after WhisperFlow.
Transform the raw speech transcript into clean, professional, publication-ready text.
Rules:
1. Strip verbal disfluencies and fillers (um, uh, er, hmm, you know).
2. Resolve verbal self-corrections (e.g. "Tuesday, no, Wednesday" -> "Wednesday").
3. Convert spoken punctuation and layout cues ("new line", "new paragraph", "comma", "period", "bullet point").
4. Fix grammar, spacing, and capitalization without altering the speaker's original meaning or intent.
5. Output ONLY the final polished text. Do NOT include greetings, preamble, quotes, or markdown codeblocks."""


def load_config() -> dict:
    """Loads configuration with environment variable fallbacks."""
    config = {
        "provider": os.environ.get("JARVIS_LLM_PROVIDER", "groq"),
        "groq_api_key": os.environ.get("GROQ_API_KEY", ""),
        "groq_model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "deepseek_api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "deepseek_model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "ollama_url": os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        "ollama_model": os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b"),
        "xai_api_key": os.environ.get("XAI_API_KEY", os.environ.get("GROK_API_KEY", "")),
        "xai_model": os.environ.get("XAI_MODEL", "grok-beta"),
    }

    if CONFIG_FILE.is_file():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config.update(saved)
        except Exception:
            pass

    return config


def save_config(config: dict) -> None:
    """Saves configuration to ~/.config/jarvis/config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def format_with_groq(text: str, api_key: str, model: str = "llama-3.3-70b-versatile") -> Optional[str]:
    """Call Groq Cloud OpenAI-compatible endpoint with low latency."""
    if not api_key:
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}",
        "User-Agent": "JARVIS-WhisperFlow/1.0",
    }
    payload = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Raw transcript: {text}"},
        ],
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=4.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"].strip()
        return content


def format_with_deepseek(text: str, api_key: str, model: str = "deepseek-chat") -> Optional[str]:
    """Call DeepSeek OpenAI-compatible endpoint."""
    if not api_key:
        return None

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}",
        "User-Agent": "JARVIS-WhisperFlow/1.0",
    }
    payload = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Raw transcript: {text}"},
        ],
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"].strip()
        return content


def format_with_ollama(text: str, url: str = "http://localhost:11434", model: str = "qwen2.5-coder:7b") -> Optional[str]:
    """Call local Ollama chat API."""
    endpoint = f"{url.rstrip('/')}/api/chat"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0.1},
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Raw transcript: {text}"},
        ],
    }

    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=6.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        content = data["message"]["content"].strip()
        return content


def format_with_xai(text: str, api_key: str, model: str = "grok-beta") -> Optional[str]:
    """Call Grok (xAI) OpenAI-compatible endpoint."""
    if not api_key:
        return None

    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}",
        "User-Agent": "JARVIS-WhisperFlow/1.0",
    }
    payload = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 1024,
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Raw transcript: {text}"},
        ],
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=4.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"].strip()
        return content


def polish_transcript(raw_transcript: str) -> str:
    """Polishes raw transcript using configured provider (Groq, Ollama, Grok) with automatic fallback."""
    if not raw_transcript or not raw_transcript.strip():
        return ""

    config = load_config()
    provider = config.get("provider", "groq").lower()
    result = None

    # Try preferred provider
    try:
        if provider == "deepseek" and config.get("deepseek_api_key"):
            result = format_with_deepseek(raw_transcript, config["deepseek_api_key"], config.get("deepseek_model", "deepseek-chat"))
        elif provider == "groq" and config.get("groq_api_key"):
            result = format_with_groq(raw_transcript, config["groq_api_key"], config.get("groq_model", "llama-3.3-70b-versatile"))
        elif provider == "ollama":
            result = format_with_ollama(raw_transcript, config.get("ollama_url", "http://localhost:11434"), config.get("ollama_model", "qwen2.5-coder:7b"))
        elif provider in ("grok", "xai") and config.get("xai_api_key"):
            result = format_with_xai(raw_transcript, config["xai_api_key"], config.get("xai_model", "grok-beta"))
    except Exception:
        result = None

    # If result clean, strip any accidental quotes
    if result:
        trimmed = result.strip()
        if (trimmed.startswith('"') and trimmed.endswith('"')) or (trimmed.startswith("'") and trimmed.endswith("'")):
            trimmed = trimmed[1:-1].strip()
        if trimmed:
            return trimmed

    # Fallback to local deterministic rules
    local_pipeline = WritingPipeline()
    return local_pipeline.format(raw_transcript)
