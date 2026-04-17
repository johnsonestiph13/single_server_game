# telegram-bot/bot/game_engine/cartela_manager.py
# Estif Bingo 24/7 - Cartela Manager
# Manages 1000 cartelas, tracks taken/selected per round, and handles availability

import json
import os
import random
import asyncio
from typing import Dict, List, Set, Optional, Any
from threading import Lock
from datetime import datetime

from bot.utils.logger import logger
from bot.config import config


class CartelaManager:
    """
    Manages 1000 cartelas for the real-time multiplayer bingo game.
    Tracks which cartelas are taken/selected in the current round.
    Singleton pattern to ensure consistent state across the application.
    """
    
    _instance = None
    _lock = Lock()
    
    # Column ranges for BINGO validation
    COLUMN_RANGES = {
        0: (1, 15),   # B
        1: (16, 30),  # I
        2: (31, 45),  # N
        3: (46, 60),  # G
        4: (61, 75)   # O
    }
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize cartela manager - loads cartelas from JSON or generates fallback"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.cartelas: List[Dict] = []           # List of cartela objects
            self.cartelas_by_id: Dict[int, Dict] = {}  # Fast lookup by ID
            self.total_cartelas: int = 1000
            
            # Round-specific state (reset each round)
            self.taken_by: Dict[int, int] = {}        # cartela_id -> user_id (who took it)
            self.selected_by: Dict[int, Set[int]] = {} # user_id -> set of cartela_ids
            self.current_round_id: Optional[int] = None
            
            # Load cartelas
            self._load_cartelas()
            
            logger.info(f"CartelaManager initialized with {len(self.cartelas)} cartelas")
    
    # ==================== LOADING METHODS ====================
    
    def _load_cartelas(self):
        """Load cartelas from JSON file or generate fallback"""
        # Try multiple possible paths
        possible_paths = [
            "data/cartelas_1000.json",
            "telegram-bot/data/cartelas_1000.json",
            "../data/cartelas_1000.json",
            "../../data/cartelas_1000.json",
            os.path.join(os.path.dirname(__file__), "../../data/cartelas_1000.json"),
            os.path.join(os.path.dirname(__file__), "../data/cartelas_1000.json"),
        ]
        
        loaded = False
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        cartelas_data = json.load(f)
                    
                    self._process_cartelas_data(cartelas_data)
                    logger.info(f"Loaded {len(self.cartelas)} cartelas from {path}")
                    loaded = True
                    break
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in {path}: {e}")
                except Exception as e:
                    logger.error(f"Error loading cartelas from {path}: {e}")
        
        if not loaded:
            logger.warning("No cartelas JSON file found. Generating fallback cartelas.")
            self._generate_fallback_cartelas()
    
    def _process_cartelas_data(self, cartelas_data: List[Dict]):
        """Process loaded cartelas data"""
        self.cartelas = []
        self.cartelas_by_id = {}
        
        for idx, cartela in enumerate(cartelas_data):
            # Get cartela ID (use index if not provided)
            cartela_id = cartela.get('id') or cartela.get('cartela_id') or (idx + 1)
            
            # Get grid
            grid = cartela.get('grid')
            
            # Validate grid
            if not grid or not self._validate_cartela_grid(grid):
                logger.warning(f"Cartela {cartela_id} has invalid grid, skipping")
                continue
            
            # Ensure grid is properly formatted
            if len(grid) != 5:
                logger.warning(f"Cartela {cartela_id} has invalid grid size: {len(grid)}")
                continue
            
            cartela_obj = {
                'id': cartela_id,
                'grid': grid
            }
            
            self.cartelas.append(cartela_obj)
            self.cartelas_by_id[cartela_id] = cartela_obj
        
        # Sort by ID
        self.cartelas.sort(key=lambda x: x['id'])
    
    def _validate_cartela_grid(self, grid: List[List[int]]) -> bool:
        """
        Validate a cartela grid (5x5 with BINGO rules)
        
        Args:
            grid: 5x5 grid of numbers
        
        Returns:
            bool: True if grid is valid
        """
        # Check grid size
        if len(grid) != 5:
            return False
        
        for col in range(5):
            if len(grid[col]) != 5:
                return False
        
        # Check center is free space (0)
        if grid[2][2] != 0:
            return False
        
        # Check column ranges
        for col in range(5):
            min_val, max_val = self.COLUMN_RANGES[col]
            for row in range(5):
                if row == 2 and col == 2:
                    continue
                value = grid[col][row]
                if value < min_val or value > max_val:
                    logger.warning(f"Invalid value {value} at position ({col},{row})")
                    return False
        
        return True
    
    def _generate_fallback_cartelas(self):
        """Generate random cartelas as fallback if JSON file not found"""
        self.cartelas = []
        self.cartelas_by_id = {}
        
        for cartela_id in range(1, self.total_cartelas + 1):
            grid = self._generate_random_cartela_grid()
            
            cartela_obj = {
                'id': cartela_id,
                'grid': grid
            }
            
            self.cartelas.append(cartela_obj)
            self.cartelas_by_id[cartela_id] = cartela_obj
        
        logger.info(f"Generated {len(self.cartelas)} fallback cartelas")
    
    def _generate_random_cartela_grid(self) -> List[List[int]]:
        """
        Generate a random valid 5x5 bingo cartela grid
        
        Returns:
            list: 5x5 grid with numbers
        """
        grid = []
        
        for col in range(5):
            col_numbers = []
            min_val, max_val = self.COLUMN_RANGES[col]
            
            # Generate 5 unique numbers for this column
            available = list(range(min_val, max_val + 1))
            random.shuffle(available)
            
            for row in range(5):
                if row == 2 and col == 2:
                    # Free space (center)
                    col_numbers.append(0)
                else:
                    col_numbers.append(available.pop())
            
            grid.append(col_numbers)
        
        return grid
    
    # ==================== ROUND MANAGEMENT ====================
    
    def reset_round(self, round_id: Optional[int] = None):
        """
        Reset cartela selections for a new round
        
        Args:
            round_id: int - New round ID (optional)
        """
        with self._lock:
            self.taken_by.clear()
            self.selected_by.clear()
            self.current_round_id = round_id
            logger.info(f"Cartela manager reset for round {round_id}")
    
    def set_round_id(self, round_id: int):
        """Set current round ID"""
        self.current_round_id = round_id
    
    # ==================== CARTELA SELECTION ====================
    
    def take_cartela(self, cartela_id: int, user_id: int) -> bool:
        """
        Mark a cartela as taken by a user.
        
        Args:
            cartela_id: int - Cartela ID (1-1000)
            user_id: int - User's Telegram ID
        
        Returns:
            bool: True if successful, False if already taken
        """
        with self._lock:
            if cartela_id in self.taken_by:
                logger.debug(f"Cartela {cartela_id} already taken by user {self.taken_by[cartela_id]}")
                return False
            
            self.taken_by[cartela_id] = user_id
            logger.debug(f"Cartela {cartela_id} taken by user {user_id}")
            return True
    
    def select_cartela(self, user_id: int, cartela_id: int) -> bool:
        """
        Add cartela to user's personal selection (after payment).
        
        Args:
            user_id: int - User's Telegram ID
            cartela_id: int - Cartela ID
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            if user_id not in self.selected_by:
                self.selected_by[user_id] = set()
            
            self.selected_by[user_id].add(cartela_id)
            logger.debug(f"User {user_id} selected cartela {cartela_id}")
            return True
    
    def unselect_cartela(self, user_id: int, cartela_id: int) -> bool:
        """
        Remove cartela from user's selection (if they change mind).
        
        Args:
            user_id: int - User's Telegram ID
            cartela_id: int - Cartela ID
        
        Returns:
            bool: True if successful
        """
        with self._lock:
            if user_id not in self.selected_by:
                return False
            
            if cartela_id not in self.selected_by[user_id]:
                return False
            
            self.selected_by[user_id].remove(cartela_id)
            
            # Also free the taken status
            if cartela_id in self.taken_by and self.taken_by[cartela_id] == user_id:
                del self.taken_by[cartela_id]
            
            logger.debug(f"User {user_id} unselected cartela {cartela_id}")
            return True
    
    def bulk_select_cartelas(self, user_id: int, cartela_ids: List[int]) -> Dict[str, Any]:
        """
        Select multiple cartelas at once.
        
        Args:
            user_id: int - User's Telegram ID
            cartela_ids: list - List of cartela IDs
        
        Returns:
            dict: Selection result with success and failed lists
        """
        result = {
            'success': [],
            'failed': [],
            'errors': []
        }
        
        for cartela_id in cartela_ids:
            # Check if cartela exists
            if not self.is_valid_cartela(cartela_id):
                result['failed'].append({'cartela_id': cartela_id, 'reason': 'invalid'})
                continue
            
            # Check if already taken
            if not self.is_cartela_available(cartela_id):
                owner = self.get_cartela_owner(cartela_id)
                result['failed'].append({'cartela_id': cartela_id, 'reason': 'taken', 'owner': owner})
                continue
            
            # Check if user already selected this
            if self.is_cartela_mine(user_id, cartela_id):
                result['failed'].append({'cartela_id': cartela_id, 'reason': 'already_selected'})
                continue
            
            # Take and select
            self.take_cartela(cartela_id, user_id)
            self.select_cartela(user_id, cartela_id)
            result['success'].append(cartela_id)
        
        return result
    
    # ==================== QUERY METHODS ====================
    
    def get_user_cartelas(self, user_id: int) -> Set[int]:
        """
        Get all cartela IDs selected by a user.
        
        Args:
            user_id: int - User's Telegram ID
        
        Returns:
            set: Set of cartela IDs
        """
        return self.selected_by.get(user_id, set())
    
    def get_user_cartelas_with_grids(self, user_id: int) -> List[Dict]:
        """
        Get all cartelas selected by a user with their grids.
        
        Args:
            user_id: int - User's Telegram ID
        
        Returns:
            list: List of cartela objects with grids
        """
        cartela_ids = self.get_user_cartelas(user_id)
        cartelas = []
        
        for cartela_id in cartela_ids:
            cartela = self.get_cartela(cartela_id)
            if cartela:
                cartelas.append(cartela)
        
        return cartelas
    
    def get_all_selected_cartelas(self) -> Dict[int, int]:
        """
        Get all selected cartelas with their owners.
        
        Returns:
            dict: {cartela_id: user_id}
        """
        return self.taken_by.copy()
    
    def is_cartela_available(self, cartela_id: int) -> bool:
        """
        Check if a cartela is available (not taken by anyone).
        
        Args:
            cartela_id: int - Cartela ID
        
        Returns:
            bool: True if available
        """
        return cartela_id not in self.taken_by
    
    def is_cartela_mine(self, user_id: int, cartela_id: int) -> bool:
        """
        Check if a cartela belongs to the user.
        
        Args:
            user_id: int - User's Telegram ID
            cartela_id: int - Cartela ID
        
        Returns:
            bool: True if cartela belongs to user
        """
        return user_id in self.selected_by and cartela_id in self.selected_by[user_id]
    
    def get_cartela_owner(self, cartela_id: int) -> Optional[int]:
        """
        Get the user ID who owns a cartela.
        
        Args:
            cartela_id: int - Cartela ID
        
        Returns:
            int: User ID or None if not taken
        """
        return self.taken_by.get(cartela_id)
    
    def get_cartela(self, cartela_id: int) -> Optional[Dict]:
        """
        Get cartela by ID.
        
        Args:
            cartela_id: int - Cartela ID
        
        Returns:
            dict: Cartela object or None if not found
        """
        return self.cartelas_by_id.get(cartela_id)
    
    def get_cartela_grid(self, cartela_id: int) -> Optional[List[List[int]]]:
        """
        Get the 5x5 grid for a cartela.
        
        Args:
            cartela_id: int - Cartela ID
        
        Returns:
            list: 5x5 grid or None if not found
        """
        cartela = self.get_cartela(cartela_id)
        return cartela.get('grid') if cartela else None
    
    def is_valid_cartela(self, cartela_id: int) -> bool:
        """
        Check if cartela ID is valid.
        
        Args:
            cartela_id: int - Cartela ID
        
        Returns:
            bool: True if cartela exists
        """
        return cartela_id in self.cartelas_by_id
    
    def get_available_cartelas(self) -> List[int]:
        """
        Get list of all cartela IDs that are not taken.
        
        Returns:
            list: List of available cartela IDs
        """
        return [cid for cid in self.cartelas_by_id.keys() if cid not in self.taken_by]
    
    def get_taken_cartelas(self) -> List[int]:
        """
        Get list of all taken cartela IDs.
        
        Returns:
            list: List of taken cartela IDs
        """
        return list(self.taken_by.keys())
    
    # ==================== COUNT METHODS ====================
    
    def get_selected_count(self) -> int:
        """
        Get total number of selected cartelas in current round.
        
        Returns:
            int: Number of selected cartelas
        """
        return len(self.taken_by)
    
    def get_user_selected_count(self, user_id: int) -> int:
        """
        Get number of cartelas selected by a specific user.
        
        Args:
            user_id: int - User's Telegram ID
        
        Returns:
            int: Number of cartelas selected by user
        """
        return len(self.selected_by.get(user_id, set()))
    
    def get_total_cartelas(self) -> int:
        """
        Get total number of cartelas.
        
        Returns:
            int: Total cartelas count
        """
        return len(self.cartelas)
    
    def get_available_count(self) -> int:
        """
        Get number of available (not taken) cartelas.
        
        Returns:
            int: Number of available cartelas
        """
        return self.get_total_cartelas() - self.get_selected_count()
    
    # ==================== CARTELA INFO METHODS ====================
    
    def get_all_cartelas(self, include_taken_status: bool = False) -> List[Dict]:
        """
        Get all cartelas.
        
        Args:
            include_taken_status: bool - Whether to include taken status
        
        Returns:
            list: List of cartela objects
        """
        if include_taken_status:
            cartelas_with_status = []
            for cartela in self.cartelas:
                cartela_copy = cartela.copy()
                cartela_copy['is_taken'] = cartela['id'] in self.taken_by
                cartela_copy['taken_by'] = self.taken_by.get(cartela['id'])
                cartelas_with_status.append(cartela_copy)
            return cartelas_with_status
        
        return self.cartelas.copy()
    
    def get_cartelas_batch(self, start: int, limit: int, include_taken_status: bool = False) -> List[Dict]:
        """
        Get a batch of cartelas for pagination.
        
        Args:
            start: int - Start index (0-based)
            limit: int - Number of cartelas to return
            include_taken_status: bool - Whether to include taken status
        
        Returns:
            list: List of cartela objects
        """
        end = min(start + limit, self.get_total_cartelas())
        batch = self.cartelas[start:end]
        
        if include_taken_status:
            for cartela in batch:
                cartela['is_taken'] = cartela['id'] in self.taken_by
                cartela['taken_by'] = self.taken_by.get(cartela['id'])
        
        return batch
    
    def get_cartela_with_status(self, cartela_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
        """
        Get cartela with its current status.
        
        Args:
            cartela_id: int - Cartela ID
            user_id: int - User ID to check if cartela belongs to them
        
        Returns:
            dict: Cartela object with status fields
        """
        cartela = self.get_cartela(cartela_id)
        if not cartela:
            return None
        
        cartela_copy = cartela.copy()
        cartela_copy['is_taken'] = cartela_id in self.taken_by
        cartela_copy['taken_by'] = self.taken_by.get(cartela_id)
        
        if user_id:
            cartela_copy['is_mine'] = self.is_cartela_mine(user_id, cartela_id)
        else:
            cartela_copy['is_mine'] = False
        
        return cartela_copy
    
    # ==================== VALIDATION METHODS ====================
    
    def validate_selection(self, user_id: int, cartela_ids: List[int]) -> Dict[str, Any]:
        """
        Validate a list of cartela selections before processing.
        
        Args:
            user_id: int - User's Telegram ID
            cartela_ids: list - List of cartela IDs to validate
        
        Returns:
            dict: Validation result with errors if any
        """
        max_cartelas = getattr(config, 'MAX_CARTELAS', 4)
        
        # Check max cartelas limit
        if len(cartela_ids) > max_cartelas:
            return {
                'valid': False,
                'error': f'Maximum {max_cartelas} cartelas allowed per player',
                'code': 'max_limit_exceeded'
            }
        
        # Check for duplicates
        if len(cartela_ids) != len(set(cartela_ids)):
            return {
                'valid': False,
                'error': 'Duplicate cartelas selected',
                'code': 'duplicate_selection'
            }
        
        # Check each cartela
        invalid_ids = []
        taken_ids = []
        mine_ids = []
        
        for cartela_id in cartela_ids:
            if not self.is_valid_cartela(cartela_id):
                invalid_ids.append(cartela_id)
            elif not self.is_cartela_available(cartela_id):
                taken_ids.append(cartela_id)
            elif self.is_cartela_mine(user_id, cartela_id):
                mine_ids.append(cartela_id)
        
        if invalid_ids:
            return {
                'valid': False,
                'error': f'Invalid cartela IDs: {invalid_ids}',
                'code': 'invalid_cartelas',
                'invalid_ids': invalid_ids
            }
        
        if taken_ids:
            return {
                'valid': False,
                'error': f'Cartelas already taken: {taken_ids}',
                'code': 'cartelas_taken',
                'taken_ids': taken_ids
            }
        
        if mine_ids:
            return {
                'valid': False,
                'error': f'You already selected: {mine_ids}',
                'code': 'already_selected',
                'mine_ids': mine_ids
            }
        
        return {'valid': True}
    
    # ==================== CARTELA GENERATION ====================
    
    def regenerate_cartela(self, cartela_id: int) -> Optional[Dict]:
        """
        Regenerate a specific cartela (admin function).
        
        Args:
            cartela_id: int - Cartela ID
        
        Returns:
            dict: New cartela object or None
        """
        if not (1 <= cartela_id <= self.total_cartelas):
            return None
        
        new_grid = self._generate_random_cartela_grid()
        
        new_cartela = {
            'id': cartela_id,
            'grid': new_grid
        }
        
        # Update in memory
        for idx, cartela in enumerate(self.cartelas):
            if cartela['id'] == cartela_id:
                self.cartelas[idx] = new_cartela
                break
        
        self.cartelas_by_id[cartela_id] = new_cartela
        
        logger.info(f"Cartela {cartela_id} regenerated")
        return new_cartela
    
    # ==================== STATISTICS ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cartela statistics for the current round.
        
        Returns:
            dict: Statistics data
        """
        total = self.get_total_cartelas()
        selected = self.get_selected_count()
        available = self.get_available_count()
        unique_players = len(self.selected_by)
        
        # Calculate player distribution
        player_cartela_counts = {}
        for user_id, cartelas in self.selected_by.items():
            player_cartela_counts[user_id] = len(cartelas)
        
        return {
            'total_cartelas': total,
            'selected_count': selected,
            'available_count': available,
            'selection_percentage': (selected / total * 100) if total > 0 else 0,
            'unique_players': unique_players,
            'average_per_player': (selected / unique_players) if unique_players > 0 else 0,
            'player_breakdown': player_cartela_counts,
            'round_id': self.current_round_id
        }


# ==================== SINGLETON INSTANCE ====================

# Create global instance for use throughout the application
cartela_manager = CartelaManager()


# ==================== EXPORTS ====================

__all__ = [
    'CartelaManager',
    'cartela_manager',
]