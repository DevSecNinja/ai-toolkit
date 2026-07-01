# Copilot Agent Instructions for AI Toolkit

## Repository Overview

This is a **content repository** that ships a curated, multi-harness toolkit of
**APM (Agent Package Manager) primitives**. It's a small, lightweight project
focused on Markdown primitives with bash automation scripts.

**Repository Type**: APM producer / content repository
**Primary Language**: Markdown (with YAML frontmatter)
**Automation**: Bash scripts
**No Dependencies**: No package.json, requirements.txt, or external build deps

**Producer vs. consumer**: `ai-toolkit` is the **producer** — the single source
of truth where primitives are authored. Other repos (including
`DevSecNinja/.github`) are **consumers** that install these primitives via
`apm install`. Org-wide primitives (e.g. the `devsecninja-conventions`
instruction and `commit-and-release` skill) are authored **here** and consumed
elsewhere — never the reverse. Do not move producer primitives into a consumer
repo.

**Do not onboard this repo as an APM consumer (no self-consumption).** The
`DevSecNinja/.github` APM sync pipeline (`apm-materialize.yml` + a Renovate
custom manager) is for **consumer** repos that pull _from_ this package. Running
it here would make `ai-toolkit` consume itself: pure duplication of `.apm/`, and
`apm install --target copilot` writes prompts into `.github/prompts/`, colliding
with `tests/validate-prompts.sh` and `scripts/generate-index.sh` (which scan that
directory). Revisit only if the org-wide primitives are split into a separate
producer package that both this repo and consumers pull.

## Source of truth: `.apm/`

`.apm/` is the **single source of truth**. Primitives are authored directly there
in native APM format. `INDEX.md` and the README index are **generated from**
`.apm/` — never hand-edit them. There is no separate browsable `prompts/` tree.

## Project Structure

```
/workspaces/ai-toolkit/
├── .apm/
│   └── prompts/                # Prompt primitives (SOURCE OF TRUTH)
│       └── <category>-<name>.prompt.md
├── apm.yml                     # APM producer manifest (name, version, includes)
├── release-please-config.json  # release-please config (bumps apm.yml via extra-files)
├── .release-please-manifest.json
├── .github/
│   ├── prompts/                # Repo-local Copilot prompts (not shipped in the package)
│   └── workflows/              # CI/CD automation
├── scripts/
│   └── generate-index.sh       # Generates INDEX.md + README index FROM .apm/
├── tests/
│   └── validate-prompts.sh     # Validates .apm/ primitives + .github/prompts
├── docs/apm.md                 # APM producer guide
├── README.md                   # Main docs (contains auto-generated index)
├── INDEX.md                    # Standalone index (auto-generated)
├── PROMPT_TEMPLATE.md          # Frontmatter template for new primitives
└── CONTRIBUTING.md             # Contribution guidelines
```

Future primitive types live alongside prompts: `.apm/instructions/`,
`.apm/agents/`, `.apm/hooks/`, `.apm/skills/`.

## Primitive format

Each `.apm/prompts/<category>-<name>.prompt.md` is YAML frontmatter + a body:

- `description` (**required**) — APM-preserved; shown in command pickers.
- `category` (**required**) — groups the generated index.
- Optional repo-only keys: `title`, `tags`, `model`, `platform`, `example`, `notes`.
- Body after the frontmatter = the prompt, delivered verbatim to the harness.

The base filename is the installed command name, so the `<category>-` prefix
avoids collisions in the flat command namespace.

## Build & Validation Commands

```bash
bash tests/validate-prompts.sh   # validate primitives (must pass; ~1s)
bash scripts/generate-index.sh   # regenerate INDEX.md + README index (~1s)
```

- `validate-prompts.sh` checks each `.apm/prompts/*.prompt.md` has frontmatter,
  a `description`, a `category`, and a non-empty body.
- `generate-index.sh` reads the frontmatter, groups by `category`, writes
  `INDEX.md`, and replaces the block between `<!-- INDEX_START -->` and
  `<!-- INDEX_END -->` in `README.md`.

## CI/CD Workflows

- **Generate Index** (`generate-index.yml`): on changes to `.apm/prompts/**` or
  `.github/prompts/**`, runs `generate-index.sh` and auto-commits `INDEX.md` /
  `README.md` (`[skip ci]`).
- **Markdown Validation** (`markdown-validation.yml`): markdownlint + link check
  (informational) and `validate-prompts.sh` (MUST pass).
- **Release Please** (`release-please.yml`): on push to `main` (or
  `workflow_dispatch`), calls the central `DevSecNinja/.github` reusable workflow
  to open/update a release PR. Merging it bumps `apm.yml` (via the config's
  `extra-files`) + `CHANGELOG.md`, tags `vX.Y.Z`, and publishes the GitHub Release.
- **Welcome** (`welcome.yml`): greets first-time contributors.

## Adding or modifying a primitive

1. Create/edit `.apm/prompts/<category>-<name>.prompt.md` (see `PROMPT_TEMPLATE.md`).
   Use `lowercase-with-hyphens`; include required `description` + `category`.
2. `bash tests/validate-prompts.sh`
3. `bash scripts/generate-index.sh`
4. Commit the primitive together with the regenerated `INDEX.md` / `README.md`.

**Common mistake**: forgetting to commit the regenerated `INDEX.md` / `README.md`.

## Markdown Configuration

### Linting Rules (`.markdownlint.json`)

- **MD013**: Line length - DISABLED
- **MD033**: HTML tags - DISABLED
- **MD041**: First line heading - DISABLED
- **MD024**: Duplicate headings - Siblings only

### Link Checking (`.markdown-link-check.json`)

- Ignores localhost links
- Accepts status codes: 200, 206, 301, 302, 307, 308, 403, 405, 999

## Critical Notes for Agents

1. **`.apm/` is the source of truth** — author primitives there; never hand-edit
   `INDEX.md` or the generated README block.
2. **No compilation required** — only bash scripts; both run in ~1s.
3. **`description` and `category` are required** in every primitive's frontmatter.
4. **Bash scripts are executable** — run as `bash script-name.sh`.
5. **No background processes** — all commands complete immediately.

## Coding Style Preferences

- **Avoid inline scripts**: don't bury logic in pipeline YAML.
- **Use external scripts**: separate files (e.g., `.devcontainer/post-create.sh`)
  for readability, diffs, testing and reuse.
- **Make scripts executable**: `chmod +x`.

## Environment

- **OS**: Ubuntu (dev container)
- **Shell**: Bash
- **Standard tools**: grep, awk, sed, find, python3
- **No additional tools required**: No npm, pip, bundle, make, etc.
