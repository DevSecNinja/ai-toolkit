"""scripts/py.sh picks the first Python that meets the minimum (#229)."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from posix_shell import posix_shell


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/py.sh"
WINDOWS_WORKFLOW = ROOT / ".github/workflows/windows-hooks.yml"
STUB = '#!/bin/sh\necho "Python was not found; run without arguments to install from the Microsoft Store"\nexit 49\n'


def interpreter(name, version):
    # Answers the version probe, otherwise reports how it was run.
    return (f'#!/bin/sh\n[ "$1" = -3 ] && shift\n'
            f'if [ "$1" = -c ]; then echo {version}; else echo "{name} $*"; fi\n')


class PyLauncherTests(unittest.TestCase):
    def run_launcher(self, **fakes):
        with tempfile.TemporaryDirectory(prefix="py-launcher-") as temp:
            store = Path(temp) / "WindowsApps"
            store.mkdir()
            for name, body in fakes.items():
                path = (store if body == STUB else Path(temp)) / name
                path.write_text(body, newline="\n")
                path.chmod(0o755)
            return subprocess.run([posix_shell("sh"), str(LAUNCHER), "-m", "unittest"],
                                  env=dict(os.environ, PATH=f"{store}{os.pathsep}{temp}"),
                                  capture_output=True, text=True, timeout=20, check=False)

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
        self.assertIn("Microsoft Store stub, runs no code", result.stderr)
        self.assertIn("py -3 (", result.stderr)
        self.assertIn("Python 3.9, too old", result.stderr)
        self.assertIn("python: not on PATH", result.stderr)
        self.assertIn("python.org", result.stderr)

    def test_minimum_matches_windows_ci_python(self):
        launcher = LAUNCHER.read_text()
        minimum = "{}.{}".format(re.search(r"(?m)^min_major=(\d+)$", launcher)[1],
                                 re.search(r"(?m)^min_minor=(\d+)$", launcher)[1])
        ci = re.search(r"python-version:\s*['\"]?([\d.]+)", WINDOWS_WORKFLOW.read_text())[1]
        self.assertEqual(minimum, ci)


if __name__ == "__main__":
    unittest.main()
