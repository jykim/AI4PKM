---
title: "Knowledge Task Evaluator"
abbreviation: "KTE"
category: "evaluation"
created: "2024-01-01"
---

Evaluate completed knowledge tasks from AI/Tasks folder for quality assessment and improvement recommendations.

## Input
- Recently completed tasks from AI/Tasks folder
- [[Knowledge Task Processor (KTP)]] guidelines
- Task-specific input & prompts
- User feedback (if available)

## Output
- Updated task files with evaluation property
- Evaluation section added to task files
- Quality assessment: SUCCESS / FAILURE / NEEDS_IMP
- Improvement recommendations where applicable

## Main Process
```
1. SCAN COMPLETED TASKS
   - Identify recently completed tasks
   - Check completion status and outputs
   - Gather evaluation criteria

2. QUALITY EVALUATION
   - Evaluate output against KTP guidelines
   - Review task-specific input & prompts
   - Consider user feedback if available
   - Assess overall task fulfillment

3. DOCUMENT EVALUATION
   - Add Evaluation property: SUCCESS / FAILURE / NEEDS_IMP
   - Create new '## Evaluation' section at end
   - Provide detailed assessment and recommendations
```

## Caveats
### Evaluation Criteria Standards
⚠️ **CRITICAL**: Base evaluation on multiple factors including guidelines, task requirements, and user feedback

### Evaluation Categories
- **SUCCESS**: Fully met user needs and requirements
- **FAILURE**: Didn't meet user needs at all
- **NEEDS_IMP**: Only partially met user needs

### Documentation Requirements
- Add evaluation property to task frontmatter
- Include detailed assessment in Evaluation section
- Provide specific improvement recommendations
- Reference evaluation criteria used
