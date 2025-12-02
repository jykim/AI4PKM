"""Limitless sync poller - syncs data from Limitless API."""

import requests
import time
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
import pytz
from tzlocal import get_localzone

from .base_poller import BasePoller
from ..logger import Logger

logger = Logger()


class LimitlessPoller(BasePoller):
    """Poller for syncing Limitless data."""

    def __init__(
        self,
        poller_config: Dict[str, Any],
        vault_path: Optional[Path] = None,
    ):
        """
        Initialize Limitless sync poller.

        Args:
            poller_config: Poller-specific configuration dictionary
            vault_path: Vault root path
        """
        super().__init__(poller_config, vault_path)
        
        self.api_key = self.poller_config.get("api_key")
        
        if not self.api_key:
            self.is_ready = False
            logger.warning("api_key not found in secrets.yaml for limitless poller. Poller will skip.")
            return
        
        self.is_ready = True
        self.api_base_url = self.poller_config.get('api_base_url', "https://api.limitless.ai/v1")
        self.output_dir = Path(self.target_dir)
        self.start_days_ago = self.poller_config.get('start_days_ago', 7)
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_debug(self):
        """Check if logger is in debug mode."""
        return logging.getLogger().getEffectiveLevel() <= logging.DEBUG

    def poll(self) -> bool:
        """
        Perform one Limitless sync operation.

        Returns:
            True if successful, False otherwise
        """
        if not hasattr(self, 'is_ready') or not self.is_ready:
            return True

        if self.is_debug:
            logger.debug("Starting Limitless data sync...")
        try:
            local_timezone_setting = self.poller_config.get("local_timezone")
            if local_timezone_setting:
                timezone_name = local_timezone_setting
                if self.is_debug:
                    logger.debug(f"Using configured timezone: {timezone_name}")
            else:
                timezone_name = str(get_localzone())
                if self.is_debug:
                    logger.debug(f"Using system local timezone: {timezone_name}")

            self.sync_missing_dates(timezone_name)

            if self.is_debug:
                logger.debug("Limitless data sync finished successfully.")
            
            return True
        except Exception as e:
            logger.error(f"An error occurred during Limitless sync: {e}")
            return False
    
    def fetch_all_lifelogs_for_day(self, date_str, timezone_str):
        """Fetch all lifelogs for a specific day."""
        all_recent_lifelogs = []
        cursor = None
        page_count = 1

        if self.is_debug:
            logger.debug("Fetching recent lifelogs...")
        while True:
            url = f"{self.api_base_url}/lifelogs"
            params = { "limit": 10 }
            if cursor:
                params['cursor'] = cursor

            try:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                data = response.json()

                lifelogs_page = data.get('data', {}).get('lifelogs', [])
                if not lifelogs_page:
                    break

                all_recent_lifelogs.extend(lifelogs_page)

                cursor = data.get('meta', {}).get('lifelogs', {}).get('nextCursor')
                if not cursor or page_count > 10:
                    break

                page_count += 1
                time.sleep(0.5)

            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response: {e.response.text}")
                return None

        if self.is_debug:
            logger.debug(f"Retrieved {len(all_recent_lifelogs)} total recent entries. Now filtering for date {date_str}...")

        target_date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        local_tz = pytz.timezone(timezone_str)

        filtered_lifelogs = []
        for log in all_recent_lifelogs:
            start_time_utc_str = log.get('startTime')
            if not start_time_utc_str:
                continue

            utc_dt = datetime.fromisoformat(start_time_utc_str.replace('Z', '+00:00'))
            local_dt = utc_dt.astimezone(local_tz)

            if local_dt.date() == target_date_obj:
                filtered_lifelogs.append(log)

        if self.is_debug:
            logger.debug(f"Found {len(filtered_lifelogs)} entries matching the date {date_str}.")
        return filtered_lifelogs

    def format_lifelogs_markdown(self, lifelogs, timezone_str):
        """Convert lifelog data to markdown format with YAML frontmatter."""
        if not lifelogs:
            return "---\ntotal_conversations: 0\nstarred_conversations: 0\nstarred_list: []\n---\n\n# Limitless Data\n\nNo lifelog data available for this date.\n"

        local_tz = pytz.timezone(timezone_str)
        markdown_content = ""

        # Track statistics
        total_conversations = len(lifelogs)
        starred_conversations = 0
        starred_list = []

        for entry in sorted(lifelogs, key=lambda x: x.get('startTime', '')):
            contents = entry.get('contents', [])
            if not contents:
                continue

            is_starred = entry.get('isStarred', False)
            if is_starred:
                starred_conversations += 1

            for item in contents:
                item_type = item.get('type')
                content = item.get('content', '').strip()
                speaker = item.get('speakerName', 'Unknown')
                timestamp_utc_str = item.get('startTime')

                if not content:
                    continue

                if item_type == 'heading1':
                    if is_starred:
                        heading = f"# ⭐ {content}"
                        starred_list.append(f"[[#⭐ {content}]]")
                    else:
                        heading = f"# {content}"
                    markdown_content += f"{heading}\n"
                elif item_type == 'heading2':
                    markdown_content += f"## {content}\n"
                elif item_type == 'blockquote':
                    time_display = ""
                    if timestamp_utc_str:
                        try:
                            utc_dt = datetime.fromisoformat(timestamp_utc_str.replace('Z', '+00:00'))
                            local_dt = utc_dt.astimezone(local_tz)
                            time_display = local_dt.strftime("%-m/%-d/%y %-I:%M %p")
                        except (ValueError, TypeError):
                            pass

                    markdown_content += f"- {speaker} ({time_display}): {content}\n"

        # Build YAML frontmatter
        frontmatter = "---\n"
        frontmatter += f"total_conversations: {total_conversations}\n"
        frontmatter += f"starred_conversations: {starred_conversations}\n"
        if starred_list:
            frontmatter += "starred_list:\n"
            for item in starred_list:
                frontmatter += f"  - \"{item}\"\n"
        else:
            frontmatter += "starred_list: []\n"
        frontmatter += "---\n\n"

        return frontmatter + markdown_content.strip()

    def sync_date(self, date_str, timezone):
        """Sync data for a specific date."""
        lifelogs = self.fetch_all_lifelogs_for_day(date_str, timezone)

        if not lifelogs:
            if self.is_debug:
                logger.debug(f"No data found for {date_str}. Skipping file creation.")
            return False

        markdown = self.format_lifelogs_markdown(lifelogs, timezone)

        if not markdown.strip():
            if self.is_debug:
                logger.debug(f"No content to save for {date_str}. Skipping file creation.")
            return False

        filepath = self.save_to_file(markdown, date_str)
        return filepath is not None

    def save_to_file(self, content, date_str):
        """Save markdown content to file."""
        filepath = self.output_dir / f"{date_str}.md"
        try:
            filepath.write_text(content, encoding='utf-8')
            logger.info(f"Saved to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            return None
            
    def get_last_sync_date(self) -> str:
        """Find the most recent date from filenames in output directory."""
        try:
            if "last_sync_date" in self.state:
                return self.state["last_sync_date"]
            
            files = list(self.output_dir.glob("????-??-??.md"))
            if not files:
                start_date = (date.today() - timedelta(days=self.start_days_ago)).strftime("%Y-%m-%d")
                if self.is_debug:
                    logger.debug(f"No previous sync files found. Starting from {self.start_days_ago} days ago.")
                return start_date

            latest_date_str = max(file.stem for file in files)
            return latest_date_str

        except Exception as e:
            logger.warning(f"Error finding last sync date: {e}")
            return (date.today() - timedelta(days=self.start_days_ago)).strftime("%Y-%m-%d")
        
    def get_date_range(self, start_dt, end_dt):
        """Get list of dates between start and end (inclusive)."""
        dates = []
        current_dt = start_dt
        while current_dt <= end_dt:
            dates.append(current_dt.strftime("%Y-%m-%d"))
            current_dt += timedelta(days=1)
        return dates

    def sync_missing_dates(self, timezone):
        """Sync all days from last synced date up to and including today."""
        last_sync_str = self.get_last_sync_date()
        last_sync_date = datetime.strptime(last_sync_str, "%Y-%m-%d").date()
        today_date = date.today()

        if self.is_debug:
            logger.debug(f"Last sync file found: {last_sync_date.strftime('%Y-%m-%d')}")
            logger.debug(f"Syncing up to today: {today_date.strftime('%Y-%m-%d')}")

        if last_sync_date > today_date:
            if self.is_debug:
                logger.debug("Last sync date is in the future. Syncing today.")
            self.sync_date(today_date.strftime("%Y-%m-%d"), timezone)
            self.update_state(last_sync_date=today_date.strftime("%Y-%m-%d"))
            return

        dates_to_sync = self.get_date_range(last_sync_date, today_date)

        if not dates_to_sync:
            if self.is_debug:
                logger.debug("Already up to date! Re-syncing today.")
            self.sync_date(today_date.strftime("%Y-%m-%d"), timezone)
            self.update_state(last_sync_date=today_date.strftime("%Y-%m-%d"))
            return

        if self.is_debug:
            logger.debug(f"Syncing {len(dates_to_sync)} day(s): from {dates_to_sync[0]} to {dates_to_sync[-1]}")

        for date_str in dates_to_sync:
            if self.is_debug:
                logger.debug(f"Syncing {date_str}...")
            self.sync_date(date_str, timezone)

        self.update_state(last_sync_date=today_date.strftime("%Y-%m-%d"))

        if self.is_debug:
            logger.debug("Sync process completed.")


def main():
    """Standalone execution entry point."""
    import sys
    from ..config import Config
    
    config = Config()
    
    poller_config = config.get('pollers', {}).get("limitless", {})
    if not poller_config:
        logger.error("limitless poller configuration not found in orchestrator.yaml")
        sys.exit(1)
    
    poller = LimitlessPoller(poller_config)
    success = poller.run_once()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

