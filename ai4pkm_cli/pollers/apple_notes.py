"""Apple Notes processing poller - syncs notes from Apple Notes app."""

import glob
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from .base_poller import BasePoller
from ..logger import Logger

logger = Logger()

class AppleNotesPoller(BasePoller):
    """Poller for processing Apple Notes with configurable destination folders."""

    def __init__(
        self,
        poller_config: Dict[str, Any],
        vault_path: Optional[Path] = None,
    ):
        """
        Initialize notes processing poller.

        Args:
            poller_config: Poller-specific configuration dictionary
            vault_path: Vault root path
        """
        super().__init__(poller_config, vault_path)
        
        self.destination_folder = str(self.target_dir)
        self.days = self.poller_config.get("days", 7)

    def poll(self) -> bool:
        """
        Perform one notes processing operation.

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Processing notes to: {self.destination_folder}")
        logger.info(f"Looking back {self.days} days")
        
        existing_note_ids = set()
        if os.path.exists(self.destination_folder):
            for filename in os.listdir(self.destination_folder):
                if filename.endswith('.md'):
                    filepath = os.path.join(self.destination_folder, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if content.startswith('---'):
                                frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
                                if frontmatter_match:
                                    frontmatter = frontmatter_match.group(1)
                                    id_match = re.search(r'^id:\s*["\']?([^"\'\n]+)', frontmatter, re.MULTILINE)
                                    if id_match:
                                        existing_note_ids.add(id_match.group(1))
                    except Exception:
                        continue
        
        logger.info(f"Found {len(existing_note_ids)} existing processed notes")

        temp_folder = os.path.join(self.destination_folder, "_temp_export")
        
        try:
            logger.info("Exporting notes from Apple Notes app...")
            
            script_path = os.path.join(
                os.path.dirname(__file__), "..", "scripts", "export_notes.applescript"
            )
            script_path = os.path.abspath(script_path)
            
            if not os.path.exists(script_path):
                logger.error(f"AppleScript not found: {script_path}")
                return False

            result = subprocess.run(
                ["osascript", script_path, temp_folder, str(self.days)], 
                capture_output=True, text=True, check=True
            )
            
            if result.stderr:
                for line in result.stderr.strip().split('\n'):
                    line = line.strip()
                    if line:
                        if any(keyword in line for keyword in ["Exported:", "Export completed:", "Total notes"]):
                            logger.info(f"AppleScript: {line}")
                        else:
                            logger.debug(f"AppleScript: {line}")
                            
            logger.info("Notes export completed successfully")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"AppleScript execution failed: {e}")
            logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error exporting/caching notes: {e}")
            return False

        try:
            logger.info("Processing exported notes...")
            
            os.makedirs(self.destination_folder, exist_ok=True)
            
            files_folder = os.path.join(self.destination_folder, "_files_")
            os.makedirs(files_folder, exist_ok=True)
            
            json_pattern = os.path.join(temp_folder, "*.json")
            json_files = glob.glob(json_pattern)
            
            logger.debug(f"Looking for JSON files with pattern: {json_pattern}")
            logger.info(f"Found {len(json_files)} exported notes to process")
            
            processed_count = 0
            skipped_count = 0
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    base_name = os.path.splitext(os.path.basename(json_file))[0]
                    html_file = os.path.join(temp_folder, base_name + ".html")
                    
                    if not os.path.exists(html_file):
                        logger.warning(f"HTML file not found for: {base_name}")
                        continue
                    
                    note_id = metadata.get('id')
                    if note_id and note_id in existing_note_ids:
                        skipped_count += 1
                        logger.debug(f"Already processed: {metadata.get('title', 'Untitled')} (id: {note_id})")
                        continue
                    
                    self._process_single_note(metadata, html_file, self.destination_folder, files_folder)
                    processed_count += 1
                    
                    final_filename = base_name + ".md"
                    logger.info(f"Processed: {final_filename}")
                    
                except Exception as e:
                    logger.error(f"Error processing {json_file}: {e}")
                    continue
            
            logger.info(f"Notes processing completed: {processed_count} processed, {skipped_count} skipped")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing notes: {e}")
            return False
        finally:
            try:
                if os.path.exists(temp_folder):
                    shutil.rmtree(temp_folder)
                    logger.debug("Cleaned up temporary export folder")
            except Exception as e:
                logger.warning(f"Could not clean up temp folder: {e}")

    def _sanitize_title(self, title: str) -> str:
        """Sanitize title to match the format used in filenames."""
        safe_title = title.replace("/", "-").replace("\\", "-").replace(":", "-")
        safe_title = safe_title.replace("*", "-").replace("?", "-").replace("\"", "-")
        safe_title = safe_title.replace("<", "-").replace(">", "-").replace("|", "-")
        safe_title = safe_title.replace("  ", " ").strip()
        
        if len(safe_title) > 100:
            safe_title = safe_title[:100]
        
        return safe_title

    def _process_single_note(self, metadata: Dict, html_file: str, destination_folder: str, files_folder: str) -> None:
        """Process a single note: convert to markdown and handle attachments."""
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        filename = metadata.get('filename', '')
        date_match = re.match(r'^(\d{4}-\d{2}-\d{2})', filename)
        date_prefix = date_match.group(1) if date_match else metadata.get('created', '').split('T')[0]
        
        note_title = metadata.get('title', 'Untitled')
        html_content = self._process_attachments_html(html_content, note_title, date_prefix, files_folder)
        
        markdown_content = self._html_to_markdown(html_content)
        
        markdown_content = re.sub(r'!\[\]\(\)', '', markdown_content)
        
        if hasattr(self, '_extracted_images') and self._extracted_images:
            if markdown_content.strip():
                markdown_content += "\n\n---\n\n"
            markdown_content += "\n".join(self._extracted_images)
        
        frontmatter = self._create_frontmatter(metadata)
        
        final_content = frontmatter + "\n\n" + markdown_content
        
        final_content = self._clean_markdown_newlines(final_content)
        
        final_filename = filename + ".md"
        final_path = os.path.join(destination_folder, final_filename)
        
        with open(final_path, 'w', encoding='utf-8') as f:
            f.write(final_content)

    def _html_to_markdown(self, html_content: str) -> str:
        """Convert HTML content to markdown."""
        try:
            import html2text
            converter = html2text.HTML2Text()
            converter.ignore_links = False
            converter.body_width = 0
            converter.unicode_snob = True
            return converter.handle(html_content).strip()
        except ImportError:
            logger.debug("html2text not available, using basic conversion")
            return self._basic_html_to_markdown(html_content)

    def _basic_html_to_markdown(self, html_content: str) -> str:
        """Basic HTML to markdown conversion without external dependencies."""
        import html
        
        content = html.unescape(html_content)
        content = re.sub(r'<[^>]*>\s*</[^>]*>', '', content)
        content = re.sub(r'<br\s*/?>', '\n', content)
        content = re.sub(r'<p[^>]*>(.*?)</p>', lambda m: m.group(1).strip() + '\n\n' if m.group(1).strip() else '', content, flags=re.DOTALL)
        content = re.sub(r'<b[^>]*>(.*?)</b>', lambda m: f'**{m.group(1).strip()}**' if m.group(1).strip() else '', content, flags=re.DOTALL)
        content = re.sub(r'<strong[^>]*>(.*?)</strong>', lambda m: f'**{m.group(1).strip()}**' if m.group(1).strip() else '', content, flags=re.DOTALL)
        content = re.sub(r'<i[^>]*>(.*?)</i>', lambda m: f'*{m.group(1).strip()}*' if m.group(1).strip() else '', content, flags=re.DOTALL)
        content = re.sub(r'<em[^>]*>(.*?)</em>', lambda m: f'*{m.group(1).strip()}*' if m.group(1).strip() else '', content, flags=re.DOTALL)
        content = re.sub(r'<h1[^>]*>(.*?)</h1>', lambda m: f'# {m.group(1).strip()}\n\n' if m.group(1).strip() else '', content, flags=re.DOTALL)
        content = re.sub(r'<h2[^>]*>(.*?)</h2>', lambda m: f'## {m.group(1).strip()}\n\n' if m.group(1).strip() else '', content, flags=re.DOTALL)
        content = re.sub(r'<h3[^>]*>(.*?)</h3>', lambda m: f'### {m.group(1).strip()}\n\n' if m.group(1).strip() else '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        return content.strip()

    def _process_attachments_html(self, html_content: str, note_title: str, date_prefix: str, files_folder: str) -> str:
        """Extract images from data URLs in HTML and save them as files."""
        import base64
        
        safe_title = self._sanitize_title(note_title)
        data_url_pattern = r'data:image/([^;]+);base64,([^"\'>\s]+)'
        
        image_count = 0
        extracted_images = []
        
        def extract_data_url(match):
            nonlocal image_count
            image_format = match.group(1)
            image_data = match.group(2)
            
            try:
                decoded_data = base64.b64decode(image_data)
                image_count += 1
                filename = f"{date_prefix} {safe_title}-image{image_count:02d}.{image_format}"
                image_path = os.path.join(files_folder, filename)
                
                os.makedirs(files_folder, exist_ok=True)
                
                with open(image_path, 'wb') as f:
                    f.write(decoded_data)
                
                extracted_images.append(f"![[{filename}]]")
                return ""
            except Exception as e:
                logger.warning(f"Could not extract image: {e}")
                return ""
        
        processed_content = re.sub(data_url_pattern, extract_data_url, html_content)
        
        if image_count > 0:
            logger.info(f"Extracted {image_count} images from HTML to _files_/")
            self._extracted_images = extracted_images
        else:
            self._extracted_images = []
        
        return processed_content

    def _create_frontmatter(self, metadata: Dict) -> str:
        """Create YAML frontmatter for the note."""
        title = metadata.get('title', 'Untitled')
        created = metadata.get('created', '')
        modified = metadata.get('modified', '')
        note_id = metadata.get('id', '')
        
        created_date = created.split('T')[0] if created else ''
        modified_date = modified.split('T')[0] if modified else ''
        
        frontmatter = f"""---
title: "{title}"
source: "Apple Notes"
created: {created_date}
modified: {modified_date}"""
        
        if note_id:
            frontmatter += f"\nid: {note_id}"
        
        frontmatter += """
tags:
  - notes
  - imported
---"""
        
        return frontmatter

    def _clean_markdown_newlines(self, content: str) -> str:
        """Clean up redundant newlines and whitespace in markdown content."""
        content = re.sub(r'\*\*\s*\*\*', '', content)
        content = re.sub(r'\*\s*\*(?!\*)', '', content)
        content = re.sub(r'^#+\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^>\s*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.rstrip() + '\n'


def main():
    """Standalone execution entry point."""
    import sys
    from ..config import Config
    
    config = Config()
    
    poller_config = config.get('pollers', {}).get("apple_notes", {})
    if not poller_config:
        logger.error("apple_notes poller configuration not found in orchestrator.yaml")
        sys.exit(1)
    
    poller = AppleNotesPoller(poller_config)
    success = poller.run_once()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

