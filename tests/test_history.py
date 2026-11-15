import unittest
import tempfile
import sqlite3
from pathlib import Path
from jarvis.history import init_db, save_history_item, list_history, delete_history_item, clear_all_history


class TestHistoryStore(unittest.TestCase):
    def setUp(self):
        # Create temp sqlite database for tests
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_history.sqlite3"
        init_db(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_save_and_list_history(self):
        item_id = save_history_item(
            raw_text="um test speech",
            formatted_text="Test speech.",
            mode="transcribe",
            provider="groq",
            duration_sec=2.1,
            db_path=self.db_path
        )
        self.assertIsInstance(item_id, int)

        items = list_history(limit=10, db_path=self.db_path)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["raw_text"], "um test speech")
        self.assertEqual(items[0]["formatted_text"], "Test speech.")

    def test_search_history(self):
        save_history_item(raw_text="apple banana", formatted_text="Apple banana.", db_path=self.db_path)
        save_history_item(raw_text="orange grape", formatted_text="Orange grape.", db_path=self.db_path)

        results = list_history(query="banana", db_path=self.db_path)
        self.assertEqual(len(results), 1)
        self.assertIn("Apple banana", results[0]["formatted_text"])

    def test_delete_history(self):
        item_id = save_history_item(raw_text="delete me", formatted_text="Delete me.", db_path=self.db_path)
        delete_history_item(item_id, db_path=self.db_path)
        items = list_history(db_path=self.db_path)
        self.assertEqual(len(items), 0)

    def test_clear_all_history(self):
        save_history_item(raw_text="1", formatted_text="1", db_path=self.db_path)
        save_history_item(raw_text="2", formatted_text="2", db_path=self.db_path)
        clear_all_history(db_path=self.db_path)
        items = list_history(db_path=self.db_path)
        self.assertEqual(len(items), 0)


if __name__ == "__main__":
    unittest.main()
