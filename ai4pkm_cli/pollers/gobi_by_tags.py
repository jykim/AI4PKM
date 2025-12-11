"""Gobi sync by tags poller - syncs data from Gobi API filtered by tags."""

import requests
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import pytz
from tzlocal import get_localzone
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_poller import BasePoller
from ..logger import Logger

logger = Logger()


class GobiByTagsPoller(BasePoller):
    """Poller for syncing Gobi data filtered by tags."""

    def __init__(
        self,
        poller_config: Dict[str, Any],
        vault_path: Optional[Path] = None,
    ):
        """
        Initialize Gobi sync by tags poller.

        Args:
            poller_config: Poller-specific configuration dictionary
            vault_path: Vault root path
        """
        super().__init__(poller_config, vault_path)
        
        self.tags = self.poller_config.get("tags")
        self.admin_api_key = self.poller_config.get("admin_api_key")
        self.api_base_url = self.poller_config.get(
            "api_base_url", "https://api.joingobi.com/api"
        )
        self.output_dir = Path(self.target_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def poll(self) -> bool:
        """
        Perform one Gobi sync by tags operation.

        Returns:
            True if successful, False otherwise
        """
        if not self.admin_api_key:
            logger.warning(
                "admin_api_key not found in secrets.yaml for gobi_by_tags poller. Skipping sync."
            )
            return False

        if not self.tags:
            logger.warning(
                "tags not found in secrets.yaml for gobi_by_tags poller. Skipping sync."
            )
            return False

        logger.info("Starting Gobi data sync by tags...")
        try:
            local_timezone_setting = self.poller_config.get("local_timezone")
            if local_timezone_setting:
                timezone_name = local_timezone_setting
                logger.info(f"Using configured timezone: {timezone_name}")
            else:
                timezone_name = str(get_localzone())
                logger.info(f"Using system local timezone: {timezone_name}")

            tags_param = ','.join(self.tags) if isinstance(self.tags, list) else self.tags
            response = requests.get(
                f"{self.api_base_url}/devices-by-tags?tags={tags_param}",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.admin_api_key,
                },
            )
            response.raise_for_status()
            data = response.json()
            devices = data.get("devices", [])

            for device in devices:
                deviceId = device.get("public_key")
                (self.output_dir / deviceId).mkdir(parents=True, exist_ok=True)

                transcriptions, frames = self.fetch_all_data(deviceId)

                markdowns = self.format_data_markdown(
                    deviceId, transcriptions, frames, timezone_name
                )

                for target_date, markdown in markdowns.items():
                    self.save_to_file(deviceId, markdown, target_date)

            logger.info("Gobi data sync by tags finished successfully.")
            
            return True
        except Exception as e:
            logger.error(f"An error occurred during Gobi sync by tags: {e}", exc_info=True)
            return False

    def fetch_all_data(self, deviceId: str):
        """Fetch all data from Gobi API for a device."""
        logger.info(f"Fetching recent data for device {deviceId}...")

        params = {}
        params["deviceId"] = deviceId
        params["tags"] = self.tags

        transcriptions = []
        frames = []
        try:
            response = requests.get(
                f"{self.api_base_url}/sync-by-tags",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.admin_api_key,
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

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return [], []

        logger.info(
            f"Retrieved {len(transcriptions)} transcriptions and {len(frames)} frames for device {deviceId}."
        )
        return transcriptions, frames

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

    def _process_entry(self, entry, local_tz, deviceId):
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
            frames_dir = self.output_dir / deviceId / relative_dir
            frames_dir.mkdir(parents=True, exist_ok=True)
            file_path = frames_dir / filename

            markdown_line = f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')} ![frame]({relative_dir}/{filename})\n"
            download_task = (download_url, file_path)
            return date_key, markdown_line, download_task

        return None, None, None

    def format_data_markdown(self, deviceId, transcriptions, frames, timezone_str):
        """Convert lifelog data to markdown format."""
        data = transcriptions + frames
        local_tz = pytz.timezone(timezone_str)
        markdown_contents = {}
        download_tasks = []
        processed_entries = []

        for entry in sorted(data, key=lambda x: x.get("created_at", "")):
            date_key, markdown_line, download_task = self._process_entry(
                entry, local_tz, deviceId
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

    def save_to_file(self, deviceId, content, target_date):
        """Save markdown content to file."""
        filepath = self.output_dir / f"{deviceId}/{target_date}.md"
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
    
    poller_config = config.get('pollers', {}).get("gobi_by_tags", {})
    if not poller_config:
        logger.error("gobi_by_tags poller configuration not found in orchestrator.yaml")
        sys.exit(1)
    
    poller = GobiByTagsPoller(poller_config)
    success = poller.run_once()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

