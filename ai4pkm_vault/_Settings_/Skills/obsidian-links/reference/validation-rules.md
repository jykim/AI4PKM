# Link Validation Rules

## Complete Validation Process

### Before Creating Any Link

```markdown
MANDATORY STEPS:

1. ✅ Identify target file
   - Full filename with date (if applicable)
   - Folder location

2. ✅ Verify file exists
   - Use Glob to search for file
   - Or Read file directly to confirm

3. ✅ If section link needed:
   - Read target file content
   - Search for exact header text
   - Copy character-for-character

4. ✅ Create link with verified information
   - Complete filename
   - Exact section header (if applicable)

❌ NEVER skip verification steps
❌ NEVER guess at filenames or headers
```

## File Existence Verification Methods

### Method 1: Glob Pattern Search
```bash
# Search for specific file
Glob: "Limitless/2025-10-31.md"

# Search for files by keyword
Glob: "Ingest/Clippings/*Perennial Seller*.md"

# Search for topic pages
Glob: "Topics/**/*PKM*.md"

# Search AI folder content
Glob: "AI/Lifelog/2025-10-31*.md"
```

### Method 2: Direct File Read
```bash
# Try to read file directly
Read: "/path/to/vault/Limitless/2025-10-31.md"

# If successful -> file exists
# If error -> file doesn't exist
```

### Method 3: Grep Search
```bash
# Search for files containing specific content
Grep: "pattern" in "Limitless/"

# Useful for finding files by content
```

## Section Header Verification

### Step-by-Step Process

```markdown
1. Read target file completely

2. Search for header pattern:
   - Look for "## {Header Text}"
   - Or "### {Header Text}" for subheaders

3. Extract exact header text:
   - Include all characters after ##
   - Include Korean characters
   - Include punctuation
   - Include spacing
   - Include emojis

4. Verify match:
   ✅ Character-for-character match
   ❌ Partial match (truncated)
   ❌ Paraphrased match

5. Create section link with exact text
```

### Example: Limitless Section Verification

```markdown
File: Limitless/2025-10-31.md

Step 1: Read file
Read: "Limitless/2025-10-31.md"

Step 2: Search for Korean headers
Found:
- ## Jin's Mortgage Payoff and Credit Card Inquiry
- ## PNC Voice Banking Call
- ## 라이언 홀리데이의 책과 스토아 철학을 통한 현대 사회의 지혜 탐구

Step 3: Choose target header
Target: "라이언 홀리데이의 책과 스토아 철학을 통한 현대 사회의 지혜 탐구"

Step 4: Create link
✅ [[Limitless/2025-10-31#라이언 홀리데이의 책과 스토아 철학을 통한 현대 사회의 지혜 탐구]]

❌ [[Limitless/2025-10-31#라이언 홀리데이]] (truncated)
❌ [[Limitless/2025-10-31#스토아 철학]] (partial)
```

## Path Resolution Rules

### Rule 1: Date-Based Files

```markdown
Pattern: YYYY-MM-DD Title.md

Locations to check (in order):
1. Limitless/YYYY-MM-DD.md
2. Journal/YYYY-MM-DD.md
3. AI/Lifelog/YYYY-MM-DD Lifelog - Agent.md
4. AI/Roundup/YYYY-MM-DD.md
5. Ingest/Clippings/YYYY-MM-DD Title.md

Link format:
- [[Limitless/2025-10-31]]
- [[Journal/2025-10-31]]
- [[Lifelog/2025-10-31 Lifelog - Codex]]
- [[Roundup/2025-10-31]] (omit AI/)
- [[Ingest/Clippings/2025-10-31 Title]]
```

### Rule 2: Topic Pages

```markdown
Location: Topics/{Category}/{Page}.md

CRITICAL: Search Topics directory BEFORE linking

Search process:
1. Glob: "Topics/**/*{keyword}*.md"
2. Verify exact category path
3. Use complete path in link

Examples:
- Topics/Technology/PKM.md → [[Topics/Technology/PKM]]
- Topics/Business & Career/Career.md → [[Topics/Business & Career/Career]]
- Topics/Philosophy/Stoicism.md → [[Topics/Philosophy/Stoicism]]

❌ NEVER link to non-existent topic pages
❌ NEVER guess at category names
```

### Rule 3: Ingested Content

```markdown
Location: Ingest/{Type}/YYYY-MM-DD Title.md

Types:
- Clippings/
- Articles/
- Books/
- Limitless/

Link format:
- [[Ingest/Clippings/2025-10-31 Perennial Seller]]
- [[Ingest/Articles/2025-08-15 역스킬 현상]]
- [[Limitless/2025-10-31]] (special: no Ingest/ prefix)

Source attribution rule:
✅ Link to Ingest/{Type}/{File}
❌ Don't link to Topics/{Category}
```

### Rule 4: AI-Generated Content

```markdown
Location: AI/{Type}/File.md

Types:
- Roundup/
- Lifelog/
- Events/
- Tasks/
- Analysis/

Link format (OMIT "AI/" prefix):
- [[Roundup/2025-10-31]]
- [[Lifelog/2025-10-31 Lifelog - Codex]]
- [[Events/2025-10-30 PKM Meeting]]
- [[Tasks/2025-10-30 Task]]
- [[Analysis/2025-10-31 Analysis]]

❌ NEVER include "AI/" in link
❌ [[AI/Roundup/2025-10-31]] (incorrect)
```

## Broken Link Detection & Fixing

### Detection Process

```markdown
1. Read document content

2. Extract all wiki links:
   - Pattern: [[...]]
   - Parse into: filename, section (optional)

3. For each link:
   a. Check if file exists
   b. If section link, verify section exists
   c. Mark as broken if not found

4. Compile list of broken links
```

### Fixing Process

```markdown
For each broken link:

1. Identify what user intended to link to:
   - Use context from surrounding text
   - Search for similar filenames
   - Check for date-based files

2. Find correct target:
   - Use Glob to search vault
   - Verify file exists
   - Read file to verify sections

3. Update link:
   - Replace broken link with correct path
   - Verify section header if applicable
   - Use Edit tool to fix in place

4. Report fix:
   - Old link (broken)
   - New link (fixed)
   - Reason for fix
```

### Example: Fix Broken Topic Link

```markdown
Broken link found:
[[Career#역스킬]]

Detection:
- File "Career.md" not found in root
- Ambiguous reference

Search process:
1. Glob: "Topics/**/*Career*.md"
2. Found: Topics/Business & Career/Career.md
3. Read file to find section "역스킬"

Fix:
Old: [[Career#역스킬]]
New: [[Topics/Business & Career/Career#역스킬]]

But BETTER: Link to source
[[Ingest/Articles/2025-08-15 역스킬 현상]]

Reason: Maintains source attribution
```

### Example: Fix Broken Limitless Section Link

```markdown
Broken link found:
[[Limitless/2025-10-31#Mortgage]]

Detection:
- File exists: Limitless/2025-10-31.md
- Section "Mortgage" not found (guessed header)

Search process:
1. Read: Limitless/2025-10-31.md
2. Search for mortgage-related headers
3. Found: "## Jin's Mortgage Payoff and Credit Card Inquiry"

Fix:
Old: [[Limitless/2025-10-31#Mortgage]]
New: [[Limitless/2025-10-31#Jin's Mortgage Payoff and Credit Card Inquiry]]

Reason: Exact header match required
```

## Validation Checklists

### Before Creating Link
- [ ] Target file path determined
- [ ] File existence verified (Glob/Read)
- [ ] Section header verified (if applicable)
- [ ] Exact text copied (Korean, punctuation, spacing)
- [ ] Path follows conventions (omit AI/, include folder)

### After Creating Link
- [ ] Link uses complete filename
- [ ] Section header matches exactly
- [ ] Path format correct (AI/ omitted where applicable)
- [ ] Link points to source (not index)

### When Fixing Broken Links
- [ ] All broken links identified
- [ ] Correct targets found
- [ ] Links updated in document
- [ ] Section headers verified
- [ ] Changes reported to user

## Error Prevention

### Common Mistakes to Avoid

```markdown
❌ Guessing at filenames
❌ Truncating section headers
❌ Linking to topic indices instead of sources
❌ Including "AI/" prefix for AI folder files
❌ Using partial/paraphrased section headers
❌ Assuming files exist without verification
❌ Creating links before verification
❌ Missing folder prefixes (Limitless/, Topics/, etc.)
```

### Verification Habits

```markdown
✅ Always search before linking
✅ Always read file for section links
✅ Always match character-for-character
✅ Always use complete filenames
✅ Always check Topics directory
✅ Always link to sources
✅ Always fix broken links immediately
✅ Always verify AI folder path format
```
