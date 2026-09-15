"""Regression tests for the CI gate; no Docker or scanner installation required."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "scan_skills", Path(__file__).resolve().parents[1] / "scripts" / "scan-skills.py"
)
scanner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scanner)


def report(*severities):
    return {
        "execution_successful": True,
        "components": [{"path": "SKILL.md", "type": "markdown"}],
        "analysis_completeness": {"is_complete": True, "scope_exclusions": []},
        "metadata": {"llm_requested": False},
        "suppressed_count": 0,
        "suppressed": [],
        "issues": [{"severity": severity} for severity in severities],
    }


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        self.output = Path(self.temporary.name) / "reports"
        self.skill = self.write(".apm/skills/example/SKILL.md").parent
        self.addCleanup(patch.stopall)
        patch.object(os, "getuid", return_value=1000, create=True).start()
        patch.object(os, "getgid", return_value=1000, create=True).start()
        patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}).start()
        patch("builtins.print").start()

    def write(self, path):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Example content\n", encoding="utf-8")
        return target

    def fake_run(self, payload, code=0):
        def execute(command, **kwargs):
            mount = next(value for value in command if value.endswith(",target=/reports"))
            output = Path(mount.removeprefix("type=bind,source=").removesuffix(",target=/reports"))
            if payload is not None:
                (output / "report.json").write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.CompletedProcess(command, code)
        return execute

    def run_with(self, payload, code=0):
        with patch.object(scanner.subprocess, "run", side_effect=self.fake_run(payload, code)):
            return scanner.run_scans(self.root, self.output, "test-scanner")

    def test_target_scope_includes_support_files_and_bundled_agents(self):
        self.write(".apm/skills/example/references/context.md")
        self.write(".apm/skills/second/SKILL.md")
        self.write(".apm/prompts/example.prompt.md")
        self.write(".apm/instructions/example.instructions.md")
        self.write(".apm/agents/example.agent.md")
        self.write(".apm/hooks/example.json")
        self.write(".github/agents/bundled.agent.md")
        self.write(".github/prompts/local.prompt.md")
        self.write("scripts/tool-guardian/guard-tool.sh")
        self.write("scripts/git-push-approval/require-push-approval.sh")
        self.write(".skillspector-source/skills/example/SKILL.md")
        self.write("README.md")
        targets = [path.relative_to(self.root).as_posix() for path in scanner.discover_targets(self.root)]
        self.assertEqual(set(targets), {
            ".apm/skills/example", ".apm/skills/second", ".apm/prompts",
            ".apm/instructions", ".apm/agents", ".apm/hooks",
            ".github/agents", ".github/prompts",
            "scripts/tool-guardian", "scripts/git-push-approval",
        })

    def test_empty_or_missing_apm_is_an_error(self):
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaises(ValueError):
            scanner.discover_targets(empty)
        (empty / ".apm").mkdir()
        with self.assertRaises(ValueError):
            scanner.discover_targets(empty)

    def test_container_has_no_network_or_credentials_and_bounded_resources(self):
        command = scanner.scan_command(self.skill, self.output, "test-scanner")
        self.assertEqual(command[command.index("--network") + 1], "none")
        self.assertEqual(command[command.index("--user") + 1], "1000:1000")
        for value in ("--read-only", "--no-llm", "--fail-on-incomplete", "--pids-limit",
                      "--memory", "--cpus", "--kill-after=10s", "180s"):
            self.assertIn(value, command)
        self.assertIn(f"type=bind,source={self.skill},target=/scan,readonly", command)
        self.assertNotIn("--transitive", command)
        self.assertNotIn("--baseline", command)
        self.assertNotIn("--use-shipped-baseline", command)
        self.assertNotIn("--env-file", command)
        self.assertIn("--output", command)

    def test_single_files_keep_their_extension(self):
        target = self.write(".apm/example.md")
        command = scanner.scan_command(target, self.output, "test-scanner")
        self.assertIn(f"type=bind,source={target},target=/scan/example.md,readonly", command)

    def test_mount_path_cannot_inject_docker_options(self):
        target = self.write(".apm/skills/example,source=outside/SKILL.md").parent
        with self.assertRaises(ValueError):
            scanner.scan_command(target, self.output, "test-scanner")

    def test_target_symlinks_are_rejected_before_traversal(self):
        original = Path.is_symlink
        skills = self.root / ".apm" / "skills"
        with patch.object(Path, "is_symlink", lambda path: path == skills or original(path)):
            with self.assertRaises(ValueError):
                scanner.discover_targets(self.root)

    def test_symlinked_primary_file_with_benign_readme_never_reaches_scanner(self):
        self.write(".apm/skills/example/README.md")
        primary = self.skill / "SKILL.md"
        original = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda path: path == primary or original(path)), \
                patch.object(scanner.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "symlinks"):
                scanner.run_scans(self.root, self.output, "test-scanner")
            run.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "Real symlink creation requires a POSIX test host.")
    def test_real_descendant_symlinks_are_rejected_without_following(self):
        self.write(".apm/skills/example/README.md")
        primary = self.skill / "SKILL.md"
        primary.unlink()
        outside = self.write("outside-scan.md")
        for target in (outside, self.root / "missing.md", self.skill):
            with self.subTest(target=target):
                primary.symlink_to(target, target_is_directory=target.is_dir())
                try:
                    with self.assertRaisesRegex(ValueError, "symlinks"):
                        scanner.discover_targets(self.root)
                finally:
                    primary.unlink()

    def test_regular_file_does_not_short_circuit_descendant_validation(self):
        self.write(".apm/skills/example/references/context.md")
        nested = self.skill / "references"
        original = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda path: path == nested or original(path)):
            with self.assertRaisesRegex(ValueError, "symlinks"):
                scanner.discover_targets(self.root)

    def test_walk_errors_fail_instead_of_silently_skipping_content(self):
        original = Path.iterdir
        def iterdir(path):
            if path == self.skill:
                raise PermissionError("Unreadable skill")
            return original(path)
        with patch.object(Path, "iterdir", iterdir):
            with self.assertRaises(PermissionError):
                scanner.discover_targets(self.root)

    def test_complete_report_with_excluded_primary_file_is_an_error(self):
        payload = report()
        payload["components"] = [{"path": "README.md", "type": "markdown"}]
        payload["analysis_completeness"]["scope_exclusions"] = [{
            "path": "SKILL.md",
            "phase": "discovery",
            "reason_code": "not_regular_file",
            "fatal": False,
        }]
        self.assertEqual(self.run_with(payload), 2)

    def test_high_and_critical_block_even_with_zero_cli_exit(self):
        for severity in ("HIGH", "CRITICAL"):
            with self.subTest(severity=severity):
                self.output = Path(self.temporary.name) / severity
                self.assertEqual(self.run_with(report(severity)), 1)

    def test_low_and_medium_pass_even_with_aggregate_risk_exit_one(self):
        self.assertEqual(self.run_with(report("LOW", "MEDIUM"), code=1), 0)

    def test_empty_findings_pass(self):
        self.assertEqual(self.run_with(report()), 0)

    def test_scanner_failure_is_not_a_clean_scan(self):
        self.assertEqual(self.run_with(report(), code=2), 2)

    def test_timeout_is_an_error(self):
        self.assertEqual(self.run_with(None, code=124), 2)

    def test_missing_report_is_an_error(self):
        self.assertEqual(self.run_with(None), 2)

    def test_report_contract_fails_closed(self):
        invalid = [
            [],
            {},
            {**report(), "components": []},
            {**report(), "components": None},
            {**report(), "issues": None},
            {**report(), "issues": [{}]},
            {**report(), "issues": [{"severity": "UNKNOWN"}]},
            {**report(), "issues": ["HIGH"]},
            {**report(), "execution_successful": False},
            {**report(), "analysis_completeness": {"is_complete": False}},
            {**report(), "analysis_completeness": None},
            {**report(), "analysis_completeness": {"is_complete": True}},
            {**report(), "analysis_completeness": {"is_complete": True, "scope_exclusions": None}},
            {**report(), "analysis_completeness": {"is_complete": True, "scope_exclusions": {}}},
            {**report(), "analysis_completeness": {
                "is_complete": True,
                "scope_exclusions": [{"path": "references/", "reason_code": "excluded_directory"}],
            }},
            {**report(), "metadata": {"llm_requested": True}},
            {**report(), "metadata": {}},
            {**report(), "suppressed_count": 1},
            {**report(), "suppressed": [{"severity": "HIGH"}]},
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(payload=payload):
                self.output = Path(self.temporary.name) / f"invalid-{index}"
                self.assertEqual(self.run_with(payload), 2)

    def test_malformed_json_is_an_error(self):
        with patch.object(scanner.subprocess, "run", side_effect=self.fake_run(report())), \
                patch.object(scanner.json, "loads", side_effect=json.JSONDecodeError("bad", "", 0)):
            self.assertEqual(scanner.run_scans(self.root, self.output, "test-scanner"), 2)

    def test_docker_unavailable_is_an_error(self):
        with patch.object(scanner.subprocess, "run", side_effect=FileNotFoundError("docker")):
            self.assertEqual(scanner.run_scans(self.root, self.output, "test-scanner"), 2)

    def test_all_targets_are_scanned_after_findings_or_errors(self):
        self.write(".apm/skills/second/SKILL.md")
        results = iter([(None, 2), (report("CRITICAL"), 1)])
        def execute(command, **kwargs):
            payload, code = next(results)
            return self.fake_run(payload, code)(command, **kwargs)
        with patch.object(scanner.subprocess, "run", side_effect=execute) as run:
            self.assertEqual(scanner.run_scans(self.root, self.output, "test-scanner"), 2)
            self.assertEqual(run.call_count, 2)
        summary = json.loads((self.output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual([row["status"] for row in summary["scans"]], ["ERROR", "BLOCK"])
        self.assertTrue((self.output / "summary.md").exists())

    def test_existing_reports_cannot_be_reused(self):
        self.output.mkdir()
        with self.assertRaises(FileExistsError):
            scanner.run_scans(self.root, self.output, "test-scanner")

    def test_output_cannot_be_inside_scanned_content(self):
        with self.assertRaises(ValueError):
            scanner.run_scans(self.root, self.skill / "reports", "test-scanner")

    def test_summary_escapes_untrusted_markdown(self):
        self.assertEqual(scanner.markdown_cell("<img src=x>|target\nname"),
                         "&lt;img src=x&gt;&#124;target name")
        self.assertEqual(scanner.markdown_cell("![tracking](url)"),
                         "&#33;&#91;tracking&#93;&#40;url&#41;")

    def test_actions_summary_is_written(self):
        summary = Path(self.temporary.name) / "actions-summary.md"
        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}):
            self.assertEqual(self.run_with(report("HIGH")), 1)
        self.assertIn("| HIGH | CRITICAL |", summary.read_text(encoding="utf-8"))
        self.assertIn("BLOCK", summary.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
