# Edge Cases and Special Situations

## Limitless File Linking

### Path Format
```markdown
✅ CORRECT: [[Limitless/2025-10-31]]
❌ INCORRECT: [[Ingest/Limitless/2025-10-31]]

Reason: Limitless files are at root level of Limitless/, not under Ingest/
```

### Section Header Verification
```markdown
CRITICAL: Always verify section exists before linking

Process:
1. Read source Limitless file
2. Find exact header text
3. Copy character-for-character (including Korean, punctuation, spaces)
4. Create section link

✅ CORRECT workflow:
- Read: [[Limitless/2025-10-31]]
- Find: "## Jin's Mortgage Payoff and Credit Card Inquiry"
- Link: [[Limitless/2025-10-31#Jin's Mortgage Payoff and Credit Card Inquiry]]

❌ INCORRECT workflow:
- Guess: [[Limitless/2025-10-31#Mortgage Payoff]] (fabricated header)
```

### When Section is Uncertain
```markdown
If you cannot verify exact header text:

✅ SAFE: Link to file only
[[Limitless/2025-10-31]]

❌ RISKY: Guess at section header
[[Limitless/2025-10-31#Mortgage]] (might not exist)
```

## Special Characters in Headers

### Punctuation Preservation
```markdown
Source: ## What's the plan? (Discussion)

✅ CORRECT:
[[File#What's the plan? (Discussion)]]

❌ INCORRECT:
[[File#Whats the plan Discussion]] (removed apostrophe and parentheses)
```

### Korean Punctuation
```markdown
Source: ## 6개월 휴직을 통해 배운 점 🌱

✅ CORRECT:
[[File#6개월 휴직을 통해 배운 점 🌱]] (includes emoji)

Note: Emojis are part of header text
```

### Colons and Special Symbols
```markdown
Source: ## Key Insight: AI Multiplier Effect

✅ CORRECT:
[[File#Key Insight: AI Multiplier Effect]]

❌ INCORRECT:
[[File#Key Insight - AI Multiplier Effect]] (changed colon to dash)
```

## Ambiguous Filenames

### Multiple Files with Similar Names
```markdown
Files:
- Ingest/Clippings/2025-10-31 Perennial Seller.md
- Projects/Writing/2025-11-01 Perennial Seller Analysis.md

✅ CORRECT: Use full path to disambiguate
- [[Ingest/Clippings/2025-10-31 Perennial Seller]]
- [[Projects/Writing/2025-11-01 Perennial Seller Analysis]]

❌ INCORRECT: Ambiguous reference
- [[Perennial Seller]] (which file?)
```

## Files Without Dates

### Topic Pages
```markdown
✅ CORRECT: [[Topics/Technology/PKM]]
✅ CORRECT: [[Topics/Business & Career/Career]]

Note: Topic files don't have date prefixes
```

### Template Files
```markdown
✅ CORRECT: [[_Settings_/Templates/Daily Journal]]
```

### Project Files
```markdown
Some project files have dates:
✅ [[Projects/AI4PKM/2025-10-19 AI4PKM Skills Evolution Roadmap]]

Some don't:
✅ [[Projects/AI4PKM/README]]
```

## Section Links with Numbering

### Auto-numbered Headers
```markdown
Source headers may have auto-numbering:
## 1. Introduction
## 2. Main Content

Link format depends on actual markdown:

If numbered in markdown:
✅ [[File#1. Introduction]]

If Obsidian auto-numbers:
✅ [[File#Introduction]] (omit number)

Rule: Match exactly what's in the markdown source
```

## Long Headers

### Full Header vs Truncation
```markdown
Source: ## PKM 시스템 유지 관리의 어려움과 업무량 감소 방안 모색 및 AI4PKM 커뮤니티 활동 계획

✅ CORRECT: Use full header
[[File#PKM 시스템 유지 관리의 어려움과 업무량 감소 방안 모색 및 AI4PKM 커뮤니티 활동 계획]]

❌ INCORRECT: Truncate for brevity
[[File#PKM 시스템 유지 관리]] (will not resolve)

Note: Obsidian requires exact match, cannot truncate
```

## Block Links vs Section Links

### Prefer Section Links
```markdown
✅ PREFERRED: [[File#Section Header]]
Reason: Headers are visible, semantic, stable

❌ AVOID: [[File#^block-id]]
Reason: Block IDs are invisible, arbitrary, fragile
```

## Links in Code Blocks

### No Link Formatting in Code
```markdown
When showing examples in code blocks, links don't resolve:

```markdown
[[This won't resolve as a link]]
```

This is expected behavior - only use wiki links in regular text.
```

## AI Folder Prefix Rules

### When to Omit "AI/"
```markdown
These folders are under AI/, omit prefix:
✅ [[Roundup/2025-10-31]] not [[AI/Roundup/2025-10-31]]
✅ [[Lifelog/2025-10-31 Lifelog - Codex]]
✅ [[Events/2025-10-30 PKM Meeting]]
✅ [[Tasks/2025-10-30 Task]]
✅ [[Analysis/2025-10-31 Analysis]]
```

### When to Keep Folder Path
```markdown
These are NOT under AI/, keep full path:
✅ [[Ingest/Clippings/2025-10-31 Article]]
✅ [[Topics/Technology/PKM]]
✅ [[Projects/AI4PKM/README]]
✅ [[Limitless/2025-10-31]]
```
