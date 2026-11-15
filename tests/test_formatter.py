import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path
from jarvis.formatter import load_config, save_config, polish_transcript


class TestFormatter(unittest.TestCase):
    def test_config_loading_and_saving(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_config = Path(tmpdir) / "config.json"
            with patch("jarvis.formatter.CONFIG_FILE", tmp_config), \
                 patch("jarvis.formatter.CONFIG_DIR", Path(tmpdir)):
                
                cfg = load_config()
                self.assertIn("provider", cfg)
                self.assertIn("groq_api_key", cfg)

                # Save new configuration
                cfg["provider"] = "groq"
                cfg["groq_model"] = "openai/gpt-oss-120b"
                save_config(cfg)

                # Reload
                reloaded = load_config()
                self.assertEqual(reloaded["provider"], "groq")
                self.assertEqual(reloaded["groq_model"], "openai/gpt-oss-120b")

    def test_polish_transcript_deterministic_fallback(self):
        # When no API keys are provided or network fails, falls back gracefully to local WritingPipeline
        with patch.dict("os.environ", {}, clear=True), \
             patch("jarvis.formatter.load_config", return_value={"provider": "groq", "groq_api_key": ""}):
            raw = "um check this crawl configuration"
            polished = polish_transcript(raw)
            # Should have removed 'um' and corrected 'crawl configuration' -> 'Groq configuration'
            self.assertIn("Groq configuration", polished)
            self.assertNotIn("um", polished.lower().split())
