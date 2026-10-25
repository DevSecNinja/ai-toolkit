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
- `bash scripts/generate-index.sh` — regenerates `INDEX.md` / `README.md` from
  `.apm/` and re-stages them, so the index never drifts from the primitives.

Within the authorized execution scope, run the suite on demand with
`mise exec -- lefthook run pre-commit --all-files`. Do not bypass required hooks,
signing or tool denials. If hooks or filters would execute unauthorized code,
stop before committing and request scoped approval. All commits must use
1Password signing; halt if it is unavailable.

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
