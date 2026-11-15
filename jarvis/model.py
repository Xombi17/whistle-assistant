import json
import os
import urllib.request
from typing import Optional

DEFAULT_BIAS_KEYWORDS = (
    # Modern AI & Tech terms frequently misheard as English common nouns
    "Groq", "Grok", "DeepSeek", "Ollama", "WhisperFlow", "Whisper", "JARVIS",
    "PipeWire", "WirePlumber", "ALSA", "Wayland", "Linux", "Ubuntu", "Python",
    "API", "JSON", "React", "Tailwind", "Vite", "Tauri", "PyTorch", "LLM",
    # Hindi words written in English letters (Hinglish vocabulary)
    "theek", "hai", "bhai", "bhaiya", "kya", "accha", "karo", "karna", "kaise",
    "samajh", "aaya", "baat", "bolo", "chalo", "shuru", "band", "dekho", "dekh",
    "mein", "hum", "aap", "tum", "mera", "meri", "mere", "yeh", "ye", "woh",
    "sahi", "galat", "nahi", "ruko", "jaldi", "abhi", "koshish", "chal", "raha",
    "hoga", "hogi", "bol", "raha", "hoon"
)


def transcribe_with_groq_whisper(wav_path: str, api_key: str, prompt: str = "") -> Optional[str]:
    """Cloud Whisper-Large-v3-Turbo with prompt biasing for ultra-fast, accurate bilingual Hinglish and tech speech recognition."""
    if not api_key:
        return None
    try:
        with open(wav_path, "rb") as f:
            file_bytes = f.read()

        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        bias_prompt = prompt or (
            "JARVIS, WhisperFlow, Groq, DeepSeek, Ollama, PipeWire, WirePlumber, ALSA, Wayland, "
            "theek hai, bhai, kya, accha, karo, kaise, samjha, dekho, Hinglish words written in English Latin script."
        )

        body = (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"model\"\r\n\r\n"
            f"whisper-large-v3-turbo\r\n"
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"prompt\"\r\n\r\n"
            f"{bias_prompt}\r\n"
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\n"
            f"Content-Type: audio/wav\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Authorization": f"Bearer {api_key.strip()}",
                "User-Agent": "JARVIS-WhisperFlow/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data.get("text", "").strip()
            return text if text else None
    except Exception:
        return None


class LocalModels:
    def __init__(self, tools):
        self.tools = tools
        self.agent = None

    def propose(self, text):
        os.environ['CACTUS_TELEMETRY'] = '0'
        os.environ['HF_HUB_OFFLINE'] = '1'
        import cactus
        if self.agent is None:
            self.agent = cactus.Cactus(tools=self.tools)
        return self.agent.complete(text)

    def reset(self):
        if self.agent is not None:
            self.agent.reset()

    def transcribe(self, wav, keywords=None):
        # 1. Try cloud Whisper-large-v3-turbo with prompt biasing when Groq API key is available
        from jarvis.formatter import load_config
        cfg = load_config()
        if cfg.get("groq_api_key"):
            cloud_result = transcribe_with_groq_whisper(wav, cfg["groq_api_key"])
            if cloud_result:
                return cloud_result

        # 2. Local Cactus.Whistle fallback with keyword biasing
        os.environ['CACTUS_TELEMETRY'] = '0'
        os.environ['HF_HUB_OFFLINE'] = '1'
        import cactus
        kw = keywords if keywords is not None else DEFAULT_BIAS_KEYWORDS
        return cactus.transcribe(wav, keywords=kw)['text']
