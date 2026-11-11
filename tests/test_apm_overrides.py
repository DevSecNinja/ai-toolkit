"""Tests for scripts/apply-apm-overrides.py (see #210).

`apm install` rewrites vendored agents, so local pins live in
apm-overrides.json and APM Materialize re-applies them. Standard library only.
"""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("apply_apm_overrides", ROOT / "scripts" / "apply-apm-overrides.py")
overrides = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(overrides)

AGENT = (
    "---\n"
    'description: "Scans code"\n'
    'model: "Claude Sonnet 4.6"\n'
    'tools: ["search"]\n'
    "---\n"
    "\n"
    "model: body text is not frontmatter\n"
)


class SetFrontmatterTests(unittest.TestCase):
    def test_replaces_existing_key_and_leaves_the_rest(self):
        result = overrides.set_frontmatter(AGENT, {"model": "Claude Sonnet 5"})
        self.assertEqual(result, AGENT.replace('"Claude Sonnet 4.6"', '"Claude Sonnet 5"'))

    def test_adds_missing_key_and_is_idempotent(self):
        once = overrides.set_frontmatter("---\nname: x\n---\nbody\n", {"model": "Claude Sonnet 5"})
        self.assertEqual(once, '---\nname: x\nmodel: "Claude Sonnet 5"\n---\nbody\n')
        self.assertEqual(overrides.set_frontmatter(once, {"model": "Claude Sonnet 5"}), once)

    def test_replaces_multi_line_values(self):
        text = "---\nmodel:\n  - a\n  - b\ntools:\n- x\nname: n\n---\n"
        result = overrides.set_frontmatter(text, {"model": "m", "tools": "t"})
        self.assertEqual(result, '---\nmodel: "m"\ntools: "t"\nname: n\n---\n')

    def test_multi_line_values_may_contain_blank_and_comment_lines(self):
        text = "---\nmodel:\n- a\n\n# note\n- b\n\n# keep\nname: n\n---\n"
        result = overrides.set_frontmatter(text, {"model": "m"})
        self.assertEqual(result, '---\nmodel: "m"\n\n# keep\nname: n\n---\n')

    def test_keeps_crlf_line_endings(self):
        result = overrides.set_frontmatter(AGENT.replace("\n", "\r\n"), {"model": "M", "extra": "E"})
        expected = AGENT.replace('"Claude Sonnet 4.6"', '"M"').replace('---\n\n', 'extra: "E"\n---\n\n')
        self.assertEqual(result, expected.replace("\n", "\r\n"))

    def test_rejects_missing_or_ambiguous_frontmatter(self):
        for text in ("no frontmatter\n", "---\nmodel: a\n", "---\nmodel: a\nmodel: b\n---\n"):
            with self.subTest(text=text), self.assertRaises(overrides.OverrideError):
                overrides.set_frontmatter(text, {"model": "x"})


class ApplyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "agent.md").write_text(AGENT, encoding="utf-8")

    def write_config(self, entries):
        (self.root / overrides.CONFIG).write_text(json.dumps({"overrides": entries}), encoding="utf-8")

    def test_check_reports_drift_without_writing_then_apply_fixes_it(self):
        self.write_config([{"file": "agent.md", "frontmatter": {"model": "Claude Sonnet 5"}}])
        self.assertEqual(overrides.main(["--check", "--root", str(self.root)]), 1)
        self.assertEqual((self.root / "agent.md").read_text(encoding="utf-8"), AGENT)
        self.assertEqual(overrides.main(["--root", str(self.root)]), 0)
        self.assertEqual(overrides.main(["--check", "--root", str(self.root)]), 0)
        self.assertIn('model: "Claude Sonnet 5"', (self.root / "agent.md").read_text(encoding="utf-8"))

    def test_fails_loudly_on_stale_or_invalid_entries(self):
        for entries in (
            [{"file": "gone.md", "frontmatter": {"model": "x"}}],
            [{"file": "../agent.md", "frontmatter": {"model": "x"}}],
            [{"file": "agent.md", "frontmatter": {"model": 5}}],
            [{"file": "agent.md", "frontmatter": {}}],
            [{"frontmatter": {"model": "x"}}],
        ):
            with self.subTest(entries=entries):
                self.write_config(entries)
                with self.assertRaises(overrides.OverrideError):
                    overrides.apply(self.root)
                self.assertEqual(overrides.main(["--root", str(self.root)]), 2)


class RepoTests(unittest.TestCase):
    def test_committed_primitives_match_their_overrides(self):
        self.assertEqual(
            overrides.apply(ROOT, check=True),
            [],
            "a vendored file lost its local override; run "
            "`python3 scripts/apply-apm-overrides.py` (see apm-overrides.json)",
        )


if __name__ == "__main__":
    unittest.main()
