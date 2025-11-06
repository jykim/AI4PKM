---
name: obsidian-links
description: Format and validate Obsidian wiki links with proper filename, section, and folder conventions. Verify links exist before creation and fix broken links. Use when creating or checking wiki links in markdown files.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Edit
license: MIT
---

# Obsidian Wiki Links

Format, validate, and fix wiki links according to vault conventions.

## When to Use This Skill

Activate when you need to:
- Create wiki links to other vault files
- Add section links to specific headers
- Format links in YAML frontmatter properties
- Verify links point to existing files/sections
- Find and fix broken links
- Validate link integrity in documents

## Core Link Formatting Rules

### 1. Complete Filename Format

**Always use full filename with date prefix**:
```markdown
✅ CORRECT: [[2025-10-31 Lifelog - Codex]]
❌ INCORRECT: [[Lifelog - Codex]] (missing date)
❌ INCORRECT: [[2025-10-31]] (missing title)
```

### 2. Folder Path Conventions

**Include folder prefix for clarity, except for AI folder**:
```markdown
✅ CORRECT: [[Limitless/2025-10-31]]
✅ CORRECT: [[Ingest/Clippings/2025-10-31 Perennial Seller]]
✅ CORRECT: [[Roundup/2025-10-31]] (omit "AI/" prefix)

❌ INCORRECT: [[AI/Roundup/2025-10-31]] (unnecessary prefix)
```

**Rule**: For files in `AI/` folder, omit the "AI/" prefix for brevity.

### 3. Section Links

**Use exact header text, character-for-character**:
```markdown
Source file header:
## PKM 시스템 유지 관리의 어려움과 업무량 감소 방안 모색

✅ CORRECT:
[[Limitless/2025-10-31#PKM 시스템 유지 관리의 어려움과 업무량 감소 방안 모색]]

❌ INCORRECT:
[[Limitless/2025-10-31#PKM 시스템]] (truncated)
[[Limitless/2025-10-31#pkm-시스템-유지]] (slug format)
```

**Critical**: Match Korean characters, punctuation, spacing exactly as written.

### 4. Link to Sources, Not Indices

**Always link to original content, not topic aggregations**:
```markdown
✅ CORRECT: [[Ingest/Articles/2025-08-15 역스킬 현상]]
❌ INCORRECT: [[Topics/Business & Career/Career#역스킬]]

Reason: Maintains source attribution and traceability
```

### 5. Properties Link Format

**Wrap links in quotes when used in YAML lists**:
```yaml
sources:
  - "[[Lifelog/2025-10-31 Lifelog - Codex]]"
  - "[[Limitless/2025-10-31]]"

links:
  - "[[Roundup/2025-10-31]]"

attendees:
  - "[[진영]]"
```

## Link Validation Principles

### 1. Search Before Link

**ALWAYS verify target exists before creating link**:
```markdown
Process:
1. Search for target file using Glob or Grep
2. Verify file exists
3. If section link, read file and verify header exists
4. Create link with exact filename and header text

❌ NEVER:
- Guess at filenames
- Assume files exist
- Fabricate section headers
```

### 2. Verify Section Headers

**For section links, read source and match exactly**:
```markdown
Steps:
1. Read target file
2. Search for exact header text
3. Copy character-for-character (Korean, punctuation, spaces)
4. Create section link

If unsure about exact header:
✅ Link to file only: [[Limitless/2025-10-31]]
❌ Don't guess: [[Limitless/2025-10-31#Guessed Header]]
```

### 3. File Existence Checking

**Use appropriate tools to verify files**:
```markdown
For specific file:
- Use Glob with full path pattern: "Limitless/2025-10-31.md"
- Or Read the file directly

For finding files by keyword:
- Use Glob with pattern: "Ingest/**/*keyword*.md"
- Check Topics directory before linking to topics
```

### 4. Fix Broken Links Immediately

**When you find broken links, fix them**:
```markdown
Process:
1. Identify broken link
2. Search for correct target file
3. Update link with correct path/filename (use Edit tool)
4. Verify section header if applicable
5. Report fix to user
```

## Complete Workflow

### Creating New Links (Format + Validate)

```markdown
Step 1: Determine Target
- Identify file to link to
- Note folder location
- Note complete filename

Step 2: Verify File Exists
- Use Glob: "**/{filename}.md"
- Or Read file directly
- If not found, search by keyword

Step 3: Verify Section (if needed)
- Read target file
- Search for exact header text
- Copy character-for-character
- If unsure, link to file only

Step 4: Format Link
- Use complete filename: [[YYYY-MM-DD Title]]
- Add folder prefix (except AI/)
- Add section if verified: [[File#Exact Header]]
- Wrap in quotes if in YAML property

Step 5: Create Link
- Link points to existing file
- Section header matches exactly (if used)
- Follows folder prefix conventions
```

### Finding and Fixing Broken Links

```markdown
Step 1: Detection
- Read document content
- Extract all wiki links
- For each link, verify file exists
- For section links, verify header exists

Step 2: Search for Correct Target
- Use context to determine intent
- Search vault with Glob/Grep
- Verify file exists

Step 3: Fix Link
- Use Edit tool to update broken link
- Replace with correct path/filename
- Verify section header if applicable

Step 4: Report
- Show old link (broken)
- Show new link (fixed)
- Explain reason for fix
```

## Special Cases

### Limitless Files
```markdown
Path: Limitless/YYYY-MM-DD.md
Format: [[Limitless/YYYY-MM-DD]] (no "Ingest/" prefix)

Section links:
- Headers are usually Korean
- ALWAYS verify exact text before linking
- If unsure, link to file only

Validation:
1. Check file: Limitless/YYYY-MM-DD.md
2. Read file content
3. Search for exact Korean header
4. Use exact match or file-only link
```

### Topic Links
```markdown
CRITICAL: Search Topics directory BEFORE linking

Validation:
1. Use Glob: "Topics/**/*{keyword}*.md"
2. Find matching topic page
3. Use complete category path

Examples:
- [[Topics/Technology/PKM]]
- [[Topics/Business & Career/Career]]

❌ NEVER link to non-existent topic pages
```

### AI Folder Files
```markdown
Path: AI/Roundup/YYYY-MM-DD.md
Format: [[Roundup/YYYY-MM-DD]] (omit "AI/")

Applies to: Roundup/, Lifelog/, Analysis/, Events/, Tasks/

Validation:
1. Check file in AI/{subfolder}/
2. Link format omits "AI/" prefix
```

### Person Names
```markdown
Simple name: [[진영]]
With context: [[People/진영]] (if folder exists)

Validation: Verify person file exists before linking
```

## Reference Documentation

For detailed examples, edge cases, and validation rules:
- `reference/examples.md` - Correct/incorrect examples by scenario
- `reference/edge-cases.md` - Limitless links, special characters, ambiguous headers
- `reference/validation-rules.md` - Complete validation procedures and fix workflows

## Quality Checklist

Before completing link operations:

**Formatting**:
- [ ] All links use complete filenames
- [ ] Folder prefixes follow conventions (omit AI/)
- [ ] Section headers match exactly (character-for-character)
- [ ] Links in YAML properties are wrapped in quotes
- [ ] All links point to sources, not topic indices

**Validation**:
- [ ] All target files verified to exist
- [ ] Section headers verified (not guessed)
- [ ] Limitless section headers verified in file
- [ ] Topic links point to existing topic pages
- [ ] Broken links identified and fixed
