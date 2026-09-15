#!/usr/bin/env python3
"""Run offline SkillSpector containers and gate individual finding severities."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
from urllib.parse import quote, urlsplit


SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
SCAN_TIMEOUT = "180s"
DETAIL_LIMIT = 100
SECURITY_SCORES = {"LOW": "3.0", "MEDIUM": "5.0", "HIGH": "8.0", "CRITICAL": "9.5"}
EXTRA_ROOTS = (
    ".github/agents",
    ".github/prompts",
    "scripts/git-push-approval",
    "scripts/tool-guardian",
)


def contains_regular_files(target: Path) -> bool:
    pending = [target]
    found = False
    while pending:
        path = pending.pop()
        if path.is_symlink():
            raise ValueError(f"Scan content must not contain symlinks: {path}")
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            pending.extend(path.iterdir())
        elif stat.S_ISREG(mode):
            found = True
        else:
            raise ValueError(f"Scan content must contain only regular files and directories: {path}")
    return found


def discover_targets(root: Path) -> list[Path]:
    apm = root / ".apm"
    if not apm.is_dir() or apm.is_symlink():
        raise ValueError("The repository must contain a non-symlink .apm directory.")

    candidates = []
    for path in sorted(apm.iterdir()):
        if path.is_symlink():
            raise ValueError(f"Scan targets must not be symlinks: {path}")
        if path.name == "skills" and path.is_dir():
            candidates.extend(sorted(path.iterdir()))
        else:
            candidates.append(path)
    candidates.extend(root / path for path in EXTRA_ROOTS)

    targets = []
    for path in candidates:
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Scan targets must stay inside the repository without symlinks: {path}")
        if path.exists() and contains_regular_files(path):
            targets.append(path)
    if not targets:
        raise ValueError("No AI primitives were found; refusing an empty scan.")
    return targets


def repository_path(root: Path, target: Path, filename: str, require_file: bool = True) -> str:
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("A finding or diagnostic is missing its file path.")
    filename = filename.replace("\\", "/")
    if filename.startswith("/scan/"):
        filename = filename[len("/scan/"):]
    relative = PurePosixPath(filename)
    if relative.is_absolute() or ".." in relative.parts or ":" in filename or any(
        ord(character) < 32 for character in filename
    ):
        raise ValueError("A reported path is outside the selected scan target.")
    base = target if target.is_dir() else target.parent
    candidate = base.joinpath(*relative.parts)
    resolved = candidate.resolve()
    boundary = target.resolve()
    if (target.is_dir() and not resolved.is_relative_to(boundary)) or (
        target.is_file() and resolved != boundary
    ):
        raise ValueError("A reported path is outside the selected scan target.")
    if candidate.is_symlink() or not resolved.is_relative_to(root.resolve()):
        raise ValueError("A reported path must remain inside the repository without symlinks.")
    if require_file and not candidate.is_file():
        raise ValueError(f"A finding refers to an unavailable source file: {filename}")
    return resolved.relative_to(root.resolve()).as_posix()


def text_field(record: dict, key: str, default: str = "") -> str:
    value = record.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"Expected text in '{key}'.")
    return "".join(character for character in value if ord(character) >= 32 or character in "\n\t")


def source_line(value: object, optional: bool = False) -> int | None:
    if optional and value is None:
        return None
    if type(value) is not int or value < 1:
        raise ValueError("A reported source line must be a positive integer.")
    return value


def normalize_finding(issue: dict, root: Path, target: Path) -> dict:
    if not isinstance(issue, dict) or issue.get("severity") not in SEVERITIES:
        raise ValueError("A finding has a missing or unknown severity.")
    rule = text_field(issue, "id")
    if not rule.strip():
        raise ValueError("A finding has no rule ID.")
    location = issue.get("location")
    if not isinstance(location, dict):
        raise ValueError("A finding has no source location.")
    line = source_line(location.get("start_line"))
    end_line = source_line(location.get("end_line"), optional=True)
    if end_line is not None and end_line < line:
        raise ValueError("A finding has an invalid source range.")
    return {
        "rule": rule,
        "severity": issue["severity"],
        "path": repository_path(root, target, location.get("file")),
        "line": line,
        "end_line": end_line,
        "title": text_field(issue, "pattern", rule),
        "evidence": text_field(issue, "finding"),
        "explanation": text_field(issue, "explanation"),
        "remediation": text_field(issue, "remediation"),
    }


def read_report(path: Path, root: Path, target: Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("Expected a SkillSpector JSON object.")
    findings = []
    diagnostics = []
    errors = []
    issues = report.get("issues")
    if not isinstance(issues, list):
        errors.append("Expected SkillSpector's 'issues' array.")
    else:
        for index, issue in enumerate(issues, start=1):
            try:
                findings.append(normalize_finding(issue, root, target))
            except ValueError as error:
                errors.append(f"Finding {index} could not be published: {error}")
    counts = {severity: sum(item["severity"] == severity for item in findings) for severity in SEVERITIES}

    # Keep usable evidence even when inspection or report validation fails.
    if report.get("execution_successful") is not True:
        errors.append("SkillSpector did not report successful execution.")
    components = report.get("components")
    if not isinstance(components, list) or not components:
        errors.append("SkillSpector did not report any inspected components.")
    completeness = report.get("analysis_completeness")
    if not isinstance(completeness, dict) or completeness.get("is_complete") is not True:
        errors.append("Static inspection was incomplete; inspect the JSON report.")
    # Upstream completeness excludes out-of-scope files from its denominator.
    if not isinstance(completeness, dict) or completeness.get("scope_exclusions") != []:
        errors.append("Inspection has missing or nonempty scope exclusions; inspect the JSON report.")
    if isinstance(completeness, dict):
        for field in ("ledger_exceptions", "scope_exclusions"):
            entries = completeness.get(field, [])
            if not isinstance(entries, list):
                errors.append(f"Invalid analysis diagnostic list: {field}")
                continue
            for entry in entries:
                try:
                    if not isinstance(entry, dict):
                        raise ValueError("Expected an analysis diagnostic object.")
                    filename = entry.get("path")
                    diagnostics.append({
                        "reason": text_field(entry, "reason_code", field),
                        "message": text_field(entry, "message"),
                        "path": repository_path(root, target, filename, require_file=False) if filename else None,
                        "line": source_line(entry.get("start_line"), optional=True),
                    })
                except ValueError as error:
                    errors.append(f"Invalid analysis diagnostic: {error}")
    metadata = report.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("llm_requested") is not False:
        errors.append("The report does not confirm static-only analysis.")
    if report.get("suppressed_count") != 0 or report.get("suppressed") != []:
        errors.append("Suppressed findings are not permitted by this gate.")
    version = metadata.get("skillspector_version") if isinstance(metadata, dict) else None
    return {
        "counts": counts,
        "findings": findings,
        "diagnostics": diagnostics,
        "errors": errors,
        "version": version if isinstance(version, str) else None,
    }


def scan_command(target: Path, output: Path, image: str) -> list[str]:
    if any(character in str(path) for path in (target, output) for character in ",\r\n"):
        raise ValueError("Docker mount paths must not contain commas or line breaks.")
    destination = "/scan" if target.is_dir() else f"/scan/{target.name}"
    return [
        "docker", "run", "--rm", "--init",
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "128",
        "--memory", "2g",
        "--cpus", "2",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=512m",
        "--env", "HOME=/tmp",
        "--env", "LANGSMITH_TRACING=false",
        "--env", "LANGCHAIN_TRACING_V2=false",
        "--env", "SKILLSPECTOR_OSV_TIMEOUT=1",
        "--mount", f"type=bind,source={target},target={destination},readonly",
        "--mount", f"type=bind,source={output},target=/reports",
        "--workdir", "/tmp",
        "--entrypoint", "timeout",
        image, "--kill-after=10s", SCAN_TIMEOUT,
        "skillspector", "scan", destination,
        "--no-llm", "--fail-on-incomplete",
        "--format", "json", "--output", "/reports/report.json",
    ]


def markdown_cell(value: str) -> str:
    escaped = html.escape(value).replace("\n", " ").replace("\r", " ")
    return escaped.translate({ord(character): f"&#{ord(character)};" for character in "\\`*_{}[]()!|"})


def source_link(path: str, line: int | None = None) -> str:
    label = path + (f":{line}" if line else "")
    label = markdown_cell(label[:256] + ("..." if len(label) > 256 else ""))
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repository = os.environ.get("GITHUB_REPOSITORY")
    revision = os.environ.get("GITHUB_SHA")
    parsed = urlsplit(server)
    if not repository or not revision or parsed.scheme != "https" or not parsed.netloc:
        return label
    url = f"{server}/{quote(repository, safe='/')}/blob/{quote(revision, safe='')}/{quote(path, safe='/')}"
    if line:
        url += f"#L{line}"
    return f"[{label}]({url})" if len(url) <= 2048 else label


def ordered_findings(rows: list[dict]) -> list[dict]:
    findings = [finding for row in rows for finding in row["findings"]]
    return sorted(findings, key=lambda finding: (
        -SEVERITIES.index(finding["severity"]), finding["path"], finding["line"], finding["rule"]
    ))


def render_summary(rows: list[dict], errors: list[dict]) -> str:
    lines = [
        "## SkillSpector static scan",
        "",
        "HIGH or CRITICAL findings block this check. Errors and incomplete scans also fail.",
        "Counts are known reported findings, not confirmed vulnerabilities or a guarantee of coverage.",
        "A dash means no readable report was available; ERROR does not mean zero findings.",
        "No LLM, network access, transitive downloads, or baseline suppressions.",
        "Live OSV lookups are unavailable; SkillSpector uses its offline fallback.",
        "",
        "| Target | Report directory | LOW | MEDIUM | HIGH | CRITICAL | Gate |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows[:DETAIL_LIMIT]:
        values = " | ".join(
            str(row["counts"][severity]) if row["counts"] is not None else "-" for severity in SEVERITIES
        )
        lines.append(
            f"| {markdown_cell(row['target'])} | {row['report_directory']} | "
            f"{values} | {row['status']} |"
        )
    if len(rows) > DETAIL_LIMIT:
        lines.append(f"\nShowing {DETAIL_LIMIT} of {len(rows)} targets; see summary.json for all targets.")
    findings = ordered_findings(rows)
    lines.extend(["", f"### Findings ({len(findings)} reported entries)", "",
                  "| Severity | Rule | File / line | Finding and evidence | Explanation |",
                  "| --- | --- | --- | --- | --- |"])
    for finding in findings[:DETAIL_LIMIT]:
        detail = finding["title"]
        if finding["evidence"]:
            detail += f" - Match: {finding['evidence']}"
        lines.append(
            f"| {finding['severity']} | {markdown_cell(finding['rule'][:128])} | "
            f"{source_link(finding['path'], finding['line'])} | {markdown_cell(detail[:500])} | "
            f"{markdown_cell(finding['explanation'][:400])} |"
        )
    if len(findings) > DETAIL_LIMIT:
        lines.append(f"\nShowing the first {DETAIL_LIMIT} findings, highest severity first.")
    if not findings:
        lines.append("\nNo publishable findings were reported. Check scan errors before interpreting this as clean.")
    diagnostics = [
        {**diagnostic, "target": row["target"]} for row in rows for diagnostic in row["diagnostics"]
    ]
    if diagnostics:
        lines.extend(["", "### Analysis limitations and exclusions", "",
                      "| Target | File / line | Reason | Explanation |",
                      "| --- | --- | --- | --- |"])
        for diagnostic in diagnostics[:DETAIL_LIMIT]:
            location = source_link(diagnostic["path"], diagnostic["line"]) if diagnostic["path"] else "-"
            lines.append(
                f"| {markdown_cell(diagnostic['target'])} | {location} | "
                f"{markdown_cell(diagnostic['reason'][:128])} | {markdown_cell(diagnostic['message'][:500])} |"
            )
        if len(diagnostics) > DETAIL_LIMIT:
            lines.append(f"\nShowing {DETAIL_LIMIT} of {len(diagnostics)} analysis limitations.")
    if errors:
        lines.extend(["", "### Scan errors", ""])
        lines.extend(
            f"- {markdown_cell(item['target'])}: {markdown_cell(item['error'][:1000])}"
            for item in errors[:DETAIL_LIMIT]
        )
        if len(errors) > DETAIL_LIMIT:
            lines.append(f"\nShowing {DETAIL_LIMIT} of {len(errors)} scan errors.")
    lines.extend(["", "Download the skillspector-reports artifact for full findings, diagnostics, and scanner logs."])
    return "\n".join(lines) + "\n"


def gate_exit_code(rows: list[dict], errors: list[dict]) -> int:
    return 2 if errors else int(any(row["status"] == "BLOCK" for row in rows))


def build_sarif(rows: list[dict], errors: list[dict]) -> dict:
    rules = {}
    results = []
    for finding in ordered_findings(rows):
        # Upstream rules can emit different severities; preserve their GitHub severity bands.
        rule_id = f"{finding['rule']}/{finding['severity'].lower()}"
        level = {"LOW": "note", "MEDIUM": "warning", "HIGH": "error", "CRITICAL": "error"}[finding["severity"]]
        rules[rule_id] = {
            "id": rule_id,
            "shortDescription": {"text": f"{finding['rule']}: {finding['severity']} static finding"},
            "helpUri": "https://github.com/NVIDIA/SkillSpector#vulnerability-patterns",
            "defaultConfiguration": {"level": level},
            "properties": {"tags": ["security"], "security-severity": SECURITY_SCORES[finding["severity"]]},
        }
        message = "\n\n".join(text for text in (
            finding["title"], finding["explanation"],
            f"Evidence: {finding['evidence']}" if finding["evidence"] else "",
            f"Remediation: {finding['remediation']}" if finding["remediation"] else "",
        ) if text)
        region = {"startLine": finding["line"]}
        if finding["end_line"] is not None:
            region["endLine"] = finding["end_line"]
        results.append({
            "ruleId": rule_id,
            "level": level,
            "message": {"text": message or finding["rule"]},
            "locations": [{"physicalLocation": {
                "artifactLocation": {"uri": quote(finding["path"], safe="/")},
                "region": region,
            }}],
        })
    notifications = [
        {"level": "error", "message": {"text": f"{item['target']}: {item['error']}"}}
        for item in errors
    ]
    for row in rows:
        for diagnostic in row["diagnostics"]:
            notifications.append({"level": "warning", "message": {"text": (
                f"{row['target']}: {diagnostic['reason']}: {diagnostic['message']}"
            )}})
    driver = {
        "name": "SkillSpector",
        "informationUri": "https://github.com/NVIDIA/SkillSpector",
        "rules": [rules[key] for key in sorted(rules)],
    }
    versions = {row["version"] for row in rows if row["version"]}
    if len(versions) == 1:
        driver["version"] = versions.pop()
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": driver},
            "results": results,
            "invocations": [{
                "executionSuccessful": not errors,
                "exitCode": gate_exit_code(rows, errors),
                "toolExecutionNotifications": notifications,
            }],
            "properties": {"analysisComplete": not errors, "scanMode": "static"},
        }],
    }


def run_scans(root: Path, output: Path, image: str, export_sarif: bool = False) -> int:
    targets = discover_targets(root)
    for target in targets:
        if output == target or target in output.parents:
            raise ValueError("Reports must be stored outside all scan targets.")
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    errors = []
    for index, target in enumerate(targets, start=1):
        relative = target.relative_to(root).as_posix()
        scope_output = output / f"{index:03d}"
        scope_output.mkdir()
        counts = None
        findings = []
        diagnostics = []
        version = None
        target_errors = []
        try:
            command = scan_command(target, scope_output, image)
            # Keep scanner-controlled text out of the Actions command channel.
            with (scope_output / "scanner.log").open("w", encoding="utf-8") as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
            if result.returncode not in (0, 1):
                target_errors.append(f"Scanner exited {result.returncode}; inspect scanner.log.")
            # Exit 1 also represents an aggregate risk score, not our severity policy.
            report_path = scope_output / "report.json"
            if report_path.is_file() or result.returncode in (0, 1):
                parsed = read_report(report_path, root, target)
                counts = parsed["counts"]
                findings = parsed["findings"]
                diagnostics = parsed["diagnostics"]
                version = parsed["version"]
                target_errors.extend(parsed["errors"])
        except (OSError, ValueError) as error:
            target_errors.append(str(error))
        if target_errors:
            status = "ERROR"
            errors.append({"target": relative, "error": " ".join(target_errors)})
        else:
            status = "BLOCK" if counts["HIGH"] or counts["CRITICAL"] else "PASS"
        rows.append({
            "target": relative,
            "report_directory": scope_output.name,
            "status": status,
            "counts": counts,
            "findings": findings,
            "diagnostics": diagnostics,
            "version": version,
        })

    (output / "summary.json").write_text(
        json.dumps({"scans": rows, "errors": errors}, indent=2) + "\n", encoding="utf-8"
    )
    summary = render_summary(rows, errors)
    (output / "summary.md").write_text(summary, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
            stream.write(summary)
    if export_sarif:
        (output / "findings.sarif").write_text(
            json.dumps(build_sarif(rows, errors), indent=2) + "\n", encoding="utf-8"
        )
        if os.environ.get("GITHUB_OUTPUT"):
            with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
                stream.write("sarif_created=true\n")
    print(f"Scanned {len(rows)} targets: {sum(row['status'] == 'BLOCK' for row in rows)} blocked, "
          f"{len(errors)} errors. Reports: {output}")
    return gate_exit_code(rows, errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--image", default="skillspector-ci")
    parser.add_argument("--sarif", action="store_true", help="Export repository findings for GitHub Code Scanning.")
    args = parser.parse_args()
    try:
        if os.name != "posix":
            raise ValueError("Run this scanner on Linux with Docker (or in WSL).")
        return run_scans(args.root.resolve(), args.output_dir.resolve(), args.image, export_sarif=args.sarif)
    except (OSError, ValueError) as error:
        print(f"SkillSpector runner failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
