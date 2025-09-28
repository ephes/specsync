---
title: Example Specification
published: true
tags: [spec, example]
author: SpecSync Team
date: 2024-01-01
---

# Example Specification

This is an example specification document that shows how to use frontmatter with SpecSync.

## Overview

SpecSync will include this file when syncing because:
- It matches the `*.md` pattern
- It has `published: true` in the frontmatter
- It's not excluded by any exclude patterns

## Features Demonstrated

- YAML frontmatter parsing
- Selective inclusion based on metadata
- Rich formatting with markdown

## Notes

This file will be synced to your workspace when you run:

```bash
specsync sync /path/to/workspace
```