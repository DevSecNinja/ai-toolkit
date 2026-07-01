---
name: meeting-transcript-creation
description: |
  Generate an Obsidian-compatible meeting notes markdown file for a Teams meeting that have transcripts, and save them into my OneDrive.
cowork:
  category: productivity
  icon: Notepad
targets:
  - copilot-cowork
---

Generate an Obsidian-compatible meeting notes markdown file for a Teams meeting that have transcripts, and save them into my OneDrive notes folder "Documents/Documents/Notes/Meetings". Work through these steps each run:

1. Check my Outlook calendar for meetings that ended within the past hour (the window since the previous run).
2. For each of those meetings that was an online Teams meeting, check whether a meeting transcript is available yet. Skip any meeting that has no transcript.
3. For meetings that do have a transcript, look in my notes folder "Documents/Documents/Notes/Meetings" and check whether a note for that meeting already exists. Notes are named "<YYYY-MM-DD> <Meeting subject>.md" using the meeting's date and subject. If a note for that meeting already exists, do nothing for it — never overwrite or duplicate.
4. Only for meetings that have a transcript AND no existing note: read my note template at "Documents/Notes/Templates/meeting.md", fill it in from the meeting's transcript (capture the key discussion points, decisions, and outstanding action items with their owners, plus attendees/date as the template provides), and save a new markdown file named "<YYYY-MM-DD> <Meeting subject>.md" into "Documents/Notes/Meetings". Keep it clean markdown that follows the template's structure and renders well in Obsidian. Only include facts grounded in the transcript — do not invent content.
5. After a new note has been saved for a meeting, push MY OWN outstanding action items from that meeting into the commitment tracker — and only mine. From the action items captured in step 4, keep only the ones whose owner is me, the user (including first-person commitments in the transcript such as "I'll…", "I will…", "let me…", or items explicitly assigned to me). Drop every action item owned by anyone else, and drop any item whose owner is ambiguous or unstated — when in doubt, leave it out. For each of my action items, add it to the commitment tracker Teams channel & Obsidian folder by leveraging the commitment-tracker skill. Capture the action item text, the meeting subject and date as the source, and any due date or deadline mentioned in the transcript. Only include action items grounded in the transcript — do not invent or reword them into new commitments. If, after filtering, none of the action items are mine, add nothing to the tracker.
6. If there were no meetings in the past hour, none of them had transcripts, or every one already has a note, finish silently: create nothing and send no messages or summaries. (Adding my action items to the tracker in step 5 only applies when a new note was actually written.)

Run quietly — only act when there is a new, transcribed, not-yet-documented meeting to write up.
