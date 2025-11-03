---
layout: post
title: "Automated Content Pipeline: From Web Clipping to Social Media Threads"
date: 2025-11-03
categories: blog
author: Jin Kim & Minsuk Kang
---

The EIC→CTP pipeline automates your content workflow from the moment you clip a web article to when it's ready to share on social media. This guide walks you through setting up and running this automated pipeline.

## Why We Built This

Content curation is a multi-step process: you find interesting articles, save them, read them, extract key insights, and eventually share those insights with others. Each step requires context switching and manual effort.

What if this entire workflow could be automated? When you clip an interesting article:
1. It gets automatically enriched with summaries and knowledge graph links
2. Shareable social media threads are generated from the enriched content
3. You review the final drafts rather than creating them from scratch

This is exactly what the EIC→CTP pipeline does. By chaining two agents together, you transform raw web clippings into publication-ready social media content—automatically.

## The EIC→CTP Pipeline

The pipeline consists of two agents working in sequence:

### EIC (Enrich Ingested Content)
Transforms raw web clippings into structured, enriched articles.

**Input**: Raw content from `Ingest/Clippings/`
- Web clippings from Readwise Reader or Obsidian Web Clipper
- Often contains transcript errors and poor formatting

**Output**: Enriched articles in `AI/Articles/`
- Fixed formatting and grammar
- Summary section for quick understanding
- Links to related knowledge base topics

**Process**:
1. Fix transcript errors and improve formatting
2. Add catchy summary suitable for sharing
3. Link to related knowledge base topics

### CTP (Create Thread Postings)
Generates social media thread candidates from enriched content.

**Input**: Enriched articles from `AI/Articles/` (EIC's output)

**Output**: Thread-ready content in `AI/Sharable/`
- Maximum 1k characters per thread
- Up to 5 threads per output
- Source attribution for each thread

**Process**:
1. Extract memorable quotes and summaries
2. Organize into thread-sized chunks
3. Add source links for attribution

### The Automated Flow

```
Web Content
    ↓ (User clips with Obsidian Web Clipper)
Ingest/Clippings/article.md
    ↓ (File monitor detects → EIC triggers)
AI/Articles/article - EIC.md
    ↓ (File monitor detects → CTP triggers)
AI/Sharable/article - CTP.md
```

The orchestrator handles the entire chain automatically. You clip content, and within minutes you have both an enriched article and shareable thread content.

> **Note**: This pipeline is for demonstration purposes. All components are fully configurable:
> - **Input/output paths** can be changed to match your vault structure
> - **Agent prompts** can be customized for your specific workflow
> - **Directory names** are examples - use whatever organization makes sense for you
>
> The orchestrator is flexible and adapts to your personal knowledge management system.

## Setup Guide

### 1. Configure EIC Agent

Add the EIC agent to your `orchestrator.yaml`:

```yaml
nodes:
  # Enrich Ingested Content
  - type: agent
    name: Enrich Ingested Content (EIC)
    input_path: Ingest/Clippings
    output_path: AI/Articles
    output_type: new_file  # Creates new files (this is the default)
```

This tells the orchestrator:
- Monitor `Ingest/Clippings/` for new files
- Run the EIC agent when files appear
- Create output in `AI/Articles/`

### 2. Configure CTP Agent

Add the CTP agent to process EIC's output:

```yaml
  # Create Thread Postings
  - type: agent
    name: Create Thread Postings (CTP)
    input_path:
      - AI/Articles
      - AI/Roundup
      - AI/Research
    output_path: AI/Sharable
```

CTP monitors multiple directories, including `AI/Articles/` where EIC writes its output. When EIC creates a new file, CTP automatically processes it.

### 3. Verify Configuration

The EIC and CTP prompt files should already exist in your vault:
- `_Settings_/Prompts/Enrich Ingested Content (EIC).md`
- `_Settings_/Prompts/Create Thread Postings (CTP).md`

Check that your agents are configured correctly:

```bash
ai4pkm --orchestrator-status
```

You should see both EIC and CTP listed with their input/output paths.

## Running the Pipeline

### Start the Orchestrator

```bash
ai4pkm -o
```

The orchestrator starts monitoring your vault for file changes. You'll see log messages as it detects events and triggers agents.

### Clip Web Content

Use your preferred web clipper (Obsidian Web Clipper or Readwise Reader) to save an article to `Ingest/Clippings/`.

### Watch the Processing

The orchestrator automatically:

1. **Detects the new clipping**
   ```
   [INFO] File created: Ingest/Clippings/article.md
   [INFO] Triggering agent: EIC
   ```

2. **Creates a task file** in `_Settings_/Tasks/`
   ```
   2025-11-03 EIC - article.md
   ```

3. **Runs EIC agent**
   - Reads the clipping
   - Enriches content
   - Creates output in `AI/Articles/`

4. **Detects EIC output and triggers CTP**
   ```
   [INFO] File created: AI/Articles/article - EIC.md
   [INFO] Triggering agent: CTP
   ```

5. **Runs CTP agent**
   - Reads enriched article
   - Generates thread content
   - Creates output in `AI/Sharable/`

### Review the Results

Check the output directories:
- `AI/Articles/` - Your enriched article with summary and links
- `AI/Sharable/` - Social media thread drafts ready to post

Task files in `_Settings_/Tasks/` show execution status and output links:

```markdown
---
status: PROCESSED
output: [[AI/Articles/article - EIC]]
---
```

## Configuration Reference

### Complete orchestrator.yaml Example

```yaml
version: "1.0"

orchestrator:
  prompts_dir: "_Settings_/Prompts"
  tasks_dir: "_Settings_/Tasks"
  logs_dir: "_Settings_/Logs"
  max_concurrent: 3
  poll_interval: 1.0

defaults:
  executor: claude_code
  timeout_minutes: 30
  task_create: true

nodes:
  # Enrich Ingested Content
  - type: agent
    name: Enrich Ingested Content (EIC)
    input_path: Ingest/Clippings
    output_path: AI/Articles
    trigger_exclude_pattern: "*-EIC*"

  # Create Thread Postings
  - type: agent
    name: Create Thread Postings (CTP)
    input_path:
      - AI/Articles
      - AI/Roundup
      - AI/Research
    output_path: AI/Sharable
```

### GitHub Links

View the complete implementation in the repository:

**Configuration Files**:
- [orchestrator.yaml](https://github.com/jykim/AI4PKM/blob/main/ai4pkm_vault/orchestrator.yaml) - Complete configuration example
- [EIC prompt](https://github.com/jykim/AI4PKM/blob/main/ai4pkm_vault/_Settings_/Prompts/Enrich%20Ingested%20Content%20(EIC).md) - EIC agent instructions
- [CTP prompt](https://github.com/jykim/AI4PKM/blob/main/ai4pkm_vault/_Settings_/Prompts/Create%20Thread%20Postings%20(CTP).md) - CTP agent instructions

**Implementation Details** (PR #40):
- [execution_manager.py](https://github.com/jykim/AI4PKM/blob/feature/output-path-injection/ai4pkm_cli/orchestrator/execution_manager.py#L443-L465) - Output path injection
- [file_monitor.py](https://github.com/jykim/AI4PKM/blob/feature/output-path-injection/ai4pkm_cli/orchestrator/file_monitor.py#L81-L86) - Atomic write detection

## Troubleshooting

### EIC or CTP Not Triggering

**Check the logs**:
```bash
tail -f ai4pkm_vault/_Settings_/Logs/*.log
```

**Common issues**:
- File excluded by `trigger_exclude_pattern`
- Output directory doesn't exist
- Agent prompt file missing

**Verify configuration**:
```bash
ai4pkm --orchestrator-status
```

### Output Not Created

**Check task files** in `_Settings_/Tasks/`:
- Status should be `PROCESSED`
- If status is `FAILED`, check error message
- Output link shows where file was created

**Check validation**:
The orchestrator validates that output files are created. If validation fails:
- Ensure output directory exists
- Check agent actually created a file
- Review execution logs for errors

### Pipeline Breaks

If EIC completes but CTP doesn't trigger:

**Verify file detection**:
- Check orchestrator console for file detection events
- EIC should create file in `AI/Articles/`
- File monitor should detect the new file

**Recent fix** (PR #40):
We added atomic write detection to handle files created by modern editors. If you're running an older version, update to get this fix.

## Next Steps

Now that you have the basic pipeline working, you can:

1. **Customize the prompts** - Edit prompt files to match your writing style
2. **Add more agents** - Create new agents for different content types
3. **Chain more agents** - Build longer pipelines (e.g., EIC → Summary → Thread → Post)
4. **Adjust concurrency** - Process multiple items in parallel with `max_concurrent`

## Resources

**Documentation**:
- [Orchestrator Guide](https://jykim.github.io/AI4PKM/orchestrator.html) - Complete orchestrator documentation
- [Workflows Guide](https://jykim.github.io/AI4PKM/workflows.html) - More workflow examples

**Blog Posts**:
- [New Architecture for Agentic AI](https://jykim.github.io/AI4PKM/blog/2025/10/30/new-architecture-for-agentic-ai.html) - Orchestrator architecture overview
- [On-demand Task Processing](https://jykim.github.io/AI4PKM/blog/2025/10/20/on-demand-knowledge-task.html) - Background and evolution

**GitHub**:
- [AI4PKM Repository](https://github.com/jykim/AI4PKM) - Source code and issues
- [Pull Request #40](https://github.com/jykim/AI4PKM/pull/40) - Output path injection and atomic write detection

---

The EIC→CTP pipeline demonstrates the power of chaining agents together. By automating the content enrichment and thread creation workflow, you can focus on curating great content rather than formatting it for sharing.
