---
name: morning-briefing
description: |
  Posts a prioritized morning briefing as an Adaptive Card to a configured Teams channel, then waits for the user to pick actions from a numbered menu. Covers today's calendar, tomorrow's prep needs, email follow-ups, and Teams items awaiting a reply.
cowork:
  category: productivity
  icon: WeatherSunny
targets:
  - copilot-cowork
---

When you use this skill, you assemble and deliver the user's morning briefing.

## DELIVERY TARGET (configure before first use)
- Team: `<TEAM_NAME>` — teamId `<TEAM_ID>`
- Channel: `<CHANNEL_NAME>` — channelId `<CHANNEL_ID>`
- Fill in the team and channel above, and store them in Memory on first run so you don't have to ask again. If they are not set, ask me which team and channel to post to before proceeding.
- Always deliver with **Postadaptivecardandwaitforaresponse** so the card posts AND the run pauses for the user's reply (e.g. "do 1, 3"). Do not use a fire-and-forget post for the scheduled briefing.

## LOOKBACK WINDOW
- Default: since yesterday end-of-business (~18:00 CET/CEST the previous day) up to now.
- If today is **Monday**, extend the window back to **Friday EOB** so the whole weekend is included.
- Header subtitle must state the date and the window, e.g. "Monday, 15 June 2026 · since Friday EOB (weekend included)" or "Tuesday, 16 June 2026 · since yesterday EOB".

## DATA TO GATHER (run reads in parallel where possible)
1. **Calendar — today**: use ListCalendarView for today (local time, Europe/Amsterdam). Time-order it. Capture title, start–end, organizer, and join link/location. Detect and flag: back-to-back meetings, conflicts/overlaps, and meetings with no prep gap before them.
2. **Calendar — tomorrow peek**: ListCalendarView for tomorrow. Surface anything that needs preparation TODAY — especially customer/external meetings. Never suggest preparing "tonight" or out of hours; instead recommend blocking **focus time during today's working hours** to prep.
3. **Email**: report the count of messages currently in folder **"1. Follow-Up Today"** and folder **"2. Follow-Up Later"** as the headline metric. Then add a short subtle one-liner naming the top 1–2 items, prioritizing key people (from Memory) and anything with a deadline. Prefer FY26 content when relevance is ambiguous.
4. **Teams**: surface @mentions, DMs, and threads awaiting a reply. Lead with these; group the rest. Respect privacy — do not reproduce private chat content in the channel card; reference it (who/where) instead.

## CARD LAYOUT (Adaptive Card, sections in this order)
1. Title "🌅 Morning Briefing" + subtitle (date · lookback window).
2. "📅 Today" — time-ordered list; ⚠️ on back-to-backs / missing prep gaps / customer meetings.
3. "🔮 Tomorrow — needs prep" — items needing action today; recommend a focus-time block. If nothing needs prep, keep the section and show "Nothing pending ✅".
4. "📧 Email — needs you" — folder counts (📌 N in Follow-Up Today · 🕒 N in Follow-Up Later), then a subtle top-items line.
5. "💬 Teams — awaiting reply" — @mentions / DMs / open threads.
6. "✅ What can I do for you?" — the action menu (below).

Empty-section rule: always keep every section visible (including Tomorrow-prep). If a section has nothing, show "Nothing pending ✅" rather than omitting it.

Use ⚠️ only for genuine warnings: back-to-backs, no prep time, un-started customer prep. Don't overuse it.

## ACTION MENU (numbered; the run waits for the user's pick)
The menu is **fully fixed 1–6** so the numbers always mean the same thing day to day. The canonical definitions live in memory (`morning-briefing.md`) — read them at the start of each run and keep the card in sync. Current set:
- **1.** Draft replies to flagged email (Follow-Up Today first)
- **2.** Block focus time before today's gaps / back-to-backs
- **3.** Block focus time today to prep tomorrow's customer/external meeting
- **4.** RSVP to open calendar invites
- **5.** Summarise a Teams thread / DM
- **6.** Reschedule or propose new times for a meeting

The label text per item may be lightly tailored to the day's content (e.g. naming the specific customer in item 3), but the NUMBER → INTENT mapping stays fixed. If the mapping is refined over time, update `morning-briefing.md` so it remains the single source of truth.

## AFTER POSTING
- The run is paused via Postadaptivecardandwaitforaresponse. When the user replies (e.g. "do 1, 3"), execute the chosen actions in order.
- For any irreversible action (sending mail, posting to others, creating/cancelling meetings), confirm specifics before executing. Drafting and blocking the user's own focus time can proceed once selected.
- Write in the user's voice; English by default. Use 24-hour time and CET/CEST.

## STYLE
Tight and scannable. Inform first, act second. No night-time asks. Be privacy-aware (GDPR) with external/personal data.