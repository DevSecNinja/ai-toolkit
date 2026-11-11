#!/usr/bin/env python3
"""Render SkillSpector gate results: Actions summary, PR comment and SARIF.

Reads summary.json from scripts/scan-skills.py. Never changes the gate result.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote, urlsplit


SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
BLOCKING = ("CRITICAL", "HIGH")
MARKER = "<!-- skillspector-report -->"
SECURITY_SCORES = {"LOW": "3.0", "MEDIUM": "5.0", "HIGH": "8.0", "CRITICAL": "9.5"}
LEVELS = {"LOW": "note", "MEDIUM": "warning", "HIGH": "error", "CRITICAL": "error"}
VERDICTS = {0: "✅ Passed", 1: "❌ Blocked: HIGH/CRITICAL findings", 2: "⚠️ Failed: scan errors"}


ESCAPES = {ord(character): f"&#{ord(character)};" for character in "\\`*_{}[]()!|@#<>&\"'"}


def cell(value: str, limit: int = 300) -> str:
    """Escape untrusted text for one Markdown table cell, in a single pass."""
    value = value if len(value) <= limit else value[:limit] + "..."
    return value.replace("\r", " ").replace("\n", " ").translate(ESCAPES)


def github_url(*parts: str) -> str | None:
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repository = os.environ.get("GITHUB_REPOSITORY")
    parsed = urlsplit(server)
    if not repository or parsed.scheme != "https" or not parsed.netloc:
        return None
    return "/".join((server, quote(repository, safe="/"), *parts))


def source_link(path: str, line: int | None = None) -> str:
    label = cell(path + (f":{line}" if line else ""), 200)
    revision = os.environ.get("SKILLSPECTOR_REVISION") or os.environ.get("GITHUB_SHA")
    url = github_url("blob", quote(revision or "", safe=""), quote(path, safe="/")) if revision else None
    if not url:
        return label
    return f"[{label}]({url}{f'#L{line}' if line else ''})"


def findings(summary: dict) -> list[dict]:
    rows = [finding for scan in summary["scans"] for finding in scan["findings"]]
    # Unaccepted blocking findings first, then by severity and location.
    return sorted(rows, key=lambda item: (
        item["severity"] not in BLOCKING or bool(item["accepted"]),
        SEVERITIES.index(item["severity"]), item["path"], item["line"], item["rule"],
    ))


def count_table(summary: dict) -> list[str]:
    lines = ["| Severity | Reported | Accepted | Blocking |", "| --- | ---: | ---: | ---: |"]
    for severity in SEVERITIES:
        rows = [item for item in findings(summary) if item["severity"] == severity]
        accepted = sum(bool(item["accepted"]) for item in rows)
        blocking = len(rows) - accepted if severity in BLOCKING else "-"
        lines.append(f"| {severity} | {len(rows)} | {accepted if severity in BLOCKING else '-'} | {blocking} |")
    unknown = [scan["target"] for scan in summary["scans"] if scan["counts"] is None]
    if unknown:
        lines.append(f"\nNo readable report for {len(unknown)} target(s); their counts are unknown, not zero.")
    return lines


def finding_table(items: list[dict], limit: int) -> list[str]:
    lines = ["| Severity | Rule | Location | Finding | Status |", "| --- | --- | --- | --- | --- |"]
    for item in items[:limit]:
        detail = item["title"] + (f": {item['evidence']}" if item["evidence"] else "")
        if item["accepted"]:
            status = f"Accepted: {cell(item['accepted'], 160)}"
        else:
            status = "**Blocking**" if item["severity"] in BLOCKING else "Advisory"
        lines.append(f"| {item['severity']} | {cell(item['rule'], 64)} | "
                     f"{source_link(item['path'], item['line'])} | {cell(detail)} | {status} |")
    if len(items) > limit:
        lines.append(f"\nShowing {limit} of {len(items)} findings, blocking first; see Code Scanning for all.")
    return lines


def render(summary: dict, limit: int, pr: int | None = None) -> str:
    code = summary["exit_code"]
    version = summary.get("skillspector_version") or "unknown"
    revision = (os.environ.get("SKILLSPECTOR_REVISION") or os.environ.get("GITHUB_SHA") or "")[:7]
    lines = [
        MARKER,
        f"## SkillSpector report: {VERDICTS.get(code, VERDICTS[2])}",
        "",
        f"SkillSpector {cell(version, 32)} static scan (no LLM, no network) of "
        f"{len(summary['scans'])} AI primitive targets" + (f" at `{revision}`." if revision else "."),
        "HIGH/CRITICAL findings block unless the owner accepted them in "
        "`.github/skillspector-accepted.json`. Findings are heuristic, not confirmed vulnerabilities.",
        "",
        *count_table(summary),
    ]
    items = findings(summary)
    if items:
        lines.extend(["", "### Top findings" if limit <= 10 else "### Findings", "", *finding_table(items, limit)])
    if summary["errors"]:
        lines.extend(["", "### Errors", ""])
        lines.extend(f"- {cell(item['target'], 120)}: {cell(item['error'], 600)}" for item in summary["errors"][:limit])
    limitations = [
        {**item, "complete": scan["complete"], "target": scan["target"]}
        for scan in summary["scans"] for item in scan["diagnostics"]
    ]
    if limitations:
        lines.extend(["", f"<details><summary>Analysis limitations ({len(limitations)})</summary>", "",
                      "| Target | Location | Reason | Status |", "| --- | --- | --- | --- |"])
        for item in limitations[:limit]:
            location = source_link(item["path"], item["line"]) if item["path"] else "-"
            if item["accepted"]:
                status = f"Accepted: {cell(item['accepted'], 160)}"
            else:
                # Caveats on otherwise complete scans are informational; anything else blocks.
                status = "Caveat, non-blocking" if item["complete"] else "**Blocking**"
            lines.append(f"| {cell(item['target'], 120)} | {location} | {cell(item['reason_code'], 64)} | {status} |")
        if len(limitations) > limit:
            lines.append(f"\nShowing {limit} of {len(limitations)} limitations; see the run summary for all.")
        lines.extend(["", "</details>"])
    links = []
    alerts = github_url("security", "code-scanning")
    if alerts:
        query = quote(f"is:open tool:SkillSpector{f' pr:{pr}' if pr else ''}")
        links.append(f"[Code Scanning alerts]({alerts}?query={query})")
    run = os.environ.get("GITHUB_RUN_ID")
    if run and github_url():
        links.append(f"[workflow run and full reports]({github_url('actions', 'runs', quote(run, safe=''))})")
    if links:
        lines.extend(["", "Full results: " + " · ".join(links)])
    return "\n".join(lines) + "\n"


def build_sarif(summary: dict) -> dict:
    rules = {}
    results = []
    for item in findings(summary):
        # Upstream rules can emit different severities; keep GitHub severity bands stable.
        rule_id = f"{item['rule']}/{item['severity'].lower()}"
        rules[rule_id] = {
            "id": rule_id,
            "shortDescription": {"text": f"{item['rule']}: {item['severity']} static finding"},
            "helpUri": "https://github.com/NVIDIA/SkillSpector#vulnerability-patterns",
            "defaultConfiguration": {"level": LEVELS[item["severity"]]},
            "properties": {"tags": ["security"], "security-severity": SECURITY_SCORES[item["severity"]]},
        }
        message = "\n\n".join(text for text in (
            item["title"], item["explanation"],
            f"Evidence: {item['evidence']}" if item["evidence"] else "",
            f"Remediation: {item['remediation']}" if item["remediation"] else "",
        ) if text)
        region = {"startLine": item["line"]}
        if item["end_line"] is not None:
            region["endLine"] = item["end_line"]
        result = {
            "ruleId": rule_id,
            "level": LEVELS[item["severity"]],
            "message": {"text": message or item["rule"]},
            "locations": [{"physicalLocation": {
                "artifactLocation": {"uri": quote(item["path"], safe="/")}, "region": region,
            }}],
        }
        if item["accepted"]:
            result["suppressions"] = [{"kind": "external", "status": "accepted", "justification": item["accepted"]}]
        results.append(result)
    notifications = [
        {"level": "error", "message": {"text": f"{item['target']}: {item['error']}"}}
        for item in summary["errors"]
    ] + [
        {"level": "warning", "message": {"text": f"{scan['target']}: {item['reason_code']}: {item['message']}"}}
        for scan in summary["scans"] for item in scan["diagnostics"] if not item["accepted"]
    ]
    driver = {
        "name": "SkillSpector",
        "informationUri": "https://github.com/NVIDIA/SkillSpector",
        "rules": [rules[key] for key in sorted(rules)],
    }
    if summary.get("skillspector_version"):
        driver["version"] = summary["skillspector_version"]
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": driver},
            "results": results,
            "invocations": [{
                "executionSuccessful": not summary["errors"],
                "exitCode": summary["exit_code"],
                "toolExecutionNotifications": notifications,
            }],
            "properties": {"analysisComplete": not summary["errors"], "scanMode": "static"},
        }],
    }


def gh(*args: str, payload: dict | None = None) -> str:
    result = subprocess.run(
        ["gh", "api", *args], input=json.dumps(payload) if payload else None,
        capture_output=True, text=True, check=False, timeout=60,
    )
    if result.returncode:
        raise RuntimeError(f"gh api {args[0]} failed: {result.stderr.strip()[:500]}")
    return result.stdout


def upsert_comment(pr: int, body: str) -> None:
    """Create the report comment or update the bot's previous one in place."""
    repository = os.environ["GITHUB_REPOSITORY"]
    existing = gh(
        "--paginate", f"repos/{repository}/issues/{pr}/comments", "--jq",
        f'.[] | select(.user.login == "github-actions[bot]" and (.body | startswith("{MARKER}"))) | .id',
    ).split()
    if existing:
        gh("--method", "PATCH", f"repos/{repository}/issues/comments/{existing[0]}", "--input", "-",
           payload={"body": body})
    else:
        gh("--method", "POST", f"repos/{repository}/issues/{pr}/comments", "--input", "-",
           payload={"body": body})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path, help="summary.json written by scan-skills.py")
    parser.add_argument("--markdown", type=Path, help="Append the detailed Markdown summary here.")
    parser.add_argument("--sarif", type=Path, help="Write SARIF 2.1.0 for GitHub Code Scanning here.")
    parser.add_argument("--comment-pr", type=int, help="Create or update the PR summary comment.")
    args = parser.parse_args()
    try:
        if not args.summary.is_file():
            if args.comment_pr:
                # The scan job has already failed; say so on the PR instead of going silent.
                run = github_url("actions", "runs", quote(os.environ.get("GITHUB_RUN_ID", ""), safe=""))
                upsert_comment(args.comment_pr, f"{MARKER}\n## SkillSpector report: {VERDICTS[2]}\n\n"
                               f"The scan produced no readable results; see the [workflow run]({run}).\n")
            raise ValueError(f"No summary at {args.summary}.")
        summary = json.loads(args.summary.read_text(encoding="utf-8"))
        if args.markdown:
            with args.markdown.open("a", encoding="utf-8") as stream:
                stream.write(render(summary, limit=100))
        if args.sarif:
            args.sarif.write_text(json.dumps(build_sarif(summary), indent=2) + "\n", encoding="utf-8")
        if args.comment_pr:
            upsert_comment(args.comment_pr, render(summary, limit=10, pr=args.comment_pr))
    except (OSError, KeyError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"SkillSpector report failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
