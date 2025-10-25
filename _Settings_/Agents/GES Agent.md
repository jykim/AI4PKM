---
title: Generate Event Summary
abbreviation: GES
category: ingestion
input_path:
  - Ingest/Limitless
  - MCP#gcal
input_type: updated_file
output_path: AI/Events
output_type: new_file
---
Summarize meeting/event content from voice transcriptions with calendar integration.

## Input
- Meeting info from Google Calendar (via MCP)
- Voice transcript from Ingest/Limitless/{{YYYY-MM-DD}}
- [[Meeting Template]] for structure reference
- Event date and timing information

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
   - Match transcript with meeting start/end time
   - Add important quotes and main discussion points
   - Optionally provide full transcript at end
```

## Caveats
### Timing Accuracy
⚠️ **CRITICAL**: Match transcript with meeting start/end time

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