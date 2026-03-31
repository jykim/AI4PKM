"""
Utilities for reading and writing markdown file frontmatter.

This module provides functions to parse and update YAML frontmatter
in markdown files. Used by both KTM (legacy) and orchestrator (new).
"""
import re
import yaml
from typing import Dict, Any
from pathlib import Path
from io import StringIO
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString


def extract_frontmatter(content: str) -> Dict[str, Any]:
    """
    Extract YAML frontmatter from markdown content.

    Args:
        content: Markdown file content

    Returns:
        Dictionary of frontmatter properties
    """
    # Match YAML frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return {}

    yaml_content = match.group(1)

    try:
        # Use yaml.safe_load for proper YAML parsing (handles lists, nested structures, etc.)
        frontmatter = yaml.safe_load(yaml_content)
        return frontmatter if frontmatter is not None else {}
    except yaml.YAMLError:
        # Fall back to empty dict if YAML is invalid
        return {}


def read_frontmatter(file_path: Path) -> Dict[str, Any]:
    """
    Read and parse frontmatter from markdown file.

    Args:
        file_path: Path to markdown file

    Returns:
        Dictionary of frontmatter properties
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        return extract_frontmatter(content)
    except Exception:
        return {}


def update_frontmatter_field(content: str, field: str, value: Any) -> str:
    """
    Update a field in YAML frontmatter using ruamel.yaml for proper quoting.

    Args:
        content: Full markdown content
        field: Field name to update
        value: New value (will be properly quoted if string)

    Returns:
        Updated content
    """
    # Match frontmatter
    match = re.match(r'^(---\s*\n)(.*?)(\n---\s*\n)', content, re.DOTALL)
    if not match:
        return content

    prefix = match.group(1)
    yaml_content = match.group(2)
    suffix = match.group(3)
    rest = content[match.end():]

    # Use ruamel.yaml for proper YAML generation with correct quoting
    yaml_parser = YAML()
    yaml_parser.preserve_quotes = True
    yaml_parser.width = 4096  # Prevent line wrapping
    
    try:
        # Parse existing YAML
        data = yaml_parser.load(yaml_content) or {}
        
        # Update field with proper quoting
        if isinstance(value, str):
            # Use double quotes for strings that need quoting (special chars, spaces, etc.)
            if any(char in value for char in ['"', "'", ':', '[', ']', '{', '}', '&', '*', '#', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`', '\n']):
                data[field] = DoubleQuotedScalarString(value)
            else:
                data[field] = value
        else:
            data[field] = value
        
        # Write back YAML
        stream = StringIO()
        yaml_parser.dump(data, stream)
        updated_yaml = stream.getvalue()
        
        return prefix + updated_yaml + suffix + rest
    except Exception as e:
        # Log the parsing failure
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"ruamel.yaml parse failed, using fallback: {e}")

        # Fallback: use PyYAML safe_load which is more tolerant
        try:
            import yaml as pyyaml
            data = pyyaml.safe_load(yaml_content) or {}
            data[field] = value
            updated_yaml = pyyaml.dump(data, default_flow_style=False, allow_unicode=True)
            return prefix + updated_yaml + suffix + rest
        except Exception:
            # Last resort: regex-based update
            field_pattern = rf'^{re.escape(field)}:\s*.*$'
            if re.search(field_pattern, yaml_content, re.MULTILINE):
                # Update existing field - escape quotes in value
                escaped_value = str(value).replace('"', '\\"')
                yaml_content = re.sub(field_pattern, f'{field}: "{escaped_value}"', yaml_content, flags=re.MULTILINE)
            else:
                # Add new field
                escaped_value = str(value).replace('"', '\\"')
                yaml_content += f'\n{field}: "{escaped_value}"'

            return prefix + yaml_content + suffix + rest


def update_frontmatter_fields(content: str, updates: Dict[str, Any]) -> str:
    """
    Update multiple fields in YAML frontmatter using ruamel.yaml.

    Args:
        content: Full markdown content
        updates: Dictionary of field: value pairs to update

    Returns:
        Updated content
    """
    # Match frontmatter
    match = re.match(r'^(---\s*\n)(.*?)(\n---\s*\n)', content, re.DOTALL)
    if not match:
        return content

    prefix = match.group(1)
    yaml_content = match.group(2)
    suffix = match.group(3)
    rest = content[match.end():]

    # Use ruamel.yaml for proper YAML generation
    yaml_parser = YAML()
    yaml_parser.preserve_quotes = True
    yaml_parser.width = 4096
    
    try:
        # Parse existing YAML
        data = yaml_parser.load(yaml_content) or {}
        
        # Update all fields with proper quoting
        for field, value in updates.items():
            if isinstance(value, str):
                # Use double quotes for strings that need quoting
                if any(char in value for char in ['"', "'", ':', '[', ']', '{', '}', '&', '*', '#', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`', '\n']):
                    data[field] = DoubleQuotedScalarString(value)
                else:
                    data[field] = value
            else:
                data[field] = value
        
        # Write back YAML
        stream = StringIO()
        yaml_parser.dump(data, stream)
        updated_yaml = stream.getvalue()
        
        return prefix + updated_yaml + suffix + rest
    except Exception as e:
        # Log the parsing failure
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"ruamel.yaml parse failed in update_frontmatter_fields, using fallback: {e}")

        # Fallback: update fields one by one (uses improved fallback in singular function)
        for field, value in updates.items():
            content = update_frontmatter_field(content, field, value)
        return content


def extract_body(content: str) -> str:
    """
    Extract body content (after frontmatter) from markdown.

    Args:
        content: Full markdown content

    Returns:
        Body content (everything after frontmatter)
    """
    # Remove frontmatter
    match = re.match(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
    if match:
        return content[match.end():]
    return content


def remove_pattern_from_content(content: str, pattern: str) -> str:
    """
    Remove pattern from content using regex.

    Generic utility for removing patterns from markdown content.
    Used for post-processing after agent execution.

    Args:
        content: Full markdown content
        pattern: Regex pattern to remove

    Returns:
        Content with pattern removed
    """
    try:
        # Remove pattern (case-insensitive, multiline)
        updated = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        return updated
    except re.error as e:
        # If pattern is invalid, return content unchanged
        return content
