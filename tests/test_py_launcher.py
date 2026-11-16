"""scripts/py.sh runs the hooks on the Python in .python-version, the single
source that mise installs (#229, #246)."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib
import unittest

from posix_shell import posix_shell


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/py.sh"
PYTHON_VERSION = ROOT / ".python-version"
MISE_CONFIG = ROOT / ".mise.toml"
WORKFLOWS = ROOT / ".github/workflows"
WINDOWS_WORKFLOW = WORKFLOWS / "windows-hooks.yml"
STUB = '#!/bin/sh\necho "Python was not found; run without arguments to install from the Microsoft Store"\nexit 49\n'


def interpreter(name, version):
    # Answers the version probe, otherwise reports how it was run.
    return (f'#!/bin/sh\n[ "$1" = -3 ] && shift\n'
            f'if [ "$1" = -c ]; then echo {version}; else echo "{name} $*"; fi\n')


def mise(python):
    # `mise -C <repo> which python` prints the installed Python, if there is one.
    found = f'echo "{python}"; exit 0' if python else "echo 'python@3.12 is not installed' >&2; exit 1"
    return (f'#!/bin/sh\n[ "$1" = -C ] && [ -r "$2/.python-version" ] || exit 2\n'
            f'shift 2\n[ "$*" = "which python" ] || exit 2\n{found}\n')


def run(launcher, path):
    return subprocess.run([posix_shell("sh"), str(launcher), "-m", "unittest"],
                          env=dict(os.environ, PATH=path),
                          capture_output=True, encoding="utf-8", timeout=20, check=False)


class PyLauncherTests(unittest.TestCase):
    def run_launcher(self, minimum="3.12\n", mise_python=None, **fakes):
        # A copy of the launcher in a fake repo, so its .python-version is ours.
        # mise_python: the version mise has installed, "" for none, None for no mise.
        with tempfile.TemporaryDirectory(prefix="py-launcher-") as temp:
            repo, bin_dir, installs = Path(temp) / "repo", Path(temp) / "bin", Path(temp) / "mise"
            store = bin_dir / "WindowsApps"
            (repo / "scripts").mkdir(parents=True)
            store.mkdir(parents=True)
            installs.mkdir()
            shutil.copyfile(LAUNCHER, repo / "scripts/py.sh")
            if minimum is not None:
                (repo / ".python-version").write_bytes(minimum.encode())
            if mise_python is not None:
                python = installs / "python"
                if mise_python:
                    python.write_text(interpreter("mise-python", mise_python), newline="\n")
                    python.chmod(0o755)
                fakes["mise"] = mise(python.as_posix() if mise_python else "")
            for name, body in fakes.items():
                path = (store if body == STUB else bin_dir) / name
                path.write_text(body, newline="\n")
                path.chmod(0o755)
            return run(repo / "scripts/py.sh", f"{store}{os.pathsep}{bin_dir}")

    def test_prefers_mise_python(self):
        result = self.run_launcher(mise_python="3.12", python3=interpreter("python3", "3.13"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "mise-python -m unittest")

    def test_falls_back_when_mise_has_no_new_enough_python(self):
        for mise_python in ("", "3.11"):
            with self.subTest(mise_python=mise_python):
                result = self.run_launcher(mise_python=mise_python, python3=interpreter("python3", "3.12"))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "python3 -m unittest")

    def test_skips_store_stub_and_old_python_for_first_new_enough(self):
        result = self.run_launcher(python3=STUB, py=interpreter("py", "3.9"),
                                   python=interpreter("python", "3.12"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "python -m unittest")

    def test_prefers_python3_then_py_launcher(self):
        result = self.run_launcher(python3=interpreter("python3", "3.13"),
                                   python=interpreter("python", "3.12"))
        self.assertEqual(result.stdout.strip(), "python3 -m unittest")
        result = self.run_launcher(py=interpreter("py", "4.0"), python=interpreter("python", "3.12"))
        self.assertEqual(result.stdout.strip(), "py -m unittest")

    def test_fails_clearly_without_a_new_enough_python(self):
        result = self.run_launcher(python3=STUB, py=interpreter("py", "3.9"))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("no Python >= 3.12 found", result.stderr)
        self.assertIn("mise: not on PATH", result.stderr)
        self.assertIn("Run `mise install` in the repo to install Python 3.12", result.stderr)
        self.assertIn("Microsoft Store stub, runs no code", result.stderr)
        self.assertIn("py -3 (", result.stderr)
        self.assertIn("Python 3.9, too old", result.stderr)
        self.assertIn("python: not on PATH", result.stderr)
        self.assertIn("python.org", result.stderr)
        result = self.run_launcher(mise_python="")
        self.assertIn("mise: Python 3.12 not installed", result.stderr)

    def test_reads_major_minor_from_python_version_file(self):
        for minimum in ("3.13", "3.13\n", "3.13.1\n", "3.13\r\n", "# floor\n\n  3.13  \n3.9\n"):
            with self.subTest(minimum=minimum):
                result = self.run_launcher(minimum, python3=interpreter("python3", "3.12"),
                                           python=interpreter("python", "3.13"))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "python -m unittest")

    def test_rejects_a_missing_or_malformed_python_version_file(self):
        for minimum in (None, "", "\n", "3", "3.", ".12", "three.12", "3.12-dev",
                        "3..12", "3.12.", "3.12.garbage", "3.12.4.5"):
            with self.subTest(minimum=minimum):
                result = self.run_launcher(minimum, python=interpreter("python", "3.13"))
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn(".python-version must hold a Python version such as 3.14 or 3.14.2", result.stderr)


class PythonVersionSourceTests(unittest.TestCase):
    """.python-version is the only place the version lives; mise, py.sh and CI read it."""

    def test_python_version_file_holds_major_minor(self):
        self.assertRegex(PYTHON_VERSION.read_text(encoding="utf-8"), r"\A\d+\.\d+\n\Z")

    def test_launcher_enforces_the_file_version(self):
        version = PYTHON_VERSION.read_text(encoding="utf-8").strip()
        self.assertNotRegex(LAUNCHER.read_text(encoding="utf-8"), r"(?m)^\s*min_(major|minor)=['\"]?\d")
        with tempfile.TemporaryDirectory(prefix="py-launcher-") as empty:
            result = run(LAUNCHER, empty)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"no Python >= {version} found", result.stderr)

    def test_mise_installs_python_from_the_file(self):
        config = tomllib.loads(MISE_CONFIG.read_text(encoding="utf-8"))
        self.assertIn("python", config.get("settings", {}).get("idiomatic_version_file_enable_tools", []))
        self.assertNotIn("python", config.get("tools", {}), "pin Python in .python-version only")

    def test_windows_ci_installs_python_with_mise(self):
        workflow = WINDOWS_WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(workflow, r"(?m)^\s+install_args:.*\bpython\b")
        self.assertNotRegex(workflow, r"PY_PYTHON3|actions/setup-python@")

    def test_every_setup_python_step_reads_the_file(self):
        for workflow in sorted(WORKFLOWS.glob("*.y*ml")):
            text = workflow.read_text(encoding="utf-8")
            with self.subTest(workflow=workflow.name):
                self.assertNotRegex(text, r"(?m)^\s+python-version:")
                self.assertEqual(len(re.findall(r"uses:\s*actions/setup-python@", text)),
                                 len(re.findall(r"(?m)^\s+python-version-file:\s*['\"]?\.python-version['\"]?\s*$", text)))


if __name__ == "__main__":
    unittest.main()