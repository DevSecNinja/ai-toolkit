#!/usr/bin/env python3
"""Keep committed external APM skills through APM Materialize (see #237).

apm-cli 0.35 trusts a skill file's overwrite baseline only from per-user
deployment receipts, never from apm.lock.yaml. A fresh CI checkout has none,
so `apm install` skips every committed external skill file and its cleanup
then deletes them all as stale (microsoft/apm#3372).

  prepare  remove the external skill folders recorded in apm.lock.yaml, so
           `apm install` redeploys them from the pinned commit. Git still
           holds the committed copy, so the materialize diff shows upstream
           changes. Run it only right before `apm install`.
  check    fail if a locked dependency deploys nothing, a deployed file is
           missing or git-ignored, a dependency lost a deployed file at the
           commit HEAD's lock already pins, or a committed .agents/skills/
           file isn't in the lock.

Usage: apm-external-skills.py {prepare,check} [--root DIR] [--base REV]

Standard library only. Parses the block-style YAML that APM writes.
"""

import argparse
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys


LOCK = "apm.lock.yaml"
SKILLS = PurePosixPath(".agents/skills")


class LockError(Exception):
    pass


def parse_lock(text):
    """Return {dependency: (resolved commit, [deployed file, ...])} from apm.lock.yaml text."""
    deps, current, in_deps, in_files = {}, None, False, False
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if not line.startswith((" ", "-")):
            in_deps, current = line.rstrip() == "dependencies:", None
            continue
        if not in_deps:
            continue
        if line.startswith("- "):
            key, _, value = line[2:].partition(":")
            if key != "repo_url" or not value.strip():
                raise LockError(f"{LOCK}:{number}: expected `- repo_url:` to start a dependency")
            current = {"repo_url": value.strip(), "files": []}
            deps[number] = current
            in_files = False
        elif line.startswith("  - ") and in_files:
            current["files"].append(line[4:].strip())
        elif line.startswith("  ") and not line.startswith("   "):
            key, _, value = line[2:].partition(":")
            in_files = key == "deployed_files"
            current[key] = value.strip()
    if not deps:
        raise LockError(f"{LOCK}: no dependencies found")
    return {
        "/".join(filter(None, (dep["repo_url"], dep.get("virtual_path")))): (dep.get("resolved_commit"), dep["files"])
        for dep in deps.values()
    }


def locked_dependencies(text):
    """Return {dependency: [deployed file, ...]} from apm.lock.yaml text."""
    return {dep: files for dep, (_, files) in parse_lock(text).items()}


def committed_lock(root, base=None):
    """Return the parsed apm.lock.yaml at `base`; without one, HEAD's lock or {}."""
    result = subprocess.run(
        ["git", "show", f"{base or 'HEAD'}:{LOCK}"], cwd=root, capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0 and base:
        raise LockError(f"cannot read {LOCK} at {base}: {result.stderr.strip()}")
    return parse_lock(result.stdout) if result.returncode == 0 else {}


def external_skill_dirs(deps):
    """Return the .agents/skills/<name> folders that locked dependencies deploy."""
    return sorted({folder for files in deps.values() for folder in skill_dirs(files)})


def skill_dirs(files):
    paths = (PurePosixPath(entry) for entry in files)
    return [path for path in paths if path.parent == SKILLS and ".." not in path.parts]


def prepare(root, deps):
    for folder in external_skill_dirs(deps):
        target = root / folder
        linked = [part for part in (folder.parents[1], folder.parent, folder) if (root / part).is_symlink()]
        if linked or (target.exists() and not target.is_dir()):
            raise LockError(f"{folder} is not a regular folder in the checkout; refusing to remove it")
        if target.is_dir():
            shutil.rmtree(target)
            print(f"Removed {folder} for a fresh deploy from its pinned commit")


def tracked_skill_files(root):
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", str(SKILLS)], cwd=root, check=True, capture_output=True, text=True
    ).stdout
    return [path for path in out.split("\0") if path]


def ignored_paths(root, paths):
    """Return the paths that .gitignore would keep out of the materialize PR."""
    result = subprocess.run(
        ["git", "check-ignore", "-z", "--stdin"],
        cwd=root,
        input="".join(f"{path}\0" for path in paths),
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    return {path for path in result.stdout.split("\0") if path}


def check(root, deps, tracked, ignored=frozenset()):
    problems = []
    claimed = set()
    for dep, files in sorted(deps.items()):
        if not files:
            problems.append(f"{dep} deploys no files; `apm install` dropped it")
        claimed.update(files)
        for entry in files:
            if not (root / entry).exists():
                problems.append(f"{entry} from {dep} is missing")
            elif entry in ignored and str(PurePosixPath(entry).parent) not in ignored:
                problems.append(f"{entry} from {dep} is git-ignored; add a .gitignore exception for it")
        for folder in skill_dirs(files):
            anchor = folder / "SKILL.md"
            if str(anchor) not in files or not (root / anchor).is_file():
                problems.append(f"{folder} from {dep} has no deployed SKILL.md")
    for path in tracked:
        if path not in claimed and (root / path).exists():
            problems.append(f"{path} is committed but no locked dependency deploys it")
    return problems


def dropped_files(previous, current):
    """List deployed paths a dependency lost although its resolved commit didn't change."""
    problems = []
    for dep, (commit, files) in sorted(current.items()):
        old_commit, old_files = previous.get(dep, (None, []))
        if commit and commit == old_commit:
            problems += [
                f"{path} from {dep} was dropped at unchanged commit {commit[:8]}"
                for path in old_files
                if path not in files
            ]
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("prepare", "check"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base", help="revision whose lock `check` compares against (default: HEAD)")
    args = parser.parse_args(argv)
    try:
        lock = parse_lock((args.root / LOCK).read_text(encoding="utf-8"))
        deps = {dep: files for dep, (_, files) in lock.items()}
        if args.command == "prepare":
            prepare(args.root, deps)
            return 0
        claimed = sorted({entry for files in deps.values() for entry in files})
        problems = check(args.root, deps, tracked_skill_files(args.root), ignored_paths(args.root, claimed))
        problems += dropped_files(committed_lock(args.root, args.base), lock)
    except (OSError, LockError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"::error::{problem}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s); see docs/apm.md (external primitives).", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
