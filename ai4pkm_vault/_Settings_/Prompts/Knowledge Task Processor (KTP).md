---
title: "Knowledge Task Processor"
abbreviation: "KTP"
category: "workflow"
created: "2024-01-01"
---

Process knowledge tasks from AI/Tasks folder systematically with priority-based execution and proper documentation.

## Input
- Knowledge tasks from AI/Tasks folder
- Task files with proper frontmatter (priority, status, worker, etc.)
- Referenced prompts/workflows for task execution
- Budget and dependency considerations

## Output
- Executed tasks with updated status
- Output files created per task requirements
- Process Log documentation
- Updated task properties (output, worker, completion details)
- Validated wiki links and accessible outputs

## Main Process
```
0. RUN TASK STATUS MANAGER
   └─ Execute: python _Settings_/Tools/automation/task_status.py --output _Settings_/Tools/task_queue.json
   └─ Load JSON results from task_queue.json
   └─ Review statistics (active tasks, priority distribution)
   └─ Get prioritized execution queue

1. BUILD EXECUTION PLAN (from Task Status Manager output)
   └─ Use execution_queue array for task order
   └─ Review statistics for workload assessment
   └─ Check grouped tasks by priority (P0 → P1 → P2 → P3)
   └─ Follow task instructions provided in queue

2. START TASK EXECUTION
   └─ Update status using script:
      python _Settings_/Tools/automation/task_status.py \
        --update "[task_filename]" \
        --status-new IN_PROGRESS \
        --worker "Claude Code"
   └─ Or update frontmatter manually and record start time

3. EXECUTE & DOCUMENT
   └─ Follow task instructions and requirements
   └─ Use specified prompts/workflows when referenced
   └─ Document progress in Process Log section
   └─ Create output files using wiki link format

4. COMPLETE TASK
   └─ Update using script:
      python _Settings_/Tools/automation/task_status.py \
        --complete "[task_filename]" \
        --output-link "[[Output/Path]]"
   └─ Or update frontmatter manually with:
      - output property with wiki links
      - status to COMPLETED or FAILED
      - completion details in Process Log
   └─ Verify all outputs are accessible

5. CLEANUP & VALIDATION
   └─ Ensure wiki links resolve correctly
   └─ Update related source documents if needed
   └─ Remove temporary files or notes
```

## Caveats
### Priority-Based Execution
⚠️ **CRITICAL**: Always process higher priority tasks first

**Priority Levels**:
- P0: Critical/urgent tasks requiring immediate attention
- P1: Important content creation and analysis tasks
- P2: Standard workflow and maintenance tasks
- P3: Low priority enhancement and optional tasks

### Status Management Rules
- Status transitions: `TBD` → `IN_PROGRESS` → `COMPLETED`/`FAILED`
- Never skip the `IN_PROGRESS` state
- Update worker field when claiming a task
- Proper status tracking prevents duplicate processing

### Output Documentation Standards
**Process Log Requirements**:
- Document decision points and reasoning
- Record challenges encountered and solutions
- Track resources used and time invested
- Include quality assessments and improvements

**Output Format Standards**:
- Use wiki links `[[Filename]]` not quoted paths
- Remove .md extensions from wiki links
- For AI folder outputs, can omit "AI/" prefix for brevity
- Single output: `output: "[[Path/To/File]]"`
- Multiple outputs: Use YAML list format

### Completion Requirements
- All outputs must be created and accessible
- `output:` property must contain valid wiki links
- Process Log must document accomplishments
- Status change to `COMPLETED` only when fully finished

## Key Lessons & Best Practices

### EIC Workflow Guidelines
⚠️ **CRITICAL**: EIC (Enrich Ingested Content) tasks update source clipping files inline
- **Never create new analysis files** for EIC tasks
- **Update existing clipping files** with Summary sections
- **Set output field to match source field** (original clipping file)
- Follow EIC prompt guideline: "Updated note inline (don't create new note)"

### Task Execution Order
- Process P1 tasks before P2, regardless of creation date
- Complete higher priority tasks fully before moving to lower priority
- Address blocking issues immediately when discovered

### Quality Control
- Read actual source documents before processing
- Verify wiki links point to existing files
- Update frontmatter properties in correct YAML format
- Place output property in frontmatter, not at end of document

### Data Source Integration
- Check for updated Limitless recordings when processing GES tasks
- Enhance summaries with actual transcript content when available
- Update source references to point to specific sections

## Task Status Manager Integration

### Automated Task Management
The Task Status Manager script (`_Settings_/Tools/automation/task_status.py`) automates mechanical aspects of task processing:

**Key Benefits**:
- 73-105x faster than manual task scanning
- Automatic priority-based sorting (P0 → P1 → P2 → P3)
- Instant duplicate detection on repeat runs
- Consistent status transition validation
- Automated execution queue generation

**Usage Modes**:
```bash
# View statistics only
python _Settings_/Tools/automation/task_status.py --stats-only

# Generate execution queue
python _Settings_/Tools/automation/task_status.py --output _Settings_/Tools/task_queue.json

# Update task status
python _Settings_/Tools/automation/task_status.py --update "[filename]" --status-new IN_PROGRESS --worker "Claude Code"

# Complete task
python _Settings_/Tools/automation/task_status.py --complete "[filename]" --output-link "[[Output]]"

# Filter by priority/status
python _Settings_/Tools/automation/task_status.py --priority P1
python _Settings_/Tools/automation/task_status.py --status TBD
```

**Task Queue JSON Structure**:
```json
{
  "statistics": {
    "total": 78,
    "active": 6,
    "by_status": {"TBD": 5, "IN_PROGRESS": 2, "COMPLETED": 64},
    "by_priority": {"P0": 2, "P1": 46, "P2": 28, "P3": 2}
  },
  "execution_queue": [
    {
      "order": 1,
      "file": "2025-10-08 Task.md",
      "priority": "P1",
      "status": "TBD",
      "instructions": "..."
    }
  ],
  "grouped": {
    "P0": [...],
    "P1": [...],
    "P2": [...],
    "P3": [...]
  }
}
```

**Workflow Integration**:
1. Run Task Status Manager at start of KTP
2. Use `execution_queue` for task order
3. Use script for status updates (optional, can update manually)
4. Re-run script to verify completion and get next tasks

**Documentation**:
- Full specification: [[2025-10-10 Task Status Manager Spec]]
- Usage guide: [[_Settings_/Tools/Task_Status_Manager_README]]
