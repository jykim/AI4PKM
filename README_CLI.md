# AI4PKM CLI

**Personal Knowledge Management CLI Framework**

Version: 0.1.0

A powerful command-line interface for automating knowledge management workflows using AI assistance. The CLI provides scheduled prompt execution, interactive report generation, and seamless integration with Claude AI through the Claude Code SDK.

## 🚀 Features

- **📅 Cron Job Scheduling**: Automated execution of knowledge management tasks
- **🤖 AI Integration**: Powered by Claude AI through Claude Code SDK
- **📊 Interactive Report Generation**: Guided report creation with templates
- **🎨 Rich Terminal Interface**: Beautiful console UI with colors and panels
- **📝 Prompt Management**: Support for both named prompts and inline prompts
- **🔍 Template System**: Parameterized templates for content generation
- **📋 Comprehensive Logging**: File and console logging with multiple levels

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- Claude Code SDK access

### Install Claude Code SDK
```bash
npm install -g @anthropic-ai/claude-code
```

### Login to Claude Code (you need API key or pro/max subscription)
```bash
claude /login
```

### Install exiftool (to process EXIF metadata from photos)
```bash
brew install exiftool
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Install as Package

```bash
pip install -e .
```

After installation, the CLI will be available as the `ai4pkm` command.

## 🎯 Usage

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

Execute pre-defined command

Sync photos from iCloud AI4PKM album to ./Photostream, process each new photo by extracting EXIF metadata, and save jpeg image and metadata in markdown to ./Ingest/Photolog/Snap/ folder.

#### Process Photos
```bash
ai4pkm -cmd process_photos
```

#### Generate Report

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

### 6. AI Agent Management

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

## ⚙️ Configuration

### AI Agent Configuration (`ai4pkm_cli.json`)

The CLI automatically creates a configuration file to manage AI agent settings:

```json
{
  "default-agent": "claude_code",
  "agents-config": {
    "claude_code": {
      "permission_mode": "bypassPermissions",
      "global_prompt": "You are an AI assistant for knowledge management. Always be concise and actionable."
    },
    "gemini_cli": {
      "command": "gemini",
      "global_prompt": "Focus on multilingual support and cultural context."
    },
    "codex_cli": {
      "command": "codex",
      "global_prompt": "Find the abbreviation in the list of prompts."
    }
  },
  "photo_processing": {
    "source_folder": "Ingest/Photolog/Original/",
    "destination_folder": "Ingest/Photolog/Processed/",
    "albums": ["AI4PKM"],
    "days": 1
  },
  "notes_processing": {
    "destination_folder": "Ingest/Apple Notes/",
    "days": 7
  },
  "cron_jobs": [...]
}
```

**Configuration Options:**
- `default-agent`: Current active agent (claude_code, gemini_cli, codex_cli)  
- `agents-config`: Configuration section for all agents
- `global_prompt`: Agent-specific prompt that gets prepended to all user prompts
- Each agent section contains agent-specific settings
- CLI commands can be customized for different installations
- CLI-based agents (Gemini, Codex) use their respective default models

**Global Prompt Feature:**
- Each agent can have its own `global_prompt` that automatically gets prepended to every user prompt
- Useful for setting agent personality, language preferences, or specialized instructions
- Empty global prompts are ignored (backward compatible)
- Global prompts are applied before template parameters and context

### Cron Jobs (in `ai4pkm_cli.json`)

Define scheduled tasks in the `cron_jobs` array within the main configuration file:

```json
{
  "cron_jobs": [
    {
      "inline_prompt": "CKU for hourly run",
      "cron": "0 * * * *",
      "description": "Regularly run tasks for keeping knowledge base clean every hour",
      "agent": "claude_code",
      "enabled": false
    },
    {
      "inline_prompt": "DIR for today", 
      "cron": "0 21 * * *",
      "description": "Daily ingestion and processing of contents into daily roundup at 9 PM",
      "enabled": true
    },
    {
      "inline_prompt": "WRP for this week",
      "cron": "0 12 * * 0", 
      "description": "Weekly review of knowledge base every Sunday at 12 PM",
      "enabled": true
    },
    {
      "command": "process_photos",
      "cron": "0 * * * *",
      "description": "Regularly sync and process photos from iCloud",
      "enabled": true
    },
    {
      "command": "process_notes",
      "cron": "15 * * * *",
      "description": "Regularly sync and process notes from Apple Notes",
      "enabled": true
    }
  ]
}
```

**Cron Job Options:**
- `inline_prompt`: Direct prompt text to execute
- `command`: Pre-defined command to run (e.g., "process_photos", "process_notes")
- `cron`: Cron expression for scheduling
- `description`: Human-readable description
- `agent`: Specific agent to use (optional, defaults to global agent)
- `enabled`: Whether the job is active (true/false)

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

## 🔧 Architecture

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


## 🐛 Troubleshooting

### Common Issues

1. **"Claude Code SDK not available"**
   - Install: `pip install claude-code-sdk`
   - Verify API credentials

2. **"Configuration file issues"**
   - Configuration is now in `ai4pkm_cli.json` (not separate cron.json)
   - The CLI automatically creates this file if it doesn't exist
   - If migrating from old format, update to new structure

3. **"Prompt file not found"**
   - Check `_Settings_/Prompts/` directory
   - Verify file naming (include .md extension in files)

4. **Cron jobs not running**
   - Verify cron expression syntax
   - Check log output for errors
   - Test individual jobs with `-t` flag

5. **Agent not available**
   - Use `--list-agents` to check agent status
   - For Gemini CLI: Install Google AI CLI tools
   - For Codex CLI: Install OpenAI CLI tools
   - System automatically falls back to available agents

6. **Agent switching not working**
   - Check `ai4pkm_cli.json` permissions
   - Verify agent type spelling (claude_code, gemini_cli, codex_cli)
   - Use shortcuts: `-a c/claude`, `-a g/gemini`, `-a o/codex`
   - Use `--show-config` to verify current settings
   - Per-prompt agents: `ai4pkm -a g -p "prompt"` doesn't change global config

### Debug Mode

For detailed debugging, check the logs in `_Settings_/Logs/` or run with verbose console output.

## 📝 Examples

### Daily Knowledge Management

```bash
# Configuration is stored in ai4pkm_cli.json
# The CLI automatically creates and manages this file

# Check the configuration
ai4pkm

# Start the scheduler (runs enabled cron jobs)
ai4pkm -c

# Test a specific job manually
ai4pkm -t

# You can also run prompts directly
ai4pkm -p "DIR for today"
```

### Custom Prompt Execution

```bash
# Ask questions directly
ai4pkm -p "What are the benefits of using a PKM system?"

# Get code help (with agent-specific global prompt)
ai4pkm -a codex -p "Write a Python script to parse JSON files"

# Content analysis (leveraging Claude's global prompt)
ai4pkm -a claude -p "Summarize the key points of this text: [your text]"

# Creative writing
ai4pkm -p "Write a brief introduction to knowledge management"

# Global prompts are automatically prepended to all prompts
# For example, if Claude has global_prompt: "Always respond in Korean",
# then "Hello" becomes "Always respond in Korean\n\nHello"
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

## 🤝 Contributing

This CLI is part of the AI4PKM knowledge management framework. Follow the existing code patterns and ensure all new features include appropriate logging and error handling.

## 📄 License

See the main project license for details.
