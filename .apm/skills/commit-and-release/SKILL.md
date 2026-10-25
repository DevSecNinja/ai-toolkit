---
name: commit-and-release
description: "Use when asked to commit, write a commit message, stage files, open a pull request, or cut a release in a DevSecNinja repo. Guides Conventional Commit messages, Conventional-Commit PR titles (repos squash-merge), the pre-commit/validate workflow, and the release-please release flow."
targets:
  - copilot
  - claude
  - agent-skills
---

# Commit & Release

DevSecNinja repositories use [Conventional Commits](https://www.conventionalcommits.org),
**squash-merge** PRs, and automated releases via
[release-please](https://github.com/googleapis/release-please). This skill is the
step-by-step procedure; the always-on rules live in the org instruction
(`devsecninja-conventions`).

## Trust gate

Apply the `untrusted-repositories` instruction before every command below,
including message validation, staging, hooks and pushes. A commit/PR request,
UI Trust or autopilot does not authorize execution of third-party repository
or dependency code. Inspect as data first; ask for explicit scoped approval
where hooks, filters, tools or workflows would execute untrusted code. Carry
the same restriction into testing and child sessions. Keep Actions disabled
on new forks we control unless separately authorized, and account for
upstream PR triggers before opening a PR.

For static-only work, report skipped runtime checks honestly. Do not bypass
required hooks or protections to commit; stop if they require unauthorized
execution. Normal checks still apply to trusted, execution-authorized work.
All commits must use 1Password signing; halt if unavailable or denied, without
substituting a signer or creating an unsigned commit.

## Conventional Commit format

```
<type>(<scope>): <description>
```

**Types:** `feat` (new feature → MINOR), `fix` (bug fix → PATCH), `docs`,
`ci`, `chore`, `refactor`, `perf`, `test`.

**Scope** is the component involved (e.g. a service/module/tool name). Multi-area
changes may omit the scope.

**Breaking changes** (→ MAJOR) are marked either way (or both):

- `!` before the colon: `feat(api)!: drop v1 endpoints`
- An uppercase `BREAKING CHANGE:` footer in the commit body.

A new required input to a centralized/reusable workflow IS breaking — mark it so
Renovate does not automerge a change that breaks downstream CI.

## PR titles matter most

Because repos **squash-merge**, the **PR title becomes the single commit on
`main`** and is what release-please reads to compute the next version and
changelog entry. So:

- The **PR title MUST be a valid Conventional Commit subject** (`type(scope): description`).
- Individual commits inside the PR may be informal — optimize them for review.
- Validate the intended PR title the same way you validate a commit message:

  ```sh
  mise exec -- cog verify "feat(auth): add device-code login"
  ```

  Exit code 0 = valid.

## Commit workflow

Follow these steps in order whenever asked to commit/push.

### 1. Inspect what changed

```sh
git diff --stat HEAD
git status --short
```

### 2. Stage explicitly

Prefer explicit paths over `git add .`:

```sh
git add path/to/changed-file other/changed-file
```

If the user already staged files, skip this.

### 3. Derive and validate the message

Review the staged diff (`git diff --cached`) and derive a clear, accurate
Conventional Commit subject from it. If the user explicitly supplied a desired
message, preserve that wording and intent while correcting it as needed for
accuracy and Conventional Commit compliance.

```sh
mise exec -- cog verify "fix(parser): handle empty frontmatter"
```

If validation fails, fix the message automatically and re-run validation until
it exits 0. Then commit with the validated message without asking the user to
approve or confirm it. Ask the user only when the staged change is genuinely
ambiguous about intent (for example, whether it is a `feat` or `fix`) and the
correct message cannot be determined from the diff or task context.

### 4. Run lint/tests before committing

Proceed only within the authorized execution scope established above.

Run all tests/validation in a **fresh testing context/subsession separate from
implementation**, including initial runs and reruns after fixes. Pause edits
and provide the exact isolated worktree/revision, acceptance criteria and
reproducible commands. Record the context identifier and results; after a fix,
start a new tester rather than reusing its conversation. A fresh task/subagent
is sufficient; no orchestration framework is needed.

```sh
mise exec -- lefthook run pre-commit
```

Plus the repo's own test command, if any. If anything fails, **stop and report**
— do not commit or open a PR with known-failing checks.

### 5. Commit and push

```sh
git commit -S -m "<message>"
git push
```

Use the configured 1Password signer and verify the resulting signature before
pushing. `-S` requests signing but does not itself select 1Password.

The `commit-msg` hook re-runs `cog verify` automatically; both hooks must pass.
Because hooks execute validation, have a fresh non-implementation context
perform the commit with the approved message and explicit staged paths.
Do not bypass hooks to avoid separate-context testing.

## Opening a pull request

- Set the **PR title to a valid Conventional Commit subject** (see above) — this
  is the release-critical field.
- Update documentation in the **same PR** as the code it describes.
- Keep the PR focused on one logical change.
- For execution-authorized work, ensure lint/tests pass before marking it ready.
  Label static-only work with the runtime checks not run; do not present it as
  runtime-validated or trigger unauthorized CI.
- Never force-push to `main` or any shared/protected branch.

## Cutting a release (release-please)

Releases are automated — you do **not** tag or run a release CLI by hand.

1. Merge feature/fix PRs to `main` with Conventional-Commit titles.
2. release-please opens (or updates) a `chore(main): release vX.Y.Z` PR
   containing the version bump and `CHANGELOG.md`.
3. Review that PR; when its checks are green, **merge it**. Merging creates the
   `vX.Y.Z` tag and the GitHub Release.

To force a specific version, add a `Release-As: X.Y.Z` footer to a commit on
`main`. The version derives from the Conventional-Commit history since the last
tag — so accurate PR titles are what make releases correct.

> Repos that have not yet migrated to release-please may still cut releases with
> `cog bump`; prefer release-please where the
> `.github/workflows/release-please.yml` caller is present.

## Always finish with a PR summary table

At the **end of the task**, output a Markdown table of every pull request you
opened or updated in this session, so the user can open and merge them quickly.
Include the release-please release PR if one is now open. Use real, clickable
URLs:

| PR   | Title                               | Status         | Link                                   |
| ---- | ----------------------------------- | -------------- | -------------------------------------- |
| #123 | `feat(auth): add device-code login` | open           | https://github.com/OWNER/REPO/pull/123 |
| #124 | `chore(main): release 1.4.0`        | open (release) | https://github.com/OWNER/REPO/pull/124 |

If no PR was opened (e.g. a direct push), say so explicitly instead of printing
an empty table.
