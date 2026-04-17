# telegram-bot/bot/utils/cartela_generator.py
# Estif Bingo 24/7 - Cartela Generator Utility
# Generates 1000 bingo cartelas (5x5 grids) following BINGO rules
# Can be used to regenerate cartelas if needed or validate existing ones

import json
import random
import os
from typing import List, Dict, Any, Tuple
from pathlib import Path

# Constants
TOTAL_CARTELAS = 1000
GRID_SIZE = 5
FREE_SPACE_POSITION = (2, 2)  # Center cell (row, col) - zero indexed

# BINGO column ranges
COLUMN_RANGES = {
    0: (1, 15),    # B column
    1: (16, 30),   # I column
    2: (31, 45),   # N column
    3: (46, 60),   # G column
    4: (61, 75)    # O column
}

# Column names for CSV export
COLUMN_NAMES = ['b', 'i', 'n', 'g', 'o']


# ==================== CARTELA GENERATION ====================

def get_random_numbers(min_val: int, max_val: int, count: int) -> List[int]:
    """
    Generate random unique numbers within a range.
    
    Args:
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)
        count: Number of numbers to generate
    
    Returns:
        list: List of unique random numbers
    """
    available = list(range(min_val, max_val + 1))
    random.shuffle(available)
    return available[:count]


def generate_single_cartela(cartela_id: int) -> Dict[str, Any]:
    """
    Generate a single bingo cartela.
    
    Args:
        cartela_id: Cartela ID (1-1000)
    
    Returns:
        dict: Cartela object with id and grid
    """
    # Generate 5 numbers for each column
    column_numbers = []
    for col in range(GRID_SIZE):
        min_val, max_val = COLUMN_RANGES[col]
        numbers = get_random_numbers(min_val, max_val, GRID_SIZE)
        column_numbers.append(numbers)
    
    # Set FREE space in center (N column, row 2)
    column_numbers[2][2] = 0
    
    # Build grid (5x5) - format: grid[col][row]
    grid = []
    for col in range(GRID_SIZE):
        col_data = []
        for row in range(GRID_SIZE):
            col_data.append(column_numbers[col][row])
        grid.append(col_data)
    
    return {
        'id': cartela_id,
        'grid': grid
    }


def generate_all_cartelas(total: int = TOTAL_CARTELAS) -> List[Dict[str, Any]]:
    """
    Generate all cartelas.
    
    Args:
        total: Number of cartelas to generate
    
    Returns:
        list: List of cartela objects
    """
    cartelas = []
    for i in range(1, total + 1):
        cartela = generate_single_cartela(i)
        cartelas.append(cartela)
    
    return cartelas


# ==================== VALIDATION ====================

def validate_cartela_grid(grid: List[List[int]]) -> Tuple[bool, str]:
    """
    Validate a cartela grid.
    
    Args:
        grid: 5x5 grid of numbers
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check grid size
    if len(grid) != GRID_SIZE:
        return False, f"Grid has {len(grid)} columns, expected {GRID_SIZE}"
    
    for col in range(GRID_SIZE):
        if len(grid[col]) != GRID_SIZE:
            return False, f"Column {col} has {len(grid[col])} rows, expected {GRID_SIZE}"
    
    # Check FREE space is in center
    if grid[2][2] != 0:
        return False, f"Center cell is {grid[2][2]}, expected 0 (FREE space)"
    
    # Check column ranges
    for col in range(GRID_SIZE):
        min_val, max_val = COLUMN_RANGES[col]
        for row in range(GRID_SIZE):
            if row == 2 and col == 2:
                continue  # Skip FREE space
            value = grid[col][row]
            if value < min_val or value > max_val:
                return False, f"Value {value} at position ({col},{row}) is outside range {min_val}-{max_val}"
    
    # Check for duplicates within each column
    for col in range(GRID_SIZE):
        values = []
        for row in range(GRID_SIZE):
            if row == 2 and col == 2:
                continue
            values.append(grid[col][row])
        if len(values) != len(set(values)):
            return False, f"Duplicate numbers found in column {col}"
    
    return True, ""


def validate_cartelas_file(file_path: str) -> Dict[str, Any]:
    """
    Validate a cartelas JSON file.
    
    Args:
        file_path: Path to cartelas JSON file
    
    Returns:
        dict: Validation results
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        cartelas = json.load(f)
    
    results = {
        'total': len(cartelas),
        'valid': 0,
        'invalid': 0,
        'errors': []
    }
    
    for cartela in cartelas:
        cartela_id = cartela.get('id') or cartela.get('cartela_id')
        grid = cartela.get('grid')
        
        if not grid:
            results['invalid'] += 1
            results['errors'].append(f"Cartela {cartela_id}: Missing grid")
            continue
        
        is_valid, error = validate_cartela_grid(grid)
        if is_valid:
            results['valid'] += 1
        else:
            results['invalid'] += 1
            results['errors'].append(f"Cartela {cartela_id}: {error}")
    
    return results


# ==================== CONVERSION UTILITIES ====================

def cartela_to_csv_row(cartela: Dict[str, Any]) -> str:
    """
    Convert a cartela to CSV row format.
    
    Args:
        cartela: Cartela object with id and grid
    
    Returns:
        str: CSV row string
    """
    cartela_id = cartela.get('id') or cartela.get('cartela_id')
    grid = cartela.get('grid')
    
    # Extract column values
    column_values = []
    for col in range(GRID_SIZE):
        col_values = [str(grid[col][row]) for row in range(GRID_SIZE)]
        column_values.append(','.join(col_values))
    
    return f"{cartela_id},{cartela_id},\"{column_values[0]}\",\"{column_values[1]}\",\"{column_values[2]}\",\"{column_values[3]}\",\"{column_values[4]}\""


def cartelas_to_csv(cartelas: List[Dict[str, Any]], output_path: str) -> None:
    """
    Convert cartelas to CSV format and save to file.
    
    Args:
        cartelas: List of cartela objects
        output_path: Output CSV file path
    """
    rows = ['card_no,user_id,b,i,n,g,o']
    
    for cartela in cartelas:
        rows.append(cartela_to_csv_row(cartela))
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(rows))
    
    print(f"✅ Saved {len(cartelas)} cartelas to CSV: {output_path}")


def cartela_to_dict(cartela_id: int, grid: List[List[int]]) -> Dict[str, Any]:
    """
    Convert grid to cartela dictionary format.
    
    Args:
        cartela_id: Cartela ID
        grid: 5x5 grid
    
    Returns:
        dict: Cartela object
    """
    return {
        'id': cartela_id,
        'grid': grid
    }


# ==================== FILE OPERATIONS ====================

def save_cartelas_to_json(cartelas: List[Dict[str, Any]], output_path: str) -> None:
    """
    Save cartelas to JSON file.
    
    Args:
        cartelas: List of cartela objects
        output_path: Output JSON file path
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cartelas, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved {len(cartelas)} cartelas to JSON: {output_path}")


def load_cartelas_from_json(file_path: str) -> List[Dict[str, Any]]:
    """
    Load cartelas from JSON file.
    
    Args:
        file_path: Path to cartelas JSON file
    
    Returns:
        list: List of cartela objects
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def regenerate_cartelas(output_path: str = "data/cartelas_1000.json") -> None:
    """
    Regenerate all cartelas and save to file.
    
    Args:
        output_path: Output JSON file path
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Generate cartelas
    cartelas = generate_all_cartelas(TOTAL_CARTELAS)
    
    # Save to JSON
    save_cartelas_to_json(cartelas, output_path)
    
    # Also save as CSV for compatibility
    csv_path = output_path.replace('.json', '.csv')
    cartelas_to_csv(cartelas, csv_path)
    
    print(f"\n✨ Generated {TOTAL_CARTELAS} cartelas successfully!")


# ==================== SAMPLE DISPLAY ====================

def display_cartela_grid(grid: List[List[int]]) -> None:
    """
    Display a cartela grid in a readable format.
    
    Args:
        grid: 5x5 grid
    """
    print("   B   I   N   G   O")
    print("  ┌───┬───┬───┬───┬───┐")
    
    for row in range(GRID_SIZE):
        row_values = []
        for col in range(GRID_SIZE):
            val = grid[col][row]
            row_values.append(f"{val:2}" if val != 0 else "⭐")
        
        print(f"{row+1} │ {' │ '.join(row_values)} │")
        if row < GRID_SIZE - 1:
            print("  ├───┼───┼───┼───┼───┤")
    
    print("  └───┴───┴───┴───┴───┘")


def display_sample_cartelas(count: int = 3) -> None:
    """
    Display sample cartelas.
    
    Args:
        count: Number of sample cartelas to display
    """
    cartelas = generate_all_cartelas(count)
    
    for cartela in cartelas:
        print(f"\n📊 Cartela #{cartela['id']}:")
        display_cartela_grid(cartela['grid'])
        print()


# ==================== STATISTICS ====================

def get_number_distribution(cartelas: List[Dict[str, Any]]) -> Dict[int, int]:
    """
    Get distribution of numbers across all cartelas.
    
    Args:
        cartelas: List of cartela objects
    
    Returns:
        dict: Number -> count mapping
    """
    distribution = {}
    
    for cartela in cartelas:
        grid = cartela.get('grid')
        if not grid:
            continue
        
        for col in range(GRID_SIZE):
            for row in range(GRID_SIZE):
                value = grid[col][row]
                if value != 0:
                    distribution[value] = distribution.get(value, 0) + 1
    
    return distribution


def print_statistics(cartelas: List[Dict[str, Any]]) -> None:
    """
    Print statistics about the cartelas.
    
    Args:
        cartelas: List of cartela objects
    """
    distribution = get_number_distribution(cartelas)
    
    if not distribution:
        print("No data to analyze")
        return
    
    min_count = min(distribution.values())
    max_count = max(distribution.values())
    avg_count = sum(distribution.values()) / len(distribution)
    
    print("\n📊 Cartela Statistics:")
    print(f"  Total cartelas: {len(cartelas)}")
    print(f"  Numbers used: {len(distribution)}")
    print(f"  Min occurrences per number: {min_count}")
    print(f"  Max occurrences per number: {max_count}")
    print(f"  Average occurrences per number: {avg_count:.2f}")


# ==================== MAIN EXECUTION ====================

def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate bingo cartelas')
    parser.add_argument('--output', '-o', default='data/cartelas_1000.json',
                        help='Output JSON file path')
    parser.add_argument('--validate', '-v', action='store_true',
                        help='Validate existing cartelas file')
    parser.add_argument('--display', '-d', type=int, default=0,
                        help='Display N sample cartelas')
    parser.add_argument('--stats', '-s', action='store_true',
                        help='Print statistics')
    
    args = parser.parse_args()
    
    if args.validate:
        # Validate existing file
        if os.path.exists(args.output):
            results = validate_cartelas_file(args.output)
            print(f"\n📋 Validation Results:")
            print(f"  Total cartelas: {results['total']}")
            print(f"  Valid: {results['valid']}")
            print(f"  Invalid: {results['invalid']}")
            if results['errors']:
                print(f"\n  Errors:")
                for error in results['errors'][:10]:
                    print(f"    - {error}")
                if len(results['errors']) > 10:
                    print(f"    ... and {len(results['errors']) - 10} more")
        else:
            print(f"File not found: {args.output}")
    
    elif args.display > 0:
        # Display sample cartelas
        display_sample_cartelas(args.display)
    
    elif args.stats:
        # Print statistics
        if os.path.exists(args.output):
            cartelas = load_cartelas_from_json(args.output)
            print_statistics(cartelas)
        else:
            print(f"File not found: {args.output}")
    
    else:
        # Generate new cartelas
        regenerate_cartelas(args.output)


if __name__ == "__main__":
    main()