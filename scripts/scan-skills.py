#!/usr/bin/env python3
"""Run offline SkillSpector containers and gate individual finding severities.

Writes summary.json for rendering; exits 0 (pass), 1 (blocking finding) or 2 (error).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys


SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
BLOCKING = ("HIGH", "CRITICAL")
SCAN_TIMEOUT = "180s"
ACCEPTED_FILE = ".github/skillspector-accepted.json"
# Directories whose children are scanned one by one, then whole extra roots.
CONTENT_ROOTS = (".apm", ".agents")
EXTRA_ROOTS = (
    ".github/agents",
    ".github/prompts",
    ".github/instructions",
    ".github/hooks",
    "scripts/git-push-approval",
    "scripts/tool-guardian",
)


def printable(text: str) -> str:
    """Escape control characters so repository paths cannot start Actions workflow commands."""
    return "".join(character if character.isprintable() else repr(character)[1:-1] for character in text)


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
    for base in (root / name for name in CONTENT_ROOTS):
        if base.is_symlink():
            raise ValueError(f"Scan targets must not be symlinks: {base}")
        if not base.is_dir():
            continue
        for path in sorted(base.iterdir()):
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
        "accepted": None,
    }


def normalize_diagnostic(entry: object, field: str, root: Path, target: Path) -> dict:
    if not isinstance(entry, dict):
        raise ValueError("Expected an analysis diagnostic object.")
    filename = entry.get("path")
    line = entry.get("start_line")
    parser = entry.get("parser_diagnostic")
    # Parser limits report their span only inside parser_diagnostic.
    if line is None and isinstance(parser, dict):
        line = parser.get("start_line")
    analyzers = entry.get("analyzers", [])
    if not isinstance(analyzers, list) or not all(isinstance(item, str) for item in analyzers):
        raise ValueError("Expected a list of analyzer IDs.")
    return {
        "kind": field,
        "reason_code": text_field(entry, "reason_code", field),
        "message": text_field(entry, "message"),
        "path": repository_path(root, target, filename, require_file=False) if filename else None,
        "line": source_line(line, optional=True),
        "analyzers": analyzers,
        "accepted": None,
    }


def analyzer_gaps(statuses: object) -> tuple[list[str], list[str]]:
    """Return (degraded analyzers that need an accepted limitation, contract errors)."""
    if not isinstance(statuses, list):
        return [], ["SkillSpector did not report analyzer statuses."]
    gaps, errors = [], []
    for status in statuses:
        if not isinstance(status, dict) or not isinstance(status.get("analyzer_id"), str):
            errors.append("Invalid analyzer status entry.")
            continue
        name, state = status["analyzer_id"], status.get("status")
        lost = [key for key in ("failed", "skipped", "unaccounted") if status.get(key, 0) != 0]
        # --no-llm disables only the semantic and meta analyzers.
        llm = name.startswith("semantic_") or name == "meta_analyzer"
        if lost or not (state in ("completed", "not_applicable", "degraded") or (state == "disabled" and llm)):
            errors.append(f"Analyzer {name} did not run to completion ({state}); inspect the JSON report.")
        elif state == "degraded":
            gaps.append(name)
    return gaps, errors


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
    else:
        for component in components:
            try:
                if not isinstance(component, dict):
                    raise ValueError("Expected a component object.")
                repository_path(root, target, component.get("path"), require_file=False)
            except ValueError as error:
                errors.append(f"Invalid inspected component: {error}")
    completeness = report.get("analysis_completeness")
    if not isinstance(completeness, dict):
        completeness = {}
        errors.append("SkillSpector did not report analysis completeness.")
    if not isinstance(completeness.get("is_complete"), bool):
        errors.append("SkillSpector did not report whether inspection was complete.")
    gaps, gap_errors = analyzer_gaps(completeness.get("analyzer_statuses"))
    errors.extend(gap_errors)
    # Upstream completeness excludes out-of-scope files from its denominator.
    if completeness.get("scope_exclusions") != []:
        errors.append("Inspection has missing or nonempty scope exclusions; inspect the JSON report.")
    for field in ("ledger_exceptions", "scope_exclusions"):
        entries = completeness.get(field, [])
        if not isinstance(entries, list):
            errors.append(f"Invalid analysis diagnostic list: {field}")
            continue
        for entry in entries:
            try:
                diagnostics.append(normalize_diagnostic(entry, field, root, target))
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
        "complete": completeness.get("is_complete") is True,
        "analyzer_gaps": gaps,
        "errors": errors,
        "version": version if isinstance(version, str) else None,
    }


def load_accepted(path: Path) -> dict:
    """Load owner-reviewed acceptances; a missing file accepts nothing."""
    if not path.exists():
        return {"findings": [], "limitations": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = {
        "findings": ({"path", "rule", "severity", "reason"}, {"evidence"}),
        "limitations": ({"path", "reason_code", "reason"}, set()),
    }
    if not isinstance(data, dict) or not set(data) <= set(schema):
        raise ValueError(f"{path.name} must be an object with 'findings' and 'limitations' lists.")
    accepted = {}
    for kind, (required, optional) in schema.items():
        entries = data.get(kind, [])
        if not isinstance(entries, list):
            raise ValueError(f"{path.name}: '{kind}' must be a list.")
        for entry in entries:
            if not isinstance(entry, dict) or not required <= set(entry) <= required | optional or not all(
                isinstance(value, str) and value.strip() for value in entry.values()
            ):
                raise ValueError(f"{path.name}: each '{kind}' entry needs non-empty {sorted(required)}.")
            if kind == "findings" and entry["severity"] not in BLOCKING:
                raise ValueError(f"{path.name}: only HIGH or CRITICAL findings need acceptance.")
        accepted[kind] = entries
    return accepted


def finding_matches(entry: dict, finding: dict) -> bool:
    keys = ("path", "rule", "severity")
    return all(entry[key] == finding[key] for key in keys) and (
        "evidence" not in entry or entry["evidence"] == finding["evidence"]
    )


def apply_acceptances(rows: list[dict], accepted: dict) -> list[str]:
    """Mark reviewed findings and limitations; return entries that matched nothing."""
    used = set()
    for row in rows:
        for finding in row["findings"]:
            for index, entry in enumerate(accepted["findings"]):
                if finding["severity"] in BLOCKING and finding_matches(entry, finding):
                    finding["accepted"] = entry["reason"]
                    used.add(("findings", index))
                    break
        if row["complete"] and not row["analyzer_gaps"]:
            continue
        for diagnostic in row["diagnostics"]:
            for index, entry in enumerate(accepted["limitations"]):
                if diagnostic["kind"] == "ledger_exceptions" and (
                    entry["path"], entry["reason_code"]
                ) == (diagnostic["path"], diagnostic["reason_code"]):
                    diagnostic["accepted"] = entry["reason"]
                    used.add(("limitations", index))
                    break
    return [
        f"Stale {kind} entry for {entry['path']} ({entry.get('rule') or entry.get('reason_code')}); "
        "remove it or update it to the current report."
        for kind in ("findings", "limitations")
        for index, entry in enumerate(accepted[kind])
        if (kind, index) not in used
    ]


def row_status(row: dict) -> str:
    if row["counts"] is None or row["errors"]:
        return "ERROR"
    if not row["complete"] or row["analyzer_gaps"]:
        diagnostics = [item for item in row["diagnostics"] if item["kind"] == "ledger_exceptions"]
        covered = {name for item in diagnostics if item["accepted"] for name in item["analyzers"]}
        if not diagnostics or any(item["accepted"] is None for item in diagnostics):
            row["errors"].append("Static inspection was incomplete; accept or resolve each limitation.")
            return "ERROR"
        # An accepted limitation only waives the analyzers it names.
        if not set(row["analyzer_gaps"]) <= covered:
            missing = ", ".join(sorted(set(row["analyzer_gaps"]) - covered))
            row["errors"].append(f"Degraded analyzers have no accepted limitation: {missing}.")
            return "ERROR"
    blocking = [item for item in row["findings"] if item["severity"] in BLOCKING and not item["accepted"]]
    return "BLOCK" if blocking else "PASS"


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


def scan_target(root: Path, target: Path, output: Path, image: str) -> dict:
    row = {
        "target": target.relative_to(root).as_posix(), "report_directory": output.name,
        "counts": None, "findings": [], "diagnostics": [], "complete": False, "analyzer_gaps": [],
        "errors": [], "version": None,
    }
    try:
        command = scan_command(target, output, image)
        # Keep scanner-controlled text out of the Actions command channel.
        with (output / "scanner.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
        if result.returncode not in (0, 1):
            row["errors"].append(f"Scanner exited {result.returncode}; inspect scanner.log.")
        # Exit 1 also covers upstream's aggregate risk score, not this severity policy.
        report_path = output / "report.json"
        if report_path.is_file() or result.returncode in (0, 1):
            parsed = read_report(report_path, root, target)
            row["errors"].extend(parsed.pop("errors"))
            row.update(parsed)
    except (OSError, ValueError) as error:
        row["errors"].append(str(error))
    return row


def gate_exit_code(rows: list[dict], errors: list[dict]) -> int:
    return 2 if errors else int(any(row["status"] == "BLOCK" for row in rows))


def run_scans(root: Path, output: Path, image: str, accepted_path: Path | None = None) -> int:
    targets = discover_targets(root)
    accepted_path = accepted_path or root / ACCEPTED_FILE
    accepted = load_accepted(accepted_path)
    for target in targets:
        if output == target or target in output.parents:
            raise ValueError("Reports must be stored outside all scan targets.")
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for index, target in enumerate(targets, start=1):
        scope_output = output / f"{index:03d}"
        scope_output.mkdir()
        rows.append(scan_target(root, target, scope_output, image))

    stale = apply_acceptances(rows, accepted)
    errors = []
    for row in rows:
        row["status"] = row_status(row)
        if row["errors"]:
            errors.append({"target": row["target"], "error": " ".join(row.pop("errors"))})
        else:
            row.pop("errors")
    accepted_name = accepted_path.relative_to(root).as_posix() if accepted_path.is_relative_to(root) else accepted_path.name
    errors.extend({"target": accepted_name, "error": message} for message in stale)
    exit_code = gate_exit_code(rows, errors)
    versions = {row["version"] for row in rows if row["version"]}
    summary = {
        "skillspector_version": versions.pop() if len(versions) == 1 else None,
        "exit_code": exit_code,
        "scans": rows,
        "errors": errors,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        counts = row["counts"] or {}
        print(f"{row['status']:5} {printable(row['target'])} " + " ".join(
            f"{severity}={counts.get(severity, '-')}" for severity in SEVERITIES
        ))
    print(f"Scanned {len(rows)} targets: {sum(row['status'] == 'BLOCK' for row in rows)} blocked, "
          f"{len(errors)} errors. Reports: {output}")
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--image", default="skillspector-ci")
    parser.add_argument("--accepted", type=Path, help=f"Reviewed acceptances (default: {ACCEPTED_FILE}).")
    args = parser.parse_args()
    try:
        if os.name != "posix":
            raise ValueError("Run this scanner on Linux with Docker (or in WSL).")
        accepted = args.accepted.resolve() if args.accepted else None
        return run_scans(args.root.resolve(), args.output_dir.resolve(), args.image, accepted)
    except (OSError, ValueError) as error:
        print(f"SkillSpector runner failed: {printable(str(error))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
