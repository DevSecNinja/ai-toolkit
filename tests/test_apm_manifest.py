"""Guard that apm.yml never lists this package as its own dependency.

Regression test for #207: a self-entry (`DevSecNinja/ai-toolkit#v0.8.0`) made
every later tag uninstallable, because a consumer pinning `#vX.Y.Z` then also
requires the older ref of the same package and APM rejects the conflict.
Dogfooding uses `includes: auto` (the local .apm/ tree) instead. Standard
library only.
"""

import os
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPO_FORMS = r"(?:(?:https?://|git@|ssh://git@)?github\.com[/:])?"


def top_level_value(content, key):
    match = re.search(rf"(?m)^{re.escape(key)}:[ \t]*['\"]?([^'\"#\s]+)", content)
    return match.group(1) if match else None


def strip_comments(content):
    """Drop YAML comment lines and trailing ` # ...` comments.

    `#` directly after a token (`owner/repo#v1.0.0`) is a ref, not a comment.
    """
    lines = (re.sub(r"[ \t]+#.*$", "", line) for line in content.splitlines())
    return "\n".join(line for line in lines if not re.match(r"^[ \t]*#", line)) + "\n"


def top_level_block(content, key):
    """Return the indented block under a top-level `key:` (empty if absent)."""
    content = strip_comments(content)
    match = re.search(rf"(?ms)^{re.escape(key)}:[^\n]*\n(.*?)(?=^\S|\Z)", content)
    return match.group(1) if match else ""


def self_references(manifest, repos):
    """Return dependency entries in `manifest` that point at one of `repos`."""
    deps = top_level_block(manifest, "dependencies")
    found = []
    for repo in repos:
        pattern = rf"(?i)(?<![\w./-]){REPO_FORMS}{re.escape(repo)}(?:\.git)?(?=[#@/\s'\"]|$)"
        found.extend(m.group(0) for m in re.finditer(pattern, deps))
    return found


def self_repos(manifest):
    """Repository slugs this package is published from."""
    repos = set()
    author, name = top_level_value(manifest, "author"), top_level_value(manifest, "name")
    if author and name:
        repos.add(f"{author}/{name}")
    if os.environ.get("GITHUB_REPOSITORY"):
        repos.add(os.environ["GITHUB_REPOSITORY"])
    return repos


class DetectorTests(unittest.TestCase):
    REPOS = {"DevSecNinja/ai-toolkit"}

    def test_detects_self_entries_in_every_form(self):
        for entry in (
            "    - DevSecNinja/ai-toolkit#v0.8.0\n",
            "    - >-\n      devsecninja/ai-toolkit#v0.8.0\n",
            "    - DevSecNinja/ai-toolkit\n",
            "    - DevSecNinja/ai-toolkit/.apm/agents/ada.agent.md#v1.0.0\n",
            "    - git: https://github.com/DevSecNinja/ai-toolkit.git\n",
            "    - git@github.com:DevSecNinja/ai-toolkit.git#main\n",
            "    - 'DevSecNinja/ai-toolkit@toolkit'\n",
        ):
            with self.subTest(entry=entry):
                manifest = f"name: ai-toolkit\ndependencies:\n  apm:\n{entry}targets:\n  - copilot\n"
                self.assertTrue(self_references(manifest, self.REPOS))

    def test_ignores_other_packages_and_non_dependency_keys(self):
        manifest = (
            "name: ai-toolkit\n"
            "description: install with apm install DevSecNinja/ai-toolkit#v1.0.0\n"
            "dependencies:\n  apm:\n"
            "    - DevSecNinja/ai-toolkit-extras#v1.0.0\n"
            "    - other/DevSecNinja/ai-toolkit#v1.0.0\n"
            "    - github/awesome-copilot/agents/x.agent.md#abc\n"
            "scripts:\n  sync: apm install DevSecNinja/ai-toolkit\n"
        )
        self.assertEqual(self_references(manifest, self.REPOS), [])

    def test_comments_neither_hide_nor_add_self_entries(self):
        hidden = (
            "name: ai-toolkit\ndependencies:\n  apm:\n"
            "    - github/awesome-copilot/agents/x.agent.md#abc\n"
            "# Self-consumption note at column zero\n"
            "    - DevSecNinja/ai-toolkit#v0.8.0\n"
        )
        self.assertTrue(self_references(hidden, self.REPOS))
        commented = (
            "name: ai-toolkit\ndependencies:\n  apm:\n"
            "    # - DevSecNinja/ai-toolkit#v0.8.0\n"
            "    - github/awesome-copilot/agents/x.agent.md#abc  # not DevSecNinja/ai-toolkit\n"
        )
        self.assertEqual(self_references(commented, self.REPOS), [])

    def test_self_repo_comes_from_author_and_name(self):
        manifest = "name: ai-toolkit\nversion: 1.0.0\nauthor: DevSecNinja\n"
        self.assertIn("DevSecNinja/ai-toolkit", self_repos(manifest))


class ManifestTests(unittest.TestCase):
    def test_apm_yml_does_not_depend_on_itself(self):
        manifest = (ROOT / "apm.yml").read_text(encoding="utf-8")
        repos = self_repos(manifest)
        self.assertTrue(repos, "apm.yml needs `author` and `name` to identify this package")
        self.assertEqual(
            self_references(manifest, repos),
            [],
            "apm.yml lists this package as its own dependency; consumers then "
            "cannot install any newer tag (see #207). Dogfood via `includes: auto`.",
        )

    def test_lockfile_does_not_pin_itself(self):
        manifest = (ROOT / "apm.yml").read_text(encoding="utf-8")
        lock = (ROOT / "apm.lock.yaml").read_text(encoding="utf-8")
        locked = {m.lower() for m in re.findall(r"(?m)^- repo_url:[ \t]*(\S+)", lock)}
        for repo in self_repos(manifest):
            self.assertNotIn(repo.lower(), locked)


if __name__ == "__main__":
    unittest.main()
