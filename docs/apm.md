# 📦 APM Producer Guide

This repository (`ai-toolkit`) is an [**APM (Agent Package Manager)**](https://microsoft.github.io/apm/)
**producer**. Its primitives can be installed directly into any supported AI
coding harness — GitHub Copilot, Claude Code, Cursor, OpenCode, Gemini and
Windsurf — as native, parameterized commands.

> APM is Microsoft's open package manager for _agentic primitives_ (prompts,
> instructions, agents, skills, hooks and MCP servers). See the official
> [producer documentation](https://microsoft.github.io/apm/producer/).

## 🧩 Source of truth: `.apm/`

`.apm/` is the **single source of truth**. Primitives are authored directly
there in native APM format — there is no second "browsable" tree to keep in
sync. The human-facing [`INDEX.md`](../INDEX.md) and the README index are
_generated from_ `.apm/`.

The toolkit ships **prompt primitives**
([`*.prompt.md`](https://microsoft.github.io/apm/producer/author-primitives/prompts/))
under [`.apm/prompts/`](../.apm/prompts/), **instruction primitives**
([`*.instructions.md`](https://microsoft.github.io/apm/producer/author-primitives/instructions-and-agents/))
under [`.apm/instructions/`](../.apm/instructions/), **agent primitives**
([`*.agent.md`](https://microsoft.github.io/apm/producer/author-primitives/instructions-and-agents/))
under [`.apm/agents/`](../.apm/agents/), and **skill primitives**
([`SKILL.md`](https://microsoft.github.io/apm/producer/author-primitives/skills/))
under [`.apm/skills/<name>/`](../.apm/skills/). The structure is built to grow
further into `.apm/hooks/` — just add the folder and author the primitive.

The [Renovate triage and merge skill](../.apm/skills/renovate-triage-and-merge/SKILL.md)
includes a Python standard-library helper and relative `references/` documentation
inside its skill folder, discovered by `includes: auto`. Preserve the complete
folder when deploying a skill, not just `SKILL.md`. It uses an existing `gh`
installation; no new MCP server or global skill installation is required.
Review is read-only until the user confirms an exact plan selection. Its
`dashboards` command also reads scoped Dependency Dashboards, including abandoned
dependency tables and current PR/check correlations. Dashboard recommendations
remain separate from merge approval; release inactivity alone is not proof of
deprecation or a reason to replace a dependency. See the
[dashboard guide](../.apm/skills/renovate-triage-and-merge/references/dashboard.md) and
[testing guide](../.apm/skills/renovate-triage-and-merge/references/testing.md)
for offline fixtures, clean-context scenarios and live-enforcement limitations.

| File / directory                      | Role                                                                          |
| ------------------------------------- | ----------------------------------------------------------------------------- |
| `apm.yml`                             | The producer manifest — package name, version, MCP servers, and what ships.   |
| `.apm/prompts/*.prompt.md`            | The prompt primitives (**source of truth**).                                  |
| `.apm/instructions/*.instructions.md` | The instruction primitives — long-lived behavior rules (**source of truth**). |
| `.apm/agents/*.agent.md`              | The agent primitives — invocable specialist personas (**source of truth**).   |
| `.apm/skills/<name>/SKILL.md`         | The skill primitives — model-invoked procedures (**source of truth**).        |
| `scripts/generate-index.sh`           | Generates `INDEX.md` + README index **from** `.apm/`.                         |
| `INDEX.md` / README index             | Generated, human-browsable catalog.                                           |

### MCP servers

The toolkit also declares **MCP servers** under `dependencies.mcp:` in `apm.yml`.
Unlike file-based primitives these are declarations, not files — `apm install`
materializes them into each detected harness's MCP config:

| Server                               | Type            | Notes                                                                                          |
| ------------------------------------ | --------------- | ---------------------------------------------------------------------------------------------- |
| `io.github.github/github-mcp-server` | registry        | GitHub repos/issues/PRs/Actions; APM injects the auth token per harness.                       |
| `microsoft-learn`                    | remote (`http`) | Trusted Microsoft/Azure docs + code samples at `https://learn.microsoft.com/api/mcp`; no auth. |

### Primitive frontmatter

Each `.apm/prompts/<category>-<name>.prompt.md` carries YAML frontmatter. Two
keys drive everything:

- `description` — APM-preserved; shown in command pickers (required).
- `category` — repo-only; groups the generated index.

Optional repo-only keys (`title`, `tags`, `model`, `platform`, `example`,
`notes`) enrich the index and the future site. Note that APM only preserves a
[fixed set of keys](https://microsoft.github.io/apm/producer/author-primitives/prompts/)
(`description`, `input`, `allowed-tools`, `model`, `argument-hint`) at consumer
install time — extra keys are retained in this repo but dropped from the
installed command. The body after the frontmatter is the prompt, delivered
verbatim to the harness.

The command name is the filename: `coding-code-review-assistant.prompt.md` is
exposed as `coding-code-review-assistant`. The `<category>-` prefix avoids
cross-category collisions in the flat command namespace.

## 🛠️ Generating the index

For AI-assisted changes, run these validation steps in a fresh testing
context/subsession, separate from implementation (see
[contributor guidance](../CONTRIBUTING.md#5-testing-your-prompt)).

```bash
bash tests/validate-prompts.sh   # validate the .apm primitives
bash scripts/generate-index.sh   # regenerate INDEX.md + README index
```

The [Generate Index](../.github/workflows/generate-index.yml) workflow runs this
automatically whenever a primitive changes and commits the refreshed index.

## 📥 How to consume these primitives

Pin a released version and pick your harness with `--target`:

```bash
apm install DevSecNinja/ai-toolkit#v0.1.0 --target copilot
```

> Omit `#vX.Y.Z` to install from the latest default branch, and omit `--target`
> to install into every detected harness. Run `apm targets` to list the
> supported harnesses you can pass to `--target` (`copilot`, `claude`, `cursor`,
> `opencode`, `gemini`, `windsurf`). `apm install` resolves by **GitHub
> repository name** (`ai-toolkit`, matching `apm.yml`'s `name`).

`apm install` deploys each prompt to the targeted harness(es), keeping its
`<category>-<name>` command name:

| Harness        | Where the prompt lands                        | How to invoke        |
| -------------- | --------------------------------------------- | -------------------- |
| GitHub Copilot | `.github/prompts/<category>-<name>.prompt.md` | prompts picker       |
| Claude Code    | `.claude/commands/<category>-<name>.md`       | `/<category>-<name>` |
| Cursor         | `.cursor/commands/<category>-<name>.md`       | `/<category>-<name>` |
| OpenCode       | `.opencode/commands/<category>-<name>.md`     | `/<category>-<name>` |
| Gemini         | `.gemini/commands/<category>-<name>.toml`     | `/<category>-<name>` |
| Windsurf       | `.windsurf/workflows/<category>-<name>.md`    | workflows menu       |

### Untrusted repositories before the first fork

The canonical policy is
[`.apm/instructions/untrusted-repositories.instructions.md`](../.apm/instructions/untrusted-repositories.instructions.md),
with `applyTo: "**"`. Newly forked/cloned third-party repositories and their
dependencies are data-only by default, even when the fork belongs to you.
UI Trust, autopilot, a feature request and a clean static review do not
authorize execution. Review and edit source as data; obtain explicit scoped
approval before running repository/dependency code, setup, hooks or workflows.
Delegated sessions inherit the same boundary. A Python venv is not a security
sandbox. Trusted, execution-authorized work retains normal validation; report
skipped runtime checks honestly for static-only work.

**Distribution is not pre-fork coverage.** Existing APM sync distributes
primitives to opted-in consumer repositories when their selected version is
updated and materialized. A pinned release predating this policy does not
contain it. Merely storing it here, or consuming it in the special
`DevSecNinja/.github` repository, does not make it available before opening
every new fork on every machine. `ai-toolkit` remains the authoring source;
do not create another independently maintained policy in a consumer.

For pre-fork coverage, arrange trusted user-level loading/bootstrap on each
machine **before** opening an untrusted checkout:

1. Obtain the policy from a reviewed toolkit revision using a trusted process,
   not setup code or instructions from the new fork.
2. For **GitHub Copilot CLI**, deploy the policy body into the documented
   `$HOME/.copilot/copilot-instructions.md` user-level instructions, preserving
   existing user rules. Keep it a managed deployment of the canonical source,
   not a second authoring location. `COPILOT_HOME`, if set, replaces
   `$HOME/.copilot`. Modular user instructions and
   `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` are also documented, but path-specific
   instructions apply only when matching files are being worked on; do not
   rely solely on them for authorization before the first file operation.
3. Restart or resume the CLI session after changing instructions and use
   `/instructions` to verify that the intended instructions are discovered
   and enabled. Check for conflicting user/repository instructions: the CLI
   combines them and does not define a general precedence order.
4. Configure restrictive tool permissions separately. Keep Actions disabled on
   newly created forks you control unless separately authorized, verify that
   state before triggering events, and account for upstream PR workflows.
   Stop if the required controls cannot be verified; Git operations must not
   incidentally execute unapproved hooks, filters or workflows.

These loading paths and commands are documented for **Copilot CLI** in
[GitHub's custom-instructions guide](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions).
They are not a claim about desktop-app loading or permission behavior.
Other harnesses need their own documented, verified user-level deployment.
This change ships the source policy and guidance only; it does not install a
bootstrap, alter dotfiles/app settings, disable Actions remotely, or synchronize
machine trust lists, credentials or sessions.

**Instructions are guidance, not a permission-enforcement sandbox.** APM
distribution and static checks cannot guarantee that a model, child session or
host will refuse execution. Use host/tool permission controls as enforcement,
and never treat a repository's instructions or a clean review as authorization.
All commits require 1Password signing; if signing or a required tool is
unavailable or denied, halt rather than bypassing it.

## 🛡️ External primitives: review gate

Every dependency in `apm.yml` is third-party prompt text: the
`github/awesome-copilot` agents and the
[`cloudflare/security-audit-skill`](https://github.com/cloudflare/security-audit-skill)
skill. Every change to them needs the owner's approval, and neither PR in the
flow below may auto-merge.

1. **Renovate bump.** Renovate's custom manager (see
   [`renovate.json5`](../renovate.json5)) bumps the pinned SHA of any
   `owner/repo/<subpath>#<sha>` entry. A package rule matching every
   `apm.yml` dependency re-enables these digest updates (off org-wide) in their
   own PR rather than the weekly batch, turns off the shared auto-merge preset
   and adds the `external-primitives` and `merge: manual` labels. The diff only
   shows a hash. Renovate can't remove the preset's `merge: auto` label, but
   `automerge: false` takes precedence.
2. **Materialize PR.** Merging the bump triggers
   [APM Materialize](../.github/workflows/apm-materialize.yml). It runs
   `apm install`, re-applies the local overrides and opens
   `chore: materialize APM primitives` from `chore/apm-materialize`, labelled
   `apm-sync`, `external-primitives` and `merge: manual`. **Review the
   `.github/agents/` and `.agents/skills/` diff**: this is where upstream text
   changes become visible. Merge it yourself once you're satisfied; close it
   and revert the bump if not.

External skills deploy to `.agents/skills/<name>/`. That folder is gitignored
for our own `.apm/skills/` copies, so each external skill needs a negation in
[`.gitignore`](../.gitignore) to stay in the reviewable snapshot. The whole
folder is committed, including its companion files and scripts.

The labels come from [`.github/labels-base.yaml`](../.github/labels-base.yaml)
(org-wide, synced from `DevSecNinja/.github` by Config Sync) and
[`.github/labels.yaml`](../.github/labels.yaml), applied by
[Label Sync](../.github/workflows/label-sync.yml). `gh pr create` fails on a
missing label, so a label must exist before a workflow uses it.

### Local overrides of vendored agents

`apm install` rewrites every file it deploys, so never hand-edit
`.github/agents/` for a dependency: the next materialize run reverts it (APM
has no override setting). Add the change to
[`apm-overrides.json`](../apm-overrides.json) instead:

```json
{
  "file": ".github/agents/sast-sca-security-analyzer.agent.md",
  "reason": "Pinned to Sonnet 5 (#135).",
  "frontmatter": { "model": "Claude Sonnet 5" }
}
```

Each entry sets top-level frontmatter keys to string values. Only a
single-line value is replaced; if upstream switches a key to a multi-line
value, the script fails and the override needs a manual update.
[`scripts/apply-apm-overrides.py`](../scripts/apply-apm-overrides.py) applies
them, and APM Materialize runs it after `apm install`. Run it yourself after a
local `apm install`. It fails when a file is missing, so drop stale entries
when an agent is removed. `tests/test_apm_overrides.py` fails if a committed
agent doesn't match its override. `apm audit` reports overridden files as
drift from the lockfile, which is expected.

## 🔐 Security primitives: which one to use

The toolkit bundles several security primitives. They overlap, so pick by the
depth of evidence you need:

| Need                                                                                                    | Use                                                                  |
| ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Quick SAST/SCA pass: flag CWE-mapped flaws, vulnerable dependencies or licence risk in a diff or repo   | `sast-sca-security-analyzer` agent                                   |
| Security-focused review of a change against OWASP, Zero Trust and LLM guidance                          | `se-security-reviewer` agent                                         |
| A focused security question, or triage of one suspected issue                                           | `security-audit` skill in **guidance mode** (the default)            |
| Full, verified source audit of a repository, with a coverage ledger and independently verified findings | `security-audit` skill in **full audit mode** (ask for a full audit) |

Use the analyzer for fast feedback; it reports likely issues without proving
them. Use the `security-audit` skill when you need to show a finding is real:
it traces each candidate to a concrete trust-boundary violation, has fresh
agents verify it, and writes `findings.json` and `coverage-ledger.json`, checked
by its bundled `validate-*.cjs` scripts (Node.js, standard library only)
against `report-schema.json`. Full audits are expensive, so keep them for
release reviews, new executable skill helpers, hooks or scripts, and
repositories that consume the toolkit.

**Sandbox.** The skill only runs target code (builds, tests, fixtures) inside
an OS-enforced sandbox with no network, an empty environment, a read-only
target and resource limits. Without one it stays read-only: it inspects source
and records unproven leads as `needs_validation` instead of executing anything.
That matches the
[untrusted-repositories policy](#untrusted-repositories-before-the-first-fork)
and is the expected mode on a work machine. Full audit output goes outside the
target by default (`~/security-audit-skill/<repo>/run-<N>`).

## 🏷️ Versioning

Versioning is driven by [release-please](https://github.com/googleapis/release-please)
via the central `DevSecNinja/.github` reusable workflow
([`.github/workflows/release-please.yml`](../.github/workflows/release-please.yml)).

The flow:

1. Every push to `main` opens or updates a `chore(main): release vX.Y.Z` PR,
   with the next [semver](https://semver.org/) computed from
   [Conventional Commits](https://www.conventionalcommits.org/) since the last tag.
2. Merging that PR bumps `.release-please-manifest.json`, **`apm.yml`'s `version:`
   field** (via the `extra-files` entry in
   [`release-please-config.json`](../release-please-config.json)) and
   `CHANGELOG.md`, then creates the `vX.Y.Z` tag and the GitHub Release.

Because `apm.yml` is bumped _inside the release PR_, the tagged commit always
carries the matching version — so **pinned installs (`@1.2.3`) resolve to a tree
whose `apm.yml` says `1.2.3`**. (This replaces the earlier post-release sync
workflow, which bumped `apm.yml` _after_ tagging and left the tag tree stale.)

> `apm.yml` uses release-please's `yaml` updater (`"jsonpath": "$.version"`), not
> the comment-driven `generic` updater: the APM CLI re-serializes `apm.yml` and
> drops YAML comments, which silently broke the old `# x-release-please-version`
> annotation. The `yaml` updater re-serializes the file too (comments and
> line-folding change), which is fine because `apm.yml` is tool-formatted and
> excluded from yamlfmt/yamllint. `tests/test_release_please_config.py` fails if
> release-please can no longer find the version or it drifts from the manifest.

> **Never add `DevSecNinja/ai-toolkit` to its own `apm.yml`** (for example by
> running the consumer `apm install DevSecNinja/ai-toolkit#vX.Y.Z` here). A
> consumer pinning a newer tag would then also need the older ref of the same
> package, and APM fails with "incompatible immutable requirements" (#207). This
> repo already dogfoods its own primitives through `includes: auto`.
> `tests/test_apm_manifest.py` fails on a self-entry, and the **Check Consumer
> Install** CI job installs each commit into a throwaway consumer project.

To force a specific version, add a `Release-As: X.Y.Z` footer to any commit on
`main`. See the org
[release-please onboarding guide](https://github.com/DevSecNinja/.github/blob/main/docs/release-please-onboarding.md)
for prerequisites (GitHub App install, the `RELEASE_PLEASE_APP_ID` variable and
`RELEASE_PLEASE_APP_PRIVATE_KEY` secret, and the "Allow GitHub Actions to create
and approve pull requests" setting).

## ➕ Adding or updating a primitive

Author the primitive directly under `.apm/` (see
[`PROMPT_TEMPLATE.md`](../PROMPT_TEMPLATE.md) for the prompt frontmatter), then:

```bash
bash tests/validate-prompts.sh   # validate
bash scripts/generate-index.sh   # refresh INDEX.md / README
```

Commit the primitive together with the regenerated index files.
