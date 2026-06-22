---
name: focus-time-blocker
description: |
  Carve out deep-work time by scanning today's calendar for gaps and
  booking at least 2 hours of "Focus Time" events inside the user's
  working hours and timezone, morning-preferred and protecting lunch.
  Use when the user says "block focus time", "protect my deep-work
  time", "find me heads-down time", "defend my calendar", "schedule
  focus blocks", or runs a recurring start-of-day calendar-defense task.
  Do NOT use for booking meetings with other people (this never invites
  anyone) or for reading/triaging the calendar without creating events.
cowork:
  category: productivity
  icon: CalendarClock
targets:
  - copilot-cowork
---

# Focus Time Blocker

Plan focus blocks on the user's calendar for today: find free slots
between existing meetings and book at least 2 hours of focus time as
calendar events. **Never invite anyone. Never schedule outside working
hours.**

## Workflow

### Step 1 — Read timezone and working hours first

Before looking at any slot, fetch the user's configured timezone and
working hours (e.g. 09:00–17:00). Both are hard constraints:

- Interpret and schedule **all** times in the user's configured timezone.
- Only place focus blocks **inside** working hours. Never start a block
  before the working day begins or end one after it finishes.

### Step 2 — Find free gaps

Check today's calendar and identify the free time slots between existing
meetings, within working hours.

### Step 3 — Arrange at least 2 hours of focus time

Get creative with the arrangement — aim for **at least 2 hours total**,
split however fits the schedule best:

- 1 × 2-hour block, or
- 2 × 1-hour blocks, or
- 4 × 30-minute blocks, or
- any other combination summing to ≥ 2 hours.

Preferences:

- **Prefer mornings** — focus tends to be better earlier in the day —
  but adapt to what's actually free.
- **Protect lunch**: avoid scheduling over ~12:00–13:00 (the lunch
  window may shift).

If respecting working hours means the full 2 hours can't fit, **drop the
total** rather than spilling outside working hours, and tell the user how
much you could fit.

### Step 4 — Create the events

Create each focus block as a calendar event:

- Title: `Focus Time`
- Show-as: `busy` so others see the user is unavailable.
- **Do not invite anyone.**

## Guardrails

- NEVER schedule a block that starts before working hours begin or ends
  after they finish — drop time instead of spilling over.
- NEVER invite other attendees to a focus block.
- ALWAYS schedule in the user's configured timezone, not UTC or the
  agent's local time.
- If no qualifying gap exists, report that no focus time could be booked
  rather than overwriting or double-booking existing meetings.
