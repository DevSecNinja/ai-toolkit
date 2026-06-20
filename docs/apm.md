# 📦 APM Producer Guide

This repository is an [**APM (Agent Package Manager)**](https://microsoft.github.io/apm/)
**producer**. That means the prompts in this collection can be installed
directly into any supported AI coding harness — GitHub Copilot, Claude Code,
Cursor, OpenCode, Gemini and Windsurf — as native, parameterized commands.

> APM is Microsoft's open package manager for *agentic primitives* (prompts,
> instructions, agents, skills, hooks and MCP servers). See the official
> [producer documentation](https://microsoft.github.io/apm/producer/).

## 🧩 What artifacts this repo produces

The browsable [`prompts/`](../prompts/) collection is the single source of
truth. From it, this repo produces **APM prompt primitives** — one
[`*.prompt.md`](https://microsoft.github.io/apm/producer/author-primitives/prompts/)
file per prompt — under [`.apm/prompts/`](../.apm/prompts/).

| File / directory | Role |
|------------------|------|
| `apm.yml` | The producer manifest — declares the package name, version and what ships. |
| `.apm/prompts/*.prompt.md` | The installable prompt primitives (generated artifacts). |
| `prompts/**/*.md` | Human-browsable source collection (single source of truth). |
| `scripts/generate-apm-primitives.sh` | Transforms `prompts/**` into `.apm/prompts/` primitives. |

Each generated primitive is named `<category>-<name>.prompt.md`, so
`prompts/coding/code-review-assistant.md` becomes
`.apm/prompts/coding-code-review-assistant.prompt.md` and is exposed to
consumers as the `coding-code-review-assistant` command.

## 🛠️ How artifacts are produced

The primitives are generated deterministically, the same way `INDEX.md` and the
`README.md` index are generated:

```bash
bash scripts/generate-apm-primitives.sh
```

The script:

1. Scans every `prompts/<category>/<name>.md` file.
2. Extracts the title, the `## Description`, and the `## Prompt` code block.
3. Writes an APM prompt primitive with a `description` frontmatter key and the
   prompt body to `.apm/prompts/<category>-<name>.prompt.md`.

The generated files are committed to the repository, and the
[Generate Prompt Index](../.github/workflows/generate-index.yml) workflow keeps
them in sync whenever a prompt changes.

## 📥 How to consume these prompts

In any repository where you use a supported harness, install this package with
the [APM CLI](https://microsoft.github.io/apm/getting-started/installation/):

```bash
apm install DevSecNinja/gpt-prompts
```

`apm install` deploys each prompt to every detected harness. Each prompt keeps
its `<category>-<name>` command name (e.g. `coding-code-review-assistant`), for
example:

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
workflow writes the release tag (with any leading `v` stripped) into `apm.yml`
and commits it back to `main`, so the APM package version always matches the
latest release. To bump the version, cut a GitHub release.

## ➕ Adding or updating a prompt

Nothing changes about the normal contribution flow described in
[`CONTRIBUTING.md`](../CONTRIBUTING.md). Add or edit a file under
`prompts/<category>/` and regenerate the artifacts:

```bash
bash tests/validate-prompts.sh          # validate the source prompt
bash scripts/generate-index.sh          # update INDEX.md / README.md
bash scripts/generate-apm-primitives.sh # update .apm/prompts/ primitives
```

Commit the prompt together with the regenerated `.apm/prompts/` files.
