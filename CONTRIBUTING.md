# 🤝 Contributing to AI Toolkit

Thank you for your interest in contributing! This document provides guidelines for adding your primitives to this toolkit.

## 📋 How to Contribute

### 1. Choose Your Category

Primitives are authored as files under `.apm/prompts/`, named
`<category>-<name>.prompt.md`. The `category` also goes in the file's
frontmatter. Common categories:

- `coding` - Development, debugging, code review
- `writing` - Documentation, content, technical writing
- `analysis` - Data analysis, research, insights
- `productivity` - Workflow, email, task management
- `home-assistant` - Home automation, smart home
- Create a new category if needed!

### 2. Use the Template

Copy [`PROMPT_TEMPLATE.md`](/PROMPT_TEMPLATE.md) and fill in the frontmatter and body:

- **description** (required): Brief overview (1-2 sentences), shown in command pickers
- **category** (required): Used to group the generated index
- **title / tags / model / example / notes** (optional): enrich the index and future site
- **Body**: the complete, ready-to-use prompt (delivered verbatim to the harness)

### 3. File Naming

Name the file `<category>-<name>.prompt.md`, lowercase with hyphens. The base
filename becomes the installed command name:

- ✅ `.apm/prompts/coding-code-review-assistant.prompt.md`
- ✅ `.apm/prompts/writing-api-documentation-generator.prompt.md`
- ❌ `Code Review Assistant.md`
- ❌ `API_docs.md`

### 4. Quality Guidelines

**Good prompts are:**

- ✨ **Clear and Specific** - Leave no ambiguity
- 🎯 **Action-Oriented** - Tell the AI what to do
- 📊 **Well-Structured** - Use numbered lists or sections
- 💡 **Contextual** - Set the right role and expertise
- ♻️ **Reusable** - Work for multiple scenarios

**Avoid:**

- ❌ Vague or generic prompts
- ❌ Overly complex instructions
- ❌ Personal or sensitive information
- ❌ Prompts that encourage harmful content

### 5. Testing Your Prompt

Before submitting:

1. Test the prompt with an AI assistant
2. Verify it produces useful results
3. Refine based on the output
4. Include example use cases from your testing

> **Tip:** Primitives are authored directly under `.apm/`. After adding or
> editing one, regenerate the [index](/docs/apm.md) with
> `bash scripts/generate-index.sh` and commit the updated `INDEX.md` / `README.md`
> alongside your primitive.

## 🪝 Git hooks (lefthook)

This repo uses [lefthook](https://lefthook.dev) to run the same quality gates as
CI before each commit. Inside the **Dev Container / Codespaces** the hooks are
installed for you by `.devcontainer/post-create.sh`. For a local setup, install
the pinned lefthook (see [`.mise.toml`](/.mise.toml)) and wire up the hooks:

```bash
mise install                    # installs the pinned lefthook
mise exec -- lefthook install   # wires up the git hooks
```

What runs on **pre-commit**:

- `bash tests/validate-prompts.sh` — validates every primitive's frontmatter.
- `bash scripts/generate-index.sh` — regenerates `INDEX.md` / `README.md` from
  `.apm/` and re-stages them, so the index never drifts from the primitives.

Run the suite on demand with `mise exec -- lefthook run pre-commit --all-files`.
To bypass hooks in an emergency, use `git commit --no-verify` (please don't make
a habit of it).

## SkillSpector security scans

The [SkillSpector workflow](.github/workflows/skillspector.yml) runs on every
pull request, push to `main`, and manual dispatch. It scans each skill directory
under `.apm/skills/` separately, including supporting files, plus the other
`.apm/` primitive directories, committed `.github/agents/` and `.github/prompts/`,
and the `scripts/git-push-approval/` and `scripts/tool-guardian/` hook implementations.
Add any new hook implementation directories to `EXTRA_ROOTS` in
[`scripts/scan-skills.py`](scripts/scan-skills.py).

**Any individual HIGH or CRITICAL finding fails the check.** LOW and MEDIUM
findings remain visible but do not block it, regardless of the aggregate risk
score. Scanner errors, missing or invalid reports, and incomplete inspection
also fail. Every selected directory is checked for descendant symlinks and
non-regular files without following links; unreadable content fails discovery.
Reports must explicitly contain an empty `scope_exclusions` list: upstream can
call an inspection complete even after excluding files, which is not sufficient
for this gate. No exclusions, findings, or baselines are automatically accepted.

Review findings in the **Actions run summary**: it shows severity, rule, linked
repository file/line, matched evidence, explanations, and analysis limitations.
Findings and counts from incomplete scans remain visible alongside an `ERROR`
status. A dash means no readable report was available, not zero findings.
Long summaries show up to 100 entries per section, with the highest-severity
findings first; full data remains in the artifact.

Repository findings are also exported to **SARIF** and uploaded using
`github/codeql-action/upload-sarif`, even when the severity gate fails. Find them
under **Security > Code scanning**, selecting the relevant branch/PR and the
SkillSpector tool. PR annotations appear only where findings overlap changed
lines. Repository-relative locations and stable rule/severity IDs let GitHub
track findings across runs; the upload action supplies source fingerprints.
SARIF records incomplete execution and diagnostic notifications rather than
presenting partial scans as clean. Severity bands are mapped to GitHub's numeric
security-severity categories, not independently calculated CVSS scores.

The scan job grants only `contents: read` and `security-events: write`; it does
not need a PR-write token or `pull_request_target`. Only the repository scan opts
in to SARIF export. Synthetic smoke findings stay in the artifact; they are
excluded from the Actions summary and never uploaded to Code Scanning.
Uploads require a generated SARIF file and are skipped on cancellation.

The `skillspector-reports` artifact retains raw JSON reports, scanner logs,
`summary.json`, `summary.md`, and `repository/findings.sarif` for 14 days.
Review the evidence before deciding how to remediate a finding; heuristic
matches are not proof of exploitability. Reports may contain source excerpts,
so treat them with the same sensitivity as the scanned content.

The workflow builds [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector)
v2.11.2 from commit `69dcdfb74487d361ba4c811d088cfdea2ff3a9dc` using its upstream
Dockerfile. Building downloads Python dependencies; the scanner revision and
upstream base image are pinned, but the upstream install resolves transitive
dependencies rather than using a frozen lockfile. Scanning then runs as a
non-root user with read-only input, no network, no host credentials, bounded
resources, and a three-minute timeout per target. `--no-llm` disables semantic
analysis; live OSV vulnerability queries and transitive downloads are unavailable
in the network-isolated container. OSV uses the scanner's offline fallback, so a
passing check is not a guarantee that a primitive or its dependencies are safe.

Before scanning the toolkit, the workflow exercises the same image and runner
with benign content, a synthetic HIGH finding, an invalid archive, and a short
timeout. These cases verify the real gate outcomes and saved diagnostics rather
than mocking Docker. Their reports live under `smoke/` in the artifact; the
toolkit's reports live under `repository/`. Smoke failures prevent the toolkit
scan from running, and diagnostics are uploaded even when a check fails.

For a local run on Linux with Docker, build the same pinned upstream image as
the workflow, then run:

```bash
python3 -m unittest discover -s tests -p 'test_skillspector.py'
python3 tests/smoke-skillspector.py --output-dir /tmp/skillspector-smoke
python3 scripts/scan-skills.py --output-dir /tmp/skillspector-reports --sarif
```

Use a new output directory for each run; existing reports are never reused.
No Python packages, scanner service, or reusable scanning skill are added to the
APM package. To enforce this check at merge time, require **Scan AI primitives**
in the repository's branch protection or ruleset.

## 🚀 Submission Process

1. **Fork** this repository
2. **Create** a new branch (`git checkout -b add-my-prompt`)
3. **Add** your prompt file in the correct category
4. **Commit** your changes (`git commit -m 'Add: [prompt name]'`)
5. **Push** to your branch (`git push origin add-my-prompt`)
6. **Open** a Pull Request

## 📝 Pull Request Guidelines

Your PR description should include:

- Brief explanation of what the prompt does
- Why it's useful (use case)
- Any testing or validation you've done

## 🎨 Formatting Standards

- Use proper Markdown formatting
- Include code blocks for the actual prompt
- Keep lines under 100 characters when possible
- Use emoji sparingly but effectively

## ❓ Questions?

Open an issue if you:

- Need help with formatting
- Want to suggest a new category
- Have questions about prompt quality
- Need clarification on guidelines

## 🌟 Recognition

All contributors will be recognized! Your contributions help the entire community create better AI interactions.

---

**Thank you for making this collection better!** 🙏
