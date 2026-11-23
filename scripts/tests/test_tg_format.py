"""tg.py formatting: labelled buttons and the plain-text fallback. Run: python3 -m unittest discover -s scripts/tests"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tg  # noqa: E402


def buttons(spec):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(spec, handle)
    try:
        return tg.load_buttons(handle.name)["inline_keyboard"]
    finally:
        Path(handle.name).unlink()


class ButtonTests(unittest.TestCase):
    def test_labelled_buttons_one_per_row(self):
        rows = buttons([{"qid": "Q-4", "options": ["A", "B", "C"], "recommended": "A",
                         "labels": {"A": "Friend's sector", "B": "Finance", "C": "Keep broad"}}])
        self.assertEqual([r[0]["text"] for r in rows], ["A · Friend's sector ⭐", "B · Finance", "C · Keep broad"])
        self.assertEqual(rows[1][0]["callback_data"], "q:Q-4:B")

    def test_unlabelled_buttons_keep_old_shape(self):
        rows = buttons([{"qid": "Q-2", "options": ["A", "B"], "recommended": "B"}])
        self.assertEqual([b["text"] for b in rows[0]], ["Q-2 A", "Q-2 B ⭐"])

    def test_labels_are_truncated(self):
        rows = buttons([{"qid": "Q-1", "options": ["A", "B"], "recommended": "A", "labels": {"A": "x" * 40}}])
        self.assertEqual(rows[0][0]["text"], "A · " + "x" * 24 + " ⭐")


class StripHtmlTests(unittest.TestCase):
    def test_strip_html(self):
        self.assertEqual(tg.strip_html("<b>1. Costs &lt; £5 &amp; up</b> <i>ok</i>"), "1. Costs < £5 & up ok")


class LooksLikeHtmlTests(unittest.TestCase):
    def test_detects_template_tags(self):
        self.assertTrue(tg.looks_like_html("<b>Studio update</b>"))
        self.assertFalse(tg.looks_like_html("costs < 5 and > 2"))


if __name__ == "__main__":
    unittest.main()
