#!/usr/bin/env python3
"""Re-apply local overrides to vendored APM primitives.

`apm install` rewrites every file it deploys, so a hand edit to a vendored
agent (for example a model pin) is lost on the next APM Materialize run. Keep
such edits in apm-overrides.json instead; APM Materialize runs this script
right after `apm install`. Each override sets top-level frontmatter keys of
one deployed file to string values. Standard library only.

Usage: apply-apm-overrides.py [--check] [--root DIR]

  --check  list files that don't match their overrides and exit 1; write nothing.
"""

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys


CONFIG = "apm-overrides.json"
KEY = re.compile(r"[A-Za-z0-9_-]+")


class OverrideError(Exception):
    pass


def load_overrides(root):
    try:
        data = json.loads((root / CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise OverrideError(f"{CONFIG}: {error}") from error
    overrides = data.get("overrides") if isinstance(data, dict) else None
    if not isinstance(overrides, list):
        raise OverrideError(f"{CONFIG}: `overrides` must be a list")
    for number, override in enumerate(overrides, 1):
        where = f"{CONFIG}: override {number}"
        if not isinstance(override, dict):
            raise OverrideError(f"{where} must be an object")
        path, values = override.get("file"), override.get("frontmatter")
        if not isinstance(path, str) or not path:
            raise OverrideError(f"{where} needs a `file`")
        parts = PurePosixPath(path)
        if parts.is_absolute() or ".." in parts.parts or "\\" in path:
            raise OverrideError(f"{where}: `file` must be a relative path inside the repo")
        if not isinstance(values, dict) or not values:
            raise OverrideError(f"{where} needs a non-empty `frontmatter` object")
        for key, value in values.items():
            if not KEY.fullmatch(key) or not isinstance(value, str):
                raise OverrideError(f"{where}: frontmatter `{key}` must be a plain key with a string value")
    return overrides


def set_frontmatter(text, values):
    """Return `text` with top-level frontmatter `values` set; add missing keys."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise OverrideError("no YAML frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == "---"), None)
    if end is None:
        raise OverrideError("unterminated YAML frontmatter")
    newline = "\r\n" if lines[0].endswith("\r\n") else "\n"
    for key, value in values.items():
        line = f"{key}: {json.dumps(value, ensure_ascii=False)}{newline}"
        pattern = re.compile(rf"{re.escape(key)}[ \t]*:")
        matches = [i for i in range(1, end) if pattern.match(lines[i])]
        if len(matches) > 1:
            raise OverrideError(f"frontmatter key `{key}` appears more than once")
        if not matches:
            lines.insert(end, line)
            end += 1
            continue
        start = stop = matches[0]
        # Swallow a multi-line value: indented lines or a column-0 `- ` list,
        # including blank and comment lines between its items.
        for i in range(start + 1, end):
            if lines[i].strip() and re.match(r"[ \t]|-([ \t]|$)", lines[i]):
                stop = i
            elif lines[i].strip() and not lines[i].startswith("#"):
                break
        lines[start:stop + 1] = [line]
        end -= stop - start
    return "".join(lines)


def apply(root, check=False):
    """Apply every override under `root`; return the files that changed."""
    changed = []
    for override in load_overrides(root):
        path = root / override["file"]
        try:
            text = path.read_bytes().decode("utf-8")
        except OSError as error:
            raise OverrideError(
                f"{override['file']}: {error.strerror}; drop or update its entry in {CONFIG}"
            ) from error
        try:
            updated = set_frontmatter(text, override["frontmatter"])
        except OverrideError as error:
            raise OverrideError(f"{override['file']}: {error}") from error
        if updated != text:
            changed.append(override["file"])
            if not check:
                path.write_bytes(updated.encode("utf-8"))
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        changed = apply(args.root, check=args.check)
    except OverrideError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    for path in changed:
        print(f"{'needs override' if args.check else 'applied override'}: {path}")
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
