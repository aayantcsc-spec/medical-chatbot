"""model_status.py is read-only and must describe the shipped artifacts truthfully."""
import json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from chatbot.health_qa import model_status as ms  # noqa: E402


class ModelStatusTests(unittest.TestCase):
    def test_report_structure_and_label_spaces(self):
        out = ms.collect()
        self.assertIsInstance(out["problems"], list)
        r = out["report"]
        self.assertEqual(r["knowledge_base_intents"], 91)
        self.assertTrue(r["label_spaces_agree"])
        self.assertEqual(r["distilbert"]["config_vocab_size"], r["distilbert"]["tokenizer_vocab_size"])
        self.assertEqual(r["svm"]["classes"], 91)

    def test_legacy_metrics_are_flagged_not_silently_trusted(self):
        notes = " ".join(ms.collect()["notes"])
        self.assertIn("must NOT be cited", notes)

    def test_english_only_base_model_is_disclosed(self):
        self.assertIn("English-only", " ".join(ms.collect()["notes"]))

    def test_it_does_not_modify_any_model_file(self):
        before = {p: os.path.getmtime(p) for p in (os.path.join(ms.MODELS, "svm", "svm_meta.json"), os.path.join(ms.MODELS, "health_qa_metrics.json"))}
        ms.collect()
        after = {p: os.path.getmtime(p) for p in before}
        self.assertEqual(before, after)

    def test_cli_json_output_is_valid(self):
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = ms.main(["--json"])
        json.loads(buf.getvalue())
        self.assertIn(code, (0, 1))


if __name__ == "__main__":
    unittest.main()
