# Frontmatter Examples by Content Type

## Daily Content

### Journal Entry
```yaml
---
tags:
  - journal
  - daily
links:
  - "[[Roundup/2025-10-31]]"
---

## Morning Reflection
```

### Daily Roundup
```yaml
---
title: 2025-10-31 Daily Roundup
created: 2025-10-31
tags:
  - roundup
  - daily
sources:
  - "[[Lifelog/2025-10-31 Lifelog - Codex]]"
  - "[[Limitless/2025-10-31]]"
links:
  - "[[Topics/Philosophy/Stoicism]]"
---

# 2025-10-31 Daily Roundup
```

### Lifelog
```yaml
---
title: 2025-10-31 Lifelog
created: 2025-10-31
tags:
  - lifelog
  - daily
links:
  - "[[Limitless/2025-10-31]]"
  - "[[Roundup/2025-10-31]]"
---

# 2025-10-31 Lifelog - Codex
```

## Ingested Content

### Article/Clipping
```yaml
---
title: "Five New Thinking Styles for Working With Thinking Machines"
source: https://example.com/article
created: 2025-10-31
tags:
  - clipping
  - ai
  - thinking
status: processed
---

## Summary
```

### Book Notes
```yaml
---
title: Perennial Seller
author: Ryan Holiday
source: https://goodreads.com/book/perennial-seller
created: 2025-10-31
tags:
  - book
  - marketing
  - reading
---

## Summary
```

### Web Clipping with Multiple Authors
```yaml
---
title: "How Tools Shape How We See the World"
source: https://example.com
author:
  - "[[Author One]]"
  - "[[Author Two]]"
created: 2025-10-31
tags:
  - article
  - philosophy
status: processed
---

## Summary
```

## Created Content

### Analysis Document
```yaml
---
title: "Applying Perennial Seller Lessons to AI4PKM"
created: 2025-10-31
tags:
  - analysis
  - ai4pkm
  - strategy
sources:
  - "[[Ingest/Clippings/2025-10-31 Perennial Seller]]"
  - "[[Projects/AI4PKM/2025-10-19 AI4PKM Skills Evolution Roadmap]]"
links:
  - "[[Topics/Business & Career/Product Strategy]]"
---

## Executive Summary
```

### Event Summary
```yaml
---
title: "패캠 강의 기획 미팅"
created: 2025-10-29
event_date: 2025-10-29
event_time: 2:00-3:30 PM
attendees:
  - "[[진영]]"
  - 민성
  - 서경
sources:
  - "[[Limitless/2025-10-29#패캠 미팅]]"
tags:
  - meeting
  - event
  - ai4pkm
---

## Executive Summary
```

### Task Document
```yaml
---
title: "PKM Meeting Prep"
created: 2025-10-30
due_date: 2025-10-30
tags:
  - task
  - meeting-prep
links:
  - "[[Events/2025-10-30 PKM Meeting]]"
---

## Objectives
```

## Topic Pages

### Technology Topic
```yaml
---
title: Personal Knowledge Management
tags:
  - topic
  - technology
  - pkm
---

## Overview
```

### Philosophy Topic
```yaml
---
title: Stoicism
tags:
  - topic
  - philosophy
  - life
links:
  - "[[Topics/Philosophy/Marcus Aurelius]]"
  - "[[Topics/Philosophy/Seneca]]"
---

## Core Principles
```

## Project Pages

### Project Overview
```yaml
---
title: AI4PKM Project
created: 2025-08-01
tags:
  - project
  - ai4pkm
  - pkm
links:
  - "[[Projects/AI4PKM/README]]"
---

## Project Mission
```

### Project Document
```yaml
---
title: "AI4PKM Skills Evolution Roadmap"
created: 2025-10-19
tags:
  - roadmap
  - ai4pkm
  - planning
links:
  - "[[Projects/AI4PKM/README]]"
---

## Roadmap Overview
```

## Special Cases

### Voice Conversation
```yaml
---
title: 2025-10-31 Voice Conversation
created: 2025-10-31
tags:
  - voice
  - conversation
---

# Voice Conversation - 2025-10-31

## Session 1: Morning Check-in (7:54 AM)
```

### Photo Documentation
```yaml
---
title: "2025-09-06 Museum Visit Photos"
created: 2025-09-06
event_date: 2025-09-06
tags:
  - photo
  - family
  - museum
links:
  - "[[Lifelog/2025-09-06 Lifelog - Codex]]"
---

## Photos
```

## Common Mistakes vs Corrections

### Mistake: Hashtags in YAML
```yaml
❌ INCORRECT:
tags:
  - #journal
  - #daily

✅ CORRECT:
tags:
  - journal
  - daily
```

### Mistake: Missing Quotes on Links
```yaml
❌ INCORRECT:
sources:
  - [[Limitless/2025-10-31]]

✅ CORRECT:
sources:
  - "[[Limitless/2025-10-31]]"
```

### Mistake: Inconsistent Property Names
```yaml
❌ INCORRECT:
date: 2025-10-31
Created: 2025-10-31

✅ CORRECT:
created: 2025-10-31
```

### Mistake: Content Before First Heading
```yaml
❌ INCORRECT:
---
title: Document
---
This is intro text before heading.

## First Section

✅ CORRECT:
---
title: Document
---

## Introduction
This is intro text in a section.
```

### Mistake: Missing Blank Line After Frontmatter
```yaml
❌ INCORRECT:
---
title: Document
---
## First Section

✅ CORRECT:
---
title: Document
---

## First Section
```

### Mistake: Unquoted Colons
```yaml
❌ INCORRECT:
title: Part 1: Introduction
source: https://example.com

✅ CORRECT:
title: "Part 1: Introduction"
source: "https://example.com"
```
