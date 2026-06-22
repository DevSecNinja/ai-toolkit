---
name: email-follow-up-tracker
description: |
  Find sent emails still awaiting a reply: scan Sent Items over a date
  range for questions, requests, or scheduling proposals that never got
  a substantive response, and report them as a prioritized follow-up
  table. Use when the user says "what am I waiting on", "which emails
  need follow-up", "who hasn't replied to me", "track my sent
  follow-ups", or "did anyone ignore my email". Do NOT use for triaging
  the inbox (that is inbox-zero) or for drafting or sending replies —
  this only reports what needs chasing.
cowork:
  category: productivity
  icon: MailClock
targets:
  - copilot-cowork
---

# Email Follow-up Tracker

Identify sent emails that need a follow-up because no substantive reply
came back. **Read-only: never send, reply, or flag — only report.**

## Step 1 — Establish the date range

Default to **last month** (first day to last day) unless the user
specifies another range. Review the user's **Sent Items** for that range.

## Step 2 — Select candidate emails

Include sent emails where the user asked a question, requested
information, proposed scheduling, or otherwise indicated they expected a
response.

**Exclude:**

- Newsletters, automated notifications, system emails, and any
  no-reply / DoNotReply recipients.
- Out-of-office and other automated responses.

## Step 3 — Reply detection rules

Treat a sent email as **replied** only if there is a later Inbox message
that:

1. Appears in the **same conversation/thread**; AND
2. Has a timestamp **after** the sent email; AND
3. Is from one of the original **To** recipients (ignore CC/BCC); AND
4. Contains **substantive** content addressing the question/request —
   not just an acknowledgment like "Thanks" or "Got it".

Additional rules:

- Do NOT treat earlier messages in the thread as replies to a later sent
  email.
- Replies received **after** the date range still count as replies.
- For each candidate, walk the full conversation thread chronologically
  and use content/context to judge whether a reply is substantive.

## Step 4 — Output table

Produce a table, sorted by **Days Since Sent** (oldest first), including
**only** rows where no substantive reply was received. End with a
counter of how many emails require follow-up.

| Date Sent | Recipient (Organization) | Subject | Key Question/Request | Days Since Sent | Follow-up Priority (High/Medium/Low) | Received Substantive Reply (Yes/No) |
|-----------|--------------------------|---------|----------------------|-----------------|--------------------------------------|-------------------------------------|

## Guardrails

- NEVER send, reply to, or flag mail — this skill only reports.
- Mark "needs follow-up" only when no qualifying reply exists from the
  intended recipient(s).
- Do not include rows that already received a substantive reply.
