# telegram-bot/bot/game_engine/winner_detector.py
# Estif Bingo 24/7 - Winner Detector
# Detects winning patterns (horizontal, vertical, diagonal) in bingo cartelas

from typing import List, Dict, Set, Optional, Tuple, Any
from enum import Enum

from bot.utils.logger import logger


class WinPattern(Enum):
    """Types of winning patterns in bingo"""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    DIAGONAL_MAIN = "diagonal_main"
    DIAGONAL_ANTI = "diagonal_anti"
    FULL_HOUSE = "full_house"


class WinnerDetector:
    """
    Detects winning patterns in bingo cartelas.
    Supports horizontal lines, vertical lines, and diagonal lines.
    """
    
    GRID_SIZE = 5
    FREE_SPACE_POSITION = (2, 2)  # Center is free space (row, col)
    
    def __init__(self):
        """Initialize the winner detector"""
        self.winning_patterns_cache: Dict[str, Dict] = {}
        logger.info("WinnerDetector initialized")
    
    # ==================== WIN DETECTION METHODS ====================
    
    def check_win(self, cartela_grid: List[List[int]], called_numbers: List[int]) -> Optional[Dict]:
        """
        Check if a cartela has a winning pattern.
        
        Args:
            cartela_grid: 5x5 grid of numbers (0 for free space)
            called_numbers: List of numbers that have been called
        
        Returns:
            dict: Winning pattern information or None if no win
        """
        if not cartela_grid or not called_numbers:
            return None
        
        called_set = set(called_numbers)
        
        # Check all winning patterns in order of priority
        patterns_to_check = [
            ('horizontal', self._check_horizontal),
            ('vertical', self._check_vertical),
            ('diagonal_main', self._check_diagonal_main),
            ('diagonal_anti', self._check_diagonal_anti),
        ]
        
        for pattern_type, check_func in patterns_to_check:
            result = check_func(cartela_grid, called_set)
            if result:
                return {
                    'type': pattern_type,
                    'cells': result['cells'],
                    'line_index': result.get('index'),
                    'completed_at': len(called_numbers)
                }
        
        return None
    
    def _check_horizontal(self, grid: List[List[int]], called_set: Set[int]) -> Optional[Dict]:
        """
        Check for horizontal winning lines.
        
        Args:
            grid: 5x5 grid
            called_set: Set of called numbers
        
        Returns:
            dict: Winning line info or None
        """
        for row in range(self.GRID_SIZE):
            line_complete = True
            cells = []
            
            for col in range(self.GRID_SIZE):
                value = grid[col][row]
                cells.append({'col': col, 'row': row, 'value': value})
                
                if value != 0 and value not in called_set:
                    line_complete = False
                    break
            
            if line_complete:
                return {
                    'cells': cells,
                    'index': row
                }
        
        return None
    
    def _check_vertical(self, grid: List[List[int]], called_set: Set[int]) -> Optional[Dict]:
        """
        Check for vertical winning lines.
        
        Args:
            grid: 5x5 grid
            called_set: Set of called numbers
        
        Returns:
            dict: Winning line info or None
        """
        for col in range(self.GRID_SIZE):
            line_complete = True
            cells = []
            
            for row in range(self.GRID_SIZE):
                value = grid[col][row]
                cells.append({'col': col, 'row': row, 'value': value})
                
                if value != 0 and value not in called_set:
                    line_complete = False
                    break
            
            if line_complete:
                return {
                    'cells': cells,
                    'index': col
                }
        
        return None
    
    def _check_diagonal_main(self, grid: List[List[int]], called_set: Set[int]) -> Optional[Dict]:
        """
        Check for main diagonal (top-left to bottom-right) winning line.
        
        Args:
            grid: 5x5 grid
            called_set: Set of called numbers
        
        Returns:
            dict: Winning line info or None
        """
        line_complete = True
        cells = []
        
        for i in range(self.GRID_SIZE):
            value = grid[i][i]
            cells.append({'col': i, 'row': i, 'value': value})
            
            if value != 0 and value not in called_set:
                line_complete = False
                break
        
        if line_complete:
            return {'cells': cells, 'index': 0}
        
        return None
    
    def _check_diagonal_anti(self, grid: List[List[int]], called_set: Set[int]) -> Optional[Dict]:
        """
        Check for anti-diagonal (top-right to bottom-left) winning line.
        
        Args:
            grid: 5x5 grid
            called_set: Set of called numbers
        
        Returns:
            dict: Winning line info or None
        """
        line_complete = True
        cells = []
        
        for i in range(self.GRID_SIZE):
            col = i
            row = self.GRID_SIZE - 1 - i
            value = grid[col][row]
            cells.append({'col': col, 'row': row, 'value': value})
            
            if value != 0 and value not in called_set:
                line_complete = False
                break
        
        if line_complete:
            return {'cells': cells, 'index': 0}
        
        return None
    
    # ==================== MULTI-CARTELA WIN DETECTION ====================
    
    def check_all_cartelas(
        self,
        user_cartelas: Dict[int, List[Dict]],
        called_numbers: List[int]
    ) -> List[Dict]:
        """
        Check all cartelas for all players for winning patterns.
        
        Args:
            user_cartelas: dict - {user_id: [cartela1, cartela2, ...]}
            called_numbers: list - Called numbers so far
        
        Returns:
            list: List of winners with cartela and pattern info
        """
        winners = []
        called_set = set(called_numbers)
        
        for user_id, cartelas in user_cartelas.items():
            for cartela in cartelas:
                grid = cartela.get('grid')
                cartela_id = cartela.get('id')
                
                if not grid:
                    continue
                
                win_info = self.check_win(grid, called_numbers)
                if win_info:
                    winners.append({
                        'user_id': user_id,
                        'cartela_id': cartela_id,
                        'pattern': win_info['type'],
                        'cells': win_info['cells'],
                        'line_index': win_info.get('line_index'),
                        'numbers_until_win': len(called_numbers)
                    })
        
        return winners
    
    def get_first_winner(
        self,
        user_cartelas: Dict[int, List[Dict]],
        called_numbers: List[int]
    ) -> Optional[Dict]:
        """
        Get the first winner (by cartela ID order).
        
        Args:
            user_cartelas: dict - User cartelas mapping
            called_numbers: list - Called numbers so far
        
        Returns:
            dict: First winner info or None
        """
        winners = self.check_all_cartelas(user_cartelas, called_numbers)
        
        if winners:
            # Sort by cartela ID (or could sort by any criteria)
            winners.sort(key=lambda x: x['cartela_id'])
            return winners[0]
        
        return None
    
    # ==================== MARKED CELLS CALCULATION ====================
    
    def get_marked_cells(
        self,
        cartela_grid: List[List[int]],
        called_numbers: List[int]
    ) -> List[Dict]:
        """
        Get all marked cells on a cartela based on called numbers.
        
        Args:
            cartela_grid: 5x5 grid
            called_numbers: List of called numbers
        
        Returns:
            list: List of marked cell positions
        """
        called_set = set(called_numbers)
        marked_cells = []
        
        for col in range(self.GRID_SIZE):
            for row in range(self.GRID_SIZE):
                value = cartela_grid[col][row]
                
                # Free space is always marked
                if value == 0:
                    marked_cells.append({
                        'col': col,
                        'row': row,
                        'value': 0,
                        'is_free': True
                    })
                elif value in called_set:
                    marked_cells.append({
                        'col': col,
                        'row': row,
                        'value': value,
                        'is_free': False
                    })
        
        return marked_cells
    
    def get_marked_cells_for_user(
        self,
        user_cartelas: List[Dict],
        called_numbers: List[int]
    ) -> Dict[int, List[Dict]]:
        """
        Get marked cells for all of a user's cartelas.
        
        Args:
            user_cartelas: list - User's cartelas
            called_numbers: list - Called numbers so far
        
        Returns:
            dict: {cartela_id: [marked_cells]}
        """
        result = {}
        
        for cartela in user_cartelas:
            cartela_id = cartela.get('id')
            grid = cartela.get('grid')
            
            if grid:
                result[cartela_id] = self.get_marked_cells(grid, called_numbers)
        
        return result
    
    # ==================== WINNING LINE VALIDATION ====================
    
    def validate_winning_line(
        self,
        cartela_grid: List[List[int]],
        called_numbers: List[int],
        pattern_type: str,
        line_index: Optional[int] = None
    ) -> bool:
        """
        Validate if a specific pattern is a winning line.
        
        Args:
            cartela_grid: 5x5 grid
            called_numbers: List of called numbers
            pattern_type: Type of pattern ('horizontal', 'vertical', 'diagonal_main', 'diagonal_anti')
            line_index: Index for horizontal/vertical lines
        
        Returns:
            bool: True if the line is winning
        """
        called_set = set(called_numbers)
        
        if pattern_type == 'horizontal' and line_index is not None:
            for col in range(self.GRID_SIZE):
                value = cartela_grid[col][line_index]
                if value != 0 and value not in called_set:
                    return False
            return True
        
        elif pattern_type == 'vertical' and line_index is not None:
            for row in range(self.GRID_SIZE):
                value = cartela_grid[line_index][row]
                if value != 0 and value not in called_set:
                    return False
            return True
        
        elif pattern_type == 'diagonal_main':
            for i in range(self.GRID_SIZE):
                value = cartela_grid[i][i]
                if value != 0 and value not in called_set:
                    return False
            return True
        
        elif pattern_type == 'diagonal_anti':
            for i in range(self.GRID_SIZE):
                value = cartela_grid[i][self.GRID_SIZE - 1 - i]
                if value != 0 and value not in called_set:
                    return False
            return True
        
        return False
    
    # ==================== PROGRESS TRACKING ====================
    
    def get_completion_percentage(
        self,
        cartela_grid: List[List[int]],
        called_numbers: List[int]
    ) -> float:
        """
        Calculate how close a cartela is to winning (percentage of numbers marked).
        
        Args:
            cartela_grid: 5x5 grid
            called_numbers: List of called numbers
        
        Returns:
            float: Completion percentage (0-100)
        """
        called_set = set(called_numbers)
        total_cells = self.GRID_SIZE * self.GRID_SIZE
        marked_count = 0
        
        for col in range(self.GRID_SIZE):
            for row in range(self.GRID_SIZE):
                value = cartela_grid[col][row]
                if value == 0 or value in called_set:
                    marked_count += 1
        
        return (marked_count / total_cells) * 100
    
    def get_closest_to_win(
        self,
        user_cartelas: Dict[int, List[Dict]],
        called_numbers: List[int]
    ) -> List[Dict]:
        """
        Get players/cartelas closest to winning.
        
        Args:
            user_cartelas: dict - User cartelas mapping
            called_numbers: list - Called numbers so far
        
        Returns:
            list: List sorted by completion percentage (highest first)
        """
        results = []
        
        for user_id, cartelas in user_cartelas.items():
            for cartela in cartelas:
                grid = cartela.get('grid')
                cartela_id = cartela.get('id')
                
                if grid:
                    percentage = self.get_completion_percentage(grid, called_numbers)
                    results.append({
                        'user_id': user_id,
                        'cartela_id': cartela_id,
                        'completion_percentage': percentage
                    })
        
        # Sort by completion percentage descending
        results.sort(key=lambda x: x['completion_percentage'], reverse=True)
        
        return results
    
    # ==================== PATTERN GENERATION ====================
    
    def get_all_possible_patterns(self) -> List[Dict]:
        """
        Get all possible winning patterns on a 5x5 grid.
        
        Returns:
            list: List of all possible winning patterns
        """
        patterns = []
        
        # Horizontal lines
        for row in range(self.GRID_SIZE):
            cells = [{'col': col, 'row': row} for col in range(self.GRID_SIZE)]
            patterns.append({
                'type': WinPattern.HORIZONTAL.value,
                'name': f'Row {row + 1}',
                'cells': cells,
                'index': row
            })
        
        # Vertical lines
        for col in range(self.GRID_SIZE):
            cells = [{'col': col, 'row': row} for row in range(self.GRID_SIZE)]
            patterns.append({
                'type': WinPattern.VERTICAL.value,
                'name': f'Column {col + 1}',
                'cells': cells,
                'index': col
            })
        
        # Main diagonal
        main_diag_cells = [{'col': i, 'row': i} for i in range(self.GRID_SIZE)]
        patterns.append({
            'type': WinPattern.DIAGONAL_MAIN.value,
            'name': 'Main Diagonal',
            'cells': main_diag_cells,
            'index': 0
        })
        
        # Anti diagonal
        anti_diag_cells = [{'col': i, 'row': self.GRID_SIZE - 1 - i} for i in range(self.GRID_SIZE)]
        patterns.append({
            'type': WinPattern.DIAGONAL_ANTI.value,
            'name': 'Anti Diagonal',
            'cells': anti_diag_cells,
            'index': 0
        })
        
        return patterns
    
    def is_full_house(self, cartela_grid: List[List[int]], called_numbers: List[int]) -> bool:
        """
        Check if all numbers on the cartela have been called (full house).
        
        Args:
            cartela_grid: 5x5 grid
            called_numbers: List of called numbers
        
        Returns:
            bool: True if full house
        """
        called_set = set(called_numbers)
        
        for col in range(self.GRID_SIZE):
            for row in range(self.GRID_SIZE):
                value = cartela_grid[col][row]
                if value != 0 and value not in called_set:
                    return False
        
        return True
    
    # ==================== UTILITY METHODS ====================
    
    def clear_cache(self):
        """Clear the winning patterns cache"""
        self.winning_patterns_cache.clear()
        logger.debug("Winner detector cache cleared")
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about the winner detector.
        
        Returns:
            dict: Statistics
        """
        return {
            'grid_size': self.GRID_SIZE,
            'total_patterns': len(self.get_all_possible_patterns()),
            'cache_size': len(self.winning_patterns_cache)
        }


# ==================== FAST WINNER DETECTOR (OPTIMIZED) ====================

class FastWinnerDetector(WinnerDetector):
    """
    Optimized winner detector with caching for better performance.
    Caches win checks for cartelas to avoid redundant calculations.
    """
    
    def __init__(self):
        super().__init__()
        self._win_cache: Dict[str, Optional[Dict]] = {}
    
    def _get_cache_key(self, cartela_id: int, called_numbers_hash: str) -> str:
        """Generate cache key for a cartela and called numbers state"""
        return f"{cartela_id}:{called_numbers_hash}"
    
    def check_win_with_cache(
        self,
        cartela_id: int,
        cartela_grid: List[List[int]],
        called_numbers: List[int]
    ) -> Optional[Dict]:
        """
        Check for win with caching for performance.
        
        Args:
            cartela_id: int - Cartela ID
            cartela_grid: 5x5 grid
            called_numbers: List of called numbers
        
        Returns:
            dict: Winning pattern info or None
        """
        # Create a simple hash of called numbers state (last 10 numbers)
        # This is a trade-off between accuracy and cache hits
        cache_key = f"{cartela_id}:{len(called_numbers)}:{hash(tuple(called_numbers[-10:])) if called_numbers else 0}"
        
        if cache_key in self._win_cache:
            return self._win_cache[cache_key]
        
        result = self.check_win(cartela_grid, called_numbers)
        self._win_cache[cache_key] = result
        
        return result
    
    def clear_cache(self):
        """Clear the win cache"""
        self._win_cache.clear()
        super().clear_cache()


# ==================== FACTORY FUNCTION ====================

def create_winner_detector(optimized: bool = False) -> WinnerDetector:
    """
    Factory function to create a WinnerDetector instance.
    
    Args:
        optimized: bool - Whether to use optimized version with caching
    
    Returns:
        WinnerDetector: WinnerDetector instance
    """
    if optimized:
        return FastWinnerDetector()
    return WinnerDetector()


# ==================== EXPORTS ====================

__all__ = [
    'WinPattern',
    'WinnerDetector',
    'FastWinnerDetector',
    'create_winner_detector',
]