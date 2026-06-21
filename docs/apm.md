# 📦 APM Producer Guide

This repository (`ai-toolkit`) is an [**APM (Agent Package Manager)**](https://microsoft.github.io/apm/)
**producer**. Its primitives can be installed directly into any supported AI
coding harness — GitHub Copilot, Claude Code, Cursor, OpenCode, Gemini and
Windsurf — as native, parameterized commands.

> APM is Microsoft's open package manager for *agentic primitives* (prompts,
> instructions, agents, skills, hooks and MCP servers). See the official
> [producer documentation](https://microsoft.github.io/apm/producer/).

## 🧩 Source of truth: `.apm/`

`.apm/` is the **single source of truth**. Primitives are authored directly
there in native APM format — there is no second "browsable" tree to keep in
sync. The human-facing [`INDEX.md`](../INDEX.md) and the README index are
*generated from* `.apm/`.

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

| File / directory | Role |
|------------------|------|
| `apm.yml` | The producer manifest — package name, version, MCP servers, and what ships. |
| `.apm/prompts/*.prompt.md` | The prompt primitives (**source of truth**). |
| `.apm/instructions/*.instructions.md` | The instruction primitives — long-lived behavior rules (**source of truth**). |
| `.apm/agents/*.agent.md` | The agent primitives — invocable specialist personas (**source of truth**). |
| `.apm/skills/<name>/SKILL.md` | The skill primitives — model-invoked procedures (**source of truth**). |
| `scripts/generate-index.sh` | Generates `INDEX.md` + README index **from** `.apm/`. |
| `INDEX.md` / README index | Generated, human-browsable catalog. |

### MCP servers

The toolkit also declares **MCP servers** under `dependencies.mcp:` in `apm.yml`.
Unlike file-based primitives these are declarations, not files — `apm install`
materializes them into each detected harness's MCP config:

| Server | Type | Notes |
|--------|------|-------|
| `io.github.github/github-mcp-server` | registry | GitHub repos/issues/PRs/Actions; APM injects the auth token per harness. |
| `microsoft-learn` | remote (`http`) | Trusted Microsoft/Azure docs + code samples at `https://learn.microsoft.com/api/mcp`; no auth. |

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

| Harness | Where the prompt lands | How to invoke |
|---------|------------------------|---------------|
| GitHub Copilot | `.github/prompts/<category>-<name>.prompt.md` | prompts picker |
| Claude Code | `.claude/commands/<category>-<name>.md` | `/<category>-<name>` |
| Cursor | `.cursor/commands/<category>-<name>.md` | `/<category>-<name>` |
| OpenCode | `.opencode/commands/<category>-<name>.md` | `/<category>-<name>` |
| Gemini | `.gemini/commands/<category>-<name>.toml` | `/<category>-<name>` |
| Windsurf | `.windsurf/workflows/<category>-<name>.md` | workflows menu |

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

Because `apm.yml` is bumped *inside the release PR*, the tagged commit always
carries the matching version — so **pinned installs (`@1.2.3`) resolve to a tree
whose `apm.yml` says `1.2.3`**. (This replaces the earlier post-release sync
workflow, which bumped `apm.yml` *after* tagging and left the tag tree stale.)

> The `# x-release-please-version` annotation on the `version:` line in `apm.yml`
> is what the generic updater keys off — keep it intact.

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
