# telegram-bot/bot/db/repository/game_repo.py
# Estif Bingo 24/7 - Game Repository
# Handles all database operations for game rounds, cartelas, and game statistics

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bot.db.database import Database

logger = logging.getLogger(__name__)


class GameRepository:
    """Repository for game-related database operations"""

    # ==================== GAME ROUNDS ====================

    @staticmethod
    async def create_round(round_data: Dict[str, Any]) -> int:
        """
        Create a new game round
        
        Args:
            round_data: Dictionary containing:
                - round_number: int
                - status: str (selection, drawing, ended)
                - start_time: datetime
                - selection_end_time: datetime (optional)
                - end_time: datetime (optional)
                - total_cartelas: int (optional)
                - total_players: int (optional)
                - winners: list (optional)
                - prize_pool: float (optional)
        
        Returns:
            int: Round ID
        """
        query = """
            INSERT INTO game_rounds (
                round_number, status, start_time, selection_end_time,
                end_time, total_cartelas, total_players, winners,
                prize_pool, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            round_data['round_number'],
            round_data.get('status', 'selection'),
            round_data.get('start_time', datetime.utcnow()),
            round_data.get('selection_end_time'),
            round_data.get('end_time'),
            round_data.get('total_cartelas', 0),
            round_data.get('total_players', 0),
            round_data.get('winners'),
            round_data.get('prize_pool', 0)
        )
        
        round_id = result['id'] if result else None
        logger.info(f"Created game round #{round_id} (Round {round_data['round_number']})")
        
        return round_id

    @staticmethod
    async def get_round(round_id: int) -> Optional[Dict[str, Any]]:
        """
        Get game round by ID
        
        Args:
            round_id: int - Round ID
        
        Returns:
            dict: Round data or None if not found
        """
        query = """
            SELECT * FROM game_rounds
            WHERE id = $1
        """
        
        result = await Database.fetch_one(query, round_id)
        return dict(result) if result else None

    @staticmethod
    async def get_current_round() -> Optional[Dict[str, Any]]:
        """
        Get current active game round
        
        Returns:
            dict: Current round data or None if no active round
        """
        query = """
            SELECT * FROM game_rounds
            WHERE status IN ('selection', 'drawing')
            ORDER BY id DESC
            LIMIT 1
        """
        
        result = await Database.fetch_one(query)
        return dict(result) if result else None

    @staticmethod
    async def get_current_round_number() -> Optional[int]:
        """
        Get current round number
        
        Returns:
            int: Current round number or None
        """
        query = """
            SELECT round_number FROM game_rounds
            WHERE status IN ('selection', 'drawing')
            ORDER BY id DESC
            LIMIT 1
        """
        
        result = await Database.fetch_one(query)
        return result['round_number'] if result else None

    @staticmethod
    async def update_round(round_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update game round
        
        Args:
            round_id: int - Round ID
            updates: dict - Fields to update
        
        Returns:
            bool: True if successful
        """
        set_clauses = []
        params = []
        param_index = 2
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ${param_index}")
            params.append(value)
            param_index += 1
        
        params.insert(0, round_id)
        
        query = f"""
            UPDATE game_rounds
            SET {', '.join(set_clauses)}, updated_at = NOW()
            WHERE id = $1
            RETURNING id
        """
        
        result = await Database.fetch_one(query, *params)
        
        if result:
            logger.info(f"Updated game round #{round_id}")
            return True
        
        return False

    @staticmethod
    async def end_round(round_id: int, winners: List[Dict], prize_pool: float) -> bool:
        """
        End a game round with winners
        
        Args:
            round_id: int - Round ID
            winners: list - List of winner dictionaries
            prize_pool: float - Total prize pool
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE game_rounds
            SET 
                status = 'ended',
                end_time = NOW(),
                winners = $2,
                prize_pool = $3,
                updated_at = NOW()
            WHERE id = $1
            RETURNING id
        """
        
        result = await Database.fetch_one(query, round_id, winners, prize_pool)
        
        if result:
            logger.info(f"Ended game round #{round_id} with {len(winners)} winners")
            return True
        
        return False

    @staticmethod
    async def count_rounds(status: Optional[str] = None) -> int:
        """
        Count game rounds
        
        Args:
            status: str - Filter by status (selection, drawing, ended)
        
        Returns:
            int: Number of rounds
        """
        if status:
            query = "SELECT COUNT(*) as count FROM game_rounds WHERE status = $1"
            result = await Database.fetch_one(query, status)
        else:
            query = "SELECT COUNT(*) as count FROM game_rounds"
            result = await Database.fetch_one(query)
        
        return result['count'] if result else 0

    # ==================== ROUND SELECTIONS ====================

    @staticmethod
    async def create_selection(selection_data: Dict[str, Any]) -> int:
        """
        Create a round selection record (player selected a cartela)
        
        Args:
            selection_data: Dictionary containing:
                - round_id: int
                - user_id: int
                - cartela_id: int
                - amount: float (price paid)
        
        Returns:
            int: Selection ID
        """
        query = """
            INSERT INTO round_selections (round_id, user_id, cartela_id, amount, selected_at)
            VALUES ($1, $2, $3, $4, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            selection_data['round_id'],
            selection_data['user_id'],
            selection_data['cartela_id'],
            selection_data['amount']
        )
        
        selection_id = result['id'] if result else None
        logger.debug(f"Created selection #{selection_id} for round {selection_data['round_id']}")
        
        return selection_id

    @staticmethod
    async def get_round_selections(round_id: int) -> List[Dict[str, Any]]:
        """
        Get all selections for a round
        
        Args:
            round_id: int - Round ID
        
        Returns:
            list: List of selections with user info
        """
        query = """
            SELECT 
                rs.*,
                u.first_name,
                u.username
            FROM round_selections rs
            LEFT JOIN users u ON rs.user_id = u.telegram_id
            WHERE rs.round_id = $1
            ORDER BY rs.selected_at ASC
        """
        
        results = await Database.fetch_all(query, round_id)
        return [dict(row) for row in results]

    @staticmethod
    async def get_user_selections(round_id: int, user_id: int) -> List[Dict[str, Any]]:
        """
        Get a user's selections for a round
        
        Args:
            round_id: int - Round ID
            user_id: int - User's Telegram ID
        
        Returns:
            list: List of user's cartela selections
        """
        query = """
            SELECT * FROM round_selections
            WHERE round_id = $1 AND user_id = $2
            ORDER BY selected_at ASC
        """
        
        results = await Database.fetch_all(query, round_id, user_id)
        return [dict(row) for row in results]

    @staticmethod
    async def get_round_selections_count(round_id: int) -> int:
        """
        Get total number of selections in a round
        
        Args:
            round_id: int - Round ID
        
        Returns:
            int: Number of selections
        """
        query = """
            SELECT COUNT(*) as count FROM round_selections
            WHERE round_id = $1
        """
        
        result = await Database.fetch_one(query, round_id)
        return result['count'] if result else 0

    @staticmethod
    async def get_round_total_bets(round_id: int) -> float:
        """
        Get total bets amount for a round
        
        Args:
            round_id: int - Round ID
        
        Returns:
            float: Total bets amount
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM round_selections
            WHERE round_id = $1
        """
        
        result = await Database.fetch_one(query, round_id)
        return float(result['total']) if result else 0.0

    # ==================== CARTELAS ====================

    @staticmethod
    async def get_cartela(cartela_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cartela by ID
        
        Args:
            cartela_id: int - Cartela ID
        
        Returns:
            dict: Cartela data or None if not found
        """
        query = "SELECT * FROM cartelas WHERE id = $1"
        result = await Database.fetch_one(query, cartela_id)
        return dict(result) if result else None

    @staticmethod
    async def get_all_cartelas(limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all cartelas with pagination
        
        Args:
            limit: int - Maximum number of records
            offset: int - Pagination offset
        
        Returns:
            list: List of cartelas
        """
        query = """
            SELECT * FROM cartelas
            ORDER BY id
            LIMIT $1 OFFSET $2
        """
        
        results = await Database.fetch_all(query, limit, offset)
        return [dict(row) for row in results]

    @staticmethod
    async def get_cartelas_count() -> int:
        """
        Get total number of cartelas
        
        Returns:
            int: Total cartelas count
        """
        query = "SELECT COUNT(*) as count FROM cartelas"
        result = await Database.fetch_one(query)
        return result['count'] if result else 0

    # ==================== GAME STATISTICS ====================

    @staticmethod
    async def get_user_games_count(user_id: int) -> int:
        """
        Get number of games a user has played
        
        Args:
            user_id: int - User's Telegram ID
        
        Returns:
            int: Number of games played
        """
        query = """
            SELECT COUNT(DISTINCT round_id) as count
            FROM round_selections
            WHERE user_id = $1
        """
        
        result = await Database.fetch_one(query, user_id)
        return result['count'] if result else 0

    @staticmethod
    async def get_user_total_bets(user_id: int) -> float:
        """
        Get total amount a user has spent on cartelas
        
        Args:
            user_id: int - User's Telegram ID
        
        Returns:
            float: Total bets amount
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM round_selections
            WHERE user_id = $1
        """
        
        result = await Database.fetch_one(query, user_id)
        return float(result['total']) if result else 0.0

    @staticmethod
    async def get_user_wins_count(user_id: int) -> int:
        """
        Get number of times a user has won
        
        Args:
            user_id: int - User's Telegram ID
        
        Returns:
            int: Number of wins
        """
        query = """
            SELECT COUNT(*) as count
            FROM game_rounds
            WHERE winners IS NOT NULL
            AND $1 = ANY(SELECT jsonb_array_elements(winners)->>'user_id')
        """
        
        result = await Database.fetch_one(query, user_id)
        return result['count'] if result else 0

    @staticmethod
    async def get_global_stats() -> Dict[str, Any]:
        """
        Get global game statistics
        
        Returns:
            dict: Global statistics
        """
        query = """
            SELECT 
                (SELECT COUNT(*) FROM game_rounds) as total_rounds,
                (SELECT COUNT(DISTINCT user_id) FROM round_selections) as total_players,
                (SELECT COALESCE(SUM(amount), 0) FROM round_selections) as total_bets,
                (SELECT COALESCE(SUM(prize_pool), 0) FROM game_rounds WHERE status = 'ended') as total_payouts,
                (SELECT COUNT(*) FROM round_selections) as total_cartelas_sold
        """
        
        result = await Database.fetch_one(query)
        
        if result:
            return {
                'total_rounds': result['total_rounds'] or 0,
                'total_players': result['total_players'] or 0,
                'total_bets': float(result['total_bets'] or 0),
                'total_payouts': float(result['total_payouts'] or 0),
                'total_cartelas_sold': result['total_cartelas_sold'] or 0
            }
        
        return {
            'total_rounds': 0,
            'total_players': 0,
            'total_bets': 0.0,
            'total_payouts': 0.0,
            'total_cartelas_sold': 0
        }

    @staticmethod
    async def get_daily_stats(date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get daily game statistics
        
        Args:
            date: datetime - Specific date (default: today)
        
        Returns:
            dict: Daily statistics
        """
        if date is None:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        next_date = date.replace(day=date.day + 1) if date.day < 31 else date.replace(month=date.month + 1, day=1)
        
        query = """
            SELECT 
                COUNT(DISTINCT gr.id) as rounds_count,
                COUNT(DISTINCT rs.user_id) as players_count,
                COALESCE(SUM(rs.amount), 0) as total_bets,
                COALESCE(SUM(gr.prize_pool), 0) as total_payouts,
                COUNT(rs.id) as cartelas_sold
            FROM game_rounds gr
            LEFT JOIN round_selections rs ON gr.id = rs.round_id
            WHERE gr.start_time >= $1 AND gr.start_time < $2
        """
        
        result = await Database.fetch_one(query, date, next_date)
        
        if result:
            return {
                'date': date,
                'rounds_count': result['rounds_count'] or 0,
                'players_count': result['players_count'] or 0,
                'total_bets': float(result['total_bets'] or 0),
                'total_payouts': float(result['total_payouts'] or 0),
                'cartelas_sold': result['cartelas_sold'] or 0
            }
        
        return {
            'date': date,
            'rounds_count': 0,
            'players_count': 0,
            'total_bets': 0.0,
            'total_payouts': 0.0,
            'cartelas_sold': 0
        }

    @staticmethod
    async def get_weekly_stats() -> List[Dict[str, Any]]:
        """
        Get weekly game statistics (last 7 days)
        
        Returns:
            list: Weekly statistics by day
        """
        stats = []
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            daily_stats = await GameRepository.get_daily_stats(date)
            stats.append(daily_stats)
        
        return stats

    @staticmethod
    async def get_monthly_stats(year: int, month: int) -> List[Dict[str, Any]]:
        """
        Get monthly game statistics
        
        Args:
            year: int - Year
            month: int - Month (1-12)
        
        Returns:
            list: Monthly statistics by day
        """
        from calendar import monthrange
        
        stats = []
        days_in_month = monthrange(year, month)[1]
        
        for day in range(1, days_in_month + 1):
            date = datetime(year, month, day, 0, 0, 0)
            daily_stats = await GameRepository.get_daily_stats(date)
            stats.append(daily_stats)
        
        return stats

    @staticmethod
    async def get_win_percentage() -> int:
        """
        Get current winning percentage from system settings
        
        Returns:
            int: Winning percentage (default 80)
        """
        query = """
            SELECT value FROM system_settings
            WHERE key = 'winning_percentage'
        """
        
        result = await Database.fetch_one(query)
        
        if result:
            return int(result['value'])
        
        return 80

    @staticmethod
    async def set_win_percentage(percentage: int) -> bool:
        """
        Set winning percentage in system settings
        
        Args:
            percentage: int - Winning percentage (75, 78, 79, 80)
        
        Returns:
            bool: True if successful
        """
        query = """
            INSERT INTO system_settings (key, value, updated_at)
            VALUES ('winning_percentage', $1, NOW())
            ON CONFLICT (key) DO UPDATE
            SET value = $1, updated_at = NOW()
            RETURNING key
        """
        
        result = await Database.fetch_one(query, str(percentage))
        
        if result:
            logger.info(f"Set winning percentage to {percentage}%")
            return True
        
        return False

    @staticmethod
    async def get_default_sound_pack() -> str:
        """
        Get default sound pack from system settings
        
        Returns:
            str: Default sound pack (default 'pack1')
        """
        query = """
            SELECT value FROM system_settings
            WHERE key = 'default_sound_pack'
        """
        
        result = await Database.fetch_one(query)
        
        if result:
            return result['value']
        
        return 'pack1'

    @staticmethod
    async def set_default_sound_pack(sound_pack: str) -> bool:
        """
        Set default sound pack in system settings
        
        Args:
            sound_pack: str - Sound pack name (pack1, pack2, pack3, pack4)
        
        Returns:
            bool: True if successful
        """
        query = """
            INSERT INTO system_settings (key, value, updated_at)
            VALUES ('default_sound_pack', $1, NOW())
            ON CONFLICT (key) DO UPDATE
            SET value = $1, updated_at = NOW()
            RETURNING key
        """
        
        result = await Database.fetch_one(query, sound_pack)
        
        if result:
            logger.info(f"Set default sound pack to {sound_pack}")
            return True
        
        return False

    @staticmethod
    async def get_maintenance_mode() -> bool:
        """
        Get maintenance mode status from system settings
        
        Returns:
            bool: True if maintenance mode is enabled
        """
        query = """
            SELECT value FROM system_settings
            WHERE key = 'maintenance_mode'
        """
        
        result = await Database.fetch_one(query)
        
        if result:
            return result['value'] == 'true'
        
        return False

    @staticmethod
    async def set_maintenance_mode(enabled: bool) -> bool:
        """
        Set maintenance mode in system settings
        
        Args:
            enabled: bool - Enable or disable maintenance mode
        
        Returns:
            bool: True if successful
        """
        query = """
            INSERT INTO system_settings (key, value, updated_at)
            VALUES ('maintenance_mode', $1, NOW())
            ON CONFLICT (key) DO UPDATE
            SET value = $1, updated_at = NOW()
            RETURNING key
        """
        
        result = await Database.fetch_one(query, 'true' if enabled else 'false')
        
        if result:
            status = "enabled" if enabled else "disabled"
            logger.info(f"Maintenance mode {status}")
            return True
        
        return False

    @staticmethod
    async def get_active_players_count() -> int:
        """
        Get number of active players in current game (from in-memory state)
        
        Returns:
            int: Number of active players
        """
        # This should be implemented in bingo_room.py
        # For now, return 0 as placeholder
        return 0

    @staticmethod
    async def total_cartelas_sold() -> int:
        """
        Get total number of cartelas sold across all rounds
        
        Returns:
            int: Total cartelas sold
        """
        query = "SELECT COALESCE(SUM(total_cartelas), 0) as total FROM game_rounds"
        result = await Database.fetch_one(query)
        return result['total'] if result else 0


# Import timedelta for date calculations
from datetime import timedelta