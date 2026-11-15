"""Deterministic speech-to-text writing pipeline modeled after WhisperFlow.
Handles filler removal, self-corrections, spoken punctuation, structure, and typographic cleanup."""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

_PROTECTED_TOKEN = "\ue000{index}\ue001"
_PROTECTED_TOKEN_RE = re.compile(r"\ue000\d+\ue001")
_URL = r"https?://[^\s<>]+"
_EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
_QUOTED = r'"[^"\n]*"|\'[^\'\n]*\''
_WINDOWS_PATH = r"[A-Za-z]:\\[^\s<>]+"
_POSIX_PATH = r"(?<!\w)(?:~|\.{1,2})?/(?:[^\s<>/]+/)*[^\s<>/]+"
_CODE = r"`[^`\n]+`|(?<!\w)(?:--?[A-Za-z0-9][\w-]*|[A-Za-z_][\w]*_[A-Za-z0-9_]+|[A-Za-z_]\w*\(\))(?!\w)"
_PROTECTED_RE = re.compile(
    rf"(?P<quoted>{_QUOTED})|(?P<url>{_URL})|(?P<email>{_EMAIL})|"
    rf"(?P<windows_path>{_WINDOWS_PATH})|(?P<posix_path>{_POSIX_PATH})|(?P<code>{_CODE})"
)

_FILLER_RE = re.compile(r"(?<!\w)(?:um|uh|er|hmm|you\s+know)(?!\w)[,;:]?\s*", re.I)

_SELF_CORRECTION_RE = re.compile(
    r"\b(?P<old>[\w']+)\s*,\s*(?:no|i\s+mean|nahi)\s*,?\s*(?P<new>[\w']+)\b",
    re.I,
)

_AMBIGUOUS_PRECEDERS = frozenset(
    {"a", "an", "each", "every", "my", "our", "the", "this", "that", "your", "for", "in", "during"}
)
_COPULAS = frozenset({"am", "are", "is", "means", "mean", "was", "were"})

_TERMINAL_PUNCTUATION = frozenset(".!?;:")
_CLOSING_PUNCTUATION = frozenset('"\'»”’)]}')

# Phonetic technical auto-corrections for common ASR mishearings
PHONETIC_TECH_REPLACEMENTS = [
    (re.compile(r"\b(?:crawl|crock|clock|grock)\s+(configuration|config|settings|api|key|model|endpoint|token)\b", re.I), r"Groq \1"),
    (re.compile(r"\b(?:crawl|crock)\b(?=\s+(?:is|was|has|have|run|tested|added))", re.I), r"Groq"),
    (re.compile(r"\bdeep\s+sick\b", re.I), r"DeepSeek"),
    (re.compile(r"\bdeep\s+seek\b", re.I), r"DeepSeek"),
    (re.compile(r"\bwhisper\s+flow\b", re.I), r"WhisperFlow"),
    (re.compile(r"\bpipe\s+wire\b", re.I), r"PipeWire"),
    (re.compile(r"\bwire\s+plumber\b", re.I), r"WirePlumber"),
    (re.compile(r"\bway\s+land\b", re.I), r"Wayland"),
    (re.compile(r"\bpie\s+torch\b", re.I), r"PyTorch"),
]

# Standard Hinglish phonetic normalization (Hindi words in English Latin script)
HINGLISH_NORMALIZATIONS = [
    (re.compile(r"\bthik\s+h\b", re.I), r"theek hai"),
    (re.compile(r"\bthik\s+hai\b", re.I), r"theek hai"),
    (re.compile(r"\bkro\b", re.I), r"karo"),
    (re.compile(r"\bkr\s+rha\b", re.I), r"kar raha"),
    (re.compile(r"\bkr\s+rhi\b", re.I), r"kar rahi"),
    (re.compile(r"\bkrna\b", re.I), r"karna"),
    (re.compile(r"\bsmjh\s+gya\b", re.I), r"samajh gaya"),
    (re.compile(r"\bsmjh\b", re.I), r"samajh"),
    (re.compile(r"\bacha\b", re.I), r"accha"),
    (re.compile(r"\bbhiya\b", re.I), r"bhaiya"),
    (re.compile(r"\bkya\s+h\b", re.I), r"kya hai"),
    (re.compile(r"\byrr\b", re.I), r"yaar"),
]


def apply_phonetic_and_hinglish_corrections(text: str) -> str:
    """Applies phonetic tech homophone corrections and standardizes Hinglish spellings."""
    for pattern, repl in PHONETIC_TECH_REPLACEMENTS:
        text = pattern.sub(repl, text)
    for pattern, repl in HINGLISH_NORMALIZATIONS:
        text = pattern.sub(repl, text)
    return text


def protect_tokens(text: str, custom_terms: Tuple[str, ...] = ()) -> Tuple[str, Dict[str, str]]:
    """Protects technical tokens (URLs, paths, code, emails) from alteration."""
    token_map: Dict[str, str] = {}
    counter = 0

    def _replace(match: re.Match) -> str:
        nonlocal counter
        token = _PROTECTED_TOKEN.format(index=counter)
        counter += 1
        token_map[token] = match.group(0)
        return token

    protected = _PROTECTED_RE.sub(_replace, text)
    for term in sorted(custom_terms, key=len, reverse=True):
        if term.strip():
            pat = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.I)
            protected = pat.sub(_replace, protected)

    return protected, token_map


def restore_tokens(text: str, token_map: Dict[str, str]) -> str:
    """Restores masked tokens back to their original strings."""
    for token, original in token_map.items():
        text = text.replace(token, original)
    return text


def remove_fillers(text: str) -> str:
    """Removes verbal fillers like um, uh, er, hmm, you know."""
    cleaned = _FILLER_RE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def apply_self_corrections(text: str) -> str:
    """Fixes mid-sentence spoken verbal corrections ('Monday, no, Tuesday')."""
    return _SELF_CORRECTION_RE.sub(
        lambda m: m.group("new"),
        text,
    )


def replace_spoken_punctuation(text: str) -> str:
    """Translates spoken punctuation cues into marks while respecting ambiguous contexts."""
    spoken_marks = {
        "period": ".",
        "full stop": ".",
        "comma": ",",
        "question mark": "?",
        "exclamation mark": "!",
        "exclamation point": "!",
        "semicolon": ";",
        "semi-colon": ";",
        "colon": ":",
    }

    pattern = re.compile(
        r"\b(?:full\s+stop|period|comma|question\s+mark|exclamation\s+mark|exclamation\s+point|semi[- ]?colon|colon)\b",
        re.I,
    )

    def _sub(match: re.Match) -> str:
        matched_str = re.sub(r"\s+", " ", match.group(0).casefold())
        start = match.start()
        end = match.end()

        # Check preceding and following words for ambiguity (e.g. "during this period")
        before = text[:start].rstrip()
        after = text[end:].lstrip()
        prev_word_match = re.search(r"[A-Za-z']+$", before)
        next_word_match = re.match(r"[A-Za-z']+", after)

        prev_word = prev_word_match.group(0).casefold() if prev_word_match else ""
        next_word = next_word_match.group(0).casefold() if next_word_match else ""

        if prev_word in _AMBIGUOUS_PRECEDERS or next_word in _COPULAS:
            return match.group(0)

        return spoken_marks.get(matched_str, match.group(0))

    return pattern.sub(_sub, text)


def format_spoken_structure(text: str) -> str:
    """Converts structural speech commands like 'new line' or 'new paragraph'."""
    text = re.sub(r"\bnew\s+paragraph\b", "\n\n", text, flags=re.I)
    text = re.sub(r"\bnew\s+line\b", "\n", text, flags=re.I)

    # Bullet lists: "first ... second ... third ..."
    list_match = re.fullmatch(
        r"\s*first\s+(.+?),\s*second\s+(.+?)(?:,\s*third\s+(.+?))?\s*([.!?])?\s*",
        text,
        flags=re.I | re.S,
    )
    if list_match:
        items = [x.strip() for x in list_match.groups()[:3] if x]
        punct = list_match.group(4) or ""
        lines = [f"- {item}" for item in items]
        if lines:
            lines[-1] += punct
        return "\n".join(lines)

    return text


def clean_typography(text: str) -> str:
    """Collapses extra whitespace, formats punctuation spacing, and capitalizes sentences."""
    # Normalize whitespace
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Punctuation spacing (no space before, exactly one space after unless newline)
    text = re.sub(r"\s+([,.;!?:])", r"\1", text)
    text = re.sub(r"([,;:])(?=[^\s\n])", r"\1 ", text)
    text = re.sub(r"([.!?])(?=[A-Za-z])", r"\1 ", text)

    # Sentence Capitalization
    text = re.sub(
        r"(^|[.!?]\s+|\n+)([a-z])",
        lambda m: m.group(1) + m.group(2).upper(),
        text,
    )
    text = re.sub(
        r"(^|\n)([-*]\s+)([a-z])",
        lambda m: m.group(1) + m.group(2) + m.group(3).upper(),
        text,
    )

    return text.strip()


def ensure_terminal_punctuation(text: str) -> str:
    """Ensures complete sentences end with proper punctuation."""
    if not text:
        return text
    candidate = text.rstrip()
    while candidate and candidate[-1] in _CLOSING_PUNCTUATION:
        candidate = candidate[:-1].rstrip()
    if candidate and candidate[-1] in _TERMINAL_PUNCTUATION:
        return text
    # Only add period if not multiline list or code
    if "\n-" in text or text.endswith("```"):
        return text
    return f"{text}."


class WritingPipeline:
    """Complete WhisperFlow-style text normalization pipeline."""

    def __init__(self, snippets: Optional[Dict[str, str]] = None, custom_words: Optional[Set[str]] = None):
        self.snippets = snippets or {}
        self.custom_words = tuple(custom_words or set())

    def format(self, raw_transcript: str) -> str:
        """Run raw transcript through the full normalization pipeline."""
        if not raw_transcript or not raw_transcript.strip():
            return ""

        # 1. Expand custom snippets / macros first
        text = raw_transcript
        for trigger, replacement in sorted(self.snippets.items(), key=lambda x: -len(x[0])):
            pattern = re.compile(rf"(?<!\w){re.escape(trigger)}(?!\w)", re.I)
            text = pattern.sub(replacement, text)

        # 2. Protect technical tokens (URLs, paths, emails, code)
        protected_text, token_map = protect_tokens(text, custom_terms=self.custom_words)

        # 3. Remove verbal fillers
        cleaned = remove_fillers(protected_text)

        # 4. Resolve verbal self-corrections
        corrected = apply_self_corrections(cleaned)

        # 4b. Apply phonetic auto-corrections and Hinglish normalization
        autocorrected = apply_phonetic_and_hinglish_corrections(corrected)

        # 5. Format spoken punctuation
        punctuated = replace_spoken_punctuation(autocorrected)

        # 6. Format structural commands (new line, new paragraph, lists)
        structured = format_spoken_structure(punctuated)

        # 7. Apply typography & capitalization
        polished = clean_typography(structured)

        # 8. Ensure terminal punctuation
        final_protected = ensure_terminal_punctuation(polished)

        # 9. Restore protected tokens
        return restore_tokens(final_protected, token_map)
