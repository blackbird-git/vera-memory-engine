import unittest
from unittest.mock import patch
from vera.ollama import final_answer_only, generate
import json


class TestFinalAnswerOnly(unittest.TestCase):
    def test_plain_answer(self):
        self.assertEqual(final_answer_only("Sarah remembers the coast."), "Sarah remembers the coast.")

    def test_thinking_block_removed(self):
        self.assertEqual(
            final_answer_only("<think>First I will reason...</think>Sarah recalls 1986."),
            "Sarah recalls 1986.",
        )

    def test_missing_opening_marker(self):
        self.assertEqual(
            final_answer_only("Okay, let me reason first.\n</think>Sarah recalls 1986."),
            "Sarah recalls 1986.",
        )

    def test_unfinished_thinking_rejected(self):
        with self.assertRaises(RuntimeError):
            final_answer_only("<think>Still reasoning")

    def test_unmarked_analysis_rejected(self):
        with self.assertRaises(RuntimeError):
            final_answer_only("Okay, the user asked about the trip. Let me think.")

    def test_empty_final_rejected(self):
        with self.assertRaises(RuntimeError):
            final_answer_only("<think>Only reasoning</think>")


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode()


class TestOllamaClient(unittest.TestCase):
    @patch("vera.ollama.urlopen")
    def test_disables_thinking_and_returns_final_only(self, mock_open):
        def responder(request, timeout):
            req = json.loads(request.data)
            self.assertIs(req["think"], False)
            self.assertTrue(req["raw"])
            self.assertIn("/no_think", req["prompt"])
            return FakeResponse({
                "done_reason": "stop",
                "message": {"content": "<think>Planning</think>Sarah remembers a cottage.", "thinking": "internal reasoning"},
            })
        mock_open.side_effect = responder
        answer = generate(
            question="Tell me about the coast.",
            context="Sarah remembers a cottage.",
            model="qwen3:4b",
            url="http://127.0.0.1:11434",
        )
        self.assertEqual(answer, "Sarah remembers a cottage.")

    @patch("vera.ollama.urlopen")
    def test_retries_on_output_limit(self, mock_open):
        mock_open.side_effect = [
            FakeResponse({"done_reason": "length", "message": {"content": "<think>unfinished"}}),
            FakeResponse({"done_reason": "stop", "message": {"content": "Sarah remembers a cottage."}}),
        ]
        answer = generate(
            question="Tell me about the coast.", context="Sarah remembers a cottage.",
            model="qwen3:4b", url="http://localhost:11434",
        )
        self.assertEqual(answer, "Sarah remembers a cottage.")
        self.assertEqual(mock_open.call_count, 2)


if __name__ == "__main__":
    unittest.main()
