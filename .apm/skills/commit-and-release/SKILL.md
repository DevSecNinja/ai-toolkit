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

### 3. Draft and validate the message

Write a clear, accurate Conventional Commit subject from the diff and validate it:

```sh
mise exec -- cog verify "fix(parser): handle empty frontmatter"
```

Fix and re-run until it exits 0. Don't stop to ask the user to confirm the
wording — just choose a correct, descriptive message. (If the change is genuinely
ambiguous about intent — e.g. `feat` vs `fix` — ask only that.)

### 4. Run lint/tests before committing

```sh
mise exec -- lefthook run pre-commit
```

Plus the repo's own test command, if any. If anything fails, **stop and report**
— do not commit or open a PR with known-failing checks.

### 5. Commit and push

```sh
git commit -m "<message>"
git push
```

The `commit-msg` hook re-runs `cog verify` automatically; both hooks must pass.

## Opening a pull request

- Set the **PR title to a valid Conventional Commit subject** (see above) — this
  is the release-critical field.
- Update documentation in the **same PR** as the code it describes.
- Keep the PR focused on one logical change.
- Ensure lint/tests pass before marking it ready.
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

| PR | Title | Status | Link |
|----|-------|--------|------|
| #123 | `feat(auth): add device-code login` | open | https://github.com/OWNER/REPO/pull/123 |
| #124 | `chore(main): release 1.4.0` | open (release) | https://github.com/OWNER/REPO/pull/124 |

If no PR was opened (e.g. a direct push), say so explicitly instead of printing
an empty table.
