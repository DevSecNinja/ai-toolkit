"""Test fixtures must leave alone the repo a commit hook points at (#251).

In a linked worktree, `git commit` exports GIT_DIR=<main>/.git/worktrees/<name>
and GIT_INDEX_FILE to the hooks. A fixture `git init` that inherits them
re-initialises that git dir, takes it for a bare repo (its path doesn't end in
.git) and writes `core.bare = true` to the shared <main>/.git/config, which
breaks the main checkout; fixture commits land on its HEAD. Run every suite
that creates git fixtures with such an environment, pointed at a throwaway
main repo and worktree, and check that nothing there changed.
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


TESTS = Path(__file__).resolve().parent
SUITES = ["test_apm_external_skills.WorkTreeTests", "test_renovate_prs.RepositoryScriptTests"]
if os.name != "nt" and shutil.which("jq"):
    # The push-hook tests need a POSIX shell and jq, which stock macOS lacks.
    SUITES.append("test_hook_scripts.FeatureBranchPushTest")


def without_git_env():
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(*args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
                          env=without_git_env(), check=True, capture_output=True, encoding="utf-8", timeout=60).stdout


def snapshot(main, gitdir):
    files = {str(path): path.read_bytes() for path in (main / ".git/HEAD", gitdir / "HEAD", gitdir / "index")}
    return git("-C", str(main), "for-each-ref", "--format=%(refname) %(objectname)"), files


class HookGitEnvironmentTests(unittest.TestCase):
    def test_git_fixtures_leave_the_hook_repo_alone(self):
        with tempfile.TemporaryDirectory(prefix="hook-git-env-") as tmp:
            main, worktree = Path(tmp) / "main", Path(tmp) / "worktree"
            git("init", "-q", "-b", "main", str(main))
            (main / "README.md").write_text("x\n", encoding="utf-8")
            git("-C", str(main), "add", "README.md")
            git("-C", str(main), "commit", "-qm", "init")
            git("-C", str(main), "worktree", "add", "-q", "-b", "feature", str(worktree))
            gitdir = Path(git("-C", str(worktree), "rev-parse", "--absolute-git-dir").strip())
            config = (main / ".git/config").read_text(encoding="utf-8")
            before = snapshot(main, gitdir)

            # What `git commit` in the worktree hands its pre-commit hooks.
            hook_env = {**without_git_env(), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(TESTS),
                        "GIT_DIR": gitdir.as_posix(), "GIT_INDEX_FILE": (gitdir / "index").as_posix()}
            result = subprocess.run([sys.executable, "-m", "unittest", *SUITES], cwd=worktree, env=hook_env,
                                    capture_output=True, text=True, timeout=600, check=False)

            self.assertEqual(result.returncode, 0, result.stderr[-4000:])
            self.assertEqual((main / ".git/config").read_text(encoding="utf-8"), config)
            self.assertEqual(snapshot(main, gitdir), before, "a fixture changed the hook repo's refs or index")


if __name__ == "__main__":
    unittest.main()
