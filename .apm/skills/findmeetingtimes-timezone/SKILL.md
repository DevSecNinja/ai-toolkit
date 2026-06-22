---
name: findmeetingtimes-timezone
description: |
  Use whenever calling FindMeetingTimes, interpreting its output, or
  scheduling a meeting that depends on cross-timezone availability.
  FindMeetingTimes ALWAYS returns suggestions in UTC even when the
  request was sent in a local timezone. This skill prevents misreading
  UTC slots as local time. Triggers: "find a time", "check availability",
  "when is X free", "schedule a meeting", "vind een moment", "wanneer
  kan X", any use of FindMeetingTimes.
cowork:
  category: productivity
  icon: Clock
targets:
  - copilot-cowork
---

# FindMeetingTimes — timezone handling

## The trap

`FindMeetingTimes` accepts `start`, `end`, and `time_zone` parameters
in local time, but its **response always reports suggestion times in
UTC** — regardless of the requested timezone. Reading a UTC slot as if
it were local time silently produces a wrong-by-1-or-2-hour proposal.

## Required workflow

1. **Always pass `time_zone` explicitly** in the request (e.g. `W. Europe Standard Time`).
2. **Treat every `dateTime` in the response as UTC** until proven otherwise.
3. **Convert each suggestion to the user's local timezone before
   reasoning, comparing to a calendar, or proposing it to the user.**
4. **Show your conversion in writing**: when proposing a slot from a
   FindMeetingTimes result, state the source UTC and the converted
   local time, e.g. "11:00 UTC = 13:00 CEST".
5. **Verify against the user's busy calendar in local time.** A slot
   marked `free` for the attendee can still conflict with the user's
   own calendar — cross-check `ListCalendarView` results in local time.

## Conversion reference (Europe/Berlin, NL user)

| Period | Offset | UTC → local |
|--------|--------|-------------|
| CET (winter, ~late Oct → late Mar) | UTC+1 | add 1 hour |
| CEST (summer, ~late Mar → late Oct) | UTC+2 | add 2 hours |

DST transitions: last Sunday of March (→ CEST) and last Sunday of
October (→ CET). Around those dates, do not assume — verify the offset.

## Verification gate

Before sending or proposing any meeting time derived from
FindMeetingTimes:

- [ ] Did I add the local-timezone offset to every UTC value?
- [ ] Did I write out the conversion in the chat ("X UTC = Y local")?
- [ ] Did I cross-check the converted local time against the user's
      own calendar (ListCalendarView)?
- [ ] Does the proposed local time fall inside the user's stated
      working-hours preference?

If any box is unchecked, do not propose the slot yet.

## When NOT to use

- Pure user-only availability questions answered from
  `ListCalendarView` directly (no FindMeetingTimes call needed)
- Times the user typed verbatim ("schedule for 10:00 tomorrow") — no
  conversion needed; trust the user's local-time intent

## Common failure modes

| Symptom | Likely cause |
|---------|--------------|
| Proposed slot is off by 2 hours in summer | Read UTC as CEST |
| Proposed slot is off by 1 hour in winter | Read UTC as CET |
| Attendee shows "free" but conflicts with user's calendar | Skipped the cross-check step |
| Proposed slot near DST transition is off by 1 hour | Used wrong offset for the date |
