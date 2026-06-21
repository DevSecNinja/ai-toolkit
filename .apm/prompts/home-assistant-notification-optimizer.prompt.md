---
description: "Optimizes Home Assistant automation notifications for Apple Watch and iPhone by rewriting titles and messages to be concise, glanceable, and follow Apple's notification best practices."
category: "home-assistant"
title: "Home Assistant Notification Optimizer"
tags: ["home-assistant", "notifications", "apple-watch", "automation", "yaml", "smart-home", "ios"]
example: |
  Use this prompt when your Home Assistant automations.yaml file has grown organically and notifications have become verbose, technical, or poorly formatted for mobile devices. Ideal for users who rely on Apple Watch or iPhone lock screen notifications and want clearer, more actionable alerts without manually rewriting each automation.
notes: |
  - Always back up your automations.yaml before running this prompt
  - The prompt instructs the AI to run `ha core check` after making changes to validate syntax
  - Focus is on notify.* service calls only; all other automation logic remains unchanged
  - Best used with AI assistants that have direct file editing capabilities in your workspace
  - Can be adapted for Android or other notification platforms by modifying the platform-specific guidelines
credits: |
  - Created by: DevSecNinja
  - Follows [Apple Human Interface Guidelines for Notifications](https://developer.apple.com/design/human-interface-guidelines/notifications)
  - Designed for Home Assistant YAML automation files
---

You are reviewing the Home Assistant automations.yaml file.

For each automation, inspect all notify.* actions.
For every notification, rewrite (if not already optimal):

title
• Start with a single, relevant emoji
• Max 6 words
• Clear and glanceable on an Apple Watch
• No technical jargon, IDs, or automation language
• Capitalize like a sentence, not ALL CAPS

message
• Max 2 short lines
• Optimized for Apple Watch and iPhone lock screen
• Plain, everyday language
• Immediately understandable without context
• State what happened and what the user should do (if anything)
• Avoid unnecessary details, timestamps, or system wording

Rules
• Do NOT change logic, triggers, conditions, or non-notification actions
• Do NOT change formatting since Home Assistant is sensitive to indentation and structure
• Only update title and message fields inside notify.* actions
• If a notification has no title, add one
• If a message is too long, simplify it aggressively
• Assume the notification may arrive while the user is busy or distracted
• Tone should be calm, helpful, and human — like a considerate tap on the wrist
• Follow Apple notification best practices: concise, actionable, and respectful of attention. [Source](https://developer.apple.com/design/human-interface-guidelines/notifications)
• If the notification repeats or can be noisy, make that clear in the wording
• Must run `ha core check` after making changes to ensure no syntax errors were introduced.
