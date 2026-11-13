"""Keep the shipped hook scripts compatible with Bash 3.2.

Regression test for #217: `${1,,}` in require-push-approval.sh is a "bad
substitution" under the Bash 3.2 that stock macOS runs for `#!/bin/bash`, and a
crashing `preToolUse` hook is fail-closed, so every tool call was denied.

Two layers:
- a static scan of every script referenced by `.apm/hooks/*.json` for Bash 4+
  syntax, which runs anywhere;
- behaviour checks that run the hooks with `$HOOK_BASH` (default: `bash`).
  CI runs them a second time with a Bash 3.2 build (see tests/build-bash32.sh).
  Set `EXPECT_BASH_VERSION` (e.g. `3.2`) to assert which interpreter ran.

Standard library only.
"""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOK_BASH = os.environ.get("HOOK_BASH", "bash")
PUSH_HOOK = ROOT / "scripts" / "git-push-approval" / "require-push-approval.sh"
GUARD_HOOK = ROOT / "scripts" / "tool-guardian" / "guard-tool.sh"

# (regex, what it is). Applied per line, after dropping full-line comments.
BASH4_SYNTAX = [
    (r"\$\{[A-Za-z0-9_]+(\[[^]]*\])?(\^|,)", "case modification ${var,,} / ${var^^} (Bash 4.0)"),
    (r"\$\{[^}]*@[QEPAaUuLKk]\}", "parameter transformation ${var@Q} (Bash 4.4)"),
    (r"\$\{[A-Za-z_][A-Za-z0-9_]*\[-[0-9]", "negative array index ${arr[-1]} (Bash 4.3)"),
    (r"\b(declare|typeset|local)\s+(-[A-Za-z]+\s+)*-[A-Za-z]*[Anlu]", "declare -A/-n/-l/-u (Bash 4.0/4.3)"),
    (r"\b(mapfile|readarray|coproc)\b", "mapfile/readarray/coproc (Bash 4.0)"),
    (r"\|&", "|& pipe (Bash 4.0)"),
    (r"&>>", "&>> redirect (Bash 4.0)"),
    (r";;&|\s;&\s*$", "case fall-through ;& / ;;& (Bash 4.0)"),
    (r"(\[\[|\[|\btest)\s+-v\s", "-v variable test (Bash 4.2)"),
    (r"\bwait\s+-n\b", "wait -n (Bash 4.3)"),
    (r"\bshopt\s+-s\s+(globstar|lastpipe|autocd|direxpand|checkjobs)\b", "Bash 4+ shopt option"),
    (r"\$\{?(EPOCHSECONDS|EPOCHREALTIME|BASH_ARGV0)\b", "Bash 5.0 variable"),
    (r"\{-?[0-9]+\.\.-?[0-9]+\.\.-?[0-9]+\}", "brace expansion step {1..9..2} (Bash 4.0)"),
    (r"%\([^)]*\)T", "printf %(...)T (Bash 4.2)"),
]


def bash4_findings(text):
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        for pattern, label in BASH4_SYNTAX:
            if re.search(pattern, line):
                findings.append(f"line {number}: {label}: {line.strip()}")
    return findings


def hook_scripts():
    """Scripts that `.apm/hooks/*.json` runs via the `bash` key."""
    scripts = set()
    for manifest in sorted((ROOT / ".apm" / "hooks").glob("*.json")):
        hooks = json.loads(manifest.read_text(encoding="utf-8")).get("hooks", {})
        for entries in hooks.values():
            for entry in entries:
                command = entry.get("bash")
                if command:
                    scripts.add(ROOT / command.replace("${PLUGIN_ROOT}/", "", 1))
    return sorted(scripts)


def run_hook(script, payload, **env):
    merged = {**os.environ, "SKIP_PUSH_APPROVAL": "", "SKIP_TOOL_GUARD": "", **env}
    return subprocess.run(
        [HOOK_BASH, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=merged,
        timeout=30,
        check=False,
    )


class Bash4SyntaxScanTest(unittest.TestCase):
    def test_hook_scripts_are_found(self):
        scripts = hook_scripts()
        self.assertIn(PUSH_HOOK, scripts)
        self.assertIn(GUARD_HOOK, scripts)
        for script in scripts:
            self.assertTrue(script.is_file(), f"{script} is referenced by a hook but missing")

    def test_hook_scripts_have_no_bash4_syntax(self):
        for script in hook_scripts():
            with self.subTest(script=script.relative_to(ROOT).as_posix()):
                self.assertEqual(bash4_findings(script.read_text(encoding="utf-8")), [])

    def test_scan_flags_bash4_syntax(self):
        for snippet in (
            'case "${1,,}" in',
            'echo "${name^^}"',
            "declare -A seen=()",
            "local -n ref=$1",
            "mapfile -t lines < file",
            "cmd |& tee log",
            'if [[ -v FOO ]]; then',
        ):
            with self.subTest(snippet=snippet):
                self.assertNotEqual(bash4_findings(snippet), [])

    def test_scan_ignores_bash32_syntax(self):
        for snippet in (
            'if [[ ${#ALLOWLIST[@]} -gt 0 ]]; then',
            'echo "${1:-}" "${match:0:35}"',
            "GIT_PUSH_REGEX='git([[:space:]]+[^[:space:];&|]+)*'",
            "# ${1,,} in a comment is fine",
            "local name",
        ):
            with self.subTest(snippet=snippet):
                self.assertEqual(bash4_findings(snippet), [])


class HookBehaviourTest(unittest.TestCase):
    def test_interpreter_version(self):
        expected = os.environ.get("EXPECT_BASH_VERSION")
        if not expected:
            self.skipTest("EXPECT_BASH_VERSION not set")
        result = subprocess.run(
            [HOOK_BASH, "-c", "printf %s \"$BASH_VERSION\""],
            capture_output=True, text=True, check=True,
        )
        self.assertTrue(result.stdout.startswith(expected), result.stdout)

    def assert_asks(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["permissionDecision"], "ask")

    def assert_silent(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_push_hook_asks_for_git_push_with_any_tool_name_case(self):
        for tool in ("bash", "Bash", "PowerShell", "SHELL"):
            with self.subTest(tool=tool):
                self.assert_asks(run_hook(
                    PUSH_HOOK, {"toolName": tool, "toolArgs": {"command": "git push origin main"}}))

    def test_push_hook_accepts_vscode_payload(self):
        self.assert_asks(run_hook(
            PUSH_HOOK, {"tool_name": "Bash", "tool_input": {"command": "git -C /repo push"}}))

    def test_push_hook_ignores_other_commands_and_tools(self):
        for payload in (
            {"toolName": "Bash", "toolArgs": {"command": "git status && npm run push"}},
            {"toolName": "edit", "toolArgs": {"path": "README.md", "text": "run git push"}},
        ):
            with self.subTest(payload=payload):
                self.assert_silent(run_hook(PUSH_HOOK, payload))

    def test_push_hook_can_be_skipped(self):
        self.assert_silent(run_hook(
            PUSH_HOOK, {"toolName": "bash", "toolArgs": {"command": "git push"}},
            SKIP_PUSH_APPROVAL="true"))

    def test_guard_hook_allows_safe_and_blocks_dangerous_commands(self):
        with tempfile.TemporaryDirectory() as log_dir:
            safe = run_hook(GUARD_HOOK, {"toolName": "bash", "toolInput": "ls -la"},
                            TOOL_GUARD_LOG_DIR=log_dir, GUARD_MODE="block")
            self.assertEqual(safe.returncode, 0, safe.stderr)
            dangerous = run_hook(GUARD_HOOK, {"toolName": "bash", "toolInput": "rm -rf /"},
                                 TOOL_GUARD_LOG_DIR=log_dir, GUARD_MODE="block")
            self.assertEqual(dangerous.returncode, 1, dangerous.stderr)
            self.assertIn("destructive_file_ops", dangerous.stdout)


class FeatureBranchPushTest(unittest.TestCase):
    """#228: feature-branch pushes to origin pass silently; everything else asks."""

    ALLOWED = (
        "git push origin feat",
        "git push --force-with-lease origin feat",
        "git push --force-with-lease=feat:abc123 --force-if-includes origin HEAD",
        "git push -u origin HEAD:refs/heads/new-topic",
        "git push",
        "git --no-pager push origin",
        "git fetch origin && git rebase origin/main && git push --force-with-lease 2>&1 | tail -n 5",
        "git checkout -b new-topic && git push -u origin new-topic",
        "git push origin 'feat' > /dev/null; git status",
    )
    ASKED = (
        # Default and protected branches; `stable` is the default via origin/HEAD.
        "git push origin main",
        "git push origin feat:master",
        "git push origin HEAD:refs/heads/main",
        "git push origin stable",
        "git push origin feat:release-please--branches--main",
        # Force without a lease, tags and bulk pushes.
        "git push --force origin feat",
        "git push -f origin feat",
        "git push origin +feat",
        "git push --force-with-lease --force origin feat",
        "git push --tags",
        "git push origin --all",
        "git push --mirror origin",
        "git push origin v1",
        "git push origin tag v1",
        "git push origin refs/tags/v1",
        # Deletions and other remotes.
        "git push --delete origin feat",
        "git push origin :feat",
        "git push upstream feat",
        "git push https://example.invalid/repo.git feat",
        # Anything the hook can't resolve with certainty.
        "git push origin $BRANCH",
        "git push origin $(git branch --show-current)",
        "git push origin `whoami`",
        "git push origin 'feat",
        "git push origin {feat,main}",
        "git push origin missing-branch",
        "git -C /tmp push origin feat",
        "sudo git push origin feat",
        "bash -c 'git push origin feat'",
        # Compound commands where one push is unsafe or the target may move.
        "git push origin feat && git push origin main",
        "cd ../other && git push origin feat",
        "git checkout main && git push",
        "git rebase origin/main main && git push",
    )

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        gitconfig = Path(cls.tmp.name) / "gitconfig"
        gitconfig.write_text("", encoding="utf-8")
        cls.env = {"GIT_CONFIG_GLOBAL": str(gitconfig), "GIT_CONFIG_NOSYSTEM": "1"}
        cls.repo = str(Path(cls.tmp.name) / "repo")
        subprocess.run(["git", "init", "-q", "-b", "main", cls.repo], check=True,
                       env={**os.environ, **cls.env})
        for args in (
            ["-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "init"],
            ["remote", "add", "origin", "https://example.invalid/repo.git"],
            ["branch", "feat"],
            ["branch", "wip"],
            ["tag", "v1"],
            ["update-ref", "refs/remotes/origin/feat", "HEAD"],
            ["update-ref", "refs/remotes/origin/stable", "HEAD"],
            ["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/stable"],
            ["config", "branch.feat.remote", "origin"],
            ["config", "branch.feat.merge", "refs/heads/feat"],
            ["config", "branch.wip.remote", "origin"],
            ["config", "branch.wip.merge", "refs/heads/main"],
        ):
            cls.git(*args)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def git(cls, *args):
        subprocess.run(["git", "-C", cls.repo, *args], check=True, capture_output=True,
                       env={**os.environ, **cls.env})

    def setUp(self):
        self.git("checkout", "-q", "feat")

    def push(self, command, vscode=False):
        if vscode:
            payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": self.repo}
        else:
            payload = {"toolName": "bash", "toolArgs": json.dumps({"command": command}), "cwd": self.repo}
        return run_hook(PUSH_HOOK, payload, **self.env)

    def assert_decision(self, result, expected):
        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(result.stdout)["permissionDecision"] if result.stdout.strip() else None
        self.assertEqual(decision, expected)

    def test_feature_branch_pushes_are_allowed(self):
        for command in self.ALLOWED:
            with self.subTest(command=command):
                self.assert_decision(self.push(command), None)
        self.assert_decision(self.push("git push origin feat", vscode=True), None)

    def test_risky_or_unresolved_pushes_ask(self):
        for command in self.ASKED:
            with self.subTest(command=command):
                self.assert_decision(self.push(command), "ask")

    def test_implicit_push_resolves_current_branch_and_upstream(self):
        for checkout in (["main"], ["wip"], ["--detach"]):
            with self.subTest(checkout=checkout):
                self.git("checkout", "-q", *checkout)
                self.assert_decision(self.push("git push --force-with-lease"), "ask")

    def test_implicit_push_asks_for_unresolved_push_config(self):
        for key, value in (("push.default", "matching"), ("remote.pushDefault", "upstream"),
                           ("remote.origin.push", "refs/heads/*:refs/heads/*")):
            with self.subTest(key=key):
                self.git("config", key, value)
                try:
                    self.assert_decision(self.push("git push"), "ask")
                finally:
                    self.git("config", "--unset", key)


if __name__ == "__main__":
    unittest.main()
