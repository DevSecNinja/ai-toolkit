"""Tests for SkillSpector report rendering, SARIF export and PR comment upserts."""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "skillspector_report", Path(__file__).resolve().parents[1] / "scripts" / "skillspector-report.py"
)
report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(report)

ENV = {
    "GITHUB_SERVER_URL": "https://github.com", "GITHUB_REPOSITORY": "owner/repo",
    "SKILLSPECTOR_REVISION": "abc1234def", "GITHUB_SHA": "merge", "GITHUB_RUN_ID": "42",
}


def finding(severity, rule="R1", accepted=None, path=".apm/skills/x/SKILL.md", line=3, title="Rule title"):
    return {
        "rule": rule, "severity": severity, "path": path, "line": line, "end_line": None,
        "title": title, "evidence": "matched text", "explanation": "Why.", "remediation": "Fix.",
        "accepted": accepted,
    }


def summary(*findings, exit_code=0, errors=(), diagnostics=(), counts=True):
    return {
        "skillspector_version": "2.13.4",
        "exit_code": exit_code,
        "scans": [{
            "target": ".apm/skills/x", "status": "PASS", "complete": True, "version": "2.13.4",
            "counts": {} if counts else None, "findings": list(findings), "diagnostics": list(diagnostics),
        }],
        "errors": list(errors),
    }


class RenderTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_comment_counts_orders_blocking_first_and_links_sources(self):
        data = summary(
            finding("MEDIUM", "M1"), finding("HIGH", "H1", accepted="Reviewed deny-list."),
            finding("CRITICAL", "C1", line=9), finding("LOW", "L1"), exit_code=1,
        )
        body = report.render(data, limit=10, pr=7)
        self.assertTrue(body.startswith(report.MARKER))
        self.assertIn("❌ Blocked", body)
        self.assertIn("| CRITICAL | 1 | 0 | 1 |", body)
        self.assertIn("| HIGH | 1 | 1 | 0 |", body)
        self.assertIn("| MEDIUM | 1 | - | - |", body)
        rows = [line for line in body.splitlines() if line.startswith("| CRITICAL |") or line.startswith("| HIGH |")]
        self.assertIn("**Blocking**", rows[2])
        self.assertIn("Accepted: Reviewed deny-list.", rows[3])
        self.assertTrue([line for line in body.splitlines() if line.startswith("| ")][-1].startswith("| LOW | L1"))
        self.assertIn("https://github.com/owner/repo/blob/abc1234def/.apm/skills/x/SKILL.md#L9", body)
        self.assertIn("security/code-scanning?query=is%3Aopen%20tool%3ASkillSpector%20pr%3A7", body)
        self.assertIn("https://github.com/owner/repo/actions/runs/42", body)

    def test_untrusted_text_cannot_inject_markup_mentions_or_links(self):
        data = summary(finding("HIGH", title="<script>x</script> | ![t](u) @owner #99 it's\nnext"), exit_code=1)
        body = report.render(data, limit=10)
        for unsafe in ("<script>", "![t]", "@owner", "#99", "\nnext", "&&"):
            self.assertNotIn(unsafe, body)
        self.assertIn("&#60;script&#62;", body)
        self.assertIn("it&#39;s", body)

    def test_limits_errors_unknown_counts_and_limitations(self):
        diagnostic = {"kind": "ledger_exceptions", "reason_code": "static_parse_limit", "message": "m",
                      "path": ".apm/skills/x/SKILL.md", "line": 2, "accepted": "Reviewed."}
        data = summary(*(finding("MEDIUM", line=index + 1) for index in range(12)), exit_code=2,
                       errors=[{"target": ".apm/skills/x", "error": "Scanner exited 124."}],
                       diagnostics=[diagnostic, {**diagnostic, "accepted": None}], counts=False)
        body = report.render(data, limit=10)
        self.assertIn("⚠️ Failed", body)
        self.assertIn("Showing 10 of 12 findings", body)
        self.assertIn("Scanner exited 124.", body)
        self.assertIn("counts are unknown, not zero", body)
        self.assertIn("Analysis limitations (2)", body)
        self.assertIn("Accepted: Reviewed.", body)
        self.assertIn("Caveat, non-blocking", body)
        data["scans"][0]["complete"] = False
        self.assertIn("| static&#95;parse&#95;limit | **Blocking** |", report.render(data, limit=10))

    def test_clean_report_passes(self):
        body = report.render(summary(), limit=100)
        self.assertIn("✅ Passed", body)
        self.assertNotIn("### Findings", body)


class SarifTests(unittest.TestCase):
    def test_sarif_has_stable_rules_encoded_uris_and_suppressions(self):
        data = summary(finding("HIGH", accepted="Reviewed."), finding("MEDIUM", path=".apm/a #b.md"),
                       exit_code=0)
        sarif = report.build_sarif(data)
        self.assertEqual(sarif, report.build_sarif(json.loads(json.dumps(data))))
        run = sarif["runs"][0]
        self.assertEqual(run["tool"]["driver"]["version"], "2.13.4")
        self.assertEqual([rule["id"] for rule in run["tool"]["driver"]["rules"]], ["R1/high", "R1/medium"])
        high, medium = run["results"]
        self.assertEqual(high["suppressions"][0]["justification"], "Reviewed.")
        self.assertNotIn("suppressions", medium)
        self.assertEqual(medium["locations"][0]["physicalLocation"]["artifactLocation"]["uri"], ".apm/a%20%23b.md")
        self.assertTrue(run["invocations"][0]["executionSuccessful"])

    def test_errors_mark_sarif_execution_unsuccessful(self):
        data = summary(finding("HIGH"), exit_code=2, errors=[{"target": "t", "error": "boom"}])
        invocation = report.build_sarif(data)["runs"][0]["invocations"][0]
        self.assertFalse(invocation["executionSuccessful"])
        self.assertEqual(invocation["exitCode"], 2)
        self.assertIn("t: boom", invocation["toolExecutionNotifications"][0]["message"]["text"])


class CommentTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_existing_bot_comment_is_updated_in_place(self):
        with patch.object(report, "gh", side_effect=["101\n", ""]) as gh:
            report.upsert_comment(7, "body")
        self.assertIn("repos/owner/repo/issues/7/comments", gh.call_args_list[0].args)
        self.assertEqual(gh.call_args_list[1].args[:3], ("--method", "PATCH", "repos/owner/repo/issues/comments/101"))
        self.assertEqual(gh.call_args_list[1].kwargs["payload"], {"body": "body"})

    def test_first_run_creates_a_comment(self):
        with patch.object(report, "gh", side_effect=["", ""]) as gh:
            report.upsert_comment(7, "body")
        self.assertEqual(gh.call_args_list[1].args[:3], ("--method", "POST", "repos/owner/repo/issues/7/comments"))

    def test_missing_summary_still_comments_and_fails(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(report, "upsert_comment") as upsert, patch("sys.stderr"), \
                patch("sys.argv", ["report", str(Path(temporary) / "summary.json"), "--comment-pr", "7"]):
            self.assertEqual(report.main(), 2)
        self.assertIn("no readable results", upsert.call_args.args[1])

    def test_cli_writes_markdown_and_sarif(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "summary.json").write_text(json.dumps(summary(finding("HIGH"), exit_code=1)))
            argv = ["report", str(directory / "summary.json"), "--markdown", str(directory / "step.md"),
                    "--sarif", str(directory / "out.sarif")]
            with patch("sys.argv", argv):
                self.assertEqual(report.main(), 0)
            self.assertIn("### Findings", (directory / "step.md").read_text(encoding="utf-8"))
            self.assertEqual(json.loads((directory / "out.sarif").read_text())["version"], "2.1.0")


if __name__ == "__main__":
    unittest.main()
