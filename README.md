This repo contains Starter PKM setup (i.e. Obsidian Vault) for AI4PKM project.
- [[PKM Guidelines]] document contains the thinking behind AI4PKM project.
- Read Jin's [PKM in AI Era](https://publish.obsidian.md/lifidea/Publish/PKM+in+AI+Era/0.+Why+PKM+now%3F) series for more tutorials.

## Directory Structure

- `_Archive_/` - Archived content that's no longer active
- `_Inbox_/` - Temporary storage for unprocessed information
- `_Settings_/` - Vault configuration, prompts, templates, and workflows
- `AI/` - AI-generated insights and research
- `Ingest/` - Incoming information from various sources
- `Journal/` - Personal reflections and daily notes
- `Projects/` - Active project documentation
- `Publish/` - Content ready for publication
- `Topics/` - Organized knowledge by subject

## Getting Started

1. **Explore Community Plugins**: 
   Open Obsidian settings and explore the pre-configured community plugins
2. **Configure Daily Notes**: 
   The daily notes plugin is pre-configured to use the Journal folder
3. **Explore Templates**: 
   Check `_Settings_/Templates/` for note templates
4. **Review Workflows**: 
   Browse `_Settings_/Workflows/` for AI-assisted workflows
5. **Review Prompts**: 
   Browse `_Settings_/Prompts/` for prompts powering the workflows

## AI Integration
This vault is optimized for AI integration with:
- Claude Code configuration in [[CLAUDE]]
- Gemini CLI configuration in [[GEMINI]]
- Codex CLI configuration in [[AGENTS]]
- Cursor IDE rules in `.cursor/rules/`

## AI4PKM CLI

For automated execution, use the CLI Tool provided as a python package.

### Quick Start

1. **Install the CLI:**
   ```bash
   pip install -e .
   ```

2. **Configure the vault:**
   The CLI requires `ai4pkm_cli.json` configuration file in your vault directory.
   
   ```bash
   # Copy example config to your vault
   cp ai4pkm_cli.json.example ai4pkm_vault/ai4pkm_cli.json
   ```

3. **Run from vault directory:**
   ```bash
   cd ai4pkm_vault
   ai4pkm
   ```

For detailed documentation, see [CLI Tool Guide](docs/cli_tool.md).

## Community Plugins
The following plugins are recommended and pre-configured:
- Calendar - Visual calendar interface
- Recent Files - Quick access to recent files
- Style Settings - Customize appearance
- Excalidraw - Diagramming and sketching
- Dataview - Query and display data
- Templater - Advanced templating
- Tasks - Task management
- And more...

