"""Tests for scripts/apm-external-skills.py (see #237).

apm-cli 0.35 deletes committed external skills on a fresh checkout, so APM
Materialize removes them first and checks the result. Standard library only.
"""

import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch


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
  resolved_commit: c1c8a8c1471069fb
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

    def test_flags_files_dropped_at_an_unchanged_commit_only(self):
        before = skills.parse_lock(LOCK.replace(f"  - {SKILL}/SKILL.md\n", f"  - {SKILL}/SKILL.md\n  - {SKILL}/schema.json\n"))
        after = skills.parse_lock(LOCK)
        self.assertEqual(
            skills.dropped_files(before, after),
            [f"{SKILL}/schema.json from owner/skills/skills/audit was dropped at unchanged commit c1c8a8c1"],
        )
        bumped = skills.parse_lock(LOCK.replace("c1c8a8c1471069fb", "0123456789abcdef"))
        self.assertEqual(skills.dropped_files(before, bumped), [])


class WorkTreeTests(unittest.TestCase):
    def setUp(self):
        # Hook-exported Git variables must not redirect fixture operations to the real repo.
        clean = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        environment = patch.dict(os.environ, clean, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
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

    def test_prepare_refuses_a_symlinked_skills_parent(self):
        outside = self.root / "outside"
        (outside / "audit").mkdir(parents=True)
        skills_root = self.root / ".agents/skills"
        moved = self.root / "moved-skills"
        skills_root.rename(moved)
        try:
            skills_root.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(skills.LockError):
            skills.prepare(self.root, skills.locked_dependencies(LOCK))
        self.assertTrue((outside / "audit").is_dir())

    def test_check_fails_when_a_deployed_skill_is_git_ignored(self):
        (self.root / ".agents/skills/renamed").mkdir()
        (self.root / ".agents/skills/renamed/SKILL.md").write_text("x\n", encoding="utf-8")
        (self.root / "apm.lock.yaml").write_text(LOCK.replace(SKILL, ".agents/skills/renamed"), encoding="utf-8")
        (self.root / ".gitignore").write_text(".agents/skills/*\n!.agents/skills/audit/\n", encoding="utf-8")
        try:
            subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git unavailable")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(skills.main(["check", "--root", str(self.root)]), 1)
        self.assertEqual(stderr.getvalue().count("git-ignored"), 1, stderr.getvalue())
        self.assertIn(".agents/skills/renamed from owner/skills/skills/audit is git-ignored", stderr.getvalue())

    def test_check_against_a_base_revision_flags_a_dropped_companion(self):
        git = ["git", "-C", str(self.root), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
        companion = f"  - {SKILL}/SKILL.md\n  - {SKILL}/schema.json\n"
        (self.root / f"{SKILL}/schema.json").write_text("{}\n", encoding="utf-8")
        (self.root / "apm.lock.yaml").write_text(LOCK.replace(f"  - {SKILL}/SKILL.md\n", companion), encoding="utf-8")
        try:
            subprocess.run(["git", "init", "-q", str(self.root)], check=True)
            subprocess.run([*git, "add", "apm.lock.yaml"], check=True)
            subprocess.run([*git, "commit", "-qm", "base"], check=True)
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git unavailable")
        base = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        (self.root / f"{SKILL}/schema.json").unlink()
        (self.root / "apm.lock.yaml").write_text(LOCK, encoding="utf-8")
        subprocess.run([*git, "commit", "-qam", "drop the companion"], check=True)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(skills.main(["check", "--root", str(self.root)]), 0, stderr.getvalue())
            self.assertEqual(skills.main(["check", "--root", str(self.root), "--base", base]), 1)
            self.assertEqual(skills.main(["check", "--root", str(self.root), "--base", "no-such-rev"]), 2)
        self.assertIn(f"{SKILL}/schema.json from owner/skills/skills/audit was dropped", stderr.getvalue())

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
        self.assertEqual(
            problems,
            [
                f"{SKILL}/SKILL.md from owner/skills/skills/audit is missing",
                f"{SKILL} from owner/skills/skills/audit has no deployed SKILL.md",
            ],
        )

    def test_check_fails_when_only_the_skill_folder_is_left(self):
        (self.root / f"{SKILL}/SKILL.md").unlink()
        (self.root / f"{SKILL}/notes.md").unlink()
        deps = skills.locked_dependencies(LOCK.replace(f"  - {SKILL}/SKILL.md\n", ""))
        self.assertEqual(skills.check(self.root, deps, []), [f"{SKILL} from owner/skills/skills/audit has no deployed SKILL.md"])


class FixtureIsolationTests(unittest.TestCase):
    def test_fixture_commits_ignore_inherited_hook_git_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            outside = Path(temp) / "outside"
            hook_env = {
                "GIT_DIR": str(outside / ".git"),
                "GIT_WORK_TREE": str(outside),
                "GIT_INDEX_FILE": str(outside / "index"),
            }
            with patch.dict(os.environ, hook_env):
                fixture = WorkTreeTests("test_check_against_a_base_revision_flags_a_dropped_companion")
                result = unittest.TestResult()
                fixture.run(result)
                self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
                self.assertEqual(result.skipped, [])
                self.assertEqual(os.environ["GIT_DIR"], hook_env["GIT_DIR"])
            self.assertFalse(outside.exists())


class RepoTests(unittest.TestCase):
    def test_committed_lock_keeps_every_external_primitive(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertEqual(skills.main(["check", "--root", str(ROOT)]), 0, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
