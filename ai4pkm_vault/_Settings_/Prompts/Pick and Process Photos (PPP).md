---
title: "Pick and Process Photos"
abbreviation: "PPP"
category: "workflow"
created: "2024-01-01"
---

Process and curate daily photos into organized photologs with quality filtering and accurate timestamping.

## Input
- Image & metadata (yaml) files in `Ingest/Photolog/Processed/`
- Calendar schedule (via MCP) for contextual understanding
- Target date for photo processing (daily basis)
- [[_Settings_/Templates/Photolog Template]] for structure

## Output
- File: `Ingest/Photolog/{YYYYMMDD} Photolog.md`
- Curated selection of 5-10 representative photos per day
- Categorized by time of day and content type (activities vs food)
- Inline image format with exact EXIF timestamps

## Main Process
```
1. CONTENT REVIEW & CAPTIONING
   - Review image & metadata files in processed folder
   - Add descriptive, specific captions based on content
   - Quality check: remove low-quality images (dark, blurry, low contrast)
   - Note: processed photos accessible despite .gitignore

2. PHOTO SELECTION
   - Pull schedule via MCP for day context
   - Select representative photos showing how day went
   - Include food items for separate logging
   - Avoid near-duplicate photos
   - Focus on story-telling and key moments
   - Sample across different times for >20 photo days

3. PHOTOLOG GENERATION
   - Create daily catalog using template structure
   - Categorize by time and content type
   - Use exact EXIF timestamps (HH:MM from DateTimeOriginal)
   - Apply inline image format consistently
```

## Caveats
### Photo Selection Limits
⚠️ **CRITICAL**: Limit to 5-10 representative photos per day to maintain focus

### Format Requirements
**Inline Image Format**: `![[filename.jpg]]` not `[[filename.jpg]]`
- **Format**: `- **HH:MM** ![[YYYY-MM-DD IMG_XXXX.jpg]] Caption text`
- **Use exact EXIF timestamps** (HH:MM from DateTimeOriginal) - no estimated times
- Reference processed metadata for accurate technical details

### Quality Standards
- Remove low-quality photos (dark, blurry, low contrast)
- Verify consistent date (no cross-date contamination)
- Ensure descriptive and specific captions
- Confirm processed images meet size requirements (<100KB)
- Check EXIF timestamps are accurate and properly formatted
