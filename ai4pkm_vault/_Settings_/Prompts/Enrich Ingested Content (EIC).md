---
title: "Enrich Ingested Content"
abbreviation: "EIC"
category: "workflow"
created: "2024-01-01"
---
Improve captured content through transcript correction, summarization, and knowledge linking.

## Input
- Target note file (typically in Ingest/Clippings/)
- Long articles may need chunking to avoid partial processing
- Original content with potential grammar/transcript errors

## Output
- Updated note inline (don't create new note)
- Status property set to `processed`
- Summary section added at beginning
- Improved formatting and structure
- Links to existing KB topics

## Main Process
```
1. IMPROVE CAPTURE & TRANSCRIPT (ICT)
   - Fix all grammar or transcript errors
   - Translate to Korean for Clippings
   - Remove extra/duplicated newlines
   - Add chapters using heading3 (###)
   - Add formatting (lists, highlights)
   - Keep overall length equal to original
   - Set status property to processed

2. ADD SUMMARY FOR THREAD
   - Add Summary section at beginning (##)
   - Write catchy summaries for Threads sharing
   - Use quotes verbatim to convey author's voice
   - Don't add highlights in summary

3. ENRICH USING TOPICS
   - Link related KB topics (existing only)
   - Add one-line summary to relevant KB topics
   - Link to related summaries (books, etc.)
```

## Caveats

### Content Completeness - CRITICAL

⚠️ **CRITICAL**: ICT section must be COMPLETE - not truncated

**Common failure pattern:**
- Agent starts ICT section
- Hits token/context limit mid-processing
- ICT cuts off mid-sentence: "Since I last wrote at the beginning of the summer, my methodol..."
- Agent marks status as PROCESSED anyway ❌ WRONG

**Prevention measures:**
1. **Check article length FIRST** before starting
2. **If source >3000 words**, process in chunks OR request context extension
3. **VERIFY ICT ends at natural stopping point** (end of paragraph/section, not mid-sentence)
4. **Self-check before marking PROCESSED**: "Does the last paragraph in ICT feel complete?"
5. **If truncated**, FINISH it before updating status to PROCESSED

**Quality verification:**
- ICT section should have multiple ### subsections (not just one incomplete section)
- Last sentence should end with proper punctuation, not "..." or cut-off text
- Length should be comparable to original source (not 30-50% shorter due to truncation)

**If you cannot complete full ICT:**
- Mark task as NEEDS_INPUT explaining length/complexity issue
- DO NOT mark PROCESSED with incomplete work

### Rename Filenames
* Convert " " (curly/typographic quotes) to " (straight quote)
   * Same for single quotes
* Remove incomplete words -- 40살 전에 알았다면 `얼마ᄂ`
* Remove `Readwise` at the end

### Formatting Standards
- Use heading3 (###) for chapters
- Limit highlights to essence (one per chapter)
- Preserve original prose structure
- Overall length should equal original

### Topic Linking
- Only link to existing topics in KB
- Validate all topic links before adding
- Add meaningful one-line summaries to topics
