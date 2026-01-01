# Orchestrator Configuration Specification

This document defines the schema for `orchestrator.yaml`, the central configuration file for AI4PKM Orchestrator.

## Overview

The configuration file uses YAML format and consists of the following top-level fields:

### Vault Metadata (Optional)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | No | Configuration schema version (e.g., "1.0") |
| `name` | string | No | Vault display name |
| `id` | string | No | Vault identifier |
| `description` | string | No | Vault description |
| `icon` | string | No | Vault icon (emoji or icon name) |
| `color` | string | No | Vault theme color |

### Main Sections

| Section | Type | Required | Description |
|---------|------|----------|-------------|
| `orchestrator` | object | No | Runtime settings for the orchestrator |
| `defaults` | object | No | Global defaults applied to all agents |
| `nodes` | array | No | Agent definitions |
| `pollers` | object | No | Data source poller configurations |

---

## `orchestrator` Section

Runtime settings for the orchestrator process.

### Directory Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prompts_dir` | string | `_Settings_/Prompts` | Directory containing agent prompt files |
| `tasks_dir` | string | `_Settings_/Tasks` | Directory for task tracking files |
| `logs_dir` | string | `_Settings_/Logs` | Directory for execution logs |
| `skills_dir` | string | `_Settings_/Skills` | Directory for Claude Code skills |
| `bases_dir` | string | `_Settings_/Bases` | Directory for knowledge bases |

### Runtime Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_concurrent` | integer | `3` | Maximum global concurrent agent executions |
| `poll_interval` | float | `1.0` | Event queue poll interval in seconds |
| `mode` | string | - | Orchestrator mode |

### Voice/Ambient Mode Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ambient_mode` | boolean | `false` | Enable ambient listening mode |
| `system_prompt` | string | - | Custom system prompt for voice interactions |
| `orchestrator_language` | string | - | Language for orchestrator responses |

### STT/TTS Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `stt_provider` | string | - | Speech-to-text provider |
| `stt_language` | string | - | STT language code |
| `tts_provider` | string | - | Text-to-speech provider |
| `mic_gain` | float | - | Microphone gain level |
| `manual_end_detection` | boolean | - | Manual speech end detection |

### Wakeword Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `wakeword_enabled` | boolean | `false` | Enable wakeword detection |
| `wakeword_mode` | string | - | Wakeword detection mode |

### Periodic Processing Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `periodic_processing` | boolean | `false` | Enable periodic background processing |
| `periodic_seconds` | integer | - | Interval between periodic processing |
| `periodic_prompt` | string | - | Prompt for periodic processing |

### Example

```yaml
orchestrator:
  # Directories
  prompts_dir: "_Settings_/Prompts"
  tasks_dir: "_Settings_/Tasks"
  logs_dir: "_Settings_/Logs"
  # Runtime
  max_concurrent: 3
  poll_interval: 1.0
  # Voice mode (optional)
  ambient_mode: true
  stt_provider: "whisper"
  tts_provider: "elevenlabs"
```

---

## `defaults` Section

Global defaults applied to all agents. Individual agent nodes can override these values.

| Field | Type | Default | Valid Values | Description |
|-------|------|---------|--------------|-------------|
| `executor` | string | `claude_code` | See [Executors](#executors) | Default executor for agents |
| `timeout_minutes` | integer | `30` | Any positive integer | Default execution timeout |
| `max_parallel` | integer | `3` | Any positive integer | Max concurrent executions per agent |
| `task_create` | boolean | `true` | `true`, `false` | Whether to create task tracking files |
| `task_priority` | string | `medium` | `low`, `medium`, `high` | Default task priority |
| `task_archived` | boolean | `false` | `true`, `false` | Whether tasks are archived by default |

### Executors

| Value | Description |
|-------|-------------|
| `claude_code` | Claude Code CLI (Anthropic) |
| `gemini_cli` | Gemini CLI (Google) |
| `codex_cli` | Codex CLI (OpenAI) |
| `cursor_agent` | Cursor Agent |
| `continue_cli` | Continue CLI |
| `grok_cli` | Grok CLI (xAI) |

### Example

```yaml
defaults:
  executor: claude_code
  timeout_minutes: 30
  max_parallel: 3
  task_create: true
  task_priority: medium
```

---

## `nodes` Section

Array of agent node definitions. Each node configures an agent's triggers, inputs, outputs, and execution parameters.

### Node Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | **Yes** | - | Node type (currently only `agent`) |
| `name` | string | **Yes** | - | Human-readable name with `(ABBR)` suffix. See [Name Format](#name-format) |
| `enabled` | boolean | No | `true` | Enable/disable the agent |
| `completion_status` | string | No | - | Agent completion state tracking |
| `prompt` | string | No | Derived from name | Abbreviation to find prompt file |
| `input_path` | string \| array | No | `[]` | Vault path(s) to monitor for triggers |
| `input_type` | string | No | Inferred | Trigger type. See [Input Types](#input-types) |
| `input_pattern` | string | No | `*.md` | Custom file pattern (e.g., `*.jpg`) |
| `output_path` | string | No | - | Directory for agent output files |
| `output_type` | string | No | `new_file` | Output mode. See [Output Types](#output-types) |
| `output_naming` | string | No | `{title} - {agent}.md` | Output filename pattern |
| `cron` | string | No | - | Cron expression for scheduled execution |
| `trigger_exclude_pattern` | string | No | - | File patterns to exclude (pipe-separated) |
| `trigger_content_pattern` | string | No | - | Regex to match in file content |
| `trigger_schedule` | string | No | - | Schedule expression |
| `trigger_wait_for` | string \| array | No | `[]` | Agent(s) to wait for before execution |
| `skills` | string \| array | No | `[]` | Claude Code skill names |
| `mcp_servers` | string \| array | No | `[]` | MCP server identifiers |
| `executor` | string | No | From defaults | Executor override |
| `max_parallel` | integer | No | From defaults | Max parallel executions |
| `timeout_minutes` | integer | No | From defaults | Execution timeout |
| `task_create` | boolean | No | From defaults | Create task tracking file |
| `task_priority` | string | No | From defaults | Task priority level |
| `task_archived` | boolean | No | From defaults | Archive task after completion |
| `post_process_action` | string | No | - | Action after execution (e.g., `remove_trigger_content`) |
| `agent_params` | object | No | `{}` | Custom agent-specific parameters |
| `log_prefix` | string | No | Agent abbreviation | Log file prefix |
| `log_pattern` | string | No | `{timestamp}-{agent}.log` | Log filename pattern |
| `version` | string | No | `1.0` | Agent version |
| `workers` | array | No | `[]` | Multi-worker configuration. See [Workers](#workers) |

### Input Types

| Value | Trigger Event | Description |
|-------|---------------|-------------|
| `new_file` | `created` | Triggers when new files are created |
| `updated_file` | `modified` | Triggers when files are modified |
| `daily_file` | `scheduled` | Triggers on schedule for daily processing |
| `manual` | `manual` | No automatic trigger; manual execution only |

### Output Types

| Value | Description |
|-------|-------------|
| `new_file` | Creates new files in output directory |
| `update_file` | Updates existing files |
| `` (empty) | No file output |

### Workers

Multi-worker execution allows an agent to run with multiple executors in parallel.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `executor` | string | **Yes** | Executor type (see [Executors](#executors)) |
| `label` | string | **Yes** | Human-readable label (e.g., "Claude", "Gemini") |
| `output_path` | string | No | Worker-specific output directory |
| `agent_params` | object | No | Worker-specific parameters |

### Name Format

Agent names should include an abbreviation suffix in parentheses. The abbreviation is used to locate the corresponding prompt file.

**Supported formats:**
- `(ABC)` - 3-letter abbreviation
- `(ABCD)` - 4-letter abbreviation
- `(ABC-XY)` - Hyphenated abbreviation (e.g., `SPT-CUA`)

**Examples:**
```yaml
name: "Enrich Ingested Content (EIC)"      # Standard 3-letter
name: "Generate Daily Summary (GSUM)"      # 4-letter
name: "Search Pilot Task CUA (SPT-CUA)"    # Hyphenated variant
```

If the name doesn't include an abbreviation, you must specify the `prompt` field explicitly.

### Node Examples

#### Basic Agent

```yaml
nodes:
  - type: agent
    name: Enrich Ingested Content (EIC)
    input_path: Ingest/Clippings
    output_path: AI/Articles
    output_type: new_file
```

#### Multi-Input Agent

```yaml
nodes:
  - type: agent
    name: Create Thread Postings (CTP)
    input_path:
      - AI/Articles
      - AI/Roundup
      - AI/Research
    output_path: AI/Sharable
```

#### Scheduled Agent (Cron)

```yaml
nodes:
  - type: agent
    name: Generate Daily Roundup (GDR)
    input_type: daily_file
    cron: "0 1 * * *"  # 1:00 AM daily
    output_path: AI/Roundup
```

#### Multi-Worker Agent

```yaml
nodes:
  - type: agent
    name: Search Pilot Eval (SPE)
    prompt: SPE
    input_path: Eval/Queries
    workers:
      - executor: claude_code
        label: Claude
        output_path: Eval/Results/Claude
      - executor: gemini_cli
        label: Gemini
        output_path: Eval/Results/Gemini
```

#### Content-Triggered Agent

```yaml
nodes:
  - type: agent
    name: Handle Translation Command (HTC)
    input_path: ""  # Watch entire vault
    input_type: updated_file
    trigger_content_pattern: "^@translate\\b"
    post_process_action: remove_trigger_content
```

#### Disabled Agent

```yaml
nodes:
  - type: agent
    name: Experimental Feature (EXP)
    enabled: false  # Temporarily disabled
    input_path: Ingest/Test
    output_path: AI/Test
```

---

## `pollers` Section

Poller configurations for syncing data from external sources.

### Common Poller Fields

All pollers support these fields:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `enabled` | boolean | No | `false` | Enable/disable the poller |
| `target_dir` | string | **Yes*** | - | Vault directory for synced files (*required if enabled) |
| `poll_interval` | integer | No | `3600` | Seconds between polls |

### Poller Types

#### `apple_photos`

Syncs photos from Apple Photos.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | integer | `7` | Number of days to sync |
| `albums` | array | `[]` | Specific albums to sync |

```yaml
pollers:
  apple_photos:
    enabled: true
    target_dir: "Ingest/Photolog"
    poll_interval: 3600
    days: 7
    albums:
      - "Favorites"
      - "Screenshots"
```

#### `apple_notes`

Syncs notes from Apple Notes.

```yaml
pollers:
  apple_notes:
    enabled: true
    target_dir: "Ingest/Apple Notes"
    poll_interval: 1800
```

#### `gobi`

Syncs content from Gobi API.

| Field | Type | Description |
|-------|------|-------------|
| `api_base_url` | string | Gobi API endpoint |
| `api_key` | string | API key (store in secrets.yaml) |
| `local_timezone` | string | Timezone for timestamps |

```yaml
pollers:
  gobi:
    enabled: true
    target_dir: "Ingest/Gobi"
    poll_interval: 3600
    api_base_url: "https://api.joingobi.com/api"
```

#### `gobi_by_tags`

Syncs Gobi content filtered by tags.

| Field | Type | Description |
|-------|------|-------------|
| `api_base_url` | string | Gobi API endpoint |
| `api_key` | string | API key |
| `admin_api_key` | string | Admin API key for tag queries |
| `tags` | array \| string | Tag names to filter |
| `local_timezone` | string | Timezone for timestamps |

```yaml
pollers:
  gobi_by_tags:
    enabled: true
    target_dir: "Ingest/GobiByTags"
    poll_interval: 3600
    api_base_url: "https://api.joingobi.com/api"
    tags:
      - "work"
      - "ideas"
```

#### `limitless`

Syncs lifelogs from Limitless Pendant.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `start_days_ago` | integer | `7` | How many days back to sync |
| `api_key` | string | - | Limitless API key |
| `local_timezone` | string | - | Timezone for timestamps |

```yaml
pollers:
  limitless:
    enabled: true
    target_dir: "Ingest/Limitless"
    poll_interval: 3600
    start_days_ago: 7
```

---

## Secrets Management

Sensitive values (API keys, tokens) should be stored in `secrets.yaml` in the same directory as `orchestrator.yaml`. The secrets file is deep-merged into the main config at load time.

### Example `secrets.yaml`

```yaml
pollers:
  gobi:
    api_key: "your-gobi-api-key"
  limitless:
    api_key: "your-limitless-api-key"
```

**Note:** `secrets.yaml` should be added to `.gitignore`.

---

## Validation

The config validator checks for:

| Check | Severity | Description |
|-------|----------|-------------|
| Missing required fields | ERROR | Required fields not present |
| Unknown fields | WARNING | Unrecognized fields (possible typos) |
| Invalid enum values | ERROR | Values not in allowed list |
| Type mismatches | WARNING | Value type differs from expected |
| Semantic issues | INFO | Logical inconsistencies |

### Running Validation

```python
from ai4pkm_cli.config import Config

config = Config(vault_path=Path('vault'))
result = config.validate()
print(result.summary())
```

Validation runs automatically after `config.reload()`.

---

## Complete Example

```yaml
# Vault metadata
version: "1.0"
name: "My Knowledge Vault"
id: "MKV"
description: "Personal knowledge management vault"

# Orchestrator settings
orchestrator:
  prompts_dir: "_Settings_/Prompts"
  tasks_dir: "_Settings_/Tasks"
  logs_dir: "_Settings_/Logs"
  skills_dir: "_Settings_/Skills"
  bases_dir: "_Settings_/Bases"
  max_concurrent: 3
  poll_interval: 1.0

# Global defaults
defaults:
  executor: claude_code
  timeout_minutes: 30
  max_parallel: 3
  task_create: true
  task_priority: medium
  task_archived: false

# Agent definitions
nodes:
  - type: agent
    name: Enrich Ingested Content (EIC)
    input_path: Ingest/Clippings
    output_path: AI/Articles
    output_type: new_file

  - type: agent
    name: Process Life Logs (PLL)
    input_path: Ingest/Limitless
    output_path: AI/Lifelog
    timeout_minutes: 60

  - type: agent
    name: Experimental Agent (EXP)
    enabled: false  # Disabled
    input_path: Ingest/Test
    output_path: AI/Test

# Poller configurations
pollers:
  apple_photos:
    enabled: false
    target_dir: "Ingest/Photolog"
    poll_interval: 3600
    days: 7

  limitless:
    enabled: true
    target_dir: "Ingest/Limitless"
    poll_interval: 3600
    start_days_ago: 7
```
