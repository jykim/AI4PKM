"""Apple Photos processing poller - syncs and processes photos from iCloud."""

import glob
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from .base_poller import BasePoller
from ..logger import Logger

logger = Logger()

class ApplePhotosPoller(BasePoller):
    """Poller for processing photos with configurable source and destination folders."""

    def __init__(
        self,
        poller_config: Dict[str, Any],
        vault_path: Optional[Path] = None,
    ):
        """
        Initialize photo processing poller.

        Args:
            poller_config: Poller-specific configuration dictionary
            vault_path: Vault root path
        """
        super().__init__(poller_config, vault_path)
        
        self.source_folder_path = self.target_dir / "Original"
        self.destination_folder_path = self.target_dir / "Processed"
        self.source_folder_path.mkdir(parents=True, exist_ok=True)
        
        self.albums = self.poller_config.get("albums", ["AI4PKM"])
        self.days = self.poller_config.get("days", 7)

    def poll(self) -> bool:
        """
        Perform one photo processing operation.

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            f"Processing photos from: {self.source_folder_path} -> {self.destination_folder_path}"
        )
        logger.info(f"Albums to process: {self.albums}")
        logger.info(f"Looking back {self.days} days")

        try:
            script_path = os.path.join(
                os.path.dirname(__file__), "..", "scripts", "export_photos.applescript"
            )
            script_path = os.path.abspath(script_path)
            
            if not os.path.exists(script_path):
                logger.error(f"AppleScript not found: {script_path}")
                return False
            
            logger.info("Exporting photos from Photos app...")
            
            for album in self.albums:
                logger.info(f"Processing album: {album}")
                result = subprocess.run(
                    ["osascript", script_path, album, str(self.source_folder_path), str(self.days)], 
                    capture_output=True, text=True, check=True
                )
                
                if result.stderr:
                    skipped_count_msgs = {"too_old": 0, "already_exists": 0, "other": 0}
                    
                    for line in result.stderr.strip().split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                            
                        if "Too old:" in line:
                            skipped_count_msgs["too_old"] += 1
                        elif "Already exists:" in line:
                            skipped_count_msgs["already_exists"] += 1
                        elif any(keyword in line for keyword in ["Exported:", "Processing", "Found", "total photos"]):
                            logger.info(f"AppleScript ({album}): {line}")
                        else:
                            logger.debug(f"AppleScript ({album}): {line}")
                            skipped_count_msgs["other"] += 1
                    
                    if skipped_count_msgs["too_old"] > 0:
                        logger.info(f"AppleScript ({album}): Skipped {skipped_count_msgs['too_old']} photos (too old)")
                    if skipped_count_msgs["already_exists"] > 0:
                        logger.info(f"AppleScript ({album}): Skipped {skipped_count_msgs['already_exists']} photos (already exists)")
                    if skipped_count_msgs["other"] > 0:
                        logger.debug(f"AppleScript ({album}): {skipped_count_msgs['other']} other debug messages")
                            
            logger.info("Photo export completed successfully for all albums")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"AppleScript execution failed for album {album}: {e}")
            logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error exporting photos: {e}")
            return False

        try:
            self.destination_folder_path.mkdir(parents=True, exist_ok=True)

            processed_basenames = set()
            source_pattern = os.path.join(str(self.source_folder_path), "*")
            processed_count = 0
            skipped_count = 0

            for file in glob.glob(source_pattern):
                if not os.path.isfile(file):
                    continue

                basename = os.path.basename(file)
                basename_no_ext = os.path.splitext(basename)[0]

                if basename_no_ext in processed_basenames:
                    continue

                processed_basenames.add(basename_no_ext)

                files = glob.glob(f"{self.destination_folder_path}*{basename_no_ext}.*")
                if files:
                    skipped_count += 1
                    continue

                script_path = os.path.join(
                    os.path.dirname(__file__), "..", "scripts", "process_photo.sh"
                )
                script_path = os.path.abspath(script_path)
                
                if not os.path.exists(script_path):
                    logger.error(f"Processing script not found: {script_path}")
                    continue
                
                logger.info(f"Processing: {basename}")
                try:
                    result = subprocess.run(
                        [script_path, file, str(self.destination_folder_path)],
                        capture_output=True, text=True, check=True
                    )
                    
                    processed_count += 1
                    logger.info(f"Successfully processed: {basename}")
                    
                    script_output = result.stdout.strip() if result.stdout else ""
                    if script_output:
                        for line in script_output.split('\n'):
                            if line.strip():
                                logger.debug(f"Shell script: {line.strip()}")
                                
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to process {basename}: {e}")
                    logger.error(f"Error output: {e.stderr}")
                    continue

            logger.info(
                f"Photo processing completed: {processed_count} processed, {skipped_count} skipped"
            )
            
            return True

        except Exception as e:
            logger.error(f"Error processing photos: {e}")
            return False


def main():
    """Standalone execution entry point."""
    import sys
    from ..config import Config
    
    config = Config()
    
    poller_config = config.get('pollers', {}).get("apple_photos", {})
    if not poller_config:
        logger.error("apple_photos poller configuration not found in orchestrator.yaml")
        sys.exit(1)
    
    poller = ApplePhotosPoller(poller_config)
    success = poller.run_once()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

