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
        "metadata": {"llm_requested": False, "skillspector_version": "2.11.2"},
        "suppressed_count": 0,
        "suppressed": [],
        "issues": [{
            "id": "R1",
            "severity": severity,
            "location": {"file": "SKILL.md", "start_line": 1},
            "pattern": "Synthetic rule",
            "explanation": "Synthetic explanation",
            "finding": "Synthetic evidence",
            "remediation": "Review the finding.",
        } for severity in severities],
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
        patch.dict(os.environ, {
            "GITHUB_STEP_SUMMARY": "", "GITHUB_OUTPUT": "",
            "GITHUB_REPOSITORY": "", "GITHUB_SHA": "",
        }).start()
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

    def run_with(self, payload, code=0, sarif=False):
        with patch.object(scanner.subprocess, "run", side_effect=self.fake_run(payload, code)):
            return scanner.run_scans(self.root, self.output, "test-scanner", export_sarif=sarif)

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

    def test_incomplete_scan_retains_high_findings_and_diagnostics(self):
        payload = report("HIGH")
        payload["analysis_completeness"].update({
            "is_complete": False,
            "ledger_exceptions": [{
                "reason_code": "reference_unresolved",
                "message": "An example output path could not be resolved.",
                "path": "SKILL.md",
                "start_line": 1,
            }],
        })
        self.assertEqual(self.run_with(payload, code=1, sarif=True), 2)
        summary = json.loads((self.output / "summary.json").read_text(encoding="utf-8"))
        row = summary["scans"][0]
        self.assertEqual(row["status"], "ERROR")
        self.assertEqual(row["counts"]["HIGH"], 1)
        self.assertEqual(row["findings"][0]["path"], ".apm/skills/example/SKILL.md")
        markdown = (self.output / "summary.md").read_text(encoding="utf-8")
        self.assertIn("Synthetic explanation", markdown)
        self.assertIn("Synthetic evidence", markdown)
        self.assertIn("reference&#95;unresolved", markdown)
        sarif = json.loads((self.output / "findings.sarif").read_text(encoding="utf-8"))
        self.assertEqual(len(sarif["runs"][0]["results"]), 1)
        self.assertFalse(sarif["runs"][0]["invocations"][0]["executionSuccessful"])
        self.assertEqual(sarif["runs"][0]["invocations"][0]["exitCode"], 2)
        self.assertFalse(sarif["runs"][0]["properties"]["analysisComplete"])
        self.assertTrue(sarif["runs"][0]["invocations"][0]["toolExecutionNotifications"])

    def test_failed_process_can_still_publish_available_findings(self):
        self.assertEqual(self.run_with(report("HIGH"), code=2, sarif=True), 2)
        summary = json.loads((self.output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["scans"][0]["counts"]["HIGH"], 1)
        self.assertEqual(summary["scans"][0]["status"], "ERROR")
        sarif = json.loads((self.output / "findings.sarif").read_text(encoding="utf-8"))
        self.assertEqual(len(sarif["runs"][0]["results"]), 1)

    def test_missing_report_is_unknown_not_zero_and_not_successful_sarif(self):
        self.assertEqual(self.run_with(None, sarif=True), 2)
        summary = json.loads((self.output / "summary.json").read_text(encoding="utf-8"))
        self.assertIsNone(summary["scans"][0]["counts"])
        self.assertIn("| - | - | - | - | ERROR |", (self.output / "summary.md").read_text(encoding="utf-8"))
        sarif = json.loads((self.output / "findings.sarif").read_text(encoding="utf-8"))
        self.assertFalse(sarif["runs"][0]["invocations"][0]["executionSuccessful"])
        self.assertEqual(sarif["runs"][0]["results"], [])

    def test_invalid_finding_does_not_hide_other_valid_findings(self):
        payload = report("HIGH", "MEDIUM")
        payload["issues"][1]["location"]["file"] = "../../outside.md"
        self.assertEqual(self.run_with(payload, sarif=True), 2)
        summary = json.loads((self.output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["scans"][0]["counts"]["HIGH"], 1)
        self.assertIn("could not be published", summary["errors"][0]["error"])
        sarif = json.loads((self.output / "findings.sarif").read_text(encoding="utf-8"))
        self.assertEqual(len(sarif["runs"][0]["results"]), 1)

    def test_untrusted_locations_cannot_escape_the_scan_target(self):
        for index, filename in enumerate((
            "../outside.md", "/etc/passwd", "C:\\outside.md", "file:///etc/passwd",
            "/scan/../outside.md", "/scan-other/SKILL.md", "missing.md", "SKILL.md\nunsafe",
        )):
            with self.subTest(filename=filename):
                self.output = Path(self.temporary.name) / f"location-{index}"
                payload = report("HIGH")
                payload["issues"][0]["location"]["file"] = filename
                self.assertEqual(self.run_with(payload, sarif=True), 2)
                sarif = json.loads((self.output / "findings.sarif").read_text(encoding="utf-8"))
                self.assertEqual(sarif["runs"][0]["results"], [])

    def test_invalid_lines_and_ranges_fail_closed(self):
        for index, line in enumerate((0, -1, True, "1", 1.5, None)):
            with self.subTest(line=line):
                self.output = Path(self.temporary.name) / f"line-{index}"
                payload = report("HIGH")
                payload["issues"][0]["location"]["start_line"] = line
                self.assertEqual(self.run_with(payload), 2)
        self.output = Path(self.temporary.name) / "range"
        payload = report("HIGH")
        payload["issues"][0]["location"].update({"start_line": 2, "end_line": 1})
        self.assertEqual(self.run_with(payload), 2)

    def test_file_targets_and_supporting_files_map_to_repository_paths(self):
        target = self.write(".apm/example.md")
        self.assertEqual(scanner.repository_path(self.root, target, "/scan/example.md"), ".apm/example.md")
        with self.assertRaises(ValueError):
            scanner.repository_path(self.root, target, "different.md")
        self.write(".apm/skills/example/references/context.md")
        self.assertEqual(
            scanner.repository_path(self.root, self.skill, "/scan/references/context.md"),
            ".apm/skills/example/references/context.md",
        )

    def test_sarif_uses_stable_rules_and_repository_relative_encoded_uris(self):
        self.write(".apm/skills/example/references/a #b.md")
        payload = report("MEDIUM", "HIGH", "CRITICAL", "LOW")
        for issue in payload["issues"]:
            issue["location"]["file"] = "references/a #b.md"
            issue["location"]["end_line"] = 1
            issue["finding_id"] = "random-run-specific-id"
        self.assertEqual(self.run_with(payload, sarif=True), 1)
        sarif = json.loads((self.output / "findings.sarif").read_text(encoding="utf-8"))
        self.assertEqual(sarif["version"], "2.1.0")
        run = sarif["runs"][0]
        self.assertEqual(run["tool"]["driver"]["version"], "2.11.2")
        self.assertTrue(run["invocations"][0]["executionSuccessful"])
        self.assertEqual(run["invocations"][0]["exitCode"], 1)
        self.assertEqual(run["results"][0]["ruleId"], "R1/critical")
        self.assertEqual(len(run["tool"]["driver"]["rules"]), 4)
        self.assertEqual(
            run["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            ".apm/skills/example/references/a%20%23b.md",
        )
        scores = {rule["id"]: rule["properties"]["security-severity"] for rule in run["tool"]["driver"]["rules"]}
        self.assertEqual(scores["R1/high"], "8.0")
        self.assertNotIn("random-run-specific-id", json.dumps(sarif))
        self.output = Path(self.temporary.name) / "second-run"
        for issue in payload["issues"]:
            issue["finding_id"] = "different-random-id"
        self.assertEqual(self.run_with(payload, sarif=True), 1)
        self.assertEqual(
            sarif, json.loads((self.output / "findings.sarif").read_text(encoding="utf-8"))
        )

    def test_summary_links_to_the_scanned_revision_and_escapes_finding_text(self):
        payload = report("HIGH")
        payload["issues"][0]["pattern"] = "<script>unsafe</script> | ![tracking](url)"
        with patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "owner/repo", "GITHUB_SHA": "abc123",
            "GITHUB_SERVER_URL": "https://github.com",
        }):
            self.assertEqual(self.run_with(payload), 1)
        markdown = (self.output / "summary.md").read_text(encoding="utf-8")
        self.assertIn("https://github.com/owner/repo/blob/abc123/.apm/skills/example/SKILL.md#L1", markdown)
        self.assertNotIn("<script>", markdown)
        self.assertNotIn("![tracking]", markdown)
        self.assertIn("&lt;script&gt;", markdown)

    def test_detail_limit_does_not_truncate_sarif_or_full_json(self):
        payload = report(*(["HIGH"] * (scanner.DETAIL_LIMIT + 1)))
        self.assertEqual(self.run_with(payload, sarif=True), 1)
        markdown = (self.output / "summary.md").read_text(encoding="utf-8")
        self.assertIn(f"Showing the first {scanner.DETAIL_LIMIT} findings", markdown)
        sarif = json.loads((self.output / "findings.sarif").read_text(encoding="utf-8"))
        self.assertEqual(len(sarif["runs"][0]["results"]), scanner.DETAIL_LIMIT + 1)
        summary = json.loads((self.output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(len(summary["scans"][0]["findings"]), scanner.DETAIL_LIMIT + 1)

    def test_sarif_records_successful_gate_exit_code(self):
        self.assertEqual(self.run_with(report("LOW"), sarif=True), 0)
        sarif = json.loads((self.output / "findings.sarif").read_text(encoding="utf-8"))
        self.assertTrue(sarif["runs"][0]["invocations"][0]["executionSuccessful"])
        self.assertEqual(sarif["runs"][0]["invocations"][0]["exitCode"], 0)

    def test_sarif_is_opt_in_so_smoke_results_are_not_published(self):
        self.assertEqual(self.run_with(report("HIGH")), 1)
        self.assertFalse((self.output / "findings.sarif").exists())

    def test_sarif_output_marker_is_emitted_even_when_gate_fails(self):
        output = Path(self.temporary.name) / "github-output"
        output.write_text("existing=true\n", encoding="utf-8")
        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}):
            self.assertEqual(self.run_with(report("HIGH"), sarif=True), 1)
        self.assertEqual(output.read_text(encoding="utf-8"), "existing=true\nsarif_created=true\n")


if __name__ == "__main__":
    unittest.main()
