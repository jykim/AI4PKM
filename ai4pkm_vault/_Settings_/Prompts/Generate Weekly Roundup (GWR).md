---
title: "Generate Weekly Roundup"
abbreviation: "GWR"
category: "workflow"
created: "2024-01-01"
---

Generate comprehensive weekly summaries from daily roundups with highlights and cross-references.

## Input
- Target Week: YYYY-MM-DD(Sun) ~ YYYY-MM-DD(Sat) (default: last week)
- Daily roundup files: AI/Roundup/{{YYYY-MM-DD}}*
- [[Weekly Roundup Template]] for structure

## Output
- File: AI/Roundup/Weekly/{{YYYY-MM-DD(1)}}~{{YYYY-MM-DD(2)}} - {{Agent-Name}}.md
- Weekly highlights with source links
- Summary section synthesizing key themes
- Original language preservation (English/한글)

## Main Process
```
1. TEMPLATE SETUP
   - Create note using [[Weekly Roundup Template]]
   - Set proper filename with date range
   - Establish section structure

2. HIGHLIGHTS COMPILATION
   - Extract highlights from daily roundups
   - List key insights and moments of the week
   - Add links to source notes & sections
   - Maintain chronological or thematic organization

3. SUMMARY SYNTHESIS
   - Add comprehensive Summary section
   - Synthesize weekly themes and patterns
   - Keep original language from source notes
```

## Caveats
### File Naming Convention
⚠️ **CRITICAL**: Use format AI/Roundup/Weekly/{{YYYY-MM-DD(1)}}~{{YYYY-MM-DD(2)}} - {{Agent-Name}}.md

### Content Standards
- Extract meaningful highlights, not just summaries
- Include links to source note & section for all highlights
- Maintain language consistency with original notes

### Week Scope
- Default to last complete week (Sunday to Saturday)
- Include all daily roundups within the target week
- Ensure comprehensive coverage of the week's content
