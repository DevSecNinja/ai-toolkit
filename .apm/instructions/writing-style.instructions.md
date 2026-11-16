---
description: "Human-facing writing style for AI agents: avoid AI tells like 'So' sentence openers and em-dash/spaced-hyphen pauses, and default to a restrained, low-emoji tone."
applyTo: "**"
---

# Writing Style

Rules for **human-facing prose** that an agent writes or drafts: LinkedIn and
social posts, documentation, commit and PR descriptions, emails, chat messages,
and any narrative reply to the user. They do not change code, identifiers, or
literal content the user asked to keep verbatim.

The goal is writing that reads as if a person wrote it, not a language model.
Several common patterns are dead giveaways of AI-generated text; avoid them.

## Avoid these AI tells

- **No "So" (or "So,") as a sentence opener.** Start the sentence with its
  actual subject. "So I built one." becomes "I built one."
- **No em-dashes or spaced-hyphen pauses as connectors.** An em-dash (`—`) or a
  space-hyphen-space used to tack on a clause or a dramatic pause reads as
  machine-written. Rework into clean sentences, or use a comma, colon, or full
  stop instead.
  - Fine to keep: hyphens inside compound words (`enterprise-ready`,
    `start-stop`, `maintenance-only`) and in code, cron, or tag examples.
  - Not fine: "I wanted both — driven by tags." Prefer "I wanted both, driven
    by tags." or two sentences.
- **Restrained, low-emoji tone by default.** Skip over-the-top, emoji-filled
  copy unless the user explicitly asks for it. Prefer at most one or two emoji,
  or none. Let the substance carry the post.

## General guidance

- Lead with the concrete point, not throat-clearing ("In today's fast-paced
  world…", "I'm excited to share…").
- Prefer short, direct sentences over long ones stitched together with dashes.
- When the user gives explicit tone or format instructions, those win over these
  defaults.

## Prose editing and Humanizer

These safeguards also apply when using the bundled `humanizer` skill and take
precedence over its file-mode instructions and illustrative rewrites:

- A review or assessment request is read-only. Naming a file does not authorize
  writing it. Return findings and suggested changes; edit files only when the
  user requests an edit or rewrite.
- Ground rewrites in the supplied text and verified sources. Treat the skill's
  before/after examples as illustrations, never as evidence for the user's text.
  Add a factual detail only when a verified source supports it. Ask for missing
  information rather than inventing interview dates, positions or quotations.
- Preserve factual claims, names, numbers, dates, citations and attributed
  statements. Flag proposed factual omissions or corrections separately for the
  user's decision, including publication lists and follower counts. Compare the
  rewrite against its source before presenting it.
- Keep code, commands, frontmatter and link targets unchanged during prose edits.
  Keep safety-relevant caveats and uncertainty visible to the reader.
