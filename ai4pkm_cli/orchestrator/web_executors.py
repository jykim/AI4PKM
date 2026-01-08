"""
Web executor implementations for Gemini and ChatGPT APIs.

This module contains the WebExecutor class that handles web API based
execution for gemini_web and chatgpt_web executors.
"""
import os
import re
import yaml
from pathlib import Path
from typing import Dict, Callable, List
from datetime import datetime

from .models import AgentDefinition, ExecutionContext
from .citation_utils import Citation, render_markdown_with_footnotes
from ..logger import Logger

logger = Logger()


class WebExecutor:
    """
    Helper class for web API based executors.

    Handles execution via Gemini and OpenAI web search APIs,
    including citation parsing and output file writing.
    """

    def __init__(self, vault_path: Path, build_prompt_fn: Callable):
        """
        Initialize WebExecutor.

        Args:
            vault_path: Path to vault root
            build_prompt_fn: Function to build prompts (from ExecutionManager)
        """
        self.vault_path = vault_path
        self._build_prompt = build_prompt_fn

    def execute_gemini_web(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Execute agent using Gemini API with Google Search grounding.

        Args:
            agent: Agent definition
            ctx: Execution context
            trigger_data: Trigger event data
        """
        from google import genai
        from google.genai import types

        ctx.prompt = self._build_prompt(agent, trigger_data, ctx)

        # Append input file content for web executors (they can't access local files)
        ctx.prompt = self._append_input_file_content(ctx.prompt, trigger_data)

        # Configure API
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable not set")

        client = genai.Client(api_key=api_key)

        # Model selection from agent_params
        agent_params = agent.agent_params or {}
        model_name = agent_params.get('model', 'gemini-2.0-flash')

        # Build config with Google Search grounding
        config_kwargs = {
            'tools': [types.Tool(google_search=types.GoogleSearch())]
        }

        # Add thinking config if enabled (for gemini-2.5-pro and similar models)
        thinking_config = agent_params.get('thinking')
        if thinking_config:
            thinking_budget = thinking_config.get('budget_tokens', 8192)
            config_kwargs['thinking_config'] = types.ThinkingConfig(
                thinking_budget=thinking_budget
            )

        # Enable Google Search grounding
        response = client.models.generate_content(
            model=model_name,
            contents=ctx.prompt,
            config=types.GenerateContentConfig(**config_kwargs)
        )

        # Parse citations from groundingMetadata
        text = response.text or ""
        citations = self._parse_gemini_citations(response)

        ctx.response = render_markdown_with_footnotes(text, citations)

        # Write output file if output_path is configured
        self._write_output(agent, ctx, trigger_data)

    def execute_chatgpt_web(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Execute agent using OpenAI Responses API with web_search tool.

        Args:
            agent: Agent definition
            ctx: Execution context
            trigger_data: Trigger event data
        """
        from openai import OpenAI

        ctx.prompt = self._build_prompt(agent, trigger_data, ctx)

        # Append input file content for web executors (they can't access local files)
        ctx.prompt = self._append_input_file_content(ctx.prompt, trigger_data)

        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")

        client = OpenAI(api_key=api_key)

        # Model selection from agent_params
        agent_params = agent.agent_params or {}
        model_name = agent_params.get('model', 'gpt-4o')

        # Build request kwargs
        request_kwargs = {
            'model': model_name,
            'input': ctx.prompt,
            'tools': [{"type": "web_search"}]
        }

        # Add reasoning config if enabled (for o1/o3 and reasoning models)
        reasoning_config = agent_params.get('reasoning')
        if reasoning_config:
            effort = reasoning_config.get('effort', 'high')
            request_kwargs['reasoning'] = {'effort': effort}

        # Use Responses API with web_search tool
        response = client.responses.create(**request_kwargs)

        # Find message output and parse citations
        text = ""
        citations = []

        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        text = content.text
                        annotations = getattr(content, "annotations", []) or []
                        citations = self._parse_openai_citations(annotations)

        ctx.response = render_markdown_with_footnotes(text, citations)

        # Write output file if output_path is configured
        self._write_output(agent, ctx, trigger_data)

    def _parse_gemini_citations(self, response) -> List[Citation]:
        """Parse Gemini grounding metadata to citations."""
        citations = []
        candidates = getattr(response, "candidates", []) or []
        if not candidates:
            return citations

        gm = getattr(candidates[0], "grounding_metadata", None)
        if not gm:
            return citations

        supports = getattr(gm, "grounding_supports", []) or []
        chunks = getattr(gm, "grounding_chunks", []) or []

        for s in supports:
            seg = getattr(s, "segment", None)
            if not seg:
                continue
            end_index = getattr(seg, "end_index", None)
            idxs = getattr(s, "grounding_chunk_indices", []) or []
            if end_index is None or not idxs:
                continue

            for i in idxs:
                if 0 <= i < len(chunks):
                    web = getattr(chunks[i], "web", None)
                    if web:
                        url = getattr(web, "uri", "") or ""
                        title = getattr(web, "title", None)
                        citations.append(Citation(end_index=int(end_index), url=url, title=title))

        return citations

    def _parse_openai_citations(self, annotations: list) -> List[Citation]:
        """Parse OpenAI url_citation annotations to citations."""
        citations = []
        for ann in annotations:
            if getattr(ann, "type", None) == "url_citation":
                end_index = getattr(ann, "end_index", None)
                url = getattr(ann, "url", "") or ""
                title = getattr(ann, "title", None)
                if end_index is not None and url:
                    citations.append(Citation(end_index=int(end_index), url=url, title=title))
        return citations

    def _append_input_file_content(self, prompt: str, trigger_data: Dict) -> str:
        """
        Append input file content to prompt for web executors.

        Web API executors (gemini_web, chatgpt_web) cannot access local files,
        so the input file content must be included in the prompt.

        Args:
            prompt: Base prompt
            trigger_data: Trigger event data with file path

        Returns:
            Prompt with input file content appended
        """
        input_path = trigger_data.get('path', '')
        if not input_path:
            return prompt

        input_file = self.vault_path / input_path
        if not input_file.exists():
            return prompt

        try:
            file_content = input_file.read_text(encoding='utf-8')
            prompt += f"\n\n# Input File Content\n"
            prompt += f"**File**: `{input_path}`\n\n"
            prompt += "```\n"
            prompt += file_content
            prompt += "\n```\n"
        except Exception as e:
            logger.warning(f"Could not read input file {input_path}: {e}")

        return prompt

    def _write_output(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Write web executor response to output file using Template Injection.

        Template Injection ensures data quality by:
        1. Extracting metadata from input file (guaranteed correct)
        2. Extracting only body content from LLM response (stripping any frontmatter)
        3. Building frontmatter from extracted metadata (LLM cannot influence)
        4. Assembling final markdown file

        This prevents common LLM output issues:
        - Corrupted scenario_id (copied incorrectly)
        - Missing frontmatter
        - Junk text before frontmatter
        - Wrong worker names
        """
        if not agent.output_path or not ctx.response:
            return

        output_dir = self.vault_path / agent.output_path
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate output filename from trigger file
        trigger_file = trigger_data.get('file_path', '')
        worker_label = getattr(agent, 'worker_label', None) or agent.executor

        if trigger_file:
            trigger_stem = Path(trigger_file).stem
            output_filename = f"{trigger_stem} - {worker_label}.md"
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_filename = f"{timestamp} - {worker_label}.md"

        # === TEMPLATE INJECTION ===
        # 1. Extract metadata from input file (guaranteed correct)
        input_metadata = self._extract_input_metadata(trigger_data)

        # 2. Extract body only from LLM response (strip any frontmatter/code blocks)
        body = self._extract_body_only(ctx.response)

        # 3. Build frontmatter (Orchestrator controls this - LLM cannot influence)
        frontmatter = self._build_result_frontmatter(input_metadata, agent)

        # 4. Assemble final content
        content = self._assemble_markdown(frontmatter, body)

        output_path = output_dir / output_filename
        output_path.write_text(content, encoding='utf-8')
        logger.info(f"Web executor output written to: {output_path.relative_to(self.vault_path)}")

    def _extract_input_metadata(self, trigger_data: Dict) -> Dict:
        """
        Extract frontmatter metadata from input file.

        Returns:
            Dict of frontmatter fields from input file, or empty dict if not found
        """
        input_path = trigger_data.get('path', '')
        if not input_path:
            return {}

        input_file = self.vault_path / input_path
        if not input_file.exists():
            return {}

        try:
            content = input_file.read_text(encoding='utf-8')
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    return yaml.safe_load(parts[1]) or {}
        except Exception as e:
            logger.warning(f"Could not parse input metadata from {input_path}: {e}")

        return {}

    def _extract_body_only(self, response: str) -> str:
        """
        Extract body content only, stripping any frontmatter or code blocks.

        LLM sometimes generates frontmatter or wraps output in code blocks.
        This method ensures we only get the actual content.

        Args:
            response: Raw LLM response

        Returns:
            Body content without frontmatter or code block wrappers
        """
        text = response.strip()

        # Strip markdown code block wrapper if present
        text = self._strip_markdown_code_block(text)

        # Strip frontmatter if LLM generated one
        if text.startswith('---'):
            parts = text.split('---', 2)
            if len(parts) >= 3:
                text = parts[2].strip()

        return text

    def _build_result_frontmatter(self, input_metadata: Dict, agent: AgentDefinition) -> Dict:
        """
        Build frontmatter for result file.

        This is the ONLY place where frontmatter is generated.
        LLM output does not influence these values.

        Args:
            input_metadata: Metadata extracted from input file
            agent: Agent definition with worker label

        Returns:
            Dict of frontmatter fields for output file
        """
        worker_label = getattr(agent, 'worker_label', None) or agent.executor

        frontmatter = {}

        # Copy from input (guaranteed correct - no LLM involvement)
        copy_fields = ['scenario_id', 'query', 'query_type', 'domain']
        for field in copy_fields:
            if field in input_metadata:
                frontmatter[field] = input_metadata[field]

        # Add execution metadata (Orchestrator controls these)
        frontmatter['task_worker'] = worker_label
        frontmatter['created'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return frontmatter

    def _assemble_markdown(self, frontmatter: Dict, body: str) -> str:
        """
        Assemble final markdown with frontmatter and body.

        Args:
            frontmatter: Dict of frontmatter fields
            body: Body content

        Returns:
            Complete markdown string with frontmatter
        """
        fm_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
        return f"---\n{fm_str}---\n\n{body}"

    def _strip_markdown_code_block(self, text: str) -> str:
        """
        Strip markdown code block wrapper from text if present.

        Models sometimes wrap their output in ```markdown ... ``` blocks.
        This method extracts the content from inside the block.

        Args:
            text: Text that may contain markdown code block wrapper

        Returns:
            Text with code block wrapper removed (if present)
        """
        # Pattern to match ```markdown or ``` at start, and ``` at end
        # Also handles variations like ```md, ```Markdown, etc.
        pattern = r'^```(?:markdown|md|Markdown|MD)?\s*\n(.*?)\n```\s*$'
        match = re.match(pattern, text.strip(), re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Also handle case where there's text before/after the code block
        # e.g., "The output file has been created:\n```markdown\n...\n```"
        pattern2 = r'```(?:markdown|md|Markdown|MD)?\s*\n(.*?)\n```'
        match2 = re.search(pattern2, text, re.DOTALL | re.IGNORECASE)
        if match2:
            return match2.group(1).strip()

        return text
