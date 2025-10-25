---
title: Enrich Ingested Content
abbreviation: EIC
category: ingestion
input_path:
  - AI/Clipping
  - Journal
input_type: daily_files
input_range: daily
output_path: AI/Roundup
output_type: daily_file
---

Generate comprehensive daily summaries integrating multiple sources with quote mining and topic linking.

## Input
- Target Date: YYYY-MM-DD (default: yesterday)
- Journal/{{YYYY-MM-DD}} as starting point
- Ingest/Clippings, Limitless, Lifelog files for date
- Apple Notes available for the date
- [[Journal Template]] if file doesn't exist

## Output
- File: AI/Roundup/{{YYYY-MM-DD}} - {{Agent-Name}}.md
- Enhanced Journal/{{YYYY-MM-DD}}.md with roundup link
- Source coverage report (processed vs. available)
- Minimum 3-5 memorable quotes per roundup
- Bidirectional linking between journal and roundup

## Main Process
```
1. JOURNAL FOUNDATION
   - Use Journal/{{YYYY-MM-DD}} as starting point
   - Use [[Journal Template]] if file doesn't exist
   - Keep original language (English/한글)
   - Fill note sections appropriately

2. COMPREHENSIVE SOURCE INTEGRATION
   - Count available sources first
   - Integrate Apple Notes with summaries
   - Extract insights from Life Logs (AI/Lifelog)
   - Review ALL available clippings for date
   - Include book-related content
   - Create "Additional Materials" if >10 clippings
   - Generate source coverage report

3. QUOTE MINING & TOPIC LINKING
   - Extract 3-5 memorable quotes preserving voice
   - Search existing Topics directory before linking
   - Validate all topic links point to existing files
   - Add "Topics to Create" list if needed

4. JOURNAL ENHANCEMENT
   - Enrich Journal page using roundup contents
   - Add roundup link to links property
   - Ensure bidirectional linking is complete
```

## Caveats
### Source Coverage Requirements
⚠️ **CRITICAL**: Target 80%+ coverage of available sources

### Quote Mining Standards
- Format: > "Quote text" - Context/Speaker if applicable
- Prioritize voice preservation over summary
- Include quotes from multiple sources
- Place strategically to support key insights

### Topic Linking Validation
- **CRITICAL**: Search existing Topics directory BEFORE creating links
- Format: "[[Category/Page Title]]" (e.g., "[[Technology/AI Tools]]")
- All topic links must point to existing files
- Use established topics: PKM.md, AI Tools.md, Golf.md, Life Philosophy.md

### Journal Enhancement Rules
- Be brief but comprehensive
- Don't touch existing contents
- Each content should have link(s) to source note
- Ensure bidirectional linking is complete
