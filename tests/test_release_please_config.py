"""Guard that release-please can bump every version it is configured to bump.

Regression test for #204: the APM CLI re-serializes apm.yml and drops comments,
which silently removed the `# x-release-please-version` annotation the generic
updater needs, so release PRs stopped bumping apm.yml. Standard library only.
"""

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "release-please-config.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((ROOT / ".release-please-manifest.json").read_text(encoding="utf-8"))
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
GENERIC_MARKERS = ("x-release-please-version", "x-release-please-start-version")


def yaml_top_level_string(content, jsonpath):
    """Return the string release-please's yaml updater would replace, or None.

    Only top-level `$.<key>` paths are supported; anything else fails loudly so
    this check is extended rather than silently skipped.
    """
    match = re.fullmatch(r"\$\.([A-Za-z_][A-Za-z0-9_-]*)", jsonpath)
    if not match:
        raise ValueError(f"unsupported jsonpath {jsonpath!r}; extend this test")
    key = re.escape(match.group(1))
    values = re.findall(rf"(?m)^{key}:[ \t]*(.*?)[ \t]*$", content)
    if len(values) != 1:
        return None
    value = re.sub(r"\s+#.*$", "", values[0])
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value if SEMVER.match(value) else None


def updatable_version(entry, content):
    """Return the version the extra-files entry would update, or None."""
    kind = entry.get("type")
    if kind == "generic":
        return "annotated" if any(marker in content for marker in GENERIC_MARKERS) else None
    if kind == "yaml":
        return yaml_top_level_string(content, entry["jsonpath"])
    raise ValueError(f"unsupported extra-files type {kind!r}; extend this test")


class ResolverTests(unittest.TestCase):
    def test_stripped_generic_annotation_is_detected(self):
        entry = {"type": "generic", "path": "apm.yml"}
        self.assertIsNone(updatable_version(entry, "name: x\nversion: 1.2.3\n"))
        self.assertEqual(
            updatable_version(entry, "version: 1.2.3 # x-release-please-version\n"),
            "annotated",
        )

    def test_yaml_version_resolution(self):
        entry = {"type": "yaml", "path": "apm.yml", "jsonpath": "$.version"}
        self.assertEqual(updatable_version(entry, "name: x\nversion: 1.2.3\n"), "1.2.3")
        self.assertEqual(updatable_version(entry, "version: '1.2.3' # note\n"), "1.2.3")
        self.assertIsNone(updatable_version(entry, "name: x\n"))
        self.assertIsNone(updatable_version(entry, "meta:\n  version: 1.2.3\n"))
        self.assertIsNone(updatable_version(entry, "version: 1\n"))


class ReleasePleaseConfigTests(unittest.TestCase):
    def setUp(self):
        self.package = CONFIG["packages"]["."]
        self.extra_files = self.package.get("extra-files", [])

    def test_apm_yml_is_bumped_by_release_please(self):
        paths = [entry.get("path") for entry in self.extra_files]
        self.assertIn("apm.yml", paths, "release PRs must bump apm.yml's version")

    def test_every_extra_file_is_updatable(self):
        for entry in self.extra_files:
            with self.subTest(path=entry["path"]):
                content = (ROOT / entry["path"]).read_text(encoding="utf-8")
                self.assertIsNotNone(
                    updatable_version(entry, content),
                    f"release-please cannot find the version in {entry['path']}",
                )

    def test_apm_yml_version_matches_manifest(self):
        entry = next(e for e in self.extra_files if e.get("path") == "apm.yml")
        content = (ROOT / "apm.yml").read_text(encoding="utf-8")
        self.assertEqual(updatable_version(entry, content), MANIFEST["."])


if __name__ == "__main__":
    unittest.main()
