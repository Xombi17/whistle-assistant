import unittest
from jarvis.writing import (
    WritingPipeline,
    remove_fillers,
    apply_self_corrections,
    replace_spoken_punctuation,
    format_spoken_structure,
    clean_typography,
    apply_phonetic_and_hinglish_corrections,
)


class TestWritingPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = WritingPipeline()

    def test_filler_removal(self):
        raw = "Um, so I was thinking, uh, we should start now."
        cleaned = remove_fillers(raw)
        self.assertNotIn("Um,", cleaned)
        self.assertNotIn("uh,", cleaned)

    def test_self_corrections(self):
        raw = "Let's schedule this for Monday, no, Tuesday afternoon."
        corrected = apply_self_corrections(raw)
        self.assertEqual(corrected, "Let's schedule this for Tuesday afternoon.")

    def test_spoken_punctuation(self):
        raw = "Hello world comma how are you question mark"
        punctuated = replace_spoken_punctuation(raw)
        self.assertIn(",", punctuated)
        self.assertIn("?", punctuated)

    def test_phonetic_tech_correction(self):
        raw = "I am testing this crawl configuration now."
        corrected = apply_phonetic_and_hinglish_corrections(raw)
        self.assertIn("Groq configuration", corrected)

    def test_deepseek_phonetic_correction(self):
        raw = "Check if deep sick api key is valid."
        corrected = apply_phonetic_and_hinglish_corrections(raw)
        self.assertIn("DeepSeek", corrected)

    def test_hinglish_normalization(self):
        raw = "thik h bhai ye kaam kro comma aur smjh gya"
        corrected = apply_phonetic_and_hinglish_corrections(raw)
        self.assertIn("theek hai", corrected)
        self.assertIn("karo", corrected)
        self.assertIn("samajh gaya", corrected)

    def test_full_pipeline_end_to_end(self):
        raw = "um so I added the crawl configuration comma no comma Groq configuration period"
        result = self.pipeline.format(raw)
        self.assertIn("Groq configuration", result)
        self.assertTrue(result.endswith("."))


if __name__ == "__main__":
    unittest.main()
