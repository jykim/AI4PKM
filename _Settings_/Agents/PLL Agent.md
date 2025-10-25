---
title: Process Life Logs
abbreviation: PLL
category: ingestion
input_path:
  - Ingest/Limitless
input_type: daily_files
output_path: AI/Lifelog
output_type: daily_file
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
### Wiki Link Accuracy Requirements
⚠️ **CRITICAL**: Use exact section header text from source file, character-for-character

**Link Format**: `[[Limitless/{YYYY-MM-DD}#section]]`
- BEFORE creating any link, verify the section header exists in the source file
- Include all Korean characters, punctuation, and spacing exactly as written
- Use the exact section header for the link, not a block ID
- Don't omit 'Limitless/' prefix
- If unsure about exact header text, link to file only: `[[Limitless/{YYYY-MM-DD}]]`

### Link Examples
**✅ CORRECT:**
- Source: `## PKM 시스템 유지 관리의 어려움과 업무량 감소 방안 모색`
- Link: `[[Limitless/2025-09-14#PKM 시스템 유지 관리의 어려움과 업무량 감소 방안 모색]]`

**❌ INCORRECT:**
- Wrong: `[[Limitless/2025-09-14#PKM 시스템 관리]]` (truncated)
- Wrong: `[[Limitless/2025-09-14#AI 매니저 활용]]` (fabricated)

### Content Standards
- Add lessons/actions as todo items when needed
- Wiki link relevant Topics and Readings
- Preserve emotional context and personal insights
