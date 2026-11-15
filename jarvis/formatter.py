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

DEFAULT_SYSTEM_PROMPT = """You are an expert voice-to-text dictation editor modeled after WhisperFlow, specialized in developer terminology and bilingual Hinglish (Hindi written in English alphabet / Latin script).

Transform the raw speech transcript into clean, professional, publication-ready text following these strict rules:

1. PHONETIC & TECHNICAL AUTO-CORRECT:
   - Intelligently fix acoustic speech recognition mishearings and homophones based on developer context.
   - For example:
     * "crawl configuration/api/key/model" -> "Groq configuration/API/key/model" (or "Grok")
     * "deep sick" -> "DeepSeek"
     * "whisper flow" -> "WhisperFlow"
     * "allama" -> "Ollama"
     * "pipe wire" -> "PipeWire"
     * "wire plumber" -> "WirePlumber"
     * "way land" -> "Wayland"
     * "pie torch" -> "PyTorch"
   - Contextually repair misrecognized programming words, libraries, and flags.

2. HINGLISH SUPPORT (HINDI WRITTEN IN ENGLISH/LATIN ALPHABET):
   - First-class support for Hindi words written in English letters (Hinglish), e.g. "theek hai", "bhai", "karo", "kya", "accha", "samjha", "kaise", "karna hai", "chal raha hai", "sahi", "haan", "dekh", "le", "bhi", etc.
   - STRICT: Do NOT translate Hindi words into English (e.g. keep "theek hai bhai", do NOT change to "alright brother").
   - STRICT: Do NOT transliterate into Devanagari script (always keep in Latin/English alphabet).
   - Standardize phonetic Hinglish spellings (e.g. "thik h" -> "theek hai", "kro" -> "karo", "acha" -> "accha", "smjh gya" -> "samajh gaya", "bhiya" -> "bhaiya").
   - Punctuate mixed English-Hinglish naturally (e.g. "Maine Groq configuration add kar diya hai, theek hai, hope this works.").

3. DISFLUENCIES & SELF-CORRECTIONS:
   - Strip verbal fillers (um, uh, er, hmm, like, you know, yaani, matlab).
   - Resolve verbal self-corrections ("Monday, no, Tuesday" -> "Tuesday", "first model, nahi, second model" -> "second model").

4. PUNCTUATION & CAPITALIZATION:
   - Translate spoken punctuation cues ("new line", "period", "full stop", "comma", "question mark") into standard marks.
   - Apply clean capitalization, proper sentence casing, and clean spacing.

5. OUTPUT FORMAT:
   - Output ONLY the final polished text.
   - Never output explanations, greetings, quotes, or markdown code fence wrappers."""


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


def format_with_groq(text: str, api_key: str, model: str = "openai/gpt-oss-120b") -> Optional[str]:
    """Call Groq Cloud OpenAI-compatible endpoint with low latency and model fallback."""
    if not api_key:
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}",
        "User-Agent": "JARVIS-WhisperFlow/1.0",
    }

    candidates = [model]
    for alt in ("openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"):
        if alt not in candidates:
            candidates.append(alt)

    for cand in candidates:
        payload = {
            "model": cand,
            "temperature": 0.1,
            "max_tokens": 1024,
            "messages": [
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
                {"role": "user", "content": f"Raw transcript: {text}"},
            ],
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    return content
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                continue
            raise e
        except Exception:
            continue

    return None


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
