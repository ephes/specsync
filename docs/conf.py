from __future__ import annotations

import sys
from pathlib import Path

import tomllib

# Resolve project root and ensure src/ is importable for autodoc
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

with (ROOT_DIR / "pyproject.toml").open("rb") as pyproject_file:
    project_metadata = tomllib.load(pyproject_file)

# Project information
project = "SpecSync"
author = "SpecSync Contributors"
release = project_metadata["project"]["version"]
version = release

# General configuration
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinxcontrib.mermaid",
]

myst_enable_extensions = [
    "deflist",
    "tasklist",
    "html_image",
    "colon_fence",
    "fieldlist",
]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Options for HTML output
html_theme = "furo"
html_title = "SpecSync Documentation"
html_static_path = ["_static"]
html_css_files: list[str] = []

html_theme_options = {
    "source_repository": "https://github.com/ephes/specsync",
    "source_branch": "main",
    "source_directory": "docs/",
}
