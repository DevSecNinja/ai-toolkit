# Outlook Inbox-Zero Triage Pass

A conservative, repeatable triage pass for the Outlook Inbox. Every mail in the Inbox root is moved into one of nine subfolders (calendar invites stay put), replies are proposed in chat, RSVPs are proposed for invites, the original mail is tagged with an Outlook category so the inbox view shows which mails have a draft ready, stale outgoing threads are flagged for follow-up, and a single Teams summary is posted at the end so you can see exactly what changed.

## Description

Designed to bring the Inbox back to zero in one pass without sending anything or deleting anything. The agent classifies each mail using a strict rule order, surfaces calendar invites with an RSVP proposal grounded in your role and calendar conflicts, proposes language-matched placeholder replies for human asks (so you can review and confirm before the assistant sends them in an interactive turn), tags the original mail with `🦞 Draft Ready` so the inbox view shows which mails have a reply waiting, scans the Sent folder for stale threads waiting on others, and reports back over Teams.

## AI Model

- Platform: Microsoft 365 Copilot with Cowork
- Note: Requires Microsoft 365 Copilot license with WorkIQ & Cowork access

## When to Use

- Hourly inbox sweep (ask Cowork to schedule this hourly).
- After being out of office, when the Inbox needs to be brought back to zero.
- Whenever the Inbox root has accumulated unsorted mail and you want a single pass to classify, propose drafts/RSVPs, and report — without sending anything.

## Required Inbox Subfolders

Set these up once in Outlook before running the prompt. Numeric prefixes ensure stable ordering in the Outlook folder pane:

1. `1. Follow-Up Today`
2. `2. Follow-Up Later`
3. `3. Waiting For`
4. `4. Read Later`
5. `5. External Newsletter`
6. `6. Internal Comms`
7. `7. Reference`
8. `8. Archive`
9. `9. Expenses`

## Required Outlook Categories

Create these once in Outlook (Home → Categorize → All Categories → New). Names must match exactly — the lobster emoji is part of the name.

- `🦞 Draft Ready` — applied by the assistant whenever it has a proposed reply waiting for the user to confirm. Pick a high-visibility colour (e.g. orange).
- `🦞 Follow-up Booked` — applied by the assistant when it has created a calendar block to deliver on a commitment in the reply. Pick a second colour (e.g. purple).

## Prompt

```text
You are running an inbox triage pass. Goal: empty the Inbox by moving every mail into the correct subfolder, except calendar invites which stay put for RSVP. Be conservative — when in doubt, prefer "4. Read Later" over auto-archiving. Do NOT send any emails or RSVPs. Do NOT delete anything.

## Step 1 — List new mail in Inbox root only

Use ListMessages with folder_id="<inbox folder id>" and top=50. Only process mails whose parentFolderId is the Inbox root (not already in a subfolder). Skip mails already in subfolders 1–9, Daily, or Periodic Check-In.

In parallel, run mcp__graph__QueryGraph on /me/mailFolders/{inbox_id}/messages with $top=50, $orderby=receivedDateTime desc, $select=id,subject — Graph returns @odata.type per message, which is the reliable signal for calendar-invite detection. Cross-reference by id.

## Step 2 — Classify each mail using these rules (in order)

For each mail, decide ONE destination:

1. **Calendar invite** (@odata.type: "#microsoft.graph.eventMessageRequest") — do NOT move. Surface in Step 4 with an RSVP proposal. Outlook auto-clears the invite from the inbox once the user RSVPs.
2. **Calendar response** (@odata.type: "#microsoft.graph.eventMessageResponse") — Accepted: / Declined: / Tentative: confirmations from attendees → "7. Reference".
3. **"9. Expenses"** — anything money-related: receipts, invoices, booking confirmations (flights, hotels, trains, rideshare, restaurants), corporate card statements, MyExpenses approval/rejection notices, travel insurance & visa docs.
4. **"1. Follow-Up Today"** — direct ask requiring your reply TODAY: you're on To: line (not just CC), question or action requested by a real human (not a bot/system), and not already replied to. Examples: meeting requests, decisions needed, questions from colleagues/customers.
5. **"2. Follow-Up Later"** — automated or system-generated call-to-action that needs YOUR action, but not necessarily today. Has a deadline or expiry but is not urgent right now. Examples: Microsoft certification renewal reminders, Connect/HR resubmit requests, mandatory training reminders, expiring access requests, compliance attestations. Differs from "1. Follow-Up Today" because the sender is a bot/system, and from "7. Reference" because the user must take an action (not just keep a record).
6. **"3. Waiting For"** — the mail is a confirmation/acknowledgement that someone received your request and will get back to you, OR it's a thread where you've already replied and are awaiting next move from the other side.
7. **"5. External Newsletter"** — external sender (not @microsoft.com), has unsubscribe link or List-Unsubscribe header, marketing/product update style. Examples: vendor newsletters, conference promos, SaaS product updates.
8. **"6. Internal Comms"** — internal mass communications (@microsoft.com sender, sent to large DLs, "All Employees", org news, exec messages, internal newsletters, Viva digest).
9. **"7. Reference"** — non-financial reference: calendar accepts/declines (handled by rule 2), password resets, automated transactional notifications worth keeping but requiring NO further action from you. Receipts go to "9. Expenses" instead.
10. **"8. Archive"** — pure noise with no reference value: build/CI notifications you've already handled, expired alerts, duplicate notifications, automated FYIs that don't fit Reference.
11. **"4. Read Later"** — fallback for everything else: informational, you're CC'd, long reads, FYIs from humans that don't need a reply today.

Use folder IDs from ListMailFolders to get the exact IDs. Move with MoveMessage. Skip move for calendar invites (rule 1).

## Step 3 — Propose replies for "1. Follow-Up Today" (do NOT send)

For each mail moved to "1. Follow-Up Today":

1. Compose a proposed reply (plain text or simple HTML — both work; the platform preprocesses HTML and adds the Cowork footer automatically).
2. Detect the language of the incoming mail body (English, Dutch, etc.) and draft in that same language.
3. Keep it polite, concise, and address the ask directly so the user can edit minimally and send.
4. Do NOT add footers to the comment — the auto-appended Cowork footer already discloses AI authorship on reply tools, and adding the line on top duplicates it.
5. Tag the original mail with the `🦞 Draft Ready` Outlook category so the user can see in their inbox view that a draft is ready. Use UpdateMessage with categories=["🦞 Draft Ready"] (preserve any other existing categories on the mail — fetch first, then merge).
6. Include the proposed reply text verbatim in the final Teams summary so the user can review and confirm.

Do NOT call ReplyToMessage / ReplyAllToMessage / CreateDraftMessage inside this scheduled run — the per-call approval dialog has an "Always allow" button that one mis-click would convert into blanket send permission for every future scheduled run. Reply tools are reserved for interactive turns where the user is present.

If for any reason a draft cannot be prepared (e.g. mail body unreadable, language detection failed), log it in the Teams summary and skip — do not guess.

## Step 4 — Propose RSVPs for calendar invites (do NOT send)

For each eventMessageRequest found in Step 2:

1. Fetch invite + event details via mcp__graph__QueryGraph on /me/messages/{id} with $expand=microsoft.graph.eventMessage/event($select=id,start,end,organizer,attendees,responseRequested). Capture: meetingMessageType, startDateTime, endDateTime, responseRequested, event.id, event.attendees, event.organizer.
2. Locate the user in event.attendees by email and read their type (required or optional).
3. Cross-check conflicts with ListCalendarView for the invite window in the user's local time zone. Ignore the auto-added tentative entry for this same invite when scoring conflicts.
4. Apply the RSVP recommendation matrix:

   | Role     | Conflict? | Recommendation |
   |----------|-----------|----------------|
   | Required | No        | Accept |
   | Required | Yes       | Tentative + flag the conflict |
   | Optional | No        | Accept (or Tentative if low-relevance) |
   | Optional | Yes       | Decline |

5. Surface in the Teams summary: subject, organiser, start–end (local time), the user's role, conflicts found, the recommendation with a one-line reason, and the calendar event alias for confirmation.

Do NOT call AcceptEvent / TentativelyAcceptEvent / DeclineEvent inside this scheduled run — same "Always allow" hazard. The user confirms in chat and the email-reply skill executes the response.

## Step 5 — Cleanup `🦞 Draft Ready` tags on stale items

For mails currently tagged `🦞 Draft Ready`:

- If the conversation has since moved into "3. Waiting For" (i.e. the user replied without going through the assistant), clear the tag via UpdateMessage with categories list excluding `🦞 Draft Ready`.
- If the original mail is no longer in "1. Follow-Up Today" (user moved/archived it), clear the tag.
- If the user explicitly sent the proposed reply via the assistant, the assistant's interactive flow swaps `🦞 Draft Ready` → `🦞 Sent by agent` at send time — no cleanup needed here.

This keeps the inbox view honest: `🦞 Draft Ready` only ever sits on mails where a draft is actually waiting.

## Step 6 — Sent Items follow-up flagging

Use ListMessages with folder_id="<sent items folder id>" and top=50, received_after=14 days ago.

For each sent mail, check:

- Is the conversation thread now sitting in "3. Waiting For"? (look up by conversationId across all inbox subfolders)
- OR: does the body contain a question (ends with "?", or contains phrases like "could you", "let me know", "thoughts?", "kun je", "laat me weten") AND has received no reply for 3+ business days?

If yes to either, log it in the Teams summary listing items that should be followed up, with subject + recipient + date + reason. (FlagEmail is available — set flag_status='flagged' to flag directly in addition to logging.)

## Step 7 — Roll-forward for "1. Follow-Up Today" and "2. Follow-Up Later"

Mails already in "1. Follow-Up Today" or "2. Follow-Up Later" stay there indefinitely until the user replies or moves them. Do NOT auto-move them out. Just count how many are in each, and run the Step 3 draft-proposal logic for any "1. Follow-Up Today" mails that don't yet carry a `🦞 Draft Ready` tag.

## Step 8 — Final report

At end of the pass, send ONE Teams message via PostMessage summarising:

- Inbox before → after counts
- How many moved to each folder (with folder name)
- Calendar invites with RSVP proposals (subject + organiser + time + role + conflicts + recommendation, with calendar event aliases for confirmation)
- How many proposed reply drafts (with subject lines AND the proposed reply body for each, so the user can confirm-and-send in chat)
- How many `🦞 Draft Ready` tags applied / cleared
- Sent items flagged for follow-up (subject + recipient + reason)
- Any classification you were uncertain about (so the user can correct)
- Any tooling failures so the user knows what to handle manually

Keep the Teams message under 1500 chars when possible — if proposed drafts/RSVP details push it over, prefer a longer message over truncating.

## Guardrails

- NEVER send emails or RSVPs inside the scheduled run. Reply tools (ReplyToMessage, ReplyAllToMessage, ForwardMessage) and calendar response tools (AcceptEvent, TentativelyAcceptEvent, DeclineEvent) are reserved for interactive turns where the user is present.
- NEVER fall back silently to creating standalone "Re: ..." drafts via CreateDraftMessage — non-threaded drafts are worse than no draft.
- NEVER move calendar invites — Outlook auto-clears them on RSVP.
- NEVER delete mails. Only move.
- NEVER touch mails already in subfolders 1–9 (except for the `🦞 Draft Ready` cleanup pass in Step 5).
- ALWAYS preserve existing categories when adding/removing the lobster categories — fetch first, merge, then UpdateMessage.
- The user's existing rule (Power Automate No Reply → Archive) is separate and untouched.
- If Inbox is already empty, send a brief "Inbox zero ✅" Teams message and stop.
```

## Notes

- Conservative-by-default: ambiguous mail goes to `4. Read Later`, never to `8. Archive`.
- `2. Follow-Up Later` is for automated CTAs (cert renewals, Connect resubmits, training reminders) that need eventual action but aren't time-critical today — keeps `1. Follow-Up Today` reserved for human-driven asks.
- `9. Expenses` separates money-related mail (receipts, bookings, corporate card, expense reports) from `7. Reference` so monthly expense reconciliation is faster.
- Calendar invites are detected via `@odata.type: "#microsoft.graph.eventMessageRequest"` — surfaced via a parallel Graph query because the standard ListMessages projection drops the type discriminator. Invites stay in the Inbox; Outlook auto-clears them on RSVP.
- RSVP proposals use a role × conflict matrix and the `event.id` from the eventMessage's `event` expansion — `AcceptEvent` / `TentativelyAcceptEvent` / `DeclineEvent` take the event id, not the message id.
- Drafts are language-matched to the incoming mail (e.g. Dutch in → Dutch draft).
- The triage prompt does NOT call any reply or RSVP API directly. It proposes drafts/RSVPs in the Teams summary; the user confirms in an interactive chat turn and the assistant then sends via `ReplyToMessage` / `ReplyAllToMessage` (which thread correctly on the original conversation and inherit recipients server-side) or `AcceptEvent` / `TentativelyAcceptEvent` / `DeclineEvent`. This avoids a known UX gotcha: the per-call approval dialog's "Always allow" button could convert one mis-click into blanket send permission for every future scheduled run.
- Outlook categories (`🦞 Draft Ready`, `🦞 Follow-up Booked`) give a visual signal in the inbox view of which mails have a reply pending, already sent, or had a calendar block created for a commitment.
- Adjust folder names in Step 2 if your inbox uses a different taxonomy.

## Tags

- productivity
- outlook
- email
- triage
- inbox-zero
- m365
- copilot
- calendar-invites
- rsvp

## Credits

Designed for Microsoft Copilot / Cowork with M365 tools (Outlook + Teams + Calendar). Originally built for a personal Inbox-zero workflow with Dutch/English mixed mail.
