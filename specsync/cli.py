"""CLI interface for SpecSync."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from specsync.config import Config
from specsync.sync import SpecSync


console = Console()


@click.group()
@click.version_option()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path]) -> None:
    """SpecSync - Selective Markdown sync between your repo and any workspace folder."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@cli.command()
@click.argument("workspace", type=click.Path(path_type=Path))
@click.option(
    "--specs-dir",
    default="specs",
    help="Directory containing spec files (default: specs)",
)
@click.option(
    "--pattern",
    multiple=True,
    help="File patterns to include (can be specified multiple times)",
)
@click.option(
    "--exclude-pattern",
    multiple=True,
    help="File patterns to exclude (can be specified multiple times)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be synced without actually syncing",
)
@click.pass_context
def sync(
    ctx: click.Context,
    workspace: Path,
    specs_dir: str,
    pattern: tuple[str, ...],
    exclude_pattern: tuple[str, ...],
    dry_run: bool,
) -> None:
    """Sync specs to workspace folder."""
    try:
        config = Config.load(ctx.obj.get("config_path"))
        
        # Override config with CLI options
        if pattern:
            config.include_patterns = list(pattern)
        if exclude_pattern:
            config.exclude_patterns = list(exclude_pattern)
        
        syncer = SpecSync(
            specs_dir=Path(specs_dir),
            workspace_dir=workspace,
            config=config,
        )
        
        if dry_run:
            console.print("[yellow]Dry run mode - no files will be modified[/yellow]")
            files_to_sync = syncer.get_files_to_sync()
            for file_path in files_to_sync:
                console.print(f"Would sync: {file_path}")
        else:
            syncer.sync_to_workspace()
            console.print("[green]Sync completed successfully![/green]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--specs-dir",
    default="specs",
    help="Directory containing spec files (default: specs)",
)
@click.pass_context
def sync_back(
    ctx: click.Context,
    workspace: Path,
    specs_dir: str,
) -> None:
    """Sync changes back from workspace to specs directory."""
    try:
        config = Config.load(ctx.obj.get("config_path"))
        
        syncer = SpecSync(
            specs_dir=Path(specs_dir),
            workspace_dir=workspace,
            config=config,
        )
        
        syncer.sync_from_workspace()
        console.print("[green]Sync back completed successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--specs-dir",
    default="specs",
    help="Directory containing spec files (default: specs)",
)
@click.pass_context
def watch(
    ctx: click.Context,
    workspace: Path,
    specs_dir: str,
) -> None:
    """Watch for changes and sync automatically."""
    try:
        config = Config.load(ctx.obj.get("config_path"))
        
        syncer = SpecSync(
            specs_dir=Path(specs_dir),
            workspace_dir=workspace,
            config=config,
        )
        
        console.print(f"[blue]Watching {specs_dir} and {workspace} for changes...[/blue]")
        console.print("[yellow]Press Ctrl+C to stop[/yellow]")
        
        syncer.watch()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping watch mode...[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def init() -> None:
    """Initialize a new SpecSync configuration."""
    config_path = Path("specsync.yaml")
    if config_path.exists():
        console.print(f"[yellow]Configuration file {config_path} already exists[/yellow]")
        return
    
    config = Config()
    config.save(config_path)
    console.print(f"[green]Created configuration file: {config_path}[/green]")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()