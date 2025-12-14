# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLI tool that exports Cooklang recipes to Bring! shopping list app. Parses `.cook` recipe files using the Cooklang CLI, aggregates ingredients, and adds them to a Bring! shopping list via unofficial API.

## Commands

```bash
# Install dependencies
uv sync

# Run the script
uv run add_to_bring.py                           # Interactive mode
uv run add_to_bring.py German/recipe.cook        # Single recipe
uv run add_to_bring.py recipe.cook:2             # Scale recipe (double)
uv run add_to_bring.py --dry-run --list recipe.cook  # Preview only

# Linting and formatting
pre-commit run --all-files                       # Run all checks
uvx ruff check --fix .                           # Lint with auto-fix
uvx ruff format .                                # Format code
uvx pyright                                      # Type checking
uvx deptry .                                     # Check dependencies
```

## Architecture

Single-file script (`add_to_bring.py`) with two modes:

- **Interactive mode**: Terminal UI for browsing kitchens (recipe subdirectories), selecting recipes, scaling, and previewing before sending
- **CLI mode**: Direct recipe paths with flags for dry-run, scaling, and staples filtering

Key flow: Recipe files → `cook shopping-list -f json` → parse/aggregate → filter staples → Bring! API

## Configuration

- `.env`: Bring! credentials (`BRING_EMAIL`, `BRING_PASSWORD`, `BRING_LIST_NAME`)
- `RECIPES_DIR` env var: Path to recipes directory
- `aisle.conf`: Maps ingredients to store aisles (lives in `$RECIPES_DIR/config/`)

## Dependencies

- External: Cooklang CLI (`cook`) must be in PATH
- Python: `python-bring-api`, `python-dotenv`

## Code Style

- Python 3.12+, 100-char line length
- Ruff for linting/formatting (double quotes, spaces, LF line endings)
- Pyright for type checking (standard mode)
