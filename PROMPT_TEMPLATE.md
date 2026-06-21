---
# APM prompt primitive — authored directly under .apm/prompts/<category>-<name>.prompt.md
# `description` and `category` are required. Other keys are optional and enrich
# the generated index / future site.
description: "Brief 1-2 sentence summary of what this prompt does (shown in command pickers)."
category: "coding"            # groups the index; matches the filename prefix
title: "Prompt Title"          # human-readable title for the index
model: "claude-opus-4-7"       # optional: preferred model slug (APM-preserved)
platform: "GitHub Copilot"     # optional: platform it was designed/tested for
tags: ["tag1", "tag2", "tag3"]
example: |
  Describe when and how to use this prompt effectively.
notes: |
  Any additional context, variations, or tips for using this prompt.
---

[Your complete prompt goes here. Everything after the frontmatter is delivered
verbatim to the harness. Be specific and clear about:
- The role or expertise the AI should take
- The task or output expected
- Any specific format or structure requirements
- Guidelines or constraints]
