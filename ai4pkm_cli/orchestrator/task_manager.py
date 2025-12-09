"""
Task file manager for orchestrator.

Creates and updates task tracking files in _Tasks_/ directory.
"""
from pathlib import Path
from datetime import datetime
from typing import Optional

from .models import AgentDefinition, ExecutionContext
from ..logger import Logger

logger = Logger()


class TaskFileManager:
    """Manages task file creation and updates."""

    def __init__(self, vault_path: Path, config: Optional['Config'] = None, orchestrator_settings: Optional[dict] = None):
        """
        Initialize task file manager.

        Args:
            vault_path: Path to vault root
            config: Config instance (will create default if None)
            orchestrator_settings: Orchestrator settings from YAML (optional, overrides config)
        """
        from ..config import Config

        self.vault_path = Path(vault_path)
        self.config = config or Config()
        self.orchestrator_settings = orchestrator_settings or {}

        # Get tasks directory from orchestrator settings or fallback to config
        if orchestrator_settings and 'tasks_dir' in orchestrator_settings:
            tasks_dir = orchestrator_settings['tasks_dir']
        else:
            tasks_dir = self.config.get_orchestrator_tasks_dir()

        self.tasks_dir = self.vault_path / tasks_dir
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def create_task_file(
        self,
        ctx: ExecutionContext,
        agent: AgentDefinition,
        initial_status: str = "IN_PROGRESS",
        trigger_data_json: Optional[str] = None
    ) -> Optional[Path]:
        """
        Create a task tracking file for this execution.

        Args:
            ctx: Execution context
            agent: Agent definition
            initial_status: Initial task status (default: IN_PROGRESS)
            trigger_data_json: JSON-encoded trigger data for QUEUED tasks

        Returns:
            Path to created task file, or None if task creation disabled
        """
        if not agent.task_create:
            logger.debug(f"Task file creation disabled for agent {agent.abbreviation}")
            return None

        try:
            # Generate task filename
            task_filename = self._generate_task_filename(ctx, agent)
            task_path = self.tasks_dir / task_filename

            # Check if task file already exists (prevent duplicates)
            if task_path.exists():
                logger.debug(f"Task file already exists: {task_path.name}, returning existing file")
                return task_path

            # Get input file info
            input_file_path = ctx.trigger_data.get('path', 'unknown')
            input_file_name = Path(input_file_path).stem

            # Get generation log link
            log_link = ""
            if ctx.log_file:
                # Make relative to vault for wiki link
                try:
                    rel_log = ctx.log_file.relative_to(self.vault_path)
                    log_link = f"[[{rel_log.parent}/{rel_log.stem}]]"
                except ValueError:
                    log_link = f"[[{ctx.log_file}]]"

            # Create task content
            task_content = self._build_task_content(
                agent=agent,
                ctx=ctx,
                input_file_path=input_file_path,
                log_link=log_link,
                initial_status=initial_status,
                trigger_data_json=trigger_data_json
            )

            # Write task file
            task_path.write_text(task_content, encoding='utf-8')
            logger.info(f"💾 Created task file: {task_path.name}", console=True)

            return task_path

        except Exception as e:
            logger.error(f"Failed to create task file: {e}")
            return None

    def update_task_status(
        self,
        task_path: Path,
        status: str,
        output: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Update task file status and output.

        Args:
            task_path: Path to task file
            status: New status (IN_PROGRESS, PROCESSED, FAILED, etc.)
            output: Optional output file link
            error_message: Optional error message for failed tasks
        """
        if not task_path or not task_path.exists():
            logger.warning(f"Task file not found: {task_path}")
            return

        try:
            # Read current content
            content = task_path.read_text(encoding='utf-8')

            # Update frontmatter
            from ..markdown_utils import update_frontmatter_fields

            updates = {'status': status}
            if output:
                updates['output'] = output
            if error_message:
                # Add error to Process Log section instead of frontmatter
                content = self._append_to_process_log(content, f"Error: {error_message}")

            content = update_frontmatter_fields(content, updates)

            # Write back with explicit flush and sync to ensure disk write
            import os
            with open(task_path, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            logger.info(f"🔄 Updated task file ({status}): {task_path.name}", console=True)

        except Exception as e:
            logger.error(f"❌ Failed to update task file: {e}")

    def update_task_status_with_trigger_data(
        self,
        task_path: Path,
        status: str,
        trigger_data_json: str
    ):
        """
        Update task file status and add trigger_data_json atomically.
        
        Used when enriching QUEUED tasks with trigger data.

        Args:
            task_path: Path to task file
            status: New status (typically "QUEUED")
            trigger_data_json: JSON-encoded trigger data to add to frontmatter
        """
        if not task_path or not task_path.exists():
            logger.warning(f"Task file not found: {task_path}")
            return

        try:
            # Read current content
            content = task_path.read_text(encoding='utf-8')

            # Update frontmatter - both status and trigger_data_json
            from ..markdown_utils import update_frontmatter_fields, extract_frontmatter
            
            # Check if trigger_data_json already exists
            frontmatter = extract_frontmatter(content)
            updates = {'status': status}
            
            # Add trigger_data_json if not already present
            if 'trigger_data_json' not in frontmatter:
                # We need to add it manually since update_frontmatter_fields doesn't handle multi-line values well
                # Find the end of frontmatter and insert trigger_data_json before closing ---
                import re
                import yaml
                match = re.match(r'^(---\s*\n)(.*?)(\n---\s*\n)', content, re.DOTALL)
                if match:
                    prefix = match.group(1)
                    yaml_content = match.group(2)
                    suffix = match.group(3)
                    rest = content[match.end():]
                    
                    # Use YAML's literal block scalar (|) to preserve JSON string without escaping issues
                    # This handles special characters, quotes, and Unicode properly
                    yaml_content += f'\ntrigger_data_json: |\n'
                    # Indent each line of the JSON string
                    for line in trigger_data_json.split('\n'):
                        yaml_content += f'  {line}\n'
                    
                    content = prefix + yaml_content + suffix + rest
                else:
                    logger.warning(f"Could not parse frontmatter in {task_path.name}")
            else:
                # Update existing trigger_data_json - use literal block scalar
                import re
                # Match existing trigger_data_json (could be quoted string or literal block)
                lines = content.split('\n')
                new_lines = []
                skip_indented = False
                for line in lines:
                    if skip_indented:
                        # Skip indented lines (part of literal block or quoted string continuation)
                        # Stop when we hit a non-indented line (new key or closing ---)
                        if line and not line.startswith(' ') and not line.startswith('\t'):
                            skip_indented = False
                        else:
                            continue  # Skip this indented line
                    
                    if re.match(r'^trigger_data_json:\s*', line):
                        # Replace with new literal block format
                        new_lines.append('trigger_data_json: |')
                        # Add JSON content with proper indentation
                        for json_line in trigger_data_json.split('\n'):
                            new_lines.append(f'  {json_line}')
                        skip_indented = True
                    else:
                        new_lines.append(line)
                content = '\n'.join(new_lines)

            # Update status
            content = update_frontmatter_fields(content, updates)

            # Write back with explicit flush and sync to ensure disk write
            import os
            with open(task_path, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            logger.info(f"🔄 Updated task file ({status} with trigger_data): {task_path.name}", console=True)

        except Exception as e:
            logger.error(f"❌ Failed to update task file with trigger data: {e}")

    def _truncate_filename_to_bytes(self, filename: str, max_bytes: int = 250) -> str:
        """
        Truncate filename to fit within byte limit (for filesystem compatibility).

        macOS/HFS+ has a 255-byte filename limit. Since UTF-8 characters can be 1-4 bytes,
        we need to truncate based on byte length, not character count.

        Args:
            filename: Original filename (including extension)
            max_bytes: Maximum byte length (default 250 for safety margin)

        Returns:
            Truncated filename that fits within byte limit
        """
        # Split into stem and extension
        path = Path(filename)
        stem = path.stem
        ext = path.suffix

        # Calculate current byte length
        current_bytes = len(filename.encode('utf-8'))

        if current_bytes <= max_bytes:
            return filename

        # Need to truncate - calculate how many bytes we need to remove
        ext_bytes = len(ext.encode('utf-8'))
        ellipsis = "..."
        ellipsis_bytes = len(ellipsis.encode('utf-8'))

        # Available bytes for stem (accounting for extension and ellipsis)
        available_bytes = max_bytes - ext_bytes - ellipsis_bytes

        # Truncate stem byte by byte until it fits
        stem_encoded = stem.encode('utf-8')
        truncated_stem = stem_encoded[:available_bytes].decode('utf-8', errors='ignore')

        return f"{truncated_stem}{ellipsis}{ext}"

    def _generate_task_filename(self, ctx: ExecutionContext, agent: AgentDefinition) -> str:
        """
        Generate task filename: YYYY-MM-DD {agent_abbr} - {input_filename}.md

        Args:
            ctx: Execution context
            agent: Agent definition

        Returns:
            Task filename (truncated to fit macOS 255-byte limit)
        """
        date_str = ctx.start_time.strftime('%Y-%m-%d') if ctx.start_time else datetime.now().strftime('%Y-%m-%d')

        # Extract input filename from trigger data
        input_path = ctx.trigger_data.get('path', '')
        if input_path:
            input_name = Path(input_path).stem
        else:
            # For scheduled agents, use 'scheduled' with timestamp
            timestamp = ctx.start_time.strftime('%H%M') if ctx.start_time else datetime.now().strftime('%H%M')
            input_name = f'scheduled-{timestamp}'

        filename = f"{date_str} {agent.abbreviation} - {input_name}.md"

        # Truncate if needed to fit macOS 255-byte filename limit
        return self._truncate_filename_to_bytes(filename, max_bytes=250)

    def _build_task_content(
        self,
        agent: AgentDefinition,
        ctx: ExecutionContext,
        input_file_path: str,
        log_link: str,
        initial_status: str = "IN_PROGRESS",
        trigger_data_json: Optional[str] = None
    ) -> str:
        """
        Build task file content.

        Args:
            agent: Agent definition
            ctx: Execution context
            input_file_path: Path to input file
            log_link: Wiki link to generation log
            initial_status: Initial task status (default: IN_PROGRESS)
            trigger_data_json: JSON-encoded trigger data for QUEUED tasks

        Returns:
            Task file content
        """
        from ruamel.yaml import YAML
        from ruamel.yaml.scalarstring import DoubleQuotedScalarString
        from io import StringIO
        
        # Build frontmatter data structure
        created_time = ctx.start_time.isoformat() if ctx.start_time else datetime.now().isoformat()
        
        title = f"{agent.abbreviation} - {Path(input_file_path).stem}"
        
        # Extract base task type and worker label from abbreviation
        # Worker agents have abbreviation like "SPT-Gemini" or "SPE-GeminiResults-Codex"
        # For multi-level agents (e.g., SPE-GeminiResults-Codex), we need to split from the RIGHT
        # to correctly extract: base_task_type="SPE-GeminiResults", worker_label="Codex"
        if '-' in agent.abbreviation:
            parts = agent.abbreviation.rsplit('-', 1)  # Split from right
            base_task_type = parts[0]  # Parent agent ID (e.g., "SPE-GeminiResults")
            worker_label = parts[1]    # Worker label only (e.g., "Codex")
        else:
            base_task_type = agent.abbreviation
            worker_label = ""

        frontmatter_data = {
            'title': title,
            'created': created_time,
            'archived': str(agent.task_archived).lower(),
            'worker': agent.executor,
            'status': initial_status,
            'priority': agent.task_priority,
            'output': "",
            'task_type': base_task_type,  # Base agent abbreviation (e.g., "EIC")
            'generation_log': log_link
        }

        # Add worker_label for multi-worker tasks
        if worker_label:
            frontmatter_data['worker_label'] = worker_label
        
        # Add agent_params if available
        if agent.agent_params:
            frontmatter_data['agent_params'] = agent.agent_params
        
        # Add trigger data for QUEUED tasks
        if trigger_data_json:
            frontmatter_data['trigger_data_json'] = trigger_data_json
        
        # Use ruamel.yaml to generate properly quoted YAML
        yaml_parser = YAML()
        yaml_parser.preserve_quotes = True
        yaml_parser.width = 4096
        
        # Convert ALL string values to DoubleQuotedScalarString for consistency
        for key, value in frontmatter_data.items():
            if isinstance(value, str):
                # Always quote ALL string fields for consistency
                frontmatter_data[key] = DoubleQuotedScalarString(value)
            elif isinstance(value, dict):
                # Handle nested dicts (like agent_params)
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, str):
                        value[nested_key] = DoubleQuotedScalarString(nested_value)
        
        # Generate YAML frontmatter
        stream = StringIO()
        yaml_parser.dump(frontmatter_data, stream)
        frontmatter = "---\n" + stream.getvalue() + "---"

        # Build body
        event_type = ctx.trigger_data.get('event_type', 'unknown')
        event_desc = f"{event_type.capitalize()} file event triggered {agent.name} processing"

        # Remove frontmatter from prompt body if present
        prompt_body = agent.prompt_body
        if prompt_body.startswith('---'):
            # Skip frontmatter in agent definition
            parts = prompt_body.split('---', 2)
            if len(parts) >= 3:
                prompt_body = parts[2].strip()

        body = f"""
## Input

Target file: `[[{input_file_path}]]`

{event_desc}.

## Output

{agent.name} will update this section with output information.

## Instructions

{prompt_body}

## Process Log

## Evaluation Log

"""

        return frontmatter + "\n" + body

    def _append_to_process_log(self, content: str, log_entry: str) -> str:
        """
        Append entry to Process Log section.

        Args:
            content: Current task file content
            log_entry: Log entry to append

        Returns:
            Updated content
        """
        # Find Process Log section
        if "## Process Log" in content:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"\n- [{timestamp}] {log_entry}\n"
            content = content.replace("## Process Log", f"## Process Log{log_line}", 1)

        return content
