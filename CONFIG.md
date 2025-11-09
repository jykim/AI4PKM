# AI4PKM Configuration Guide

## Configuration File Location

### Where is `ai4pkm_cli.json`?

The `ai4pkm_cli.json` configuration file should be located in your **vault directory**, not in the repository root.

**Correct location:** `ai4pkm_vault/ai4pkm_cli.json`

### Why this location?

The AI4PKM CLI is designed to work with your Obsidian vault. When you run `ai4pkm` commands, the CLI:
1. Looks for `ai4pkm_cli.json` in the current working directory
2. Expects to be run from inside your vault directory
3. Uses relative paths configured in the JSON file (relative to the vault root)

## Initial Setup

### 1. Copy the Example Configuration

An example configuration file is provided in the repository root:

```bash
cp ai4pkm_cli.json.example ai4pkm_vault/ai4pkm_cli.json
```

### 2. Navigate to Your Vault

Always run the CLI from your vault directory:

```bash
cd ai4pkm_vault
```

### 3. Verify Setup

Run the CLI to verify your configuration:

```bash
ai4pkm --show-config
```

## Configuration File Structure

The `ai4pkm_cli.json` file contains several configuration sections:

### Agent Configuration

```json
{
  "default-agent": "claude_code",
  "agents-config": {
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
}
```

- `default-agent`: Which AI agent to use by default
- `agents-config`: Settings for each available agent

### Photo Processing

```json
{
  "photo_processing": {
    "source_folder": "Ingest/Photolog/Original/",
    "destination_folder": "Ingest/Photolog/Processed/",
    "albums": ["AI4PKM"],
    "days": 7
  }
}
```

Configures automatic photo sync and processing from iCloud.

### Task Management

```json
{
  "task_management": {
    "max_concurrent": 5,
    "processing_agent": {
      "EIC": "claude_code",
      "Research": "gemini_cli",
      "default": "claude_code"
    },
    "evaluation_agent": "claude_code",
    "timeout_minutes": 30,
    "max_retries": 2
  }
}
```

Controls how knowledge tasks are generated, processed, and evaluated.

### Orchestrator Settings

```json
{
  "orchestrator": {
    "prompts_dir": "_Settings_/Prompts",
    "tasks_dir": "_Settings_/Tasks",
    "logs_dir": "_Settings_/Logs",
    "skills_dir": "_Settings_/Skills",
    "bases_dir": "_Settings_/Bases",
    "max_concurrent": 3,
    "poll_interval": 1.0
  }
}
```

Settings for the multi-agent orchestrator system.

### Cron Jobs

```json
{
  "cron_jobs": [
    {
      "inline_prompt": "DIR for today",
      "cron": "0 21 * * *",
      "description": "Daily ingestion and processing",
      "enabled": true
    }
  ]
}
```

Scheduled automation tasks with cron syntax.

## Troubleshooting

### Error: "ai4pkm_cli.json not found"

**Cause:** You're running the CLI from the wrong directory.

**Solution:** 
1. Make sure `ai4pkm_cli.json` exists in your vault directory
2. Navigate to your vault: `cd ai4pkm_vault`
3. Run the CLI from there: `ai4pkm`

### Config file exists but CLI doesn't see it

**Cause:** You may be in the wrong directory.

**Solution:**
```bash
# Check your current directory
pwd

# You should be in your vault directory, e.g.:
# /path/to/AI4PKM/ai4pkm_vault

# Check if config exists
ls -la ai4pkm_cli.json
```

### Creating a new vault

If you're creating a new vault (not using `ai4pkm_vault`):

1. Create your vault directory
2. Copy the example config:
   ```bash
   cp ai4pkm_cli.json.example my_vault/ai4pkm_cli.json
   ```
3. Navigate to your vault and run:
   ```bash
   cd my_vault
   ai4pkm
   ```

## Additional Configuration Files

The AI4PKM system uses multiple configuration files:

- **`ai4pkm_cli.json`** (vault root) - Main CLI configuration
- **`orchestrator.yaml`** (vault root) - Orchestrator agent definitions
- **`.obsidian/`** (vault root) - Obsidian app configuration

All paths in `ai4pkm_cli.json` are relative to your vault directory.

## See Also

- [CLI Tool Documentation](docs/cli_tool.md)
- [Orchestrator User Guide](docs/_specs/2025-10-27%20Orchestrator%20User%20Guide)
- [Example Configuration](ai4pkm_cli.json.example)
