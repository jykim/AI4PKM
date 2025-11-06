---
title: Generate Event Summary (GES)
abbreviation: GES
category: ingestion
---
Summarize meeting/event content from voice transcriptions with calendar integration.

## Input
- Meeting info from Google Calendar (via MCP)
- Voice transcript from Ingest/Limitless/{{YYYY-MM-DD}}
- Local time (from unix `date` command)
- [[Meeting Template]] for structure reference
- Event date and timing information

## Parameters
* Calendar name (Default: `Default`)
* Time window (Default: past `24` hours)

## Output
- File: AI/Events/{{YYYY-MM-DD}} Summary for {{Event}} - {{Agent-Name}}.md
- Korean language summary (unless original is English)
- Matched transcript timing with meeting schedule
- Important quotes and main discussion points
- Optional full transcript if requested

## Main Process
```
1. CALENDAR INTEGRATION
   - Pull meeting info from Google Calendar MCP server
   - Get event timing and participant details
   - Verify meeting context and title

2. TRANSCRIPT PROCESSING
   - Use Ingest/Limitless/{{YYYY-MM-DD}} for transcript
   - Keep original language (English/한글)
   - Chunk file & merge if needed (don't omit parts)
   - Update output file if it exists

3. SUMMARY GENERATION
   - Use [[Meeting Template]] as starting point
   - Write in Korean unless original is English
     - Fix all transcription / grammar errors / filler words
   - Match transcript with meeting start/end time
   - Add important quotes and main discussion points
   - Add link from corresponding daily Journal doc
```

## Caveats
### Timing Accuracy
⚠️ **CRITICAL**: Match transcript with meeting start/end time

### Duplication Check
⚠️ **CRITICAL**: Always check for existing event summaries before creating new ones
- Search pattern: `AI/Events/{{YYYY-MM-DD}} Summary for {{Event}}*.md`
- Check for files from ANY agent (Claude Code, Claude, Gemini, Codex)
- If exists: Update the existing file rather than creating a new one
- Never create multiple summaries for the same event with different agent names

### Language Standards
- **한글로 작성** (unless original transcript is in English)
- Keep the language of the original note for consistency
- Preserve important quotes in original language

### Content Processing
- Actual meeting time may be slightly off (especially end time)
- Chunk large files to avoid partial processing
- Don't omit any part of the transcript
- Update existing output file rather than creating new

### Transcript Handling
- Full transcript should provide only what was said
- Include only when specifically requested
- Focus on discussion points and key insights