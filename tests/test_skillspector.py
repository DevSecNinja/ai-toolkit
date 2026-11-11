"""Regression tests for the SkillSpector gate; no Docker or scanner installation required."""

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


def report(*severities, complete=True, ledger=(), degraded=()):
    statuses = [{"analyzer_id": "static_patterns", "status": "completed"},
                {"analyzer_id": "semantic_security_discovery", "status": "disabled"}]
    statuses += [{"analyzer_id": name, "status": "degraded", "partial": 1} for name in degraded]
    return {
        "execution_successful": True,
        "components": [{"path": "SKILL.md", "type": "markdown"}],
        "analysis_completeness": {
            "is_complete": complete, "scope_exclusions": [], "ledger_exceptions": list(ledger),
            "analyzer_statuses": statuses,
        },
        "metadata": {"llm_requested": False, "skillspector_version": "2.13.4"},
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


PARSE_LIMIT = {
    "reason_code": "static_parse_limit", "message": "Bounded parser limit.", "path": "SKILL.md",
    "start_line": None, "parser_diagnostic": {"start_line": 1}, "analyzers": ["tool_misuse"],
}
SKILL = ".apm/skills/example/SKILL.md"


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        self.output = Path(self.temporary.name) / "reports"
        self.skill = self.write(SKILL).parent
        self.addCleanup(patch.stopall)
        patch.object(os, "getuid", return_value=1000, create=True).start()
        patch.object(os, "getgid", return_value=1000, create=True).start()
        patch("builtins.print").start()

    def write(self, path, content="Example content\n"):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def accept(self, findings=(), limitations=()):
        self.write(scanner.ACCEPTED_FILE, json.dumps(
            {"findings": list(findings), "limitations": list(limitations)}
        ))

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

    def summary(self):
        return json.loads((self.output / "summary.json").read_text(encoding="utf-8"))

    def test_target_scope_includes_skills_primitives_agents_and_hooks(self):
        for path in (
            ".apm/skills/example/references/context.md", ".apm/skills/second/SKILL.md",
            ".apm/prompts/example.prompt.md", ".apm/hooks/example.json",
            ".agents/skills/local/SKILL.md", ".agents/notes.md",
            ".github/agents/bundled.agent.md", ".github/instructions/x.instructions.md",
            ".github/hooks/hook.json", "scripts/tool-guardian/guard-tool.sh",
            ".skillspector-source/skills/example/SKILL.md", "README.md",
        ):
            self.write(path)
        targets = [path.relative_to(self.root).as_posix() for path in scanner.discover_targets(self.root)]
        self.assertEqual(set(targets), {
            ".apm/skills/example", ".apm/skills/second", ".apm/prompts", ".apm/hooks",
            ".agents/skills/local", ".agents/notes.md", ".github/agents",
            ".github/instructions", ".github/hooks", "scripts/tool-guardian",
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
        for value in ("--transitive", "--baseline", "--use-shipped-baseline", "--env-file"):
            self.assertNotIn(value, command)

    def test_single_files_keep_their_extension(self):
        target = self.write(".apm/example.md")
        command = scanner.scan_command(target, self.output, "test-scanner")
        self.assertIn(f"type=bind,source={target},target=/scan/example.md,readonly", command)

    def test_mount_path_cannot_inject_docker_options(self):
        target = self.write(".apm/skills/example,source=outside/SKILL.md").parent
        with self.assertRaises(ValueError):
            scanner.scan_command(target, self.output, "test-scanner")

    def test_symlinks_are_rejected_before_any_scan(self):
        self.write(".apm/skills/example/references/context.md")
        original = Path.is_symlink
        for link in (self.root / ".apm" / "skills", self.skill / "SKILL.md", self.skill / "references"):
            with self.subTest(link=link), \
                    patch.object(Path, "is_symlink", lambda path, link=link: path == link or original(path)), \
                    patch.object(scanner.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "symlinks"):
                    scanner.run_scans(self.root, self.output, "test-scanner")
                run.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "Real symlink creation requires a POSIX test host.")
    def test_real_descendant_symlinks_are_rejected_without_following(self):
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

    def test_walk_errors_fail_instead_of_silently_skipping_content(self):
        original = Path.iterdir
        def iterdir(path):
            if path == self.skill:
                raise PermissionError("Unreadable skill")
            return original(path)
        with patch.object(Path, "iterdir", iterdir):
            with self.assertRaises(PermissionError):
                scanner.discover_targets(self.root)

    def test_high_and_critical_block_even_with_zero_cli_exit(self):
        for severity in ("HIGH", "CRITICAL"):
            with self.subTest(severity=severity):
                self.output = Path(self.temporary.name) / severity
                self.assertEqual(self.run_with(report(severity)), 1)
                self.assertEqual(self.summary()["exit_code"], 1)

    def test_low_and_medium_pass_even_with_aggregate_risk_exit_one(self):
        self.assertEqual(self.run_with(report("LOW", "MEDIUM"), code=1), 0)

    def test_scanner_failures_are_errors(self):
        for name, payload, code in (("crash", report(), 2), ("timeout", None, 124), ("missing", None, 0)):
            with self.subTest(name):
                self.output = Path(self.temporary.name) / name
                self.assertEqual(self.run_with(payload, code), 2)
                if payload is None:
                    self.assertIsNone(self.summary()["scans"][0]["counts"])

    def test_docker_unavailable_is_an_error(self):
        with patch.object(scanner.subprocess, "run", side_effect=FileNotFoundError("docker")):
            self.assertEqual(scanner.run_scans(self.root, self.output, "test-scanner"), 2)

    def test_report_contract_fails_closed(self):
        def completeness(**changes):
            return {**report(), "analysis_completeness": {**report()["analysis_completeness"], **changes}}
        invalid = [
            [], {},
            {**report(), "components": []},
            {**report(), "components": [None]},
            {**report(), "components": [{"path": "../outside.md"}]},
            {**report(), "issues": None},
            {**report(), "issues": [{"severity": "UNKNOWN"}]},
            {**report(), "execution_successful": False},
            {**report(), "analysis_completeness": None},
            {**report(), "analysis_completeness": {"is_complete": True}},
            completeness(is_complete=None),
            completeness(is_complete="true"),
            completeness(scope_exclusions=[{"path": "references/", "reason_code": "excluded"}]),
            completeness(analyzer_statuses=None),
            completeness(analyzer_statuses=[{"analyzer_id": "static_patterns", "status": "failed"}]),
            completeness(analyzer_statuses=[{"analyzer_id": "static_patterns", "status": "disabled"}]),
            completeness(analyzer_statuses=[{"analyzer_id": "x", "status": "completed", "unaccounted": 1}]),
            {**report(), "metadata": {"llm_requested": True}},
            {**report(), "suppressed_count": 1},
        ]
        for index, payload in enumerate(invalid):
            with self.subTest(payload=payload):
                self.output = Path(self.temporary.name) / f"invalid-{index}"
                self.assertEqual(self.run_with(payload), 2)

    def test_all_targets_are_scanned_after_findings_or_errors(self):
        self.write(".apm/skills/second/SKILL.md")
        results = iter([(None, 2), (report("CRITICAL"), 1)])
        def execute(command, **kwargs):
            payload, code = next(results)
            return self.fake_run(payload, code)(command, **kwargs)
        with patch.object(scanner.subprocess, "run", side_effect=execute) as run:
            self.assertEqual(scanner.run_scans(self.root, self.output, "test-scanner"), 2)
            self.assertEqual(run.call_count, 2)
        self.assertEqual([row["status"] for row in self.summary()["scans"]], ["ERROR", "BLOCK"])

    def test_existing_or_nested_report_directories_are_rejected(self):
        with self.assertRaises(ValueError):
            scanner.run_scans(self.root, self.skill / "reports", "test-scanner")
        self.output.mkdir()
        with self.assertRaises(FileExistsError):
            scanner.run_scans(self.root, self.output, "test-scanner")

    def test_incomplete_scan_retains_findings_and_diagnostic_lines(self):
        self.assertEqual(self.run_with(report("HIGH", complete=False, ledger=[PARSE_LIMIT]), code=1), 2)
        row = self.summary()["scans"][0]
        self.assertEqual((row["status"], row["counts"]["HIGH"]), ("ERROR", 1))
        self.assertEqual(row["findings"][0]["path"], SKILL)
        self.assertEqual((row["diagnostics"][0]["path"], row["diagnostics"][0]["line"]), (SKILL, 1))
        self.assertIn("incomplete", self.summary()["errors"][0]["error"])

    def test_untrusted_locations_and_lines_fail_closed_without_hiding_others(self):
        cases = [("file", name) for name in (
            "../outside.md", "/etc/passwd", "C:\\outside.md", "/scan/../x.md", "missing.md", "SKILL.md\nx",
        )] + [("start_line", line) for line in (0, -1, True, "1", None)]
        for index, (key, value) in enumerate(cases):
            with self.subTest(key=key, value=value):
                self.output = Path(self.temporary.name) / f"location-{index}"
                payload = report("HIGH", "MEDIUM")
                payload["issues"][1]["location"][key] = value
                self.assertEqual(self.run_with(payload), 2)
                self.assertEqual(len(self.summary()["scans"][0]["findings"]), 1)

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

    def test_reviewed_acceptance_passes_only_the_matching_finding(self):
        entry = {"path": SKILL, "rule": "R1", "severity": "HIGH", "evidence": "Synthetic evidence",
                 "reason": "Reviewed false positive."}
        self.accept([entry])
        self.assertEqual(self.run_with(report("HIGH")), 0)
        finding = self.summary()["scans"][0]["findings"][0]
        self.assertEqual(finding["accepted"], "Reviewed false positive.")
        for name, payload in (("critical", report("CRITICAL")), ("changed", report("HIGH"))):
            with self.subTest(name):
                self.output = Path(self.temporary.name) / name
                payload["issues"][0]["finding"] = "Different evidence" if name == "changed" else "Synthetic evidence"
                # The stale entry also fails, so a new finding cannot hide behind an old approval.
                self.assertEqual(self.run_with(payload), 2)
                self.assertEqual(self.summary()["scans"][0]["status"], "BLOCK")
                self.assertIn("Stale findings entry", self.summary()["errors"][0]["error"])

    def test_rule_level_acceptance_without_evidence_covers_the_file(self):
        self.accept([{"path": SKILL, "rule": "R1", "severity": "HIGH", "reason": "Deny-list."}])
        self.assertEqual(self.run_with(report("HIGH", "HIGH")), 0)

    def test_accepted_limitations_allow_incomplete_scans(self):
        self.accept(limitations=[{"path": SKILL, "reason_code": "static_parse_limit", "reason": "Reviewed."}])
        incomplete = {"complete": False, "degraded": ["tool_misuse"]}
        self.assertEqual(self.run_with(report(ledger=[PARSE_LIMIT], **incomplete), code=1), 0)
        other = {**PARSE_LIMIT, "reason_code": "reference_missing"}
        for name, payload in (
            ("other", report(ledger=[PARSE_LIMIT, other], **incomplete)),
            ("no-ledger", report(complete=False)),
            # The accepted limitation names tool_misuse, so it cannot waive an unrelated analyzer.
            ("unrelated", report(ledger=[PARSE_LIMIT], complete=False, degraded=["tool_misuse", "taint"])),
        ):
            with self.subTest(name):
                self.output = Path(self.temporary.name) / name
                self.assertEqual(self.run_with(payload, code=1), 2)

    def test_printed_paths_cannot_start_workflow_commands(self):
        self.assertEqual(scanner.printable("x\n::warning::y\r\x1b"), "x\\n::warning::y\\r\\x1b")

    def test_stale_acceptance_is_an_error(self):
        self.accept([{"path": SKILL, "rule": "R9", "severity": "HIGH", "reason": "Old."}])
        self.assertEqual(self.run_with(report()), 2)
        self.assertEqual(self.summary()["errors"][0]["target"], scanner.ACCEPTED_FILE)

    def test_invalid_acceptance_files_are_rejected(self):
        base = {"path": SKILL, "rule": "R1", "severity": "HIGH", "reason": "Reviewed."}
        for index, content in enumerate((
            "[]", '{"other": []}', '{"findings": {}}',
            json.dumps({"findings": [{**base, "reason": " "}]}),
            json.dumps({"findings": [{**base, "severity": "MEDIUM"}]}),
            json.dumps({"findings": [{**base, "line": "1"}]}),
            json.dumps({"limitations": [{"path": SKILL, "reason": "No code."}]}),
        )):
            with self.subTest(content=content):
                self.write(scanner.ACCEPTED_FILE, content)
                with self.assertRaises(ValueError):
                    scanner.run_scans(self.root, Path(self.temporary.name) / f"bad-{index}", "test-scanner")


if __name__ == "__main__":
    unittest.main()
