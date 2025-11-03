# Orchestrator

The AI4PKM Orchestrator is a multi-agent system that monitors your Obsidian vault for file changes and automatically triggers AI agents to process content.

## Overview

### What is the Orchestrator?

The Orchestrator provides an automated, event-driven workflow for personal knowledge management. When you add content to your vault—whether it's a web clipping, a voice note, or a manual hashtag—the orchestrator automatically routes it to the appropriate AI agent for processing.

**Key Features:**

- **Automatic Processing**: File changes trigger AI agents automatically
- **Multi-Agent Support**: Route tasks to different CLI agents (Claude, Gemini, Codex)
- **Concurrent Execution**: Process multiple tasks simultaneously with configurable limits
- **Task Tracking**: Full transparency with task files and execution logs
- **Flexible Configuration**: Define agents and workflows through simple YAML configuration


For more details, see the [architecture blog post](https://jykim.github.io/AI4PKM/blog/2025/10/30/new-architecture-for-agentic-ai.html).

---

## Configuration

### Directory Structure

The orchestrator requires the following directories in your vault:

```
your-vault/
├── orchestrator.yaml          # Main configuration file
├── _Settings_/
│   ├── Prompts/              # Agent prompt definitions
│   │   ├── Enrich Ingested Content (EIC).md
│   │   ├── Hashtag Task Creator (HTC).md
│   │   └── ...
│   ├── Tasks/                # Task tracking files (auto-created)
│   └── Logs/                 # Execution logs (auto-created)
├── Ingest/
│   └── Clippings/            # Input: Web clippings
└── AI/
    └── Articles/             # Output: Processed content
```

### orchestrator.yaml

The main configuration file defines orchestrator settings, defaults, and agent routing.

**Location**: `<vault_root>/orchestrator.yaml`

**Complete Example:**

```yaml
# AI4PKM Orchestrator Configuration
version: "1.0"

# Orchestrator runtime settings
orchestrator:
  prompts_dir: "_Settings_/Prompts"      # Agent prompt definitions
  tasks_dir: "_Settings_/Tasks"          # Task tracking files
  logs_dir: "_Settings_/Logs"            # Execution logs
  skills_dir: "_Settings_/Skills"        # Skills library (future)
  bases_dir: "_Settings_/Bases"          # Knowledge bases (future)
  max_concurrent: 3                      # Global concurrency limit
  poll_interval: 1.0                     # Event queue poll interval (seconds)

# Global defaults for all agents
defaults:
  executor: claude_code                  # Default CLI agent
  timeout_minutes: 30                    # Default timeout
  max_parallel: 3                        # Default per-agent limit
  task_create: true                      # Create task files
  task_priority: medium                  # Default priority
  task_archived: false                   # Default archived status

# Agent definitions (nodes-based configuration)
nodes:
  # Enrich Ingested Content
  - type: agent
    name: Enrich Ingested Content (EIC)
    input_path: Ingest/Clippings         # Auto-triggers on new files
    output_path: AI/Articles

  # Process Life Logs
  - type: agent
    name: Process Life Logs (PLL)
    input_path: Ingest/Limitless
    output_path: AI/Lifelog

  # Generate Daily Roundup (scheduled - future feature)
  - type: agent
    name: Generate Daily Roundup (GDR)
    cron: 0 1 * * *                      # 1AM every day (not yet implemented)
    output_path: AI/Roundup

  # Manual-only agent (no input_path)
  - type: agent
    name: Ad-hoc Research within PKM (ARP)
    output_path: AI/Research
```

### Configuration Reference

#### orchestrator Section

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `prompts_dir` | string | `_Settings_/Prompts` | Agent prompt definitions directory |
| `tasks_dir` | string | `_Settings_/Tasks` | Task tracking files directory |
| `logs_dir` | string | `_Settings_/Logs` | Execution logs directory |
| `max_concurrent` | integer | 3 | Max concurrent executions (global) |
| `poll_interval` | float | 1.0 | Event queue poll interval (seconds) |

#### defaults Section

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `executor` | string | `claude_code` | Default CLI agent |
| `timeout_minutes` | integer | 30 | Default execution timeout |
| `max_parallel` | integer | 3 | Default per-agent concurrency |
| `task_create` | boolean | true | Create task tracking files |
| `task_priority` | string | `medium` | Default task priority |

#### nodes Section

Each node defines an agent with the following fields:

**Required:**
- `type: agent` - Node type (required)
- `name: "Full Name (ABBR)"` - Agent name with abbreviation in parentheses
- `input_path` - Input directory to monitor (string or list)
  - If omitted or null: manual-only agent (no auto-trigger)
  - Single path: watches for new files in that directory
  - Multiple paths: triggers on first path (full multi-input support coming soon)
- `output_path` - Output directory for results
- `output_type` - How to create output (optional, default: `new_file`)
  - `new_file`: Create new file in output directory
  - `update_file`: Modify input file in place
- `cron` - Cron schedule for periodic execution (future feature)

**Agent-Specific Settings** (override defaults):
- `trigger_exclude_pattern` - Glob pattern to exclude files (e.g., `"*-EIC*"`)
- `trigger_content_pattern` - Regex to match in file content (e.g., `"(?i)%%.*?#ai\\b.*?%%"`)
- `post_process_action` - Action after completion (e.g., `"remove_trigger_content"`)
- `executor` - CLI agent to use (e.g., `"claude_code"`, `"gemini_cli"`)
- `timeout_minutes` - Execution timeout in minutes (e.g., `60`)
- `max_parallel` - Max concurrent executions for this agent (e.g., `1`)
- `task_priority` - Task priority level: `"low"`, `"medium"`, or `"high"`

**Output Configuration:**

The orchestrator supports two output modes:

1. **new_file** (default) - Creates a new file in the output directory
2. **update_file** - Updates the input file in place

```yaml
nodes:
  # Create new files in output directory
  - type: agent
    name: Enrich Ingested Content (EIC)
    input_path: Ingest/Clippings
    output_path: AI/Articles
    output_type: new_file  # Creates new file in AI/Articles

  # Update files in place
  - type: agent
    name: Daily Note Enhancer (DNE)
    input_path: Journal
    output_path: Journal
    output_type: update_file  # Modifies existing file
```

The orchestrator automatically:
- Injects output configuration into agent prompts
- Validates that output files were created/modified
- Detects files created via atomic writes (temporary file + rename)
- Triggers downstream agents when new files appear

**Example with agent-specific settings:**

```yaml
nodes:
  # Agent with custom settings
  - type: agent
    name: Hashtag Task Creator (HTC)
    trigger_exclude_pattern: "_Settings_/*"
    trigger_content_pattern: "(?i)%%.*?#ai\\b.*?%%"
    post_process_action: remove_trigger_content
    task_priority: high
    max_parallel: 1
    timeout_minutes: 10

  # Agent with minimal settings (uses defaults)
  - type: agent
    name: Enrich Ingested Content (EIC)
    input_path: Ingest/Clippings
    output_path: AI/Articles
    output_type: new_file
    trigger_exclude_pattern: "*-EIC*"
```

### Prompt Files

Agent prompts are stored as Markdown files with minimal frontmatter and prompt instructions.

**Location**: `<vault_root>/_Settings_/Prompts/`

**Naming Convention**: `{Full Name} ({ABBR}).md`

**Example**: `_Settings_/Prompts/Enrich Ingested Content (EIC).md`

```yaml
---
title: Enrich Ingested Content (EIC)
abbreviation: EIC
category: ingestion
---
Improve captured content through transcript correction, summarization, and knowledge linking.

## Input
- Target note file with original clipped content
- May contain grammar or transcript errors

## Output
- Improved formatting and structure
- Summary section added at beginning
- Related topics linked
- Status property set to "processed"

## Main Process

1. **Fix Transcript Errors**
   - Correct grammar and spelling
   - Remove extra/duplicated newlines
   - Add proper formatting (lists, highlights)

2. **Add Summary**
   - Write catchy summary for sharing
   - Use quotes verbatim to convey author's voice
   - Keep concise and engaging

3. **Enrich with Links**
   - Link related knowledge base topics (existing only)
   - Add one-line summary to relevant KB topics
   - Connect to related summaries
```

**Required Frontmatter Fields:**
- `title` - Full agent name (must match name in orchestrator.yaml)
- `abbreviation` - 3-4 letter abbreviation (e.g., "EIC", "HTC")
- `category` - Agent category: `ingestion`, `publish`, or `research`

---

## CLI Usage

### Commands

#### Show Status

```bash
ai4pkm --orchestrator-status
```

Displays:
- Vault path
- Number of loaded agents
- Max concurrent executions
- List of available agents with categories

Use this command to:
- Verify agents are configured correctly
- Check agent definitions are loaded
- Debug configuration issues

#### Start Orchestrator

```bash
# Standard mode
ai4pkm -o

# With custom concurrency
ai4pkm -o --max-concurrent 5

# Full form also works
ai4pkm --orchestrator --max-concurrent 5
```

**Options:**
- `--max-concurrent N` - Set maximum concurrent executions (default: 3)

**When Running:**
- Press `Ctrl+C` to stop gracefully
- Check logs in `_Settings_/Logs/`
- Task files created in `_Settings_/Tasks/`


## Resources

### Documentation

- [New Architecture Blog Post](https://jykim.github.io/AI4PKM/blog/2025/10/30/new-architecture-for-agentic-ai.html) - Overview of orchestrator-agent architecture
- [On-demand Task Processing](https://jykim.github.io/AI4PKM/blog/2025/10/20/on-demand-knowledge-task.html) - Background and evolution
- [GitHub Repository](https://github.com/jykim/AI4PKM) - Source code and issues

### Code Locations

- **Orchestrator Core**: [ai4pkm_cli/orchestrator/](../ai4pkm_cli/orchestrator/)
- **CLI Tool**: [ai4pkm_cli/orchestrator_cli.py](../ai4pkm_cli/orchestrator_cli.py)
- **Configuration**: [ai4pkm_vault/orchestrator.yaml](../ai4pkm_vault/orchestrator.yaml)
- **Example Prompts**: [ai4pkm_vault/_Settings_/Prompts/](../ai4pkm_vault/_Settings_/Prompts/)

### Getting Help

**Check logs:**
```bash
# Execution logs
tail -f _Settings_/Logs/*.log

# Console output shows file monitor events
ai4pkm -o
```

**Report issues:**
- [GitHub Issues](https://github.com/jykim/AI4PKM/issues)

---

*Last Updated: 2025-11-03*
*Version: 1.0 (Nodes-based configuration with orchestrator.yaml)*
