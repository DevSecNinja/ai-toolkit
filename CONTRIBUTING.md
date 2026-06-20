# 🤝 Contributing to GPT Prompts Collection

Thank you for your interest in contributing! This document provides guidelines for adding your prompts to this collection.

## 📋 How to Contribute

### 1. Choose Your Category

Place your prompt in the appropriate folder:

- `prompts/coding/` - Development, debugging, code review
- `prompts/writing/` - Documentation, content, technical writing
- `prompts/analysis/` - Data analysis, research, insights
- `prompts/creative/` - Creative writing, brainstorming
- `prompts/business/` - Strategy, planning, productivity
- Create a new category if needed!

### 2. Use the Template

Copy [`PROMPT_TEMPLATE.md`](/PROMPT_TEMPLATE.md) and fill in:

- **Title**: Clear, descriptive name
- **Description**: Brief overview (1-2 sentences)
- **Prompt**: The complete, ready-to-use prompt
- **Example Use Case**: When to use this prompt
- **Tags**: Relevant keywords for searchability
- **Credits**: Attribution for creators, contributors, or inspiration sources

**Note**: The category is automatically derived from the folder location, so you don't need to include it in the file.

### 3. File Naming

Use lowercase with hyphens:

- ✅ `code-review-assistant.md`
- ✅ `api-documentation-generator.md`
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

> **Tip:** After adding or editing a prompt, regenerate the
> [APM](/docs/apm.md) primitives with `bash scripts/generate-apm-primitives.sh`
> and commit the updated `.apm/prompts/` files alongside your prompt.

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
