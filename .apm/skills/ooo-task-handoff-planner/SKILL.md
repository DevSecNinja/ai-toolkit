---
name: ooo-task-handoff-planner
description: |
  Scan recent email to build an out-of-office handoff plan: extract
  tasks that need action before, during, or after a leave window and
  group them into prioritized "do now", "delegate", and "defer" buckets
  with delegates and deadlines. Use when the user says "plan my OOO
  handoff", "I'm going on leave/vacation", "wrap up before I'm away",
  "what do I need to hand off", "prep for out of office", or pastes an
  automatic-reply message and asks what to close out. Do NOT use for
  setting the Outlook automatic-reply itself, for general task
  management unrelated to a leave window, or for sending any mail.
cowork:
  category: productivity
  icon: Airplane
targets:
  - copilot-cowork
---

# OOO Task Handoff Planner

Build a compact, prioritized handoff plan from recent email so the user
can go out of office with zero loose ends. **Read-only: never send,
reply, delegate, or move anything — only produce the plan.**

## Step 1 — Establish the leave window and delegates

- Determine the **out-of-office window** (start and end dates). Take it
  from the user's request; if missing, ask for it before proceeding.
- If the user pasted their **automatic-reply text**, use it to identify
  named delegates/owners and key topics. If no delegate is named for a
  task, fall back to the user's manager.

## Step 2 — Scope and recency rules (must follow)

- Use items from **email only**.
- Include items received/created between **~15 days before today** and
  the **end of the OOO window**.
- Ignore older items unless there is new activity (reply, mention,
  forward, comment, or meeting follow-up referencing them).

## Step 3 — Task extraction rules

- Identify emails that assign the user a task (reply, review, approve,
  fix, ship, follow up, provide input).
- Capture unresolved issues, risks, blockers, or escalations needing
  handoff.
- Capture work the user initiated that needs closure or a status update
  before the OOO.
- Prioritize: deadlines before/during the OOO window, items from
  manager/leadership, and items blocking others or marked urgent.
- **De-dupe** related threads into one synthesized task.
- **Do not invent** tasks or deadlines.

## Step 4 — Output (compact, grouped bullets)

Group the tasks into three buckets:

- **Group 1 — Must do before \<start date\>**
- **Group 2 — Must be delegated during OOO (handoff)**
- **Group 3 — Can wait until after \<end date\>**

For every bullet, keep each field to one sentence for fast scanning:

- **Task title**
- **What it is**: one-sentence description of the email-based task.
- **Why it matters**: one-sentence impact statement.
- **Deadline**: explicit date if stated; otherwise the email arrival date.
- **Delegate**: from the automatic reply if available; else the manager.

## Guardrails

- NEVER send, reply to, forward, or flag mail — this skill only plans.
- NEVER fabricate tasks, deadlines, or delegates.
- Separate clearly what the user must finish vs. what to hand off.
- Focus on actions, not raw email activity; assume the user wants to
  wrap up completely with minimal loose ends.
