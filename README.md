# Cooklang to Bring! Shopping List

Sync [Cooklang](https://cooklang.org/) recipes to [Bring!](https://www.getbring.com/) shopping list app with an interactive CLI or command-line interface.

## Setup

```bash
# 1. Clone and install
git clone https://github.com/yourusername/cooklang-bring.git
cd cooklang-bring
uv sync

# 2. Configure Bring! credentials
cp .env.example .env
# Edit .env with your email and password

# 3. Set recipes directory (optional)
export RECIPES_DIR=~/path/to/your/recipes

# 4. Setup aisle configuration in your recipes directory
mkdir -p $RECIPES_DIR/config
cp aisle.conf.example $RECIPES_DIR/config/aisle.conf
```

**Prerequisites:** [Cooklang CLI](https://cooklang.org/cli/), Python 3.8+, [uv](https://github.com/astral-sh/uv)

## Usage

### Interactive Mode

```bash
uv run add_to_bring.py
```

Select kitchen → Select recipe → Scale if needed → Add more recipes → Preview → Send to Bring!

### Command-Line Mode

```bash
# Single recipe
uv run add_to_bring.py German/pumpkin-soup.cook

# Multiple recipes
uv run add_to_bring.py recipe1.cook recipe2.cook

# Scale recipe (double)
uv run add_to_bring.py recipe.cook:2

# Preview without sending
uv run add_to_bring.py --dry-run --list recipe.cook

# Include staples (salt, pepper, etc.)
uv run add_to_bring.py --include-staples recipe.cook
```

### Shell Alias (Optional)

```bash
# Add to ~/.zshrc or ~/.bashrc
export RECIPES_DIR=~/path/to/your/recipes
alias bring='uv run --directory ~/Projects/cooklang-bring add_to_bring.py'

# Then use
bring
```

## License

MIT License - see [LICENSE](LICENSE)

## Disclaimer

Uses unofficial Bring! API. Not affiliated with Bring! Labs AG.
