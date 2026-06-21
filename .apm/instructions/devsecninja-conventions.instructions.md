---
description: "DevSecNinja org-wide engineering conventions for AI agents: Conventional-Commit PR titles, pre-PR checks, docs, and no force-push."
applyTo: "**"
---

# DevSecNinja Engineering Conventions

Org-wide rules for every DevSecNinja repository. A repository's own
`.github/copilot-instructions.md` may add repo-specific detail on top of these.

## Pull requests

- PR titles MUST follow [Conventional Commits](https://www.conventionalcommits.org):
  `type(scope): description`. PRs are **squash-merged**, so the PR title becomes
  the commit on `main` and feeds release-please's changelog and version bump —
  get it right even if the in-PR commits are informal.
  - Types: `feat`, `fix`, `docs`, `ci`, `chore`, `refactor`, `perf`, `test`.
  - Use `feat!:` / `fix!:` (or a `BREAKING CHANGE:` footer) for breaking changes.
    A new required input to a centralized/reusable workflow IS breaking, so
    Renovate does not automerge a change that breaks downstream CI.
- Run lint and tests before opening a PR and fix anything that fails:
  `mise exec -- lefthook run pre-commit` plus the repo's test command. Never open
  a PR with known-failing checks.
- Update documentation in the same PR as the code it describes — READMEs, inline
  docs, and generated indexes. Don't defer docs to a follow-up.
- Keep PRs focused: one logical change per PR.
- Never force-push to `main` or any shared/protected branch. All changes land via
  PR through normal CI; branch protection is always respected.

## Coding standards

- Commit messages follow Conventional Commits (same types as above). In-PR
  commits may be informal; the PR title is authoritative.
- YAML: 2-space indent, start with `---`, format with yamlfmt, lint with yamllint.
- Markdown: format with dprint, 4-space indent.
- Shell: Bash dialect, 4-space indent, lint with shellcheck, format with shfmt.
- GitHub Actions: pin action refs to full commit SHAs with a version comment,
  e.g. `uses: actions/checkout@<sha> # v4.2.0`. Add a `# renovate:` comment where
  applicable so Renovate can bump it.
- Reusable workflows in `DevSecNinja/.github` MUST NOT default package/tool
  version inputs — declare them `required: true` so the caller owns the version.
- Security: never commit plaintext secrets. Use SOPS, Vault, or GitHub Secrets.

## Tooling and files

- Tools are managed by [mise](https://mise.jdx.dev/) (`.mise.toml`); run them via
  `mise exec -- <tool>`. Run `mise exec -- lefthook run pre-commit` before committing.
- LF line endings; always end files with a trailing newline.
- Don't hand-edit generated files (`CHANGELOG.md`, release-please manifests,
  lockfiles) — regenerate them via their owning tool.
