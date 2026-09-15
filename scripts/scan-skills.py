#!/usr/bin/env python3
"""Run offline SkillSpector containers and gate individual finding severities."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
SCAN_TIMEOUT = "180s"
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


def read_report(path: Path) -> dict[str, int]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("Expected a SkillSpector JSON object.")
    if report.get("execution_successful") is not True:
        raise ValueError("SkillSpector did not report successful execution.")
    components = report.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("SkillSpector did not report any inspected components.")
    completeness = report.get("analysis_completeness")
    if not isinstance(completeness, dict) or completeness.get("is_complete") is not True:
        raise ValueError("Static inspection was incomplete; inspect the JSON report.")
    # Upstream completeness excludes out-of-scope files from its denominator.
    if completeness.get("scope_exclusions") != []:
        raise ValueError("Inspection has missing or nonempty scope exclusions; inspect the JSON report.")
    metadata = report.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("llm_requested") is not False:
        raise ValueError("The report does not confirm static-only analysis.")
    if report.get("suppressed_count") != 0 or report.get("suppressed") != []:
        raise ValueError("Suppressed findings are not permitted by this gate.")
    issues = report.get("issues")
    if not isinstance(issues, list):
        raise ValueError("Expected SkillSpector's 'issues' array.")
    counts = dict.fromkeys(SEVERITIES, 0)
    for issue in issues:
        if not isinstance(issue, dict) or issue.get("severity") not in SEVERITIES:
            raise ValueError("A finding has a missing or unknown severity.")
        counts[issue["severity"]] += 1
    return counts


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


def run_scans(root: Path, output: Path, image: str) -> int:
    targets = discover_targets(root)
    for target in targets:
        if output == target or target in output.parents:
            raise ValueError("Reports must be stored outside all scan targets.")
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    errors = []
    blocked = False
    for index, target in enumerate(targets, start=1):
        relative = target.relative_to(root).as_posix()
        scope_output = output / f"{index:03d}"
        scope_output.mkdir()
        counts = dict.fromkeys(SEVERITIES, 0)
        try:
            command = scan_command(target, scope_output, image)
            # Keep scanner-controlled text out of the Actions command channel.
            with (scope_output / "scanner.log").open("w", encoding="utf-8") as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
            if result.returncode not in (0, 1):
                raise ValueError(f"Scanner exited {result.returncode}; inspect scanner.log.")
            # Exit 1 also represents an aggregate risk score, not our severity policy.
            counts = read_report(scope_output / "report.json")
            status = "BLOCK" if counts["HIGH"] or counts["CRITICAL"] else "PASS"
            blocked = blocked or status == "BLOCK"
        except (OSError, ValueError) as error:
            status = "ERROR"
            errors.append({"target": relative, "error": str(error)})
        rows.append({
            "target": relative,
            "report_directory": scope_output.name,
            "status": status,
            "counts": counts,
        })

    (output / "summary.json").write_text(
        json.dumps({"scans": rows, "errors": errors}, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "## SkillSpector static scan",
        "",
        "HIGH or CRITICAL findings block this check. Errors and incomplete scans also fail.",
        "No LLM, network access, transitive downloads, or baseline suppressions.",
        "Live OSV lookups are unavailable; SkillSpector uses its offline fallback.",
        "",
        "| Target | Report directory | LOW | MEDIUM | HIGH | CRITICAL | Gate |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        values = " | ".join(str(row["counts"][severity]) for severity in SEVERITIES)
        lines.append(
            f"| {markdown_cell(row['target'])} | {row['report_directory']} | "
            f"{values} | {row['status']} |"
        )
    if errors:
        lines.extend(["", "### Scan errors", ""])
        lines.extend(
            f"- {markdown_cell(item['target'])}: {markdown_cell(item['error'])}" for item in errors
        )
    lines.extend(["", "Download the skillspector-reports artifact for JSON findings and scanner logs."])
    summary = "\n".join(lines) + "\n"
    (output / "summary.md").write_text(summary, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
            stream.write(summary)
    print(f"Scanned {len(rows)} targets: {sum(row['status'] == 'BLOCK' for row in rows)} blocked, "
          f"{len(errors)} errors. Reports: {output}")
    return 2 if errors else int(blocked)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--image", default="skillspector-ci")
    args = parser.parse_args()
    try:
        if os.name != "posix":
            raise ValueError("Run this scanner on Linux with Docker (or in WSL).")
        return run_scans(args.root.resolve(), args.output_dir.resolve(), args.image)
    except (OSError, ValueError) as error:
        print(f"SkillSpector runner failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
