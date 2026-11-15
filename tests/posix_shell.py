"""Locate a POSIX shell for tests that run the repo's shell scripts."""

from functools import lru_cache
import os
from pathlib import Path
import shutil
import subprocess


@lru_cache(maxsize=None)
def posix_shell(name="bash"):
    """Return /bin/<name>, or Git for Windows' copy (System32\\bash.exe is WSL)."""
    if os.name != "nt":
        return f"/bin/{name}"
    # Like lefthook: the default Git for Windows install first, then next to git
    # (its exec path is <root>/<mingw64|clangarm64>/libexec/git-core).
    exec_path = subprocess.run(["git", "--exec-path"], capture_output=True, text=True,
                               timeout=20, check=True).stdout.strip()
    roots = [Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git", Path(exec_path).parents[2]]
    for root in roots:
        for directory in ("bin", "usr/bin"):
            candidate = root / directory / f"{name}.exe"
            if candidate.is_file():
                return str(candidate)
    found = shutil.which(name)
    if found and not any(part in found.lower() for part in ("system32", "windowsapps")):
        return found
    raise FileNotFoundError(f"Git for Windows' {name}.exe not found; install https://gitforwindows.org/")
