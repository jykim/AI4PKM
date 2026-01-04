#!/usr/bin/env python3
"""Self-update command for AI4PKM CLI."""

import sys
import tempfile
import zipfile
import subprocess
from pathlib import Path
from importlib.metadata import version as get_installed_version, PackageNotFoundError
from typing import Optional

import click
import requests

# GitHub repository configuration
GITHUB_REPO = "jykim/AI4PKM"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}"


def get_current_version() -> Optional[str]:
    """Get the currently installed version of ai4pkm-cli."""
    try:
        return get_installed_version("ai4pkm-cli")
    except PackageNotFoundError:
        return None


def normalize_version(version: str) -> str:
    """Normalize version string by removing 'v' prefix if present."""
    return version.lstrip("v")


def get_releases() -> list[dict]:
    """Fetch all releases from GitHub API."""
    try:
        response = requests.get(f"{GITHUB_API_BASE}/releases", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


def get_latest_release() -> Optional[dict]:
    """Fetch the latest release from GitHub API."""
    try:
        response = requests.get(f"{GITHUB_API_BASE}/releases/latest", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def get_release_by_tag(tag: str) -> Optional[dict]:
    """Fetch a specific release by tag name."""
    tags_to_try = [tag, f"v{tag}", tag.lstrip("v")]
    
    for t in tags_to_try:
        try:
            response = requests.get(f"{GITHUB_API_BASE}/releases/tags/{t}", timeout=10)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            continue
    return None


def download_zip(url: str, dest_path: Path) -> None:
    """Download a ZIP file from URL with progress indicator."""
    click.echo("Downloading...")
    
    response = requests.get(url, stream=True, timeout=60, allow_redirects=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    
    with open(dest_path, 'wb') as f:
        if total_size == 0:
            f.write(response.content)
        else:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                percent = int(100 * downloaded / total_size)
                click.echo(f"\rProgress: {percent}%", nl=False)
    
    click.echo("\nDownload complete.")


def extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    """Extract ZIP file and return path to extracted content."""
    click.echo("Extracting...")
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(dest_dir)
    
    # GitHub ZIPs contain a single directory
    extracted_dirs = [d for d in dest_dir.iterdir() if d.is_dir()]
    if len(extracted_dirs) == 1:
        return extracted_dirs[0]
    
    return dest_dir


def install_package(package_dir: Path) -> bool:
    """Install the package using pip."""
    click.echo("Installing...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", str(package_dir)],
            capture_output=True,
            text=True,
            check=True
        )
        click.echo(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        click.echo(f"Installation failed: {e.stderr}", err=True)
        return False


@click.command("update")
@click.option("--force", "-f", is_flag=True, help="Force update even if already up to date")
@click.option("--version", "-v", "target_version", type=str, help="Install a specific version")
@click.option("--list", "-l", "list_releases", is_flag=True, help="List available releases")
def update_cli(force: bool, target_version: Optional[str], list_releases: bool) -> None:
    """Self-update the AI4PKM CLI from GitHub releases."""
    click.echo("=" * 50)
    click.echo("AI4PKM CLI Self-Update")
    click.echo("=" * 50)
    click.echo()
    
    if list_releases:
        releases = get_releases()
        if not releases:
            click.echo("No releases available.")
            return
        
        click.echo("Available releases:")
        for release in releases[:10]:
            tag = release.get("tag_name", "unknown")
            name = release.get("name", "")
            prerelease = " (pre-release)" if release.get("prerelease") else ""
            click.echo(f"  {tag}{prerelease} - {name}")
        
        if len(releases) > 10:
            click.echo(f"  ... and {len(releases) - 10} more")
        return
    
    current_version = get_current_version()
    click.echo(f"Current version: {current_version or 'not installed'}")
    
    if target_version:
        release = get_release_by_tag(target_version)
        if not release:
            click.echo(f"Error: Release '{target_version}' not found.", err=True)
            click.echo("Use --list to see available releases.", err=True)
            sys.exit(1)
    else:
        release = get_latest_release()
        if not release:
            click.echo("Error: No releases available.", err=True)
            sys.exit(1)
    
    release_version = normalize_version(release.get("tag_name", "unknown"))
    zipball_url = release.get("zipball_url")
    
    click.echo(f"Target version:  {release_version}")
    click.echo()
    
    if not force and current_version and current_version == release_version:
        click.echo("Already up to date!")
        return
    
    if not zipball_url:
        click.echo("Error: No download URL found for release.", err=True)
        sys.exit(1)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        zip_path = tmpdir_path / "release.zip"
        
        try:
            download_zip(zipball_url, zip_path)
            extracted_path = extract_zip(zip_path, tmpdir_path)
            
            if install_package(extracted_path):
                click.echo()
                click.echo("=" * 50)
                click.echo("Update completed successfully!")
                click.echo("Restart your terminal for changes to take effect.")
                click.echo("=" * 50)
            else:
                click.echo("Update failed.", err=True)
                sys.exit(1)
                
        except requests.RequestException as e:
            click.echo(f"Download failed: {e}", err=True)
            sys.exit(1)
        except zipfile.BadZipFile as e:
            click.echo(f"Extraction failed: {e}", err=True)
            sys.exit(1)


if __name__ == "__main__":
    update_cli()
