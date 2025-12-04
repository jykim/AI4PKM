"""Gobi sync poller - syncs data from Gobi API."""

import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
import pytz
from tzlocal import get_localzone

from .base_poller import BasePoller
from ..logger import Logger

logger = Logger()


class GobiPoller(BasePoller):
    """Poller for syncing Gobi data."""

    def __init__(
        self,
        poller_config: Dict[str, Any],
        vault_path: Optional[Path] = None,
    ):
        """
        Initialize Gobi sync poller.

        Args:
            poller_config: Poller-specific configuration dictionary
            vault_path: Vault root path
        """
        super().__init__(poller_config, vault_path)
        
        self.api_key = self.poller_config.get("api_key")
        self.api_base_url = self.poller_config.get(
            "api_base_url", "https://api.joingobi.com/api"
        )
        self.output_dir = Path(self.target_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def poll(self) -> bool:
        """
        Perform one Gobi sync operation.

        Returns:
            True if successful, False otherwise
        """
        if not self.api_key:
            logger.warning(
                "api_key not found in secrets.yaml for gobi poller. Skipping sync."
            )
            return False

        logger.info("Starting Gobi data sync...")
        try:
            local_timezone_setting = self.poller_config.get("local_timezone")
            if local_timezone_setting:
                timezone_name = local_timezone_setting
                logger.info(f"Using configured timezone: {timezone_name}")
            else:
                timezone_name = str(get_localzone())
                logger.info(f"Using system local timezone: {timezone_name}")
            
            transcriptions, frames = self.fetch_all_data(timezone_name)

            markdowns = self.format_data_markdown(transcriptions, frames, timezone_name)

            for target_date, markdown in markdowns.items():
                self.save_to_file(markdown, target_date)

            logger.info("Gobi data sync finished successfully.")
            
            return True
        except Exception as e:
            logger.error(f"An error occurred during Gobi sync: {e}", exc_info=True)
            return False

    def fetch_all_data(self, timezone_name: str):
        """Fetch all data from Gobi API."""
        logger.info("Fetching recent data...")

        last_sync_time = None
        if "last_sync_time" in self.state:
            last_sync_time = self.state["last_sync_time"]
            last_sync_time = int(
                datetime.fromtimestamp(last_sync_time / 1000).astimezone(pytz.timezone(timezone_name))
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .timestamp()
                * 1000
            )

        params = {}
        if last_sync_time:
            params["lastSyncTime"] = last_sync_time

        transcriptions = []
        frames = []
        try:
            response = requests.get(
                f"{self.api_base_url}/sync",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key,
                },
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            transcription_chunks = data.get("transcriptions", [])
            for transcription in transcription_chunks:
                for line in transcription["transcription"].split("\n"):
                    if not line:
                        continue
                    date_time_str = ":".join(line.split(":")[:-1])
                    speaker = date_time_str.split("@")[0]
                    date_time_str = date_time_str.split("@")[1][:-6] + "Z"
                    date_time_str = datetime.fromisoformat(
                        date_time_str.replace("Z", "+00:00")
                    )
                    date_time_str = date_time_str.strftime("%Y-%m-%dT%H:%M:%SZ")
                    transcriptions.append(
                        {
                            **transcription,
                            "transcription": line.split(": ")[-1],
                            "created_at": date_time_str,
                            "speaker": speaker,
                        }
                    )
            frames.extend(data.get("frames", []))
            
            lastSyncTime = data.get("lastSyncTime")
            if lastSyncTime:
                self.update_state(last_sync_time=lastSyncTime)

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return [], []

        logger.info(
            f"Retrieved {len(transcriptions)} transcriptions and {len(frames)} frames."
        )
        
        return transcriptions, frames

    def format_data_markdown(self, transcriptions, frames, timezone_str):
        """Convert lifelog data to markdown format."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        data = transcriptions + frames
        local_tz = pytz.timezone(timezone_str)
        markdown_contents = {}
        download_tasks = []
        processed_entries = []

        for entry in sorted(data, key=lambda x: x.get("created_at", "")):
            date_key, markdown_line, download_task = self._process_entry(
                entry, local_tz
            )
            if date_key and markdown_line:
                processed_entries.append((date_key, markdown_line))
                if download_task:
                    download_tasks.append(download_task)

        if download_tasks:
            logger.info(
                f"Starting parallel download of {len(download_tasks)} frames..."
            )
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_task = {
                    executor.submit(self._download_frame, download_url, file_path): (
                        download_url,
                        file_path,
                    )
                    for download_url, file_path in download_tasks
                }

                for future in as_completed(future_to_task):
                    download_url, file_path = future_to_task[future]
                    try:
                        success = future.result()
                        if not success:
                            logger.warning(
                                f"Failed to download frame: {file_path}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Exception during frame download {file_path}: {e}"
                        )

        for date_key, markdown_line in processed_entries:
            if date_key not in markdown_contents:
                markdown_contents[date_key] = ""
            markdown_contents[date_key] += markdown_line

        return markdown_contents

    def _process_entry(self, entry, local_tz):
        """Process a single entry (transcription or frame)."""
        transcription = entry.get("transcription")
        download_url = entry.get("downloadUrl")
        timestamp = entry.get("created_at")
        speaker = entry.get("speaker")

        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        local_dt = dt.astimezone(local_tz)
        date_key = local_dt.strftime("%Y-%m-%d")

        if transcription:
            markdown_line = (
                f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')} {speaker}: {transcription}\n"
            )
            return date_key, markdown_line, None
        elif download_url:
            filename = f"{timestamp.split('T')[1].split('.')[0]}.jpeg"
            year = local_dt.strftime("%Y")
            month = local_dt.strftime("%m")
            day = local_dt.strftime("%d")
            hour = local_dt.strftime("%H")

            relative_dir = f"./frames/{year}/{month}/{day}/{hour}"
            frames_dir = self.output_dir / relative_dir
            frames_dir.mkdir(parents=True, exist_ok=True)
            file_path = frames_dir / filename

            markdown_line = f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')} ![frame]({relative_dir}/{filename})\n"
            download_task = (download_url, file_path)
            return date_key, markdown_line, download_task

        return None, None, None

    def _download_frame(self, download_url, file_path):
        """Download a single frame image."""
        try:
            if not file_path.exists():
                logger.info(f"Downloading frame to {file_path}...")
                response = requests.get(download_url)
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    f.write(response.content)
            return True
        except Exception as e:
            logger.error(f"Failed to download frame {file_path}: {e}")
            return False

    def save_to_file(self, content, target_date):
        """Save markdown content to file."""
        filepath = self.output_dir / f"{target_date}.md"
        try:
            filepath.write_text(content, encoding="utf-8")
            logger.info(f"Saved to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            return None


def main():
    """Standalone execution entry point."""
    import sys
    from ..config import Config
    
    config = Config()

    poller_config = config.get('pollers', {}).get("gobi", {})
    if not poller_config:
        logger.error("gobi poller configuration not found in orchestrator.yaml")
        sys.exit(1)
    
    poller = GobiPoller(poller_config)
    success = poller.run_once()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

