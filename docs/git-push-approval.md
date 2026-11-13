# Git push approval hook

[`require-push-approval.sh`](../scripts/git-push-approval/require-push-approval.sh) is a Copilot `preToolUse`
hook, shipped by [`.apm/hooks/git-push-approval.json`](../.apm/hooks/git-push-approval.json).
Commits stay local and rewritable until they're pushed, so `git push` is where it
asks for a human checkpoint.

## What it decides

For a shell tool call that contains `git push`, the hook either stays silent (the
normal permission flow runs, so autopilot sessions continue) or returns
`permissionDecision: "ask"`.

It stays silent only when **every** `git push` in the command targets a feature
branch on `origin`:

- `git push origin my-feature`, `git push -u origin HEAD`,
  `git push origin HEAD:refs/heads/my-feature`
- `--force-with-lease`, `--force-with-lease=<ref>:<expect>` and
  `--force-if-includes`
- `git push` or `git push origin` with no refspec, when the current branch, its
  upstream and its push remote all resolve to a non-protected branch on `origin`
- compound commands such as
  `git fetch && git rebase origin/main && git push --force-with-lease 2>&1 | tail`,
  as long as every other command is on a short allowlist: `git add`, `branch`,
  `checkout`, `commit`, `diff`, `fetch`, `log`, `rebase` (without `--exec`),
  `rev-parse`, `show`, `status` and `switch`, plus `echo`, `grep`, `head`,
  `tail`, `true` and `wc`

It asks for everything else, including:

- the default branch (from `refs/remotes/origin/HEAD`, and always when that
  can't be resolved), `main`, `master`, `trunk`, `develop`, `gh-pages`,
  `release`, `release/*`, `releases/*` and `release-please--*`
- tags, `--tags`, `--all`, `--mirror`, `--delete`, `:branch` deletions,
  `--force`, `-f`, `+refspec` and any other option it doesn't know
- `src:dst` refspecs whose destination isn't spelled `refs/heads/<branch>`,
  because Git may resolve a short name to a tag on the remote
- remotes other than `origin`, URLs and `git -C`/`-c` global options
- any other command in the same line (`cd`, `git config`, `sudo`, `bash -c`,
  aliases, ...), variables, command substitution, backslashes, unquoted globs,
  brace expansion, comments, unbalanced quotes and anything else it can't parse
- implicit targets (`git push`, `HEAD`) after a `checkout`, `switch`, `branch`
  or two-argument `rebase` in the same command
- a `push.default` other than `simple`, `current` or `upstream`, and
  `remote.origin.push`, `remote.origin.mirror` or `push.followTags` config

The hook resolves branches with read-only `git` commands in the payload's `cwd`
(or its own working directory). It can't see a directory change made by an
earlier, separate shell command, so prefer explicit refspecs such as
`git push --force-with-lease origin HEAD:refs/heads/<branch>` in persistent shells.

## Approving pushes in autopilot

Feature-branch pushes need no approval. For a push the hook asks about, switch
the session to interactive mode and approve the prompt, or push it yourself.
`SKIP_PUSH_APPROVAL=true` disables the guardrail for the whole session; agents
must never set it themselves.

## Tests

`tests/test_hook_scripts.py` covers each allow and ask case against a throwaway
repository. The **Hook Scripts** workflow runs it with the runner's Bash and
with Bash 3.2, which stock macOS uses for `#!/bin/bash`.
