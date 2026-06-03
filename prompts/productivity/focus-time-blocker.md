# Focus Time Blocker

## Description

Analyzes your calendar for the day, identifies free gaps between existing meetings, and creatively arranges at least 2 hours of focus time as calendar events — flexible on block sizes and morning-preferred, while protecting lunch.

## AI Model

- Platform: Microsoft Copilot (Cowork / Microsoft 365)
- Model: Claude Opus 4.7
- Version: claude-opus-4-7

## Prompt

``` text
Plan focus blocks on my calendar for today. Check my calendar for the day and find free time slots between existing meetings.
Get creative with the arrangement — aim for at least 2 hours of total focus time, but split it however works best given my schedule.
Acceptable arrangements include: 1 single 2-hour block, 2 × 1-hour blocks, 4 × 30-minute blocks, or any other combination that adds up to at least 2 hours.
Prefer mornings when possible since focus tends to be better earlier in the day, but adapt to what's actually free.
Avoid scheduling over lunch (around 12:00-13:00, but lunch blocks might shift).
Create the focus blocks as calendar events titled "Focus Time" with show-as set to "busy" so others see I'm unavailable.
Do not invite anyone.
```

## Example Use Case

Run this at the start of the workday — or schedule it as a recurring 6 AM task — to automatically defend deep-work time on a meeting-heavy calendar. Especially useful for knowledge workers, engineers, and sellers whose calendars get filled by recurring syncs and 1:1s, and who want a tool to carve out heads-down time without manually hunting for gaps.

## Tags

- productivity
- calendar-management
- focus-time
- deep-work
- time-blocking
- microsoft-365

## Notes

- **Recurring use**: Pair with a scheduled task ("every weekday at 6 AM") so focus blocks are placed before your day starts.
- **Flexibility tip**: The prompt is intentionally creative about block sizes. On lighter days you'll get one long block; on packed days you'll get fragmented 30-minute slivers.
- **Tentative meetings**: If the assistant comes up short of 2 hours, it will surface tentative/optional meetings as candidates to reclaim — you decide whether to override.
- **Lunch protection**: The "lunch blocks might shift" wording lets the assistant respect a lunch event even if it's not exactly at 12:00–13:00.
- **Variations**:
  - Swap "today" for "tomorrow" to plan ahead the night before.
  - Increase the target ("at least 3 hours") for heavy-thinking days.
  - Add "and send me a Teams message summarizing what was scheduled" for a confirmation ping.

## Feedback

Have suggestions or found an issue with this prompt? [Click here to provide feedback](https://github.com/DevSecNinja/gpt-prompts/issues/new?title=Feedback%3A%20%5Bproductivity%5D%20Focus%20Time%20Blocker&body=%23%23%20Feedback%20for%3A%20Focus%20Time%20Blocker%0A%0A%2A%2APrompt%20location%2A%2A%3A%20%5Bprompts%2Fproductivity%2Ffocus-time-blocker.md%5D%28https%3A%2F%2Fgithub.com%2FDevSecNinja%2Fgpt-prompts%2Fblob%2Fmain%2Fprompts%2Fproductivity%2Ffocus-time-blocker.md%29%0A%0A%2A%2ACategory%2A%2A%3A%20productivity%0A%2A%2APrompt%20name%2A%2A%3A%20focus-time-blocker%0A%0A---%0A%0A%3C%21--%20Please%20provide%20your%20feedback%20below%20--%3E%0A%0A&labels=enhancement).
