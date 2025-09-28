# SpecSync Documentation

Welcome to the SpecSync documentation site. SpecSync keeps Markdown specifications in sync between your repository and an external workspace so the information that guides development stays close to the code.

## Quick Start

1. Install SpecSync with `pipx install specsync` or `uv tool install specsync`
2. Set your workspace location: `export SPECSYNC_WORKSPACE_ROOT="/path/to/workspace"`
3. Run `specsync init` inside your repository to scaffold the `specs/` directory
4. Create or edit specs in your repo's `specs/` folder
5. Use `specsync push` to sync specs to your workspace for long-term storage

```{note}
The command-line reference in {doc}`usage` includes additional options and recommended workflows for day-to-day use.
```

## Contents

```{toctree}
:maxdepth: 2
:caption: Guides

installation
usage
configuration
architecture
changelog
api
```

## Additional Resources

- Source code: <https://github.com/username/specsync>
- {doc}`Architecture Overview <architecture>` - detailed system design and component documentation
