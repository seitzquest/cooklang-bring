#!/usr/bin/env python3
"""
Add Cooklang recipes to Bring! shopping list.

This script takes one or more .cook recipe files, generates a shopping list
using the cooklang CLI, and adds the items to your Bring! shopping list.

Usage:
    python add-to-bring.py recipe1.cook recipe2.cook
    python add-to-bring.py recipes/*.cook
    python add-to-bring.py recipe.cook:2  # Double the recipe

Requirements:
    - cooklang CLI (cook) installed and in PATH
    - python-bring-api: pip install python-bring-api
    - python-dotenv: pip install python-dotenv
"""

import argparse
import json
import os
import subprocess
import sys
import termios
import tty
from pathlib import Path

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    from python_bring_api.bring import Bring
    BRING_API_AVAILABLE = True
except ImportError:
    BRING_API_AVAILABLE = False


def load_config():
    """Load configuration from .env file."""
    if not DOTENV_AVAILABLE:
        print("Error: python-dotenv not installed. Run: pip install python-dotenv")
        sys.exit(1)

    load_dotenv()

    email = os.getenv('BRING_EMAIL')
    password = os.getenv('BRING_PASSWORD')
    list_name = os.getenv('BRING_LIST_NAME', '')

    if not email or not password:
        print("Error: BRING_EMAIL and BRING_PASSWORD must be set in .env file")
        print("See .env.example for required configuration")
        sys.exit(1)

    return email, password, list_name


def generate_shopping_list(recipe_files, recipes_dir=None):
    """
    Generate shopping list from recipe files using cooklang CLI.

    Args:
        recipe_files: List of recipe file paths (can include :scale suffix)
        recipes_dir: Directory containing recipes (defaults to current directory)

    Returns:
        List of dictionaries with category and items
    """
    if recipes_dir is None:
        recipes_dir = get_recipes_dir()
    else:
        recipes_dir = Path(recipes_dir).expanduser().resolve()

    try:
        cmd = ['cook', 'shopping-list', '-f', 'json'] + recipe_files
        # Run cook command in the recipes directory
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=str(recipes_dir))

        if result.returncode != 0:
            print(f"Error running cook command: {result.stderr}")
            sys.exit(1)

        shopping_list = json.loads(result.stdout)
        return shopping_list

    except subprocess.CalledProcessError as e:
        print(f"Error generating shopping list: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing shopping list JSON: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'cook' command not found. Please install cooklang CLI.")
        print("See: https://cooklang.org/cli/")
        sys.exit(1)


def filter_staples(shopping_list):
    """
    Filter out items in the 'staples' category from the shopping list.

    Items marked as staples in aisle.conf (salt, pepper, water, oil, etc.)
    are typically already in your pantry and don't need to be purchased.

    Args:
        shopping_list: List of dictionaries with category and items

    Returns:
        Filtered shopping list without staples category
    """
    return [cat for cat in shopping_list if cat.get('category', '').lower() != 'staples']


def format_quantity(quantity_list):
    """
    Format quantity information into a human-readable string.

    Args:
        quantity_list: List of quantity objects from cooklang

    Returns:
        String representation of quantity (e.g., "2 cups", "500 g")
    """
    if not quantity_list:
        return ""

    parts = []
    for qty in quantity_list:
        value = qty.get('value', {})
        if value.get('type') == 'number':
            num_value = value.get('value', {}).get('value', '')
            unit = qty.get('unit', '')

            if num_value:
                if unit:
                    parts.append(f"{num_value} {unit}")
                else:
                    parts.append(str(num_value))

    return ", ".join(parts)


def add_to_bring(shopping_list, email, password, list_name=''):
    """
    Add items from shopping list to Bring! app.

    Args:
        shopping_list: Shopping list from cooklang
        email: Bring! account email
        password: Bring! account password
        list_name: Optional specific list name (uses first list if not specified)
    """
    if not BRING_API_AVAILABLE:
        print("Error: python-bring-api not installed. Run: pip install python-bring-api")
        sys.exit(1)

    try:
        # Login to Bring!
        bring = Bring(email, password)
        bring.login()

        # Get available lists
        lists_data = bring.loadLists()
        lists = lists_data.get('lists', [])

        if not lists:
            print("Error: No shopping lists found in your Bring! account")
            sys.exit(1)

        # Select target list
        target_list = None
        if list_name:
            for lst in lists:
                if lst['name'].lower() == list_name.lower():
                    target_list = lst
                    break
            if not target_list:
                print(f"Warning: List '{list_name}' not found. Using first available list.")
                target_list = lists[0]
        else:
            target_list = lists[0]

        list_uuid = target_list['listUuid']
        list_display_name = target_list['name']

        print(f"Adding items to Bring! list: {list_display_name}")
        print("-" * 50)

        # Add items to Bring!
        total_items = 0
        for category in shopping_list:
            category_name = category.get('category', 'other')
            items = category.get('items', [])

            if items:
                print(f"\n{category_name.upper()}:")

            for item in items:
                item_name = item.get('name', '')
                quantity = item.get('quantity', [])

                # Format specification (quantity info)
                spec = format_quantity(quantity)

                # Add to Bring!
                try:
                    bring.saveItem(list_uuid, item_name, spec)
                    display = f"  ✓ {item_name}"
                    if spec:
                        display += f" ({spec})"
                    print(display)
                    total_items += 1
                except Exception as e:
                    print(f"  ✗ Failed to add {item_name}: {e}")

        print("-" * 50)
        print(f"Successfully added {total_items} items to '{list_display_name}'")

    except Exception as e:
        print(f"Error connecting to Bring!: {e}")
        sys.exit(1)


# Interactive mode functions
def getch():
    """Get a single character from user without requiring Enter"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def clear_screen():
    """Clear the terminal screen"""
    os.system("clear" if os.name != "nt" else "cls")


def show_context(context_dict):
    """Show current selection context"""
    print("\n━━━ Add Recipes to Bring! Shopping List ━━━\n")
    for key, value in context_dict.items():
        if value is not None:
            print(f"{key}: {value}")


def get_recipes_dir():
    """Get the recipes directory from environment or default to current directory"""
    recipes_dir = os.environ.get('RECIPES_DIR', None)
    if recipes_dir:
        return Path(recipes_dir).expanduser().resolve()
    return Path.cwd()


def get_kitchens(recipes_dir=None):
    """Get list of recipe directories (kitchens)"""
    if recipes_dir is None:
        recipes_dir = get_recipes_dir()
    else:
        recipes_dir = Path(recipes_dir).expanduser().resolve()

    # Find all subdirectories that contain .cook files
    kitchens = []
    for item in recipes_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('_'):
            # Check if directory contains any .cook files
            if list(item.glob('*.cook')):
                kitchens.append(item.name)

    return sorted(kitchens)


def get_recipes_in_kitchen(kitchen, recipes_dir=None):
    """Get list of recipes in a kitchen directory"""
    if recipes_dir is None:
        recipes_dir = get_recipes_dir()
    else:
        recipes_dir = Path(recipes_dir).expanduser().resolve()

    kitchen_path = recipes_dir / kitchen
    recipes = []

    for recipe_file in sorted(kitchen_path.glob('*.cook')):
        # Convert filename to display name
        display_name = recipe_file.stem.replace('-', ' ').replace('_', ' ').title()
        recipes.append((recipe_file.name, display_name))

    return recipes


def select_from_list(items, prompt, context=None, allow_back=False):
    """Display a selection list with numbered options"""
    clear_screen()

    if context:
        show_context(context)

    print(f"\n┌─ {prompt}")
    print("│")

    for i, (value, display) in enumerate(items, 1):
        print(f"│ {i:2d}. {display}")

    print("│")

    while True:
        try:
            prompt_text = "└─ Enter number"
            if allow_back:
                prompt_text += " (or 'b' to go back)"
            prompt_text += " (or 'q' to quit): "

            choice = input(prompt_text).strip()

            if choice.lower() == 'q':
                sys.exit(0)

            if choice.lower() == 'b' and allow_back:
                return None

            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx][0]
            else:
                print(f"   Please enter a number between 1 and {len(items)}")
        except ValueError:
            print("   Please enter a valid number")


def get_scaling_factor(context=None):
    """Ask for recipe scaling factor"""
    clear_screen()

    if context:
        show_context(context)

    print("\n┌─ Scale Recipe")
    print("│")
    print("│  1 = normal")
    print("│  2 = double")
    print("│  0.5 = half")
    print("│")

    while True:
        scale_input = input("└─ Scaling factor (or Enter for 1): ").strip()

        if not scale_input:
            return 1.0

        try:
            scale = float(scale_input)
            if scale <= 0:
                print("   Scaling factor must be positive")
                continue
            return scale
        except ValueError:
            print("   Please enter a valid number")


def show_shopping_list_preview(shopping_list):
    """Display shopping list preview"""
    print("\n" + "=" * 50)
    print("SHOPPING LIST PREVIEW")
    print("=" * 50)

    for category in shopping_list:
        category_name = category.get('category', 'other')
        items = category.get('items', [])

        if items:
            print(f"\n{category_name.upper()}:")
            for item in items:
                item_name = item.get('name', '')
                quantity = item.get('quantity', [])
                spec = format_quantity(quantity)

                display = f"  • {item_name}"
                if spec:
                    display += f" ({spec})"
                print(display)

    print("=" * 50)


def interactive_mode(recipes_dir=None):
    """Run in interactive mode to select recipes"""
    if recipes_dir is None:
        recipes_dir = get_recipes_dir()
    else:
        recipes_dir = Path(recipes_dir).expanduser().resolve()

    clear_screen()
    print("\n━━━ Add Recipes to Bring! Shopping List ━━━\n")
    print("Interactive Mode")
    print(f"Recipes: {recipes_dir}")
    print()

    selected_recipes = []
    context = {}

    while True:
        # Show currently selected recipes
        if selected_recipes:
            recipe_list = ", ".join([f"{r['display']}" + (f" (×{r['scale']:.1f})" if r['scale'] != 1.0 else "") for r in selected_recipes])
            context["Selected Recipes"] = recipe_list

        # Select kitchen
        kitchens = get_kitchens(recipes_dir)
        if not kitchens:
            print("Error: No recipe directories found!")
            sys.exit(1)

        kitchen_items = [(k, k) for k in kitchens]
        selected_kitchen = select_from_list(
            kitchen_items,
            "Select Kitchen",
            context,
            allow_back=False
        )

        if not selected_kitchen:
            continue

        context_with_kitchen = context.copy()
        context_with_kitchen["Kitchen"] = selected_kitchen

        # Select recipe from kitchen
        recipes = get_recipes_in_kitchen(selected_kitchen, recipes_dir)
        if not recipes:
            print(f"No recipes found in {selected_kitchen}")
            continue

        selected_recipe = select_from_list(
            recipes,
            f"Select Recipe from {selected_kitchen}",
            context_with_kitchen,
            allow_back=True
        )

        if not selected_recipe:
            # User went back
            continue

        # Get display name
        recipe_display = next((d for r, d in recipes if r == selected_recipe), selected_recipe)

        context_with_recipe = context_with_kitchen.copy()
        context_with_recipe["Recipe"] = recipe_display

        # Get scaling
        scale = get_scaling_factor(context_with_recipe)

        # Add to selected recipes
        recipe_path = f"{selected_kitchen}/{selected_recipe}"
        if scale != 1.0:
            recipe_path += f":{scale}"

        selected_recipes.append({
            'path': recipe_path,
            'display': f"{selected_kitchen}/{recipe_display}",
            'scale': scale
        })

        # Update context
        recipe_list = ", ".join([f"{r['display']}" + (f" (×{r['scale']:.1f})" if r['scale'] != 1.0 else "") for r in selected_recipes])
        context["Selected Recipes"] = recipe_list

        # Ask to add another recipe
        clear_screen()
        show_context(context)
        print("\n┌─ Add Another Recipe?")
        print("│")
        print("└─ (y/n): ", end="", flush=True)

        while True:
            another = getch().lower()
            if another in ('y', 'n'):
                print(another)
                break

        if another != 'y':
            break

    if not selected_recipes:
        print("No recipes selected.")
        sys.exit(0)

    # Generate shopping list
    clear_screen()
    print("\n━━━ Generating Shopping List ━━━\n")

    recipe_paths = [r['path'] for r in selected_recipes]
    shopping_list = generate_shopping_list(recipe_paths, recipes_dir)

    if not shopping_list:
        print("No items found in shopping list.")
        sys.exit(0)

    # Filter staples
    staples_category = next((cat for cat in shopping_list if cat.get('category', '').lower() == 'staples'), None)
    if staples_category:
        staples_count = len(staples_category.get('items', []))
        if staples_count > 0:
            print(f"Filtered {staples_count} staple item(s) (already in pantry)")
    shopping_list = filter_staples(shopping_list)

    # Show preview
    show_shopping_list_preview(shopping_list)

    # Ask to send to Bring!
    print("\n┌─ Send to Bring! Shopping List?")
    print("│")
    print("└─ (y/n): ", end="", flush=True)

    while True:
        send = getch().lower()
        if send in ('y', 'n'):
            print(send)
            break

    if send == 'y':
        email, password, list_name = load_config()
        add_to_bring(shopping_list, email, password, list_name)
    else:
        print("\nShopping list not sent to Bring!")


def main():
    # If no arguments provided, run in interactive mode with default recipes dir
    if len(sys.argv) == 1:
        try:
            interactive_mode()
        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            sys.exit(0)
        return

    parser = argparse.ArgumentParser(
        description='Add Cooklang recipes to Bring! shopping list',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                            # Interactive mode (no arguments)
  %(prog)s recipe.cook
  %(prog)s recipe1.cook recipe2.cook
  %(prog)s recipe.cook:2              # Double the recipe
  %(prog)s recipes/*.cook
  %(prog)s -d --list recipes/*.cook   # Dry run to see what would be added

Configuration:
  Create a .env file with:
    BRING_EMAIL=your-email@example.com
    BRING_PASSWORD=your-password
    BRING_LIST_NAME=Shopping List  # Optional, uses first list if not set
        """
    )

    parser.add_argument(
        'recipes',
        nargs='*',
        help='Recipe files to add (supports :scale suffix, e.g., recipe.cook:2). Leave empty for interactive mode.'
    )

    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        help='Generate shopping list without adding to Bring!'
    )

    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='Show shopping list in terminal'
    )

    parser.add_argument(
        '--include-staples',
        action='store_true',
        help='Include staples (salt, pepper, water, oil, etc.) in the shopping list'
    )

    parser.add_argument(
        '-r', '--recipes-dir',
        help='Directory containing recipes (defaults to RECIPES_DIR env var or current directory)'
    )

    args = parser.parse_args()

    # If no recipes provided, run in interactive mode
    if not args.recipes:
        try:
            interactive_mode(args.recipes_dir)
        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            sys.exit(0)
        return

    # Generate shopping list
    print("Generating shopping list from recipes...")
    shopping_list = generate_shopping_list(args.recipes, args.recipes_dir)

    if not shopping_list:
        print("No items found in shopping list. Check your recipe files.")
        sys.exit(0)

    # Filter out staples unless requested
    if not args.include_staples:
        # Count staples before filtering
        staples_category = next((cat for cat in shopping_list if cat.get('category', '').lower() == 'staples'), None)
        if staples_category:
            staples_count = len(staples_category.get('items', []))
            if staples_count > 0:
                print(f"Filtered {staples_count} staple item(s) (use --include-staples to show them)")
        shopping_list = filter_staples(shopping_list)

    # Show list if requested
    if args.list or args.dry_run:
        print("\nShopping List:")
        print("=" * 50)
        for category in shopping_list:
            category_name = category.get('category', 'other')
            items = category.get('items', [])

            if items:
                print(f"\n{category_name.upper()}:")
                for item in items:
                    item_name = item.get('name', '')
                    quantity = item.get('quantity', [])
                    spec = format_quantity(quantity)

                    display = f"  • {item_name}"
                    if spec:
                        display += f" ({spec})"
                    print(display)
        print("=" * 50)

    # Add to Bring! unless dry-run
    if not args.dry_run:
        email, password, list_name = load_config()
        add_to_bring(shopping_list, email, password, list_name)
    else:
        print("\nDry run mode - items were not added to Bring!")


if __name__ == '__main__':
    main()
