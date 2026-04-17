# telegram-bot/bot/db/repository/cartela_repo.py
# Estif Bingo 24/7 - Cartela Repository
# Handles all database operations for bingo cartelas (cards)

import json
import logging
import os
import random
from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple
from bot.db.database import Database

logger = logging.getLogger(__name__)


class CartelaRepository:
    """Repository for cartela database operations"""

    # ==================== CARTELA LOADING & INITIALIZATION ====================

    @staticmethod
    async def initialize_cartelas(json_path: str = "data/cartelas_1000.json") -> int:
        """
        Initialize cartelas from JSON file into database
        Only runs if cartelas table is empty
        
        Args:
            json_path: str - Path to cartelas JSON file
        
        Returns:
            int: Number of cartelas loaded
        """
        # Check if cartelas already exist
        count = await CartelaRepository.get_count()
        if count > 0:
            logger.info(f"Cartelas already exist in database: {count} cartelas")
            return count
        
        # Load from JSON file
        try:
            # Try multiple possible paths
            possible_paths = [
                json_path,
                "telegram-bot/data/cartelas_1000.json",
                "../data/cartelas_1000.json",
                "../../data/cartelas_1000.json",
                os.path.join(os.path.dirname(__file__), "../../data/cartelas_1000.json")
            ]
            
            cartelas_data = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        cartelas_data = json.load(f)
                    logger.info(f"Loaded cartelas from {path}")
                    break
            
            if not cartelas_data:
                logger.warning("No cartelas JSON file found. Generating random cartelas.")
                cartelas_data = CartelaRepository._generate_random_cartelas(1000)
            
            # Insert into database
            inserted_count = 0
            for cartela in cartelas_data:
                cartela_id = cartela.get('id') or cartela.get('cartela_id')
                grid = cartela.get('grid')
                
                if not grid:
                    continue
                
                await CartelaRepository.create({
                    'id': cartela_id,
                    'grid': grid,
                    'is_active': True
                })
                inserted_count += 1
            
            logger.info(f"Loaded {inserted_count} cartelas into database")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Failed to initialize cartelas: {e}")
            # Generate fallback cartelas
            fallback_count = await CartelaRepository._generate_fallback_cartelas()
            return fallback_count

    @staticmethod
    def _generate_random_cartelas(count: int = 1000) -> List[Dict[str, Any]]:
        """
        Generate random cartelas for fallback
        
        Args:
            count: int - Number of cartelas to generate
        
        Returns:
            list: List of cartela dictionaries
        """
        cartelas = []
        
        # Column ranges: B(1-15), I(16-30), N(31-45), G(46-60), O(61-75)
        column_ranges = [
            (1, 15),    # B
            (16, 30),   # I
            (31, 45),   # N
            (46, 60),   # G
            (61, 75)    # O
        ]
        
        for cartela_id in range(1, count + 1):
            grid = []
            
            for col in range(5):
                col_numbers = []
                min_val, max_val = column_ranges[col]
                
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
            
            cartelas.append({
                'id': cartela_id,
                'grid': grid
            })
        
        return cartelas

    @staticmethod
    async def _generate_fallback_cartelas() -> int:
        """
        Generate and insert fallback cartelas if JSON file not found
        
        Returns:
            int: Number of cartelas generated
        """
        cartelas = CartelaRepository._generate_random_cartelas(1000)
        
        inserted_count = 0
        for cartela in cartelas:
            await CartelaRepository.create({
                'id': cartela['id'],
                'grid': cartela['grid'],
                'is_active': True
            })
            inserted_count += 1
        
        logger.info(f"Generated {inserted_count} fallback cartelas")
        return inserted_count

    # ==================== CARTELA CRUD ====================

    @staticmethod
    async def create(cartela_data: Dict[str, Any]) -> int:
        """
        Create a new cartela record
        
        Args:
            cartela_data: Dictionary containing:
                - id: int (cartela number)
                - grid: list (5x5 grid)
                - is_active: bool (default True)
        
        Returns:
            int: Cartela ID
        """
        query = """
            INSERT INTO cartelas (id, grid, is_active, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (id) DO UPDATE
            SET grid = EXCLUDED.grid, is_active = EXCLUDED.is_active, updated_at = NOW()
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            cartela_data['id'],
            json.dumps(cartela_data['grid']),
            cartela_data.get('is_active', True)
        )
        
        cartela_id = result['id'] if result else None
        
        if cartela_id:
            logger.debug(f"Cartela #{cartela_id} created/updated")
        
        return cartela_id

    @staticmethod
    async def get_by_id(cartela_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cartela by ID
        
        Args:
            cartela_id: int - Cartela number (1-1000)
        
        Returns:
            dict: Cartela data or None if not found
        """
        query = """
            SELECT id, grid, is_active, created_at, updated_at
            FROM cartelas
            WHERE id = $1
        """
        
        result = await Database.fetch_one(query, cartela_id)
        
        if result:
            cartela_dict = dict(result)
            cartela_dict['grid'] = json.loads(cartela_dict['grid']) if cartela_dict.get('grid') else None
            return cartela_dict
        
        return None

    @staticmethod
    async def get_all(
        limit: int = 1000,
        offset: int = 0,
        only_active: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all cartelas with pagination
        
        Args:
            limit: int - Maximum number of records
            offset: int - Pagination offset
            only_active: bool - Only return active cartelas
        
        Returns:
            list: List of cartelas
        """
        query = """
            SELECT id, grid, is_active, created_at
            FROM cartelas
            WHERE 1=1
        """
        params = []
        param_index = 1
        
        if only_active:
            query += f" AND is_active = TRUE"
        
        query += f" ORDER BY id ASC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.append(limit)
        params.append(offset)
        
        results = await Database.fetch_all(query, *params)
        
        cartelas = []
        for row in results:
            cartela_dict = dict(row)
            cartela_dict['grid'] = json.loads(cartela_dict['grid']) if cartela_dict.get('grid') else None
            cartelas.append(cartela_dict)
        
        return cartelas

    @staticmethod
    async def get_count(only_active: bool = True) -> int:
        """
        Get total number of cartelas
        
        Args:
            only_active: bool - Only count active cartelas
        
        Returns:
            int: Number of cartelas
        """
        if only_active:
            query = "SELECT COUNT(*) as count FROM cartelas WHERE is_active = TRUE"
        else:
            query = "SELECT COUNT(*) as count FROM cartelas"
        
        result = await Database.fetch_one(query)
        return result['count'] if result else 0

    @staticmethod
    async def get_random_cartelas(count: int = 1) -> List[Dict[str, Any]]:
        """
        Get random cartelas
        
        Args:
            count: int - Number of random cartelas to retrieve
        
        Returns:
            list: List of random cartelas
        """
        query = """
            SELECT id, grid FROM cartelas
            WHERE is_active = TRUE
            ORDER BY RANDOM()
            LIMIT $1
        """
        
        results = await Database.fetch_all(query, count)
        
        cartelas = []
        for row in results:
            cartela_dict = dict(row)
            cartela_dict['grid'] = json.loads(cartela_dict['grid']) if cartela_dict.get('grid') else None
            cartelas.append(cartela_dict)
        
        return cartelas

    @staticmethod
    async def get_cartelas_batch(
        cartela_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Get multiple cartelas by IDs
        
        Args:
            cartela_ids: list - List of cartela IDs
        
        Returns:
            list: List of cartelas
        """
        if not cartela_ids:
            return []
        
        placeholders = ','.join(f'${i+1}' for i in range(len(cartela_ids)))
        query = f"""
            SELECT id, grid FROM cartelas
            WHERE id IN ({placeholders}) AND is_active = TRUE
            ORDER BY id ASC
        """
        
        results = await Database.fetch_all(query, *cartela_ids)
        
        cartelas = []
        for row in results:
            cartela_dict = dict(row)
            cartela_dict['grid'] = json.loads(cartela_dict['grid']) if cartela_dict.get('grid') else None
            cartelas.append(cartela_dict)
        
        return cartelas

    # ==================== CARTELA VALIDATION ====================

    @staticmethod
    async def is_valid_cartela(cartela_id: int) -> bool:
        """
        Check if cartela ID is valid and active
        
        Args:
            cartela_id: int - Cartela ID
        
        Returns:
            bool: True if cartela exists and is active
        """
        query = """
            SELECT id FROM cartelas
            WHERE id = $1 AND is_active = TRUE
        """
        
        result = await Database.fetch_one(query, cartela_id)
        return result is not None

    @staticmethod
    async def validate_cartela_grid(grid: List[List[int]]) -> bool:
        """
        Validate cartela grid format
        
        Args:
            grid: list - 5x5 grid
        
        Returns:
            bool: True if grid is valid
        """
        # Check if grid is 5x5
        if len(grid) != 5:
            return False
        
        for col in range(5):
            if len(grid[col]) != 5:
                return False
        
        # Check center is free space (0)
        if grid[2][2] != 0:
            return False
        
        # Check column ranges
        column_ranges = [
            (1, 15),    # B
            (16, 30),   # I
            (31, 45),   # N
            (46, 60),   # G
            (61, 75)    # O
        ]
        
        for col in range(5):
            min_val, max_val = column_ranges[col]
            for row in range(5):
                if row == 2 and col == 2:
                    continue
                value = grid[col][row]
                if value < min_val or value > max_val:
                    return False
        
        return True

    # ==================== CARTELA STATISTICS ====================

    @staticmethod
    async def get_cartela_usage_stats() -> Dict[str, Any]:
        """
        Get cartela usage statistics from game rounds
        
        Returns:
            dict: Cartela usage statistics
        """
        query = """
            SELECT 
                cartela_id,
                COUNT(*) as times_selected,
                COUNT(DISTINCT round_id) as rounds_played
            FROM round_selections
            GROUP BY cartela_id
            ORDER BY times_selected DESC
            LIMIT 100
        """
        
        results = await Database.fetch_all(query)
        
        usage_stats = {
            'most_popular': [],
            'least_popular': [],
            'total_selections': 0,
            'unique_cartelas_used': 0
        }
        
        if results:
            usage_stats['most_popular'] = [dict(row) for row in results[:10]]
            
            # Get least popular
            least_query = """
                SELECT 
                    cartela_id,
                    COUNT(*) as times_selected
                FROM round_selections
                GROUP BY cartela_id
                ORDER BY times_selected ASC
                LIMIT 10
            """
            least_results = await Database.fetch_all(least_query)
            usage_stats['least_popular'] = [dict(row) for row in least_results]
            
            # Get totals
            total_query = "SELECT COUNT(*) as total FROM round_selections"
            total_result = await Database.fetch_one(total_query)
            usage_stats['total_selections'] = total_result['total'] if total_result else 0
            
            unique_query = "SELECT COUNT(DISTINCT cartela_id) as unique FROM round_selections"
            unique_result = await Database.fetch_one(unique_query)
            usage_stats['unique_cartelas_used'] = unique_result['unique'] if unique_result else 0
        
        return usage_stats

    @staticmethod
    async def get_unused_cartelas() -> List[int]:
        """
        Get cartelas that have never been selected in any game
        
        Returns:
            list: List of unused cartela IDs
        """
        query = """
            SELECT id FROM cartelas
            WHERE is_active = TRUE
            AND id NOT IN (
                SELECT DISTINCT cartela_id FROM round_selections
            )
            ORDER BY id ASC
        """
        
        results = await Database.fetch_all(query)
        return [row['id'] for row in results]

    # ==================== CARTELA MAINTENANCE ====================

    @staticmethod
    async def deactivate_cartela(cartela_id: int) -> bool:
        """
        Deactivate a cartela (make it unavailable for selection)
        
        Args:
            cartela_id: int - Cartela ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE cartelas
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = $1 AND is_active = TRUE
            RETURNING id
        """
        
        result = await Database.fetch_one(query, cartela_id)
        
        if result:
            logger.info(f"Cartela #{cartela_id} deactivated")
            return True
        
        return False

    @staticmethod
    async def activate_cartela(cartela_id: int) -> bool:
        """
        Activate a cartela (make it available for selection)
        
        Args:
            cartela_id: int - Cartela ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE cartelas
            SET is_active = TRUE, updated_at = NOW()
            WHERE id = $1 AND is_active = FALSE
            RETURNING id
        """
        
        result = await Database.fetch_one(query, cartela_id)
        
        if result:
            logger.info(f"Cartela #{cartela_id} activated")
            return True
        
        return False

    @staticmethod
    async def bulk_activate_cartelas(cartela_ids: List[int]) -> int:
        """
        Activate multiple cartelas
        
        Args:
            cartela_ids: list - List of cartela IDs
        
        Returns:
            int: Number of cartelas activated
        """
        if not cartela_ids:
            return 0
        
        placeholders = ','.join(f'${i+1}' for i in range(len(cartela_ids)))
        query = f"""
            UPDATE cartelas
            SET is_active = TRUE, updated_at = NOW()
            WHERE id IN ({placeholders}) AND is_active = FALSE
            RETURNING id
        """
        
        results = await Database.fetch_all(query, *cartela_ids)
        activated_count = len(results)
        
        if activated_count > 0:
            logger.info(f"Activated {activated_count} cartelas")
        
        return activated_count

    @staticmethod
    async def bulk_deactivate_cartelas(cartela_ids: List[int]) -> int:
        """
        Deactivate multiple cartelas
        
        Args:
            cartela_ids: list - List of cartela IDs
        
        Returns:
            int: Number of cartelas deactivated
        """
        if not cartela_ids:
            return 0
        
        placeholders = ','.join(f'${i+1}' for i in range(len(cartela_ids)))
        query = f"""
            UPDATE cartelas
            SET is_active = FALSE, updated_at = NOW()
            WHERE id IN ({placeholders}) AND is_active = TRUE
            RETURNING id
        """
        
        results = await Database.fetch_all(query, *cartela_ids)
        deactivated_count = len(results)
        
        if deactivated_count > 0:
            logger.info(f"Deactivated {deactivated_count} cartelas")
        
        return deactivated_count

    # ==================== CARTELA VALIDATION FOR GAME ====================

    @staticmethod
    async def validate_selected_cartelas(
        cartela_ids: List[int],
        max_cartelas: int = 4
    ) -> Tuple[bool, List[int], str]:
        """
        Validate a list of selected cartelas for a game
        
        Args:
            cartela_ids: list - List of cartela IDs selected by user
            max_cartelas: int - Maximum allowed cartelas per player
        
        Returns:
            tuple: (is_valid, valid_ids, error_message)
        """
        if not cartela_ids:
            return False, [], "No cartelas selected"
        
        if len(cartela_ids) > max_cartelas:
            return False, [], f"Maximum {max_cartelas} cartelas allowed"
        
        if len(cartela_ids) != len(set(cartela_ids)):
            return False, [], "Duplicate cartelas selected"
        
        # Check each cartela exists and is active
        valid_ids = []
        for cartela_id in cartela_ids:
            if await CartelaRepository.is_valid_cartela(cartela_id):
                valid_ids.append(cartela_id)
            else:
                return False, [], f"Cartela #{cartela_id} is invalid or inactive"
        
        return True, valid_ids, ""

    @staticmethod
    async def get_cartela_grids(cartela_ids: List[int]) -> List[List[List[int]]]:
        """
        Get grids for multiple cartelas
        
        Args:
            cartela_ids: list - List of cartela IDs
        
        Returns:
            list: List of 5x5 grids
        """
        cartelas = await CartelaRepository.get_cartelas_batch(cartela_ids)
        return [cartela['grid'] for cartela in cartelas if cartela.get('grid')]

    # ==================== CARTELA CACHE ====================

    _cache = {}
    _cache_timestamp = None
    _cache_duration = 300  # 5 minutes

    @staticmethod
    async def get_cached_cartelas(force_refresh: bool = False) -> Dict[int, Dict[str, Any]]:
        """
        Get cartelas from cache (for performance)
        
        Args:
            force_refresh: bool - Force refresh cache
        
        Returns:
            dict: Dictionary of cartela_id -> cartela data
        """
        now = datetime.utcnow().timestamp()
        
        if (not force_refresh and 
            CartelaRepository._cache_timestamp and 
            now - CartelaRepository._cache_timestamp < CartelaRepository._cache_duration):
            return CartelaRepository._cache
        
        # Refresh cache
        cartelas = await CartelaRepository.get_all(limit=10000)
        
        CartelaRepository._cache = {}
        for cartela in cartelas:
            CartelaRepository._cache[cartela['id']] = cartela
        
        CartelaRepository._cache_timestamp = now
        
        logger.debug(f"Cartela cache refreshed: {len(CartelaRepository._cache)} cartelas")
        
        return CartelaRepository._cache

    @staticmethod
    async def clear_cache() -> None:
        """Clear cartela cache"""
        CartelaRepository._cache = {}
        CartelaRepository._cache_timestamp = None
        logger.debug("Cartela cache cleared")


# ==================== IN-MEMORY CARTELA MANAGER FOR ACTIVE GAME ====================

class ActiveGameCartelaManager:
    """
    In-memory manager for tracking cartela selections in the current active game.
    This is separate from the database repository for performance.
    """
    
    def __init__(self):
        self.selected_cartelas: Dict[int, int] = {}  # cartela_id -> user_id
        self.user_selections: Dict[int, Set[int]] = {}  # user_id -> set of cartela_ids
        self.round_id: Optional[int] = None
    
    def reset(self, round_id: Optional[int] = None):
        """Reset selections for a new round"""
        self.selected_cartelas.clear()
        self.user_selections.clear()
        self.round_id = round_id
    
    def take_cartela(self, cartela_id: int, user_id: int) -> bool:
        """Mark a cartela as taken by a user"""
        if cartela_id in self.selected_cartelas:
            return False
        self.selected_cartelas[cartela_id] = user_id
        return True
    
    def select_cartela(self, user_id: int, cartela_id: int) -> bool:
        """Add cartela to user's selection"""
        if user_id not in self.user_selections:
            self.user_selections[user_id] = set()
        self.user_selections[user_id].add(cartela_id)
        return True
    
    def unselect_cartela(self, user_id: int, cartela_id: int) -> bool:
        """Remove cartela from user's selection"""
        if user_id in self.user_selections and cartela_id in self.user_selections[user_id]:
            self.user_selections[user_id].remove(cartela_id)
            if cartela_id in self.selected_cartelas:
                del self.selected_cartelas[cartela_id]
            return True
        return False
    
    def get_user_cartelas(self, user_id: int) -> Set[int]:
        """Get all cartela IDs selected by a user"""
        return self.user_selections.get(user_id, set())
    
    def is_cartela_available(self, cartela_id: int) -> bool:
        """Check if a cartela is not taken by anyone"""
        return cartela_id not in self.selected_cartelas
    
    def is_cartela_mine(self, user_id: int, cartela_id: int) -> bool:
        """Check if a cartela belongs to the user"""
        return user_id in self.user_selections and cartela_id in self.user_selections[user_id]
    
    def get_cartela_owner(self, cartela_id: int) -> Optional[int]:
        """Get the user ID who owns this cartela"""
        return self.selected_cartelas.get(cartela_id)
    
    def get_available_cartelas(self, total_cartelas: int = 1000) -> List[int]:
        """Get list of all cartela IDs that are not taken"""
        return [cid for cid in range(1, total_cartelas + 1) if cid not in self.selected_cartelas]
    
    def get_selected_count(self) -> int:
        """Get total number of selected cartelas in current round"""
        return len(self.selected_cartelas)
    
    def get_user_selected_count(self, user_id: int) -> int:
        """Get number of cartelas selected by a specific user"""
        return len(self.user_selections.get(user_id, set()))
    
    def get_all_selected_cartelas(self) -> Dict[int, int]:
        """Return {cartela_id: user_id} for all selected cartelas"""
        return self.selected_cartelas.copy()


# Global instance for active game
active_game_cartelas = ActiveGameCartelaManager()