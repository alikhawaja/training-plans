import tempfile
import unittest
from pathlib import Path

from check_module import HEADINGS, check


class ModuleChecks(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / "README.md"
        self.valid = "# Module 3: Create and read\n\n" + "\n\n".join(
            f"## {heading}\n\nAn explained learner action."
            for heading in HEADINGS
        )
        self.valid += "\n\n```mermaid\nflowchart LR\n    A --> B\n```\n"

    def errors(self, text):
        self.path.write_text(text, encoding="utf-8")
        return check(self.path)

    def test_complete_module_with_existing_relative_link_passes(self):
        (self.root / "exercise.py").write_text("", encoding="utf-8")
        self.assertEqual(self.errors(self.valid + "\n[Exercise](exercise.py)\n"), [])

    def test_missing_and_empty_required_sections_fail(self):
        with self.subTest("missing"):
            errors = self.errors(self.valid.replace("## Independent exercise", "## Other"))
            self.assertTrue(any("headings" in error for error in errors))
        with self.subTest("empty"):
            errors = self.errors(self.valid.replace(
                "## Independent exercise\n\nAn explained learner action.",
                "## Independent exercise\n",
            ))
            self.assertIn("a required section is empty", errors)

    def test_unfinished_template_bad_link_and_duration_fail(self):
        errors = self.errors(
            self.valid + "\n{{Explain the task\nacross lines}}\n[Exercise](missing.py)\nAllow 30 minutes.\n"
        )
        self.assertTrue(any("placeholder" in error for error in errors))
        self.assertTrue(any("missing local link" in error for error in errors))
        self.assertTrue(any("duration" in error for error in errors))

    def test_unclosed_fence_fails(self):
        errors = self.errors(self.valid + "\n```python\nprint('unfinished')\n")
        self.assertIn("unbalanced triple-backtick fences", errors)


if __name__ == "__main__":
    unittest.main()
