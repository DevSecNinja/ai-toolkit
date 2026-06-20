---
description: "Identifies sent emails that require follow-up by analyzing your sent items for questions, requests, or scheduling proposals that haven't received direct replies within a specified date range."
---

# Email Follow-up Tracker

Review my Sent Items from last month (first day to last day) and identify emails where I asked a question, requested information, proposed scheduling, or indicated I was expecting a response — and where NO substantive reply was received.

Exclusions:

- Newsletters, automated notifications, system emails, and any recipients with no-reply/DoNotReply addresses.
- Out-of-office replies and automated responses.

Reply detection rules:

- Consider an email 'replied' only if there is a subsequent Inbox message that:
  1) Appears in the same Conversation/Thread; AND
  2) Has a DateTime after the sent email's DateTime; AND
  3) Is from one of the original TO recipients (ignore CC/BCC); AND
  4) Contains substantive content addressing the question/request (not just an acknowledgment like "Thanks" or "Got it").
- Do NOT treat earlier messages in the thread as replies to a later sent email.
- Replies received after the date range should still count as replies.

Analysis approach:

- For each sent email with a question or request, check the full conversation thread chronologically.
- Mark as "needs follow-up" only if no qualifying reply exists from the intended recipient(s).
- Use message content and context to determine if a reply is substantive.

Output:
Create a table with columns:
Date Sent | Recipient (Organization) | Subject | Key Question/Request | Days Since Sent | Follow-up Priority (High/Medium/Low) | Received Substantive Reply (Yes/No)

Sort by "Days Since Sent" (oldest first) and include ONLY rows where no substantive reply was received. Show a counter of how many emails require follow-up.
