---
title: Generate Daily Roundup (GDR)
abbreviation: GDR
category: research
---

Generate comprehensive daily summaries integrating multiple sources with quote mining and topic linking.

## Input
- Target Date: YYYY-MM-DD (default: yesterday)
- Journal/{{YYYY-MM-DD}} as starting point
- Ingest/Clippings, Limitless, Lifelog files for date
- AI/Events,Analysis,Articles
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
   - Dedup sources (processed sources have priority)
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

### Quote Mining & Topic Linking
- Extract 3-5 memorable quotes (format per `obsidian-markdown-structure` skill)
- Validate ALL topic links (use `obsidian-links` skill)
- Link to established topics: PKM.md, AI Tools.md, Golf.md, Life Philosophy.md

### Journal Enhancement Rules
- Be brief but comprehensive
- Don't touch existing contents
- Each content should have link(s) to source note
- Ensure bidirectional linking is complete
