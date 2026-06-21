---
description: "This prompt helps rewrite Home Assistant automation aliases and descriptions into clear, non-technical language that anyone in your household can understand, without changing any automation logic."
category: "home-assistant"
title: "Home Assistant Automation Renamer"
platform: "GitHub Copilot in VS Code"
tags: ["home-assistant", "automation", "documentation", "smart-home", "yaml", "refactoring"]
example: |
  Use this prompt when you have a Home Assistant automations.yaml file with technical names like "Trigger: motion_sensor_1 state to 'on'" and want to make them readable for non-technical household members. Simply paste your YAML configuration, and the AI will rewrite the aliases and descriptions in plain English while preserving all functionality.
notes: |
  - Always backup your automations.yaml before making changes
  - The prompt is designed to maintain technical accuracy while improving readability
  - Works best with complete automation blocks rather than partial configurations
  - Consider running this on all automations at once for consistent naming conventions
  - Consider checking in the automations.yaml file with git before you run this prompt so that you can easily see what changed
credits: |
  - Created by: DevSecNinja
---

You are reviewing a Home Assistant automations.yaml file.

For each automation, rewrite:

1. alias (title)
• Max 10 words
• Clear, simple, no technical jargon
• Understandable by someone with no Home Assistant knowledge

2. description
• Max 4 short lines
• Plain, everyday language
• Explain what happens, when, and why, from a user’s perspective
• Avoid technical terms like trigger, entity, service, state, automation

Rules
• Do not change any logic, triggers, conditions, or actions
• Only update alias and description fields
• If a description is missing, add one
• Keep tone friendly and human, as if explaining it to a partner at home
• If the automation could be confusing or surprising, explicitly mention that behavior

Here's my automation YAML:

[Paste your automation YAML here]
