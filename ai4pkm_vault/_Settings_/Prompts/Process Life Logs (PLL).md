---
title: Process Life Logs (PLL)
abbreviation: PLL
category: ingestion
---

Summarize voice-based life logs into structured daily summaries with accurate linking and photo integration.

## Input
- Target Date: YYYY-MM-DD (default: yesterday)
- Source file: Ingest/Limitless/{{YYYY-MM-DD}}.md
- Processed photos from [[Pick and Process Photos (PPP)]] output
- [[Lifelog Template]] for structure reference

## Output
- File: AI/Lifelog/{{YYYY-MM-DD}} Lifelog - {{Agent-Name}}.md
- Update existing file if it already exists
- Maintain original language (English/한글) from source
- Include integrated photos with timestamp matching

## Main Process
```
1. SOURCE PROCESSING
   - Use Ingest/Limitless/{{YYYY-MM-DD}} as starting point
   - Use [[Lifelog Template]] structure
   - Chunk file & merge if needed (don't omit any part)
   - Respect existing section structure

2. MEMORABLE CONTENT EXTRACTION
   - Identify memorable items (emotions, knowledge, lessons)
   - Include key quotes and highlighted conversations (== ==)
   - Include content from announcements, videos, music
   - Format by log type (monologue/chat/contents)
   - Add time of day & succinct titles
   - Create accurate wiki links to source sections

3. PHOTO INTEGRATION
   - Match timestamps between conversation and photos
   - Add relevant photos that enhance the story
   - Ensure photos blend naturally into narrative
   - Don't include all photos, only relevant ones
```

## Caveats
### Wiki Link Requirements
⚠️ **CRITICAL**: Follow `obsidian-links` skill for all wiki link creation:
- Verify Limitless section headers exist before linking (exact Korean text)
- Use format: `[[Limitless/YYYY-MM-DD#Exact Section Header]]`
- When unsure about exact header, link to file only: `[[Limitless/YYYY-MM-DD]]`

### Content Standards
- Add lessons/actions as todo items when needed
- Wiki link relevant Topics and Readings
- Preserve emotional context and personal insights
