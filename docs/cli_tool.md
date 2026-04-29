## CLI Tool
A powerful command-line interface for automating knowledge management workflows using AI assistance. The CLI provides scheduled prompt execution, interactive report generation, and seamless integration with Claude AI through the Claude Code SDK.

## Features

- **Cron Job Scheduling**: Automated execution of knowledge management tasks
- **Support for Multiple Agents**: Standardized interface to call Claude/Codex/Gemini agents
## Installation

### Prerequisites
- Python 3.8 or higher

### Install as Package

```bash
pip install -e .
```

After installation, the CLI will be available as the `ai4pkm` command.

## Usage

The CLI operates in several modes:

### 1. Default Mode (Information Display)

Run the CLI without arguments to see current configuration and usage instructions:

```bash
ai4pkm
```

This will:
- Show current agent configuration
- Display scheduled cron jobs
- List common commands and shortcuts
- Provide quick usage reference

### 2. Continuous Cron Mode

Start the cron job scheduler for automated task execution:

```bash
ai4pkm -c
# or
ai4pkm --cron
```

This will:
- Load and start configured cron jobs
- Run continuously with live logging
- Execute scheduled tasks automatically
- Continue running until stopped with Ctrl+C

### 3. One-time Prompt Execution

Execute any prompt immediately by passing it directly to the AI agent:

```bash
# Execute any arbitrary prompt
ai4pkm -p "What is machine learning?"

# Multi-line or complex prompts
ai4pkm -p "Analyze this data and provide insights: [data here]"

# Creative tasks
ai4pkm -p "Write a haiku about programming"
```

**Direct Prompt Execution:**
- All prompts are sent directly to the AI agent
- No file system lookup or template matching required
- Simple, fast, and flexible for any use case

**Per-Prompt Agent Override:**
You can use a specific agent for just one prompt without changing the global configuration:

```bash
# Use Gemini for this prompt only
ai4pkm -a g -p "Translate this to Korean: Hello world"

# Use Codex for coding tasks  
ai4pkm -a codex -p "Write a Python function to sort a list"

# Use Claude for analysis
ai4pkm -a c -p "Analyze the pros and cons of remote work"

# Global agent remains unchanged
ai4pkm --show-config
```

### 4. One-time Command Execution

Execute pre-defined commands:

**Process Photos**

Sync photos from iCloud AI4PKM album to ./Photostream, process each new photo by extracting EXIF metadata, and save jpeg image and metadata in markdown to ./Ingest/Photolog/Snap/ folder.

```bash
ai4pkm -cmd process_photos
```

**Generate Report**

Generate one time report using Adhoc/generate_report.md prompt with user inputs. User inputs are start time, end time, name and description of the event.

```bash
ai4pkm -cmd generate_report
```

### 5. Cron Job Testing

Test a specific cron job interactively:

```bash
ai4pkm -t
```

This will:
- Display all configured cron jobs
- Allow you to select and test a job
- Show execution time and results
- Useful for debugging scheduled tasks

### 6. Orchestrator Mode (Recommended)

Start the new multi-agent orchestrator system for automated knowledge workflows:

```bash
ai4pkm -o
# or
ai4pkm --orchestrator
```

**What it does:**
- Monitors vault files for changes and triggers configured agents
- Runs multiple agents in parallel with concurrency control
- Config-driven agent definitions in Markdown files
- Real-time status updates and logging
- Better architecture than legacy Task Management mode

**Quick Status Check:**
```bash
ai4pkm --orchestrator-status
```

**See Also:**
- [Orchestrator User Guide](/_specs/2025-10-27%20Orchestrator%20User%20Guide) - Detailed documentation
- [Orchestrator Design](/_specs/2025-10-25%20Orchestrator%20Detailed%20Design) - Technical architecture

---

### 7. Task Management Mode (Deprecated)

⚠️ **Note**: This mode is deprecated. Please use the new Orchestrator mode (`ai4pkm -o`) instead.

Start the on-demand task processing system for real-time knowledge task execution:

```bash
ai4pkm -t
# or
ai4pkm --task-management
```

**What it does:**
- Monitors filesystem for task triggers (web clippings, #AI hashtags, voice notes)
- Automatically generates, executes, and evaluates knowledge tasks
- Routes tasks to appropriate AI agents based on task type
- Provides real-time processing for immediate results

**Task Triggers:**
- **Web Clippings**: Drop content from [Obsidian Web Clipper](https://obsidian.md/clipper) into `Ingest/Clippings/` to trigger EIC workflow
- **#AI Hashtag**: Add `#AI` to any note to generate a knowledge task
- **Voice Commands**: Use Limitless pendant with wake words `Hey PKM` to create tasks

**Three-Phase Processing:**
1. **KTG (Knowledge Task Generator)**: Creates structured task from triggers
2. **KTP (Knowledge Task Processor)**: Routes to agent and monitors execution
3. **KTE (Knowledge Task Evaluator)**: Validates outputs and marks completion

**Configuration:**
Task routing is defined in `ai4pkm_cli.json`:
```json
{
  "task_management": {
    "processing_agent": {
      "EIC": "claude_code",
      "Research": "gemini_cli",
      "Analysis": "gemini_cli",
      "default": "claude_code"
    },
    "evaluation_agent": "claude_code"
  }
}
```

**See Also:**
- [On-demand Knowledge Task Processing]({% post_url 2025-10-20-on-demand-knowledge-task %}) - Detailed blog post
- [README_KTM.md](https://github.com/jykim/AI4PKM/blob/main/README_KTM.md) - Technical implementation

---

### 8. Vault Template Management

Create a new vault from pre-configured templates:

```bash
# List available templates
ai4pkm template list

# Install template to a directory
ai4pkm template install ai4pkm ~/my-vault

# Install specific version
ai4pkm template install ai4pkm ~/my-vault --version v1.0.0

# Force overwrite existing files
ai4pkm template install ai4pkm ~/my-vault --force
```

**Available Templates:**
- **ai4pkm**: AI4PKM starter vault with default configuration (from [ai4pkm-vault](https://github.com/jykim/ai4pkm-vault), GitHub releases)
- **cmds**: Commands vault from [cmds-vault](https://github.com/johnfkoo951/cmds-vault) (cloned via `git clone`; `--version` selects a branch/tag)

---

### 9. Agent Trigger

Manually trigger an orchestrator agent by name:

```bash
# Trigger agent by name (abbreviation or full name)
ai4pkm trigger EIC
ai4pkm trigger "Enrich Ingested Content"

# With specific input file
ai4pkm trigger EIC --input ~/vault/Ingest/Clippings/article.md
```

---

### 10. Self-Update

Update the AI4PKM CLI to the latest version:

```bash
# Update to latest release
ai4pkm update

# Check current version
ai4pkm --version
```

---

### 11. AI Agent Management

The CLI supports multiple AI agents. Manage them using these commands:

```bash
# List all available agents and their status
ai4pkm --list-agents

# Show current configuration
ai4pkm --show-config

# Switch to a different agent (full names)
ai4pkm --agent claude_code
ai4pkm --agent gemini_cli
ai4pkm --agent codex_cli

# Or use convenient shortcuts
ai4pkm -a c       # Claude
ai4pkm -a g       # Gemini  
ai4pkm -a o       # Codex

# Or use full names
ai4pkm -a claude  # Claude
ai4pkm -a gemini  # Gemini
ai4pkm -a codex   # Codex
```

**Available Agents:**
- **Claude Code**: Uses Claude Code SDK (default)
- **Gemini CLI**: Uses Google Gemini CLI
- **Codex CLI**: Uses OpenAI Codex CLI

The system automatically falls back to available agents if the selected one is not configured.

## Configuration

### Orchestrator Configuration (orchestrator.yaml)

The new multi-agent orchestrator uses vault-specific configuration in `orchestrator.yaml`:

```yaml
# Orchestrator runtime settings
orchestrator:
  prompts_dir: "_Settings_/Prompts"
  tasks_dir: "_Settings_/Tasks"
  logs_dir: "_Settings_/Logs"
  skills_dir: "_Settings_/Skills"
  bases_dir: "_Settings_/Bases"
  max_concurrent: 3
  poll_interval: 1.0

# Agent nodes
nodes:
  - type: agent
    name: Enrich Ingested Content (EIC)
    input_path: Ingest/Clippings
    output_path: AI/Articles
    # ... more agent config
```

**Key Settings:**
- `orchestrator.tasks_dir`: Where task tracking files are created
- `orchestrator.logs_dir`: Where execution logs are written
- `orchestrator.max_concurrent`: Max parallel agent executions
- `nodes`: List of agent definitions with triggers and routing

See [Orchestrator User Guide](/_specs/2025-10-27%20Orchestrator%20User%20Guide) for full configuration options.

---

### AI Agent Configuration

The CLI automatically creates a configuration file at `_Settings_/ai4pkm_config.json`:

```json
{
  "agent": "claude_code",
  "claude_code": {
    "permission_mode": "bypassPermissions"
  },
  "gemini_cli": {
    "command": "gemini"
  },
  "codex_cli": {
    "command": "codex"
  }
}
```

**Configuration Options:**
- `agent`: Current active agent (claude_code, gemini_cli, codex_cli)  
- Each agent section contains agent-specific settings
- CLI commands can be customized for different installations
- CLI-based agents (Gemini, Codex) use their respective default models

### Cron Jobs

Define scheduled tasks in the root `cron.json` file:

```json
[
  {
    "inline_prompt": "CKU for hourly run",
    "cron": "0 * * * *",
    "description": "Regularly run tasks for keeping knowledge base clean every hour"
  },
  {
    "inline_prompt": "DIR for today", 
    "cron": "0 21 * * *",
    "description": "Daily ingestion and processing of contents into daily roundup at 9 PM"
  },
  {
    "inline_prompt": "WRP for this week",
    "cron": "0 12 * * 0", 
    "description": "Weekly review of knowledge base every Sunday at 12 PM"
  }
]
```

**Cron Expression Format:**
- `* * * * *` = minute hour day month weekday
- Examples:
  - `0 * * * *` = Every hour at minute 0
  - `0 21 * * *` = Every day at 9 PM
  - `0 12 * * 0` = Every Sunday at 12 PM

### Prompts Directory Structure

```
_Settings_/
├── Prompts/
│   ├── Generate Daily Roundup (GDR).md
│   ├── Topic Knowledge Creation (TKC).md
│   ├── Process Life Logs (PLL).md
│   └── Adhoc/
│       └── custom_prompt.md
└── Templates/
    ├── Journal Template.md
    ├── Topic Template.md
    └── Weekly Roundup Template.md
```

### Template Parameters

Templates support parameter substitution using `{parameter_name}` syntax:

```markdown
# {name} - {description}

Generated on: {timestamp}
Time range: {start_time} to {end_time}

{template_content}
```

## Architecture

### Core Components

| Component | Purpose |
|-----------|---------|
| `main.py` | CLI entry point and argument parsing |
| `cli.py` | Main application logic and user interface |
| `claude_runner.py` | Claude AI integration and prompt execution |
| `cron_manager.py` | Cron job scheduling and execution |
| `logger.py` | Logging infrastructure with file and console output |
| `utils.py` | Interactive utilities (menu selection, etc.) |

### Prompt Runners

| Runner | Purpose |
|--------|---------|
| `report_generator.py` | Interactive report generation with templates |

### Data Flow

1. **Continuous Mode**: CronManager → ClaudeRunner → Logger
2. **One-time Execution**: CLI → ClaudeRunner → Logger  
3. **Interactive Testing**: CLI → CronManager → ClaudeRunner → Logger

## Troubleshooting

### Common Issues

**"Claude Code SDK not available"**
- Install: `pip install claude-code-sdk`
- Verify API credentials

**"No cron.json found"**
- Create `cron.json` in the project root
- Use the example format above

**"Prompt file not found"**
- Check `_Settings_/Prompts/` directory
- Verify file naming (include .md extension in files)

**Cron jobs not running**
- Verify cron expression syntax
- Check log output for errors
- Test individual jobs with `-t` flag

**Agent not available**
- Use `--list-agents` to check agent status
- For Gemini CLI: Install Google AI CLI tools
- For Codex CLI: Install OpenAI CLI tools
- System automatically falls back to available agents

**Agent switching not working**
- Check `_Settings_/ai4pkm_config.json` permissions
- Verify agent type spelling (claude_code, gemini_cli, codex_cli)
- Use shortcuts: `-a c/claude`, `-a g/gemini`, `-a o/codex`
- Use `--show-config` to verify current settings
- Per-prompt agents: `ai4pkm -a g -p "prompt"` doesn't change global config

### Debug Mode

For detailed debugging, check the logs in `_Settings_/Logs/` or run with verbose console output.

## Examples

### Daily Knowledge Management

```bash
# Set up daily roundup at 9 PM
echo '[{"inline_prompt": "DIR for today", "cron": "0 21 * * *", "description": "Daily roundup"}]' > cron.json

# Check the configuration
ai4pkm

# Start the scheduler
ai4pkm -c

# Test the job manually
ai4pkm -t
```

### Custom Prompt Execution

```bash
# Ask questions directly
ai4pkm -p "What are the benefits of using a PKM system?"

# Get code help
ai4pkm -a codex -p "Write a Python script to parse JSON files"

# Content analysis
ai4pkm -a claude -p "Summarize the key points of this text: [your text]"

# Creative writing
ai4pkm -p "Write a brief introduction to knowledge management"
```

### Agent Management

```bash
# Check available agents
ai4pkm --list-agents

# Switch to Gemini for better multilingual support
ai4pkm -a g

# Use Codex for coding tasks  
ai4pkm -a o

# Show current agent configuration
ai4pkm --show-config

# Run a prompt with specific agent (shortcuts work too)
ai4pkm -a c -p "GDR"

# Use different agents for different tasks
ai4pkm -a gemini -p "translate_document"    # Gemini for multilingual tasks
ai4pkm -a codex -p "generate_code"          # Codex for coding tasks
ai4pkm -a claude -p "analyze_content"       # Claude for analysis
```

## See Also

- [Guidelines](guidelines.html) - PKM overview and architecture
- [Prompts](prompts.html) - Standardized prompt system
- [Workflows](workflows.html) - How workflows use the CLI
- [FAQ](faq.html) - Frequently asked questions

