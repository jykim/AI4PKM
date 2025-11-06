Generate knowledge tasks from task generation request file and process them efficiently.

## Main Process

```
1. DETERMINE SOURCE TYPE
   └─ If #AI in existing task file (AI/Tasks/*.md): Handle in-place⁰
   └─ Otherwise: Follow normal workflow

2. VALIDATE
   └─ Duplicate check in AI/Tasks/YYYY-MM-DD*
   └─ Status consistency¹

3. PROCESS
   └─ Simple tasks: Execute immediately²
   └─ Complex tasks: Create task file³

4. CREATE TASK (if complex)
   └─ Use [[Task Template]]
   └─ File: AI/Tasks/YYYY-MM-DD [Description].md
   └─ Properties: Priority, Status: "TBD", Source
   └─ Structure: Input, Context, Requirements, Inferred

5. CLEANUP (only if task creation request source is "Markdown")
   └─ Remove the tags that triggered task creation
```

## Caveats

### Time Scope Restrictions
⚠️ **CRITICAL**: Only process sources from the **last 3 days** to prevent generating outdated tasks. This applies to all source types and prevents accumulation of stale work.

### In-Task #AI Handling

**⁰ Handle in-place** (when #AI appears in existing task files):
- **DO**: Resolve the request within the same task file
- **DO**: Update task file as needed (Process Log, properties, sections)
- **DO**: Remove the #AI tag after handling
- **DON'T**: Create new task file for simple in-context requests
- **Exception**: Create separate task only if request is complex and unrelated to the task

Examples of in-place handling:
- Simple questions about task context
- Minor clarifications or additions to task instructions
- Quick file operations related to the task
- Status updates or property modifications
- Adding links or references to task

### Status and Validation Rules

**¹ Status consistency**:
- Use proper statuses: `TBD`, `COMPLETED`, `NEEDS_INPUT`
- Verify due dates are future dates, not past
- Delete or update any outdated pending tasks found

### Processing Categories

**² Simple tasks** (execute immediately):
- Daily goals/todos → Update Journal with `- [ ]` format
- Limitless insights → Add to Journal Thoughts section
- File operations, lookups
- Quick reference tasks

**³ Complex tasks** (create task file):
- **ALL unprocessed docs requiring EIC** (always create task, never execute directly)
- Research, analysis, writing
- Multi-step workflows

### EIC Processing Policy

⚠️ **CRITICAL**: **Never execute EIC directly during KTG**
- Unprocessed docs → Create EIC task file in `AI/Tasks/`
- Reason: Maintain clear separation between task discovery and task execution
- Exception: Simple Limitless insights can be added directly to Journal Thoughts

### Task File Structure Requirements
- **Properties**: Priority (P1 content/P2 workflow), **Status: "TBD"**, Archived: false, Source link
- **Sections**: Input (full context with blockquotes), Context (time/speaker/type), Requirements (structured preferences), Inferred (input/output/instructions/budget)