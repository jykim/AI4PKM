---
title: Generate Event Agenda (GEA)
abbreviation: GEA
category: preparation
---
Prepare for upcoming meetings/events by gathering context from past meetings and creating agenda with discussion topics.

## Input
- Meeting info from Google Calendar (via MCP) - **UPCOMING events**
- Past meeting summaries from AI/Events/ (with same attendees)
- Project files linked in past meetings
- Topic files related to meeting subject
- Local time (from unix `date` command)
- [[Meeting Template]] for structure reference
- Event date and timing information

## Parameters
* Calendar name (Default: `Default`)
* Time window (Default: next `3` days)

## Output
- File: AI/Events/{{YYYY-MM-DD}} Preparation for {{Event}} - {{Agent-Name}}.md
- Korean language agenda (unless meeting is with English speakers)
- Past meeting context and action items
- Suggested discussion topics and prepared questions
- Related documents and key insights to revisit

## Main Process
```
1. CALENDAR INTEGRATION (FUTURE-FOCUSED)
   - Pull UPCOMING meeting info from Google Calendar MCP server
   - Use timeMin = now, timeMax = +7 days
   - Get event timing and participant details
   - Extract meeting title, description, and objectives

2. CONTEXT GATHERING
   - Search AI/Events/ for past meetings with same attendees
   - Limit to last 3 meetings to avoid overwhelming context
   - Extract uncompleted action items from past meetings
   - Find related project/topic files via wiki links in summaries
   - Identify recurring discussion patterns and themes

3. AGENDA GENERATION
   - Use [[Meeting Template]] Preparation section as starting point
   - Write in Korean unless meeting is with English speakers
   - Summarize relevant context from past meetings
   - List outstanding action items as checkboxes
   - Suggest discussion topics based on past context
   - Generate prepared questions for the meeting
   - Add link from corresponding daily Journal doc
```

## Caveats
### Future Event Focus
⚠️ **CRITICAL**: Prepare for UPCOMING meetings (opposite of GES)
- Use timeMin = current time, timeMax = +7 days
- Verify upcoming event details match calendar

### Duplication Check
⚠️ **CRITICAL**: Always check for existing preparation files before creating new ones
- Search pattern: `AI/Events/{{YYYY-MM-DD}} Preparation for {{Event}}*.md`
- Check for files from ANY agent (Claude Code, Claude, Gemini, Codex)
- If exists: Update the existing file rather than creating a new one
- Never create multiple preparation files for the same event with different agent names

### Past Meeting Discovery
- Use attendee names to find related past meetings
- Limit to last 3 meetings to avoid overwhelming context
- Focus on actionable items and unresolved topics
- Extract action items that remain unchecked

### Language Standards
- **한글로 작성** (unless meeting is with English speakers)
- Keep important quotes in original language
- Match language style of organization/attendees

### Content Balance
- Balance comprehensive context with concise agenda
- Prioritize actionable items over historical detail
- Focus on what needs discussion, not what was discussed
- Update existing preparation file rather than creating new

### Link Validation
- Verify all wiki links to past meetings are valid
- Ensure project/topic file links exist
- Fix broken links immediately
