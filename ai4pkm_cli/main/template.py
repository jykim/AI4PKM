#!/usr/bin/env python3
"""Template management commands for AI4PKM CLI."""

import sys
import tempfile
import zipfile
import shutil
from pathlib import Path
from typing import Optional

import click
import requests

# Template registry: maps template names to GitHub repos and vault folders
TEMPLATE_REGISTRY = {
    "ai4pkm": {
        "repo": "jykim/obsidian_vault_templates",
        "description": "AI4PKM starter vault with default configuration",
        "vault_folder": "ai4pkm_vault",
    },
}


def get_latest_release(repo: str) -> Optional[dict]:
    """Fetch the latest release from GitHub API."""
    try:
        response = requests.get(
            f"https://api.github.com/repos/{repo}/releases/latest", timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def get_release_by_tag(repo: str, tag: str) -> Optional[dict]:
    """Fetch a specific release by tag name."""
    try:
        response = requests.get(
            f"https://api.github.com/repos/{repo}/releases/tags/{tag}", timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
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


def copy_vault_folder(source_dir: Path, vault_folder: str, target_dir: Path) -> bool:
    """Copy the vault folder from extracted repo to target directory."""
    vault_path = source_dir / vault_folder
    
    if not vault_path.exists() or not vault_path.is_dir():
        click.echo(f"Error: Vault folder '{vault_folder}' not found.", err=True)
        return False
    
    target_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"Copying template to {target_dir}...")
    
    for item in vault_path.iterdir():
        dest = target_dir / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    
    return True


@click.group("template")
def template_group():
    """Manage PKM vault templates."""
    pass


@template_group.command("list")
def list_templates():
    """List available vault templates."""
    click.echo("=" * 50)
    click.echo("Available Templates")
    click.echo("=" * 50)
    click.echo()
    
    for name, info in TEMPLATE_REGISTRY.items():
        click.echo(f"  {name}")
        click.echo(f"    Description: {info['description']}")
        click.echo(f"    Repository:  https://github.com/{info['repo']}")
        click.echo()
    
    click.echo("Use 'ai4pkm template install <name> <target_dir>' to install.")


@template_group.command("install")
@click.argument("template_name")
@click.argument("target_dir", type=click.Path(path_type=Path))
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files")
@click.option("--version", "-v", "target_version", type=str, help="Install specific release version")
def install_template(template_name: str, target_dir: Path, force: bool, target_version: Optional[str]):
    """Install a vault template to the specified directory.
    
    Downloads from GitHub releases.
    """
    if template_name not in TEMPLATE_REGISTRY:
        click.echo(f"Error: Unknown template '{template_name}'.", err=True)
        click.echo(f"Available: {', '.join(TEMPLATE_REGISTRY.keys())}", err=True)
        sys.exit(1)
    
    template_info = TEMPLATE_REGISTRY[template_name]
    repo = template_info["repo"]
    
    target_dir = target_dir.resolve()
    if target_dir.exists():
        if any(target_dir.iterdir()):
            if not force:
                click.echo(f"Error: '{target_dir}' is not empty. Use --force to overwrite.", err=True)
                sys.exit(1)
            click.echo(f"Warning: Overwriting files in '{target_dir}'...")
    else:
        target_dir.mkdir(parents=True, exist_ok=True)
    
    # Get release
    if target_version:
        release = get_release_by_tag(repo, target_version)
        if not release:
            click.echo(f"Error: Release '{target_version}' not found.", err=True)
            sys.exit(1)
    else:
        release = get_latest_release(repo)
        if not release:
            click.echo("Error: No releases available.", err=True)
            sys.exit(1)
    
    zip_url = release.get("zipball_url")
    release_tag = release.get("tag_name", "unknown")
    
    if not zip_url:
        click.echo("Error: No download URL found.", err=True)
        sys.exit(1)
    
    click.echo("=" * 50)
    click.echo(f"Installing template: {template_name}")
    click.echo(f"Version: {release_tag}")
    click.echo(f"Target: {target_dir}")
    click.echo("=" * 50)
    click.echo()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        zip_path = tmpdir_path / "template.zip"
        
        try:
            download_zip(zip_url, zip_path)
            extracted_path = extract_zip(zip_path, tmpdir_path)
            
            if copy_vault_folder(extracted_path, template_info["vault_folder"], target_dir):
                click.echo()
                click.echo("=" * 50)
                click.echo("Template installed successfully!")
                click.echo(f"Vault ready at: {target_dir}")
                click.echo()
                click.echo("Next steps:")
                click.echo("  1. Open the folder in Obsidian")
                click.echo("  2. Trust the vault when prompted")
                click.echo("  3. Explore _Settings_ for configuration")
                click.echo("=" * 50)
            else:
                click.echo("Installation failed.", err=True)
                sys.exit(1)
                
        except requests.RequestException as e:
            click.echo(f"Download failed: {e}", err=True)
            sys.exit(1)
        except zipfile.BadZipFile as e:
            click.echo(f"Extraction failed: {e}", err=True)
            sys.exit(1)


if __name__ == "__main__":
    template_group()
