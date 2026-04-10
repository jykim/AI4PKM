# AI4PKM CLI

A command-line interface for automating personal knowledge management workflows using AI agents. The CLI provides scheduled prompt execution, multi-agent orchestration, and seamless integration with Claude, Gemini, and Codex.

> **Looking for the Obsidian Vault?** The starter PKM vault (templates, workflows, prompts) is in a separate repo: [jykim/ai4pkm-vault](https://github.com/jykim/ai4pkm-vault)

## Features

- **Multi-Agent Orchestrator**: Config-driven system that monitors vault files and triggers AI agents automatically
- **Cron Job Scheduling**: Automated execution of recurring knowledge management tasks
- **Multiple AI Agents**: Standardized interface to call Claude Code, Gemini CLI, and Codex CLI
- **Vault Template Management**: Bootstrap new vaults from pre-configured templates
- **Self-Update**: Keep the CLI up to date with `ai4pkm update`

## Installation

### Prerequisites
- Python 3.8 or higher

### Install as Package

```bash
pip install -e .
```

After installation, the CLI is available as the `ai4pkm` command.

## Quick Start

```bash
# Show current configuration and usage
ai4pkm

# Start the multi-agent orchestrator
ai4pkm -o

# Execute a prompt directly
ai4pkm -p "What are the key topics in my vault this week?"

# Use a specific agent for one prompt
ai4pkm -a gemini -p "Translate this to Korean: Hello world"

# Start cron scheduler for recurring tasks
ai4pkm -c

# Trigger a specific agent manually
ai4pkm trigger EIC

# Install a starter vault
ai4pkm template install ai4pkm ~/my-vault

# Update CLI to latest version
ai4pkm update
```

## Configuration

The CLI uses configuration files in the `_Settings_/` directory:

| Path | Purpose |
|------|---------|
| `_Settings_/Prompts/` | Prompt definitions for agents |
| `_Settings_/Tasks/` | Task tracking files |
| `_Settings_/Skills/` | Agent skill definitions |
| `_Settings_/Bases/` | Base configurations |
| `_Settings_/Logs/` | Execution logs |
| `orchestrator.yaml` | Multi-agent orchestrator config |
| `cron.json` | Scheduled task definitions |

## Documentation

See [docs/](docs/) for detailed documentation:
- [CLI Tool Reference](docs/cli_tool.md) - Full command reference and examples
- [Orchestrator Guide](docs/orchestrator.md) - Multi-agent orchestrator setup
- [Workflows](docs/workflows.md) - AI-assisted workflow patterns
- [Prompts](docs/prompts.md) - Prompt system documentation

## Related

- [ai4pkm-vault](https://github.com/jykim/ai4pkm-vault) - Starter Obsidian vault for AI4PKM
- Read Jin's [PKM in AI Era](https://publish.obsidian.md/lifidea/Publish/PKM+in+AI+Era/0.+Why+PKM+now%3F) series for tutorials
