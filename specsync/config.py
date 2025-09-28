"""Configuration management for SpecSync."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class Config:
    """Configuration for SpecSync."""
    
    def __init__(
        self,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        frontmatter_filter: Optional[Dict[str, Any]] = None,
        preserve_structure: bool = True,
        watch_debounce_seconds: float = 1.0,
    ) -> None:
        """Initialize configuration.
        
        Args:
            include_patterns: File patterns to include (e.g., ['*.md', 'docs/**/*.md'])
            exclude_patterns: File patterns to exclude
            frontmatter_filter: Filter files based on frontmatter fields
            preserve_structure: Whether to preserve directory structure in workspace
            watch_debounce_seconds: Seconds to wait before processing file changes
        """
        self.include_patterns = include_patterns or ["*.md"]
        self.exclude_patterns = exclude_patterns or []
        self.frontmatter_filter = frontmatter_filter or {}
        self.preserve_structure = preserve_structure
        self.watch_debounce_seconds = watch_debounce_seconds
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file or create default."""
        if config_path is None:
            # Look for config in common locations
            for path in ["specsync.yaml", "specsync.yml", ".specsync.yaml"]:
                if Path(path).exists():
                    config_path = Path(path)
                    break
        
        if config_path and config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        
        return cls()
    
    def save(self, config_path: Path) -> None:
        """Save configuration to file."""
        data = {
            "include_patterns": self.include_patterns,
            "exclude_patterns": self.exclude_patterns,
            "frontmatter_filter": self.frontmatter_filter,
            "preserve_structure": self.preserve_structure,
            "watch_debounce_seconds": self.watch_debounce_seconds,
        }
        
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def should_include_file(self, file_path: Path, frontmatter: Optional[Dict[str, Any]] = None) -> bool:
        """Check if file should be included based on patterns and frontmatter."""
        from pathlib import PurePath
        
        # Check include patterns
        included = False
        for pattern in self.include_patterns:
            # Use PurePath.match for proper glob pattern support including **
            if PurePath(file_path).match(pattern):
                included = True
                break
        
        if not included:
            return False
        
        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if PurePath(file_path).match(pattern):
                return False
        
        # Check frontmatter filter - only apply if filter is configured
        if self.frontmatter_filter:
            # If frontmatter filter is configured but file has no frontmatter, exclude it
            if not frontmatter:
                return False
                
            for key, expected_value in self.frontmatter_filter.items():
                if key not in frontmatter:
                    return False
                
                actual_value = frontmatter[key]
                
                # Handle different comparison types
                if isinstance(expected_value, bool):
                    if actual_value != expected_value:
                        return False
                elif isinstance(expected_value, str):
                    if actual_value != expected_value:
                        return False
                elif isinstance(expected_value, list):
                    # Check if actual value is in the list
                    if actual_value not in expected_value:
                        return False
        
        return True