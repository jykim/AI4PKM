# Structure by Content Type

## Daily Content Types

### Lifelog Structure
```markdown
---
title: YYYY-MM-DD Lifelog
created: YYYY-MM-DD
tags:
  - lifelog
  - daily
links:
  - "[[Limitless/YYYY-MM-DD]]"
  - "[[Roundup/YYYY-MM-DD]]"
---

# YYYY-MM-DD Lifelog - Agent Name

## Monologues
Voice memos, thoughts, and personal reflections captured throughout the day.

### Morning Thoughts (HH:MM AM)
Content...

### Afternoon Reflection (HH:MM PM)
Content...

## Conversations
Dialogues and interactions with others.

### Conversation with [Person] (HH:MM AM)
- Topic discussed
- Key points

## Contents
Books, articles, videos, and other content consumed.

### Reading
- [[Source Title]] - Key takeaways

### Watching
- Video/Media title - Notes

## Actions & Reflections
Activities, tasks, and reflections on what was done.

### Work Activities
- Task completed
- Project progress

### Personal Activities
- Exercise, hobbies, etc.

## Photos
Visual documentation of the day.

### Event/Activity Name
Images and context
```

**Key Rules**:
- Use H1 for title (exception to no-H1 rule)
- H2 for main categories (Monologues, Conversations, etc.)
- H3 for time-stamped entries or subcategories
- Include timestamp in H3 when applicable

---

### Daily Roundup Structure
```markdown
---
title: YYYY-MM-DD Daily Roundup
created: YYYY-MM-DD
tags:
  - roundup
  - daily
sources:
  - "[[Lifelog/YYYY-MM-DD Lifelog - Agent]]"
  - "[[Limitless/YYYY-MM-DD]]"
links:
  - "[[Topics/Category/Topic]]"
---

# YYYY-MM-DD Daily Roundup

> "Opening quote that captures the day's essence"
> - Attribution, via [[Source#Section]]

## 하루 요약
2-3 sentence high-level summary of the day's significance.

## 주요 활동

### 카테고리 1 (e.g., Work, Family)
#### 구체적 활동 제목 (HH:MM AM/PM)
[[Source#Section]]

Description of activity with key points.

#### 다른 활동 제목 (HH:MM PM)
Content...

### 카테고리 2
Content...

## 명언 & 인사이트

### [Theme/Topic]
> "Quote text"
> - Attribution, via [[Source#Section]]

Analysis or reflection on the quote.

### [Another Theme]
Content...

## 핵심 배움

### [Learning Theme 1]
[[Source#Section]]

What was learned and why it matters.

### [Learning Theme 2]
Content...

## 성찰
Personal reflections, connections between ideas, meta-observations about the day.

## 관련 주제
- [[Topics/Category/Topic 1]]
- [[Topics/Category/Topic 2]]

## Source Coverage
### Lifelog Coverage
- ✅ Section 1
- ✅ Section 2
- ⚠️  Section 3 (brief mention)

### Limitless Coverage
- ✅ Major conversation
- ⚠️  Minor note
```

**Key Rules**:
- Opening quote(s) before first H2
- Korean section headers
- H3 for categories, H4 for specific items
- Source links with section references
- Source coverage section at end

---

### Journal Entry Structure
```markdown
---
tags:
  - journal
  - daily
links:
  - "[[Roundup/YYYY-MM-DD]]"
---

## Morning Reflection
Free-form writing...

## Evening Reflection
Free-form writing...
```

**Key Rules**:
- No title property (date in filename)
- Start with H2
- Free-form structure
- Brief, personal content

---

## Ingested Content Types

### Clipping/Article Structure
```markdown
---
title: Article Title
source: https://url
created: YYYY-MM-DD
author: Author Name
tags:
  - clipping
  - category
  - topic
status: processed
---

## Summary

### 핵심 주제
Main theme or thesis in 2-3 sentences.

### 주요 내용
- Key point 1
- Key point 2
- Key point 3

### 개인적 의미
Why this matters, connections to other ideas.

## Improve Capture & Transcript (ICT)

### Chapter/Section 1 Title
Improved formatting with proper grammar, structure, and translation.

Key points or highlights from this section.

### Chapter/Section 2 Title
Content...

### Chapter/Section 3 Title
Content...
```

**Key Rules**:
- Summary section first with Korean H3 subsections
- ICT section improves transcript (doesn't summarize)
- ICT length comparable to source
- H3 for chapters/sections
- Status property indicates processed

---

### Book Notes Structure
```markdown
---
title: Book Title
author: Author Name
publisher: Publisher
publication_date: YYYY
source: URL (Goodreads, etc.)
created: YYYY-MM-DD
tags:
  - book
  - reading
  - category
---

## Summary
Overview of book's main themes and arguments.

## Key Concepts

### Concept 1
Explanation...

### Concept 2
Explanation...

## Highlights

### Chapter 1
> "Quote"

Notes and reflections...

### Chapter 2
Content...

## Personal Reflections
How this book relates to my life, work, or other ideas.

## Related
- [[Other Book]]
- [[Related Topic]]
```

**Key Rules**:
- Bibliographic info in frontmatter
- Summary first
- Key concepts before detailed notes
- Personal reflections included

---

## Created Content Types

### Analysis Document Structure
```markdown
---
title: Analysis Title
created: YYYY-MM-DD
tags:
  - analysis
  - category
sources:
  - "[[Source 1]]"
  - "[[Source 2]]"
links:
  - "[[Topics/Category/Topic]]"
---

## Executive Summary
High-level overview of analysis and key findings.

## Context
Background information and motivation for analysis.

## Key Findings

### Finding 1
[[Source#Section]]

Evidence and explanation...

### Finding 2
Content...

## Synthesis
Connections between findings, higher-level insights.

## Implications
What this means, next steps, applications.

## Related Topics
- [[Topics/Category/Topic]]
```

**Key Rules**:
- Executive summary first
- Source attribution inline
- Clear finding → synthesis → implications flow
- Related topics at end

---

### Event/Meeting Summary Structure
```markdown
---
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
  - event
  - category
---

# Meeting Name

## Executive Summary
2-3 sentences capturing key outcomes and decisions.

## [Main Topic 1]
[[Source#Section]]

Discussion points, decisions made, context.

### Subtopic
Details...

## [Main Topic 2]
Content...

## Key Takeaways
- Takeaway 1
- Takeaway 2
- Takeaway 3

## Next Actions
- [ ] Action item 1 - Owner
- [ ] Action item 2 - Owner
```

**Key Rules**:
- Event metadata in frontmatter
- Executive summary first
- Topic-based sections (not time-based)
- Key takeaways section
- Next actions with owners

---

### Task Document Structure
```markdown
---
title: Task Name
created: YYYY-MM-DD
due_date: YYYY-MM-DD
tags:
  - task
  - category
links:
  - "[[Related Doc]]"
---

## Objectives
What needs to be accomplished and why.

## Context
Background information, motivation.

## Approach
How to accomplish the task.

### Step 1
Details...

### Step 2
Details...

## Resources
- [[Relevant Doc 1]]
- [[Relevant Doc 2]]
- External URL

## Progress
- [x] Completed step
- [ ] Pending step
```

**Key Rules**:
- Due date in frontmatter
- Clear objectives first
- Step-by-step approach
- Progress tracking

---

## Topic/Reference Content Types

### Topic Page Structure
```markdown
---
title: Topic Name
tags:
  - topic
  - category
links:
  - "[[Related Topic 1]]"
  - "[[Related Topic 2]]"
---

## Overview
What this topic is, why it matters.

## Key Concepts
Main ideas, theories, frameworks related to this topic.

## Resources
- [[Source 1]]
- [[Source 2]]

## Related Topics
- [[Topic 1]]
- [[Topic 2]]
```

**Key Rules**:
- No created date (evergreen content)
- Overview first
- Links to sources and related topics
- Avoid duplicating source content (link instead)

---

## Structure Comparison

### Content Before First Heading

```markdown
❌ INCORRECT:
---
frontmatter
---
This is intro text before any heading.

## First Section

✅ CORRECT:
---
frontmatter
---

## Introduction
This is intro text in a proper section.
```

### Heading Hierarchy

```markdown
❌ INCORRECT:
## Section 1
#### Subsection (skipped H3)

✅ CORRECT:
## Section 1
### Subsection
#### Sub-subsection
```

### Quote Formatting

```markdown
❌ INCORRECT:
"Quote text" - Speaker

✅ CORRECT:
> "Quote text"
> - Speaker, via [[Source#Section]]
```
