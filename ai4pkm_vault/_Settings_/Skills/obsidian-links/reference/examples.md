# Wiki Link Examples

## Basic File Links

### Daily Content
```markdown
✅ CORRECT:
- [[Limitless/2025-10-31]]
- [[Journal/2025-10-31]]
- [[Lifelog/2025-10-31 Lifelog - Codex]]
- [[Roundup/2025-10-31]] (note: omits "AI/" prefix)

❌ INCORRECT:
- [[2025-10-31]] (ambiguous, which file?)
- [[Limitless]] (missing date)
- [[AI/Lifelog/2025-10-31 Lifelog - Codex]] (unnecessary AI/ prefix)
```

### Content Files
```markdown
✅ CORRECT:
- [[Ingest/Clippings/2025-10-31 Perennial Seller]]
- [[Ingest/Articles/2025-08-15 역스킬 현상]]
- [[Topics/Technology/PKM]]
- [[Projects/AI4PKM/2025-10-19 AI4PKM Skills Evolution Roadmap]]

❌ INCORRECT:
- [[Perennial Seller]] (missing path and date)
- [[Topics/PKM]] (missing category folder)
```

## Section Links

### Korean Headers
```markdown
Source: ## PKM 시스템 유지 관리의 어려움과 업무량 감소 방안 모색

✅ CORRECT:
[[Limitless/2025-10-31#PKM 시스템 유지 관리의 어려움과 업무량 감소 방안 모색]]

❌ INCORRECT:
[[Limitless/2025-10-31#PKM 시스템]] (truncated)
[[Limitless/2025-10-31#pkm 시스템 유지]] (lowercase, missing words)
```

### English Headers
```markdown
Source: ## Executive Summary

✅ CORRECT:
[[Events/2025-10-30 PKM Meeting#Executive Summary]]

❌ INCORRECT:
[[Events/2025-10-30 PKM Meeting#executive-summary]] (slug format)
[[Events/2025-10-30 PKM Meeting#Summary]] (word missing)
```

### Mixed Language Headers
```markdown
Source: ## AI4PKM 커뮤니티 미팅 준비

✅ CORRECT:
[[Tasks/2025-10-30 PKM Meeting Prep#AI4PKM 커뮤니티 미팅 준비]]

❌ INCORRECT:
[[Tasks/2025-10-30 PKM Meeting Prep#AI4PKM 미팅 준비]] (missing word)
```

## YAML Property Links

### Source Lists
```yaml
✅ CORRECT:
sources:
  - "[[Lifelog/2025-10-31 Lifelog - Codex]]"
  - "[[Limitless/2025-10-31]]"
  - "[[Ingest/Clippings/2025-10-31 Perennial Seller]]"

❌ INCORRECT:
sources:
  - [[Lifelog/2025-10-31 Lifelog - Codex]] (missing quotes)
  - "[[AI/Lifelog/2025-10-31 Lifelog - Codex]]" (unnecessary AI/)
```

### Related Links
```yaml
✅ CORRECT:
links:
  - "[[Roundup/2025-10-31]]"
  - "[[Topics/Technology/PKM]]"

❌ INCORRECT:
links:
  - [[Roundup/2025-10-31]] (missing quotes)
  - "[[AI/Roundup/2025-10-31]]" (unnecessary AI/)
```

### Attendees/People
```yaml
✅ CORRECT:
attendees:
  - "[[진영]]"
  - 민성
  - 서경

author:
  - "[[무라카미 하루키]]"

❌ INCORRECT:
attendees:
  - [[진영]] (missing quotes for wiki link)
```

## Source vs Index Links

### Linking to Original Sources
```markdown
✅ CORRECT (link to source):
"[[Ingest/Articles/2025-08-15 역스킬 현상]]에 따르면..."

Reason: Links to original article where concept first appeared
```

### Avoid Linking to Topic Indices
```markdown
❌ INCORRECT (link to aggregation):
"[[Topics/Business & Career/Career#역스킬]]에 따르면..."

Reason: Topic pages are indices/summaries, not original sources
Should link to: [[Ingest/Articles/2025-08-15 역스킬 현상]]
```

## Real Examples from Vault

### From Daily Roundup
```markdown
✅ Actual usage:
[[Limitless/2025-10-31#Jin's Mortgage Payoff and Credit Card Inquiry]]
[[Limitless/2025-10-31#PNC Voice Banking Call]]
[[Ingest/Clippings/2025-10-31 Perennial Seller]]
```

### From Lifelog
```yaml
✅ Actual frontmatter:
links:
  - "[[Limitless/2025-11-01]]"
  - "[[Roundup/2025-11-01]]"
```

### From Event Summary
```yaml
✅ Actual frontmatter:
sources:
  - "[[Limitless/2025-10-30#AI4PKM 커뮤니티 미팅]]"
attendees:
  - "[[진영]]"
  - 민성
  - 서경
```
