"""Report generation system with interactive inputs."""

from rich.console import Console


class ProcessPhotos:
    """Handles photo processing with configurable source and destination folders."""

    def __init__(self, logger, config=None):
        """Initialize photo processor."""
        self.logger = logger
        self.console = Console()
        self.config = config

    def process_photos(self):
        """Process photos with configurable source and destination folders."""
        import subprocess
        import glob
        import os

        # Get configurable paths
        if self.config:
            source_folder = self.config.get_photo_source_folder()
            destination_folder = self.config.get_photo_destination_folder()
        else:
            # Fallback to hardcoded paths if no config
            source_folder = "Photostream/"
            destination_folder = "Ingest/Photolog/Snap/"

        self.logger.info(
            f"Processing photos from: {source_folder} -> {destination_folder}"
        )

        try:
            subprocess.run(
                ["osascript", "ai4pkm_cli/scripts/export_photos.applescript"],
                check=True,
            )
        except Exception as e:
            self.logger.error(f"Error exporting photos: {e}")

        try:
            # Ensure destination directory exists
            os.makedirs(destination_folder, exist_ok=True)

            # Process all files in the source folder
            processed_basenames = set()
            source_pattern = os.path.join(source_folder, "*")
            processed_count = 0
            skipped_count = 0

            for file in glob.glob(source_pattern):
                if not os.path.isfile(file):
                    continue

                # Check if same basename file exists in destination folder
                basename = os.path.basename(file)
                basename_no_ext = os.path.splitext(basename)[0]

                if basename_no_ext in processed_basenames:
                    continue

                processed_basenames.add(basename_no_ext)

                # Check for any file whose name starts with basename_no_ext exists
                file_path = os.path.join(destination_folder, f"{basename_no_ext}")
                files = glob.glob(f"{file_path}*")
                if files:
                    skipped_count += 1
                    continue

                self.logger.info(f"Processing: {basename}")
                subprocess.run(
                    ["_Settings_/Tools/process_photo.sh", file, destination_folder],
                    check=True,
                )
                processed_count += 1
                processed_basenames.add(basename_no_ext)

            self.logger.info(
                f"Photo processing completed: {processed_count} processed, {skipped_count} skipped"
            )

        except Exception as e:
            self.logger.error(f"Error processing photos: {e}")
