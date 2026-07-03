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

## Reusing centralized artifacts

The `DevSecNinja/.github` repository is the central home for shared CI/CD
building blocks — reusable workflows, composite actions, Renovate presets, issue
and PR templates, labeler configs, and other org-wide config. Before authoring
any new workflow, composite action, or config file, you MUST check there first
and prefer reuse over duplication.

- **Check first (mandatory):** before creating a new workflow or config artifact,
  search `DevSecNinja/.github` for existing functionality that already does what
  you need. If a reusable workflow, composite action, or shared preset fits, call
  or extend it instead of writing a local copy.
- **No similar artifact? Expand an existing one.** If nothing matches but a
  related central artifact is close, prefer extending that artifact (e.g. add an
  input, a job, or an option) over creating a parallel one — provided the change
  stays backward-compatible. Remember a new **required** input to a reusable
  workflow is a breaking change (`feat!:`); add new inputs with safe defaults.
- **Can't extend? Propose implementing it centrally.** If the functionality is
  genuinely new and would add value for other repos too, suggest implementing it
  in `DevSecNinja/.github` rather than locally, so every repo can consume it.
  Call this out explicitly in the PR description and link the proposed central
  change.
- **Only build locally as a last resort.** Create a repo-local workflow or config
  only when the need is truly repo-specific and has no reuse value elsewhere.
  Document why it isn't centralized.

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
- Dependencies: when adding or updating a package, check for and use the latest
  stable release rather than scaffolding on — or leaving deps at — outdated
  versions. Let Renovate keep them current thereafter.
- Dependency provenance: prefer first-party/official sources (the vendor's own
  package or feed) over third-party or community-maintained wrappers. Before
  introducing a community-owned package, devcontainer feature, or action,
  evaluate its trustworthiness (maintainer, adoption, activity); when in doubt,
  install from the official source (e.g. via a script) instead.
- Pin versions precisely: pin every external dependency, tool, and action to an
  exact version — prefer a full commit SHA where the ecosystem supports it (e.g.
  GitHub Actions) — and let Renovate manage the bumps. Avoid floating refs like
  `latest`, `main`, or unpinned ranges. Consuming repos pin the tool versions
  they use (e.g. in `mise.toml`) rather than relying on a central default.
- Security: never commit plaintext secrets. Use SOPS, Vault, or GitHub Secrets.

## Tooling and files

- Tools are managed by [mise](https://mise.jdx.dev/) (`.mise.toml`); run them via
  `mise exec -- <tool>`. Run `mise exec -- lefthook run pre-commit` before committing.
- LF line endings; always end files with a trailing newline.
- Don't hand-edit generated files (`CHANGELOG.md`, release-please manifests,
  lockfiles) — regenerate them via their owning tool.
