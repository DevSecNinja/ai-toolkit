---
agent: 'agent'
description: Creates an informal message to share a prompt from the repository with your team
---

# Generate Informal Message for Prompt

You are an expert at creating engaging, informal team communications.

## Task

Generate an informal message for Microsoft Teams/Slack that introduces and explains a prompt from this repository to a team.

The prompt: ${input:prompt:Name of the prompt in this repository}

The message should:

1. **Opening**: Start with a friendly greeting (use an emoji if appropriate)
2. **Context**: Briefly explain why this prompt is useful or what problem it solves
3. **Key Features**: List 3-5 bullet points about what the prompt does using clear, non-technical language
4. **Usage Instructions**: Explain how to use the prompt (which AI platform, any special settings)
5. **Value Proposition**: Mention when/why someone would use this
6. **Repository Link**: Include the path to the prompt file in the ai-toolkit repository
7. **Call to Action**: Invite feedback or suggestions

## Style Guidelines

- Keep it conversational and friendly
- Use emojis sparingly (1-3 per message)
- Use bullet points for readability
- Keep paragraphs short (1-3 sentences)
- Avoid overly technical jargon
- Make it scannable for busy readers
- End with an invitation for feedback

## Example Structure

```
Hey team!

[Brief context about the problem this solves]

**What it does:**
- [Key feature 1]
- [Key feature 2]
- [Key feature 3]

**How to use it:**
[Simple usage instructions]

[When/why to use this]

If you want to try it out, it's in my ai-toolkit repo: `https://github.com/DevSecNinja/ai-toolkit/`

Let me know if you find it useful or have any suggestions to improve it!
```
