import unittest
from jarvis.core import Assistant, Model

class TestAssistant(unittest.TestCase):
    def setUp(self):
        self.model = Model()
        self.assistant = Assistant(model=self.model)

    def test_propose(self):
        text = "Open Notepad"
        calls = self.assistant.propose(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['name'], 'open_app')
        self.assertEqual(calls[0]['arguments']['name'], 'Notepad')

    def test_execute(self):
        text = "Open Notepad"
        calls = self.assistant.propose(text)
        self.assistant.execute(calls[0])
        # Add assertions to verify the action was executed

if __name__ == "__main__":
    unittest.main()
