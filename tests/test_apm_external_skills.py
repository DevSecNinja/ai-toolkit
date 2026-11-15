"""Tests for scripts/apm-external-skills.py (see #237).

apm-cli 0.35 deletes committed external skills on a fresh checkout, so APM
Materialize removes them first and checks the result. Standard library only.
"""

import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("apm_external_skills", ROOT / "scripts" / "apm-external-skills.py")
skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(skills)

SKILL = ".agents/skills/audit"
AGENT = ".github/agents/a.agent.md"
LOCK = f"""lockfile_version: '1'
dependencies:
- repo_url: owner/skills
  name: audit
  virtual_path: skills/audit
  package_type: claude_skill
  deployed_files:
  - {SKILL}
  - {SKILL}/SKILL.md
  deployed_file_hashes:
    {SKILL}/SKILL.md: sha256:00
  content_hash: sha256:11
- repo_url: owner/agents
  virtual_path: agents/a.agent.md
  deployed_files:
  - {AGENT}
deployments:
- kind: project-relative
  value: .agents/skills/local-skill
  owners:
  - .
"""
# What apm-cli 0.35.0 wrote in #233: the skill entry kept, its files dropped.
DROPPED = LOCK.replace(f"  deployed_files:\n  - {SKILL}\n  - {SKILL}/SKILL.md\n", "")


class LockParsingTests(unittest.TestCase):
    def test_reads_deployed_files_per_dependency_only_from_dependencies(self):
        self.assertEqual(
            skills.locked_dependencies(LOCK),
            {"owner/skills/skills/audit": [SKILL, f"{SKILL}/SKILL.md"], "owner/agents/agents/a.agent.md": [AGENT]},
        )
        self.assertEqual(skills.locked_dependencies(DROPPED)["owner/skills/skills/audit"], [])

    def test_rejects_unexpected_layouts(self):
        for text in ("lockfile_version: '1'\n", "dependencies:\n- name: x\n"):
            with self.subTest(text=text), self.assertRaises(skills.LockError):
                skills.locked_dependencies(text)


class WorkTreeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for path in (f"{SKILL}/SKILL.md", f"{SKILL}/notes.md", AGENT, ".agents/skills/local-skill/SKILL.md"):
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text("x\n", encoding="utf-8")

    def test_prepare_removes_only_locked_external_skill_folders(self):
        with redirect_stdout(io.StringIO()):
            skills.prepare(self.root, skills.locked_dependencies(LOCK))
        self.assertFalse((self.root / SKILL).exists())
        self.assertTrue((self.root / AGENT).exists())
        self.assertTrue((self.root / ".agents/skills/local-skill/SKILL.md").exists())

    def test_check_passes_a_complete_deploy(self):
        deps = skills.locked_dependencies(LOCK)
        self.assertEqual(skills.check(self.root, deps, [f"{SKILL}/SKILL.md"]), [])

    def test_check_fails_when_install_dropped_or_lost_a_skill(self):
        problems = skills.check(self.root, skills.locked_dependencies(DROPPED), [f"{SKILL}/SKILL.md"])
        self.assertEqual(len(problems), 2)
        self.assertIn("owner/skills/skills/audit deploys no files", problems[0])
        self.assertIn(f"{SKILL}/SKILL.md is committed but no locked dependency deploys it", problems[1])
        (self.root / f"{SKILL}/SKILL.md").unlink()
        problems = skills.check(self.root, skills.locked_dependencies(LOCK), [])
        self.assertEqual(problems, [f"{SKILL}/SKILL.md from owner/skills/skills/audit is missing"])


class RepoTests(unittest.TestCase):
    def test_committed_lock_keeps_every_external_primitive(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(skills.main(["check", "--root", str(ROOT)]), 0, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
