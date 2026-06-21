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

Today the toolkit ships **prompt primitives**
([`*.prompt.md`](https://microsoft.github.io/apm/producer/author-primitives/prompts/))
under [`.apm/prompts/`](../.apm/prompts/). The structure is built to grow into
`.apm/instructions/`, `.apm/agents/`, `.apm/hooks/` and `.apm/skills/` — just add
the folder and author the primitive.

| File / directory | Role |
|------------------|------|
| `apm.yml` | The producer manifest — package name, version and what ships. |
| `.apm/prompts/*.prompt.md` | The prompt primitives (**source of truth**). |
| `scripts/generate-index.sh` | Generates `INDEX.md` + README index **from** `.apm/`. |
| `INDEX.md` / README index | Generated, human-browsable catalog. |

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

```bash
apm install DevSecNinja/ai-toolkit
```

> **Note:** `apm install <owner>/<repo>` resolves by **GitHub repository name**.
> For `DevSecNinja/ai-toolkit` to work, the GitHub repo must be named
> `ai-toolkit` (matching `apm.yml`'s `name`). Until the repo is renamed, install
> from the current repository name.

`apm install` deploys each prompt to every detected harness, keeping its
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

The `version` field in `apm.yml` tracks the repository's GitHub releases. When a
release is published, the [Sync APM Version](../.github/workflows/sync-apm-version.yml)
workflow writes the release tag (leading `v` stripped) into `apm.yml` and commits
it back to `main`.

> **Caveat:** the bump lands on `main` *after* the release is cut, so the tag's
> tree still carries the previous version. `apm install` from `main`/latest is
> always correct; if you rely on **pinned** installs (`@1.2.3`), bump `apm.yml`
> *before* tagging — e.g. via `workflow_dispatch` on the Sync APM Version
> workflow — so the tagged commit already holds the right version.

## ➕ Adding or updating a primitive

Author the primitive directly under `.apm/` (see
[`PROMPT_TEMPLATE.md`](../PROMPT_TEMPLATE.md) for the prompt frontmatter), then:

```bash
bash tests/validate-prompts.sh   # validate
bash scripts/generate-index.sh   # refresh INDEX.md / README
```

Commit the primitive together with the regenerated index files.
