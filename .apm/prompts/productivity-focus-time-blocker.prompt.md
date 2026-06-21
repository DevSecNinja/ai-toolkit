---
description: "Analyzes your calendar for the day, identifies free gaps between existing meetings, and creatively arranges at least 2 hours of focus time as calendar events — respecting your timezone and working hours, flexible on block sizes and morning-preferred, while protecting lunch."
category: "productivity"
title: "Focus Time Blocker"
model: "claude-opus-4-7"
platform: "Microsoft Copilot (Cowork / Microsoft 365)"
tags: ["productivity", "calendar-management", "focus-time", "deep-work", "time-blocking", "microsoft-365"]
example: |
  Run this at the start of the workday — or schedule it as a recurring 6 AM task — to automatically defend deep-work time on a meeting-heavy calendar. Especially useful for knowledge workers, engineers, and sellers whose calendars get filled by recurring syncs and 1:1s, and who want a tool to carve out heads-down time without manually hunting for gaps. Because it honors timezone and working hours, blocks always land inside the real workday — no after-hours focus time.
notes: |
  - **Timezone aware**: The prompt explicitly checks your config
---

Plan focus blocks on my calendar for today. Check my calendar for the day and find free time slots between existing meetings.

First, check my timezone and working hours settings, and follow both:
- Interpret and schedule all times in my configured timezone.
- Only place focus blocks inside my working hours (e.g., 09:00–17:00). Never schedule a block that starts before my working day begins or ends after it finishes. If respecting working hours means I can't reach the full target, drop the total focus time rather than spilling outside working hours — and tell me how much you could fit.

Get creative with the arrangement — aim for at least 2 hours of total focus time, but split it however works best given my schedule.
Acceptable arrangements include: 1 single 2-hour block, 2 × 1-hour blocks, 4 × 30-minute blocks, or any other combination that adds up to at least 2 hours.
Prefer mornings when possible since focus tends to be better earlier in the day, but adapt to what's actually free.
Avoid scheduling over lunch (around 12:00-13:00, but lunch blocks might shift).
Create the focus blocks as calendar events titled "Focus Time" with show-as set to "busy" so others see I'm unavailable.
Do not invite anyone.
