"""Run the Renovate helper with every `gh` call routed to the offline fake.

Executing the extensionless fake through PATH only works on POSIX; on Windows
CreateProcess would find the real gh.exe instead. Routing here works everywhere
and keeps live credentials out of the tests. Usage: run_helper.py HELPER ARGS...
"""

from pathlib import Path
import runpy
import subprocess
import sys

FAKE_GH = Path(__file__).with_name("gh")
_run = subprocess.run


def run(args, *rest, **kwargs):
    if args and args[0] == "gh":
        args = [sys.executable, str(FAKE_GH), *args[1:]]
    return _run(args, *rest, **kwargs)


subprocess.run = run
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
