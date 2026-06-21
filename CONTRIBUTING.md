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
