"""Core synchronization functionality for SpecSync."""

import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import frontmatter
from rich.console import Console
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from specsync.config import Config


console = Console()


class SpecSync:
    """Main class for syncing specs with workspace."""
    
    def __init__(self, specs_dir: Path, workspace_dir: Path, config: Config) -> None:
        """Initialize SpecSync.
        
        Args:
            specs_dir: Directory containing spec files
            workspace_dir: Target workspace directory
            config: Configuration object
        """
        self.specs_dir = specs_dir.resolve()
        self.workspace_dir = workspace_dir.resolve()
        self.config = config
        
        # Create directories if they don't exist
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
    
    def get_files_to_sync(self) -> List[Path]:
        """Get list of files that should be synced based on configuration."""
        files_to_sync = []
        
        if not self.specs_dir.exists():
            return files_to_sync
        
        for file_path in self.specs_dir.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Get relative path for pattern matching
            rel_path = file_path.relative_to(self.specs_dir)
            
            # Parse frontmatter if it's a markdown file
            frontmatter_data = None
            if file_path.suffix.lower() == ".md":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        post = frontmatter.load(f)
                        frontmatter_data = post.metadata
                except Exception:
                    # If we can't parse frontmatter, continue without it
                    pass
            
            if self.config.should_include_file(rel_path, frontmatter_data):
                files_to_sync.append(file_path)
        
        return files_to_sync
    
    def sync_to_workspace(self) -> None:
        """Sync files from specs directory to workspace."""
        files_to_sync = self.get_files_to_sync()
        
        if not files_to_sync:
            console.print("[yellow]No files to sync[/yellow]")
            return
        
        for file_path in files_to_sync:
            self._copy_file_to_workspace(file_path)
        
        console.print(f"[green]Synced {len(files_to_sync)} files to workspace[/green]")
    
    def sync_from_workspace(self) -> None:
        """Sync files from workspace back to specs directory."""
        if not self.workspace_dir.exists():
            console.print("[yellow]Workspace directory does not exist[/yellow]")
            return
        
        synced_files = []
        
        for file_path in self.workspace_dir.rglob("*.md"):
            if file_path.is_file():
                self._copy_file_from_workspace(file_path)
                synced_files.append(file_path)
        
        if synced_files:
            console.print(f"[green]Synced {len(synced_files)} files from workspace[/green]")
        else:
            console.print("[yellow]No files to sync from workspace[/yellow]")
    
    def _copy_file_to_workspace(self, file_path: Path) -> None:
        """Copy a single file from specs to workspace."""
        rel_path = file_path.relative_to(self.specs_dir)
        
        if self.config.preserve_structure:
            target_path = self.workspace_dir / rel_path
        else:
            # Flatten structure
            target_path = self.workspace_dir / file_path.name
        
        # Create target directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(file_path, target_path)
        console.print(f"Copied: {rel_path} -> {target_path.relative_to(self.workspace_dir)}")
    
    def _copy_file_from_workspace(self, file_path: Path) -> None:
        """Copy a single file from workspace to specs."""
        rel_path = file_path.relative_to(self.workspace_dir)
        
        if self.config.preserve_structure:
            target_path = self.specs_dir / rel_path
        else:
            # When flattened, we need to find the original location
            # For now, put it in the root of specs dir
            target_path = self.specs_dir / file_path.name
        
        # Create target directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(file_path, target_path)
        console.print(f"Copied back: {rel_path} -> {target_path.relative_to(self.specs_dir)}")
    
    def watch(self) -> None:
        """Watch both directories for changes and sync automatically."""
        event_handler = SyncEventHandler(self)
        observer = Observer()
        
        # Watch specs directory
        if self.specs_dir.exists():
            observer.schedule(event_handler, str(self.specs_dir), recursive=True)
        
        # Watch workspace directory
        if self.workspace_dir.exists():
            observer.schedule(event_handler, str(self.workspace_dir), recursive=True)
        
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        
        observer.join()


class SyncEventHandler(FileSystemEventHandler):
    """Event handler for file system changes."""
    
    def __init__(self, syncer: SpecSync) -> None:
        """Initialize event handler.
        
        Args:
            syncer: SpecSync instance to use for syncing
        """
        self.syncer = syncer
        self.last_sync_time: Dict[str, float] = {}
    
    def on_modified(self, event) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Debounce events
        now = time.time()
        if file_path.name in self.last_sync_time:
            if now - self.last_sync_time[file_path.name] < self.syncer.config.watch_debounce_seconds:
                return
        
        self.last_sync_time[file_path.name] = now
        
        # Determine sync direction
        try:
            if self.syncer.specs_dir in file_path.parents or file_path == self.syncer.specs_dir:
                # File is in specs directory, sync to workspace
                if file_path.is_file() and file_path in self.syncer.get_files_to_sync():
                    self.syncer._copy_file_to_workspace(file_path)
                    console.print(f"[blue]Auto-synced to workspace: {file_path.name}[/blue]")
            
            elif self.syncer.workspace_dir in file_path.parents or file_path == self.syncer.workspace_dir:
                # File is in workspace directory, sync back to specs
                if file_path.is_file() and file_path.suffix.lower() == ".md":
                    self.syncer._copy_file_from_workspace(file_path)
                    console.print(f"[blue]Auto-synced to specs: {file_path.name}[/blue]")
        
        except Exception as e:
            console.print(f"[red]Error syncing {file_path.name}: {e}[/red]")
    
    def on_created(self, event) -> None:
        """Handle file creation events."""
        self.on_modified(event)