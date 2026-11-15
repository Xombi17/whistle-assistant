# Contributing to Whistle Assistant

Thank you for your interest in contributing to Whistle Assistant!

## Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for all contributors. Please be respectful and constructive in all interactions.

---

## Development Setup

1. **Fork and Clone the Repository**:
   ```bash
   git clone https://github.com/Xombi17/whistle-assistant.git
   cd whistle-assistant
   ```

2. **Set up Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   pip install pytest
   ```

3. **Install System Dependencies (Ubuntu / Debian)**:
   ```bash
   sudo apt install alsa-utils wl-clipboard wtype libglib2.0-bin xdg-utils
   ```

---

## Running Tests

All unit tests are located in `tests/` and run using `pytest`:

```bash
pytest tests/ -v
```

Before submitting a Pull Request, ensure that all tests pass without errors or warnings.

---

## Expanding Phonetic & Hinglish Dictionaries

Whistle includes both acoustic prompt biasing and deterministic post-processing rules.

- **ASR Keyword Biasing**: Found in `jarvis/model.py` (`DEFAULT_BIAS_KEYWORDS`). Add common developer terms or homophones here.
- **Deterministic Tech Repairs**: Found in `jarvis/writing.py` (`PHONETIC_TECH_REPLACEMENTS`).
- **Hinglish Normalization**: Found in `jarvis/writing.py` (`HINGLISH_NORMALIZATIONS`). Ensure that words are kept in English Latin script and never transliterated into Devanagari or translated into English.

---

## Submitting Pull Requests

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. Commit your changes with descriptive commit messages:
   ```bash
   git commit -m "feat(asr): add custom vocabulary biasing for Kubernetes terms"
   ```
3. Run the test suite:
   ```bash
   pytest tests/
   ```
4. Push your branch and open a Pull Request against `main`.
