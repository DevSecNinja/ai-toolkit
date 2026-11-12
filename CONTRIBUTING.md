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

First apply the [untrusted-repositories policy](.apm/instructions/untrusted-repositories.instructions.md).
A newly forked/cloned third-party repository, including its setup instructions
and dependencies, is untrusted data until execution is explicitly authorized.
UI Trust or a contribution request does not grant that permission. The commands
below apply to trusted, execution-authorized work; otherwise inspect and edit
statically, disclose skipped runtime checks, and request scoped approval when
execution is needed. Keep Actions disabled on new forks you control unless
separately authorized, and check Git/PR operations for implicit execution.

For AI-assisted work, **all tests and validation must run in a fresh context or
subsession separate from implementation**, including initial runs and reruns
after fixes. A fresh testing task/subagent is sufficient; no orchestration
framework is required. Pause implementation edits while testing. Give the
tester the exact isolated worktree/revision, acceptance criteria, commands and
fixtures. Record the context identifier and actual results. Incorporate fixes,
then start a new tester rather than reusing its conversation. Do not validate
against a primary/shared checkout.

This includes primitive validation, linting, behavioral tests, generated-index
checks and validation run by commit hooks. If hooks execute tests, have a fresh
non-implementation context perform the commit; do not bypass hooks to avoid
separate-context testing.

Before submitting, in the testing context:

1. Test the prompt with an AI assistant
2. Verify it produces useful results
3. Refine based on the output
4. Include example use cases from your testing

Skills with executable helpers also need deterministic behavioral and CLI
contract tests, not just frontmatter linting. Use mocks/fixtures for write
paths; never mutate live third-party systems to exercise a skill. See the
[Renovate skill testing guide](.apm/skills/renovate-triage-and-merge/references/testing.md)
for commands and clean-context behavior scenarios.

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
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_renovate_prs.py'`
  — exercises the Renovate helper with offline GitHub fixtures.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_release_please_config.py'`
  — checks release-please can still find and bump the version in `apm.yml`.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_apm_manifest.py'`
  — checks `apm.yml` doesn't list `ai-toolkit` as its own dependency.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_apm_overrides.py'`
  — checks vendored agents keep their `apm-overrides.json` pins.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_skillspector*.py'`
  — checks the SkillSpector severity gate, reviewed acceptances and report rendering.
- `bash scripts/generate-index.sh` — regenerates `INDEX.md` / `README.md` from
  `.apm/` and re-stages them, so the index never drifts from the primitives.

Within the authorized execution scope, run the suite on demand with
`mise exec -- lefthook run pre-commit --all-files`. Do not bypass required hooks,
signing or tool denials. If hooks or filters would execute unauthorized code,
stop before committing and request scoped approval. All commits must use
1Password signing; halt if it is unavailable.

## 🛡️ Changes to external agents

The `github/awesome-copilot` agents in `apm.yml` are reviewed by the owner and
never auto-merge. A Renovate SHA bump and the follow-up
`chore: materialize APM primitives` PR both carry the `external-primitives`
label; review the `.github/agents/` diff in the materialize PR before merging.
Don't hand-edit a vendored agent: put local changes such as a model pin in
`apm-overrides.json`. See "External primitives: review gate" in
[the APM guide](docs/apm.md).

## 🛡️ SkillSpector security scans

The [SkillSpector workflow](.github/workflows/skillspector.yml) runs a static
[NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) scan of every AI
primitive: each `.apm/skills/` and `.agents/skills/` skill (with its supporting
files), the other `.apm/` and `.agents/` primitives, `.github/agents|prompts|instructions|hooks/`,
and the hook scripts in `scripts/git-push-approval/` and `scripts/tool-guardian/`.
Add new hook script directories to `EXTRA_ROOTS` in
[`scripts/scan-skills.py`](scripts/scan-skills.py).

**When it runs.** The **Scan AI primitives** job reports on every pull request.
It builds and scans only when the PR changes `apm.yml`, `apm.lock.yaml`, any of
the paths above, or the scanner itself; otherwise it passes in seconds. That
includes materialize review PRs (`apm-sync`) and Renovate `github/awesome-copilot`
bumps (`external-primitives`). It also runs on pushes to `main`, weekly and on
demand.

**What fails the check.** Any HIGH or CRITICAL finding that isn't accepted,
scanner errors, missing or malformed reports, scope exclusions and incomplete
inspection all fail it. LOW and MEDIUM findings are reported but never block.
Scans run in a non-root, read-only container with no network, no credentials,
no LLM and bounded resources, with a three-minute timeout per target. A passing
static scan is not a safety guarantee: OSV lookups use the offline fallback.

**Where to read the report.**

- A **PR comment** (updated in place on every re-run) shows counts by severity,
  the top findings with file/line links, accepted items and links to the run.
  Comments are posted only on PRs from this repository; fork PRs get a read-only
  token. If a later push stops changing AI primitives, the comment is marked
  "Not needed" so stale results don't linger.
- The **Actions run summary** lists up to 100 findings and every analysis
  limitation.
- **Security > Code scanning** (tool: SkillSpector) holds every finding as
  SARIF. GitHub ignores SARIF suppressions, so accepted findings are uploaded
  as `<rule>/accepted` notes without a security severity. They stay visible but
  can't trip Code Scanning's own severity threshold.
- The `skillspector-reports` artifact keeps raw JSON, scanner logs, `summary.json`
  and `findings.sarif` for 14 days. Reports can quote source text.

**Approving a finding.** When a HIGH/CRITICAL finding or an inspection
limitation is a reviewed false positive, add it to
[`.github/skillspector-accepted.json`](.github/skillspector-accepted.json) in the
same PR, with the `reason` you accepted it:

- For a finding, copy `path`, `rule`, `severity`, the exact `evidence` and its
  `fingerprint` (when not `null`) from `summary.json` in the
  `skillspector-reports` artifact. The fingerprint covers the full match, because
  `evidence` can be a 200-character preview. Findings inside an
  inspected archive use the `<archive>!/<member>` path that SkillSpector reports;
  their links and Code Scanning alerts point at the archive file.
- For a limitation, copy `path`, `reason_code` and its `analyzers` list (omit it
  when the limitation names no analyzers).

Each entry accepts exactly one occurrence, so a repeated finding needs one entry
per occurrence. Line numbers aren't part of the match, so unrelated edits don't
invalidate approvals. New, escalated or changed findings, and limitations that
degrade another analyzer, still block. Entries that no longer match anything
fail the check, so remove them when the content changes. Never accept a finding
just to get a green check.

**Making it a required check.** In **Settings > Rules > Rulesets**, add a status
check rule for the default branch requiring **Scan AI primitives** (source:
GitHub Actions). Because the job always reports, PRs that don't touch AI
primitives aren't left waiting. Don't require **Post SkillSpector report**: it
only posts on same-repository PRs that were scanned, and passes as a no-op
otherwise. First, stop the
[Generate Index workflow](.github/workflows/generate-index.yml) from pushing
`[skip ci]` commits to PR branches with `GITHUB_TOKEN`. Those commits don't
trigger CI, so a required check would stay pending on the new head.

**Upgrading SkillSpector.** The workflow builds the upstream Dockerfile from a
commit SHA with a `# renovate: datasource=github-tags depName=NVIDIA/SkillSpector`
comment. Building resolves upstream's Python dependencies, which aren't frozen.
Review the release notes and any new findings before merging a bump.

**Run it locally** on Linux with Docker:

```bash
git clone https://github.com/NVIDIA/SkillSpector /tmp/skillspector
git -C /tmp/skillspector checkout <sha-from-the-workflow>
docker build --tag skillspector-ci /tmp/skillspector
python3 tests/smoke-skillspector.py --output-dir /tmp/skillspector-smoke
python3 scripts/scan-skills.py --output-dir /tmp/skillspector-reports
python3 scripts/skillspector-report.py /tmp/skillspector-reports/summary.json --markdown /tmp/report.md
```

Use a new output directory for each run; existing reports are never reused.

## 🚀 Submission Process

1. **Fork** this repository
2. **Create** a new branch (`git checkout -b add-my-prompt`)
3. **Add** your prompt file in the correct category
4. **Commit** your changes with the configured 1Password signer
   (`git commit -S -m 'Add: [prompt name]'`). Confirm Git's effective signer
   configuration and intended signing key first; halt if 1Password is
   unavailable or the signer cannot be confirmed.
5. **Verify** the commit (`git verify-commit HEAD`) before pushing. Confirm the
   signature matches the intended key and the commit was created through the
   confirmed 1Password signer; a valid signature alone does not identify the
   signing application. Halt if verification fails or either check cannot be
   confirmed.
6. **Push** to your branch (`git push origin add-my-prompt`) only after the
   signing and verification checks succeed.
7. **Open** a Pull Request

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
