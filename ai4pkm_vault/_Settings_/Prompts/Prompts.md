---
tags: 
links: 
---
## Overview
AI prompts

## Recent Updates
%%auto-populated based on AI workflow%%

| Date | Title | Summary |
| ---- | ----- | ------- |
|      |       |         |

## List of All Notes
```dataviewjs
const title = dv.current().file.name;
const pages = dv.pages()
  .where(p => p.file.ext === "md"
           && p.file.path !== dv.current().file.path
           && p.file.folder.split("/").pop() === title);
dv.list(pages.sort(p => p.file.name, 'asc').map(p => p.file.link));
```
