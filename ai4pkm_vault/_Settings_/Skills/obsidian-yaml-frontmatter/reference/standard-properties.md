# Standard Property Definitions

## Core Properties

### `title`
- **Type**: String
- **Required**: Optional (filename often sufficient)
- **Format**: Plain text or quoted if contains special chars
- **Example**: `title: "AI Era: Thriving Framework"`

### `created`
- **Type**: Date string
- **Required**: Recommended for all content
- **Format**: `YYYY-MM-DD`
- **Example**: `created: 2025-10-31`
- **Note**: Use `created` not `date` (avoid duplicates)

### `tags`
- **Type**: List of strings
- **Required**: Recommended
- **Format**: List with dashes, plain text (NO hashtags)
- **Example**:
```yaml
tags:
  - journal
  - daily
  - reflection
```

## Source Attribution

### `source`
- **Type**: String (URL or file path)
- **Required**: For ingested content (clippings, articles)
- **Format**: URL or path string
- **Example**:
  - `source: https://example.com/article`
  - `source: /path/to/file.pdf`

### `author`
- **Type**: String or quoted wiki link
- **Required**: For authored content
- **Format**: Plain text or wiki link
- **Example**:
  - `author: 무라카미 하루키`
  - `author: "[[Author Name]]"`

### `sources`
- **Type**: List of wiki links
- **Required**: For aggregated/analyzed content
- **Format**: List of quoted wiki links
- **Example**:
```yaml
sources:
  - "[[Lifelog/2025-10-31 Lifelog - Codex]]"
  - "[[Limitless/2025-10-31]]"
```

## Relational Properties

### `links`
- **Type**: List of wiki links
- **Required**: For related content
- **Format**: List of quoted wiki links
- **Example**:
```yaml
links:
  - "[[Roundup/2025-10-31]]"
  - "[[Topics/Technology/PKM]]"
```

### `attendees`
- **Type**: List of names (plain or wiki links)
- **Required**: For meetings/events
- **Format**: Mixed list (wiki links quoted, plain names unquoted)
- **Example**:
```yaml
attendees:
  - "[[진영]]"
  - 민성
  - 서경
```

## Event Properties

### `event_date`
- **Type**: Date string
- **Required**: For events/meetings
- **Format**: `YYYY-MM-DD`
- **Example**: `event_date: 2025-10-30`
- **Note**: Different from `created` (when document was created)

### `event_time`
- **Type**: Time string
- **Required**: Optional
- **Format**: `HH:MM AM/PM` or `HH:MM-HH:MM AM/PM`
- **Example**:
  - `event_time: 10:00 AM`
  - `event_time: 2:00-3:30 PM`

## Status Properties

### `status`
- **Type**: String (enum)
- **Required**: For processed content
- **Format**: Specific values (processed, pending, reviewed)
- **Example**: `status: processed`
- **Used in**: EIC workflow for clippings

## Content-Specific Properties

### For Books
```yaml
title: Book Title
author: Author Name
publisher: Publisher Name
publication_date: YYYY
isbn: ISBN number
tags:
  - book
  - reading
```

### For Articles
```yaml
title: Article Title
source: https://url
author: Author Name
created: YYYY-MM-DD
tags:
  - article
  - topic
```

### For Meetings
```yaml
title: Meeting Name
created: YYYY-MM-DD
event_date: YYYY-MM-DD
event_time: HH:MM AM/PM
attendees:
  - "[[Person 1]]"
  - Person 2
sources:
  - "[[Limitless/YYYY-MM-DD#Section]]"
tags:
  - meeting
```

## Property Naming Conventions

### Use Consistent Names
- ✅ `created` not `date`, `Date`, or `creation_date`
- ✅ `tags` not `tag`, `Tag`, or `categories`
- ✅ `source` not `url`, `link`, or `origin`
- ✅ `author` not `authors`, `by`, or `writer`

### Lowercase Keys
```yaml
✅ CORRECT:
title: Title
created: 2025-10-31

❌ INCORRECT:
Title: Title
Created: 2025-10-31
```

### No Underscores Unless Necessary
```yaml
✅ PREFERRED:
eventdate: 2025-10-31

✅ ACCEPTABLE (for clarity):
event_date: 2025-10-31

❌ AVOID:
event_Date: 2025-10-31
```

## Value Quoting Rules

### Always Quote
- URLs (contain colons): `source: "https://example.com"`
- Titles with colons: `title: "Part 1: Introduction"`
- Titles with hashes: `title: "#1 Bestseller"`
- Version numbers: `version: "2.0"` (prevent parsing as float)
- Wiki links in lists: `- "[[Link]]"`

### Optional Quote
- Plain text without special chars: `author: John Smith`
- Single-word values: `status: processed`

### Never Quote
- Numbers (unless you want them as strings): `page: 42`
- Booleans: `published: true`
- Dates in YYYY-MM-DD: `created: 2025-10-31`
