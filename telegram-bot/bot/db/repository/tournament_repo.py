# telegram-bot/bot/db/repository/tournament_repo.py
# Estif Bingo 24/7 - Tournament Repository
# Handles all database operations for tournaments, registrations, and leaderboards

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bot.db.database import Database

logger = logging.getLogger(__name__)


class TournamentRepository:
    """Repository for tournament-related database operations"""

    # ==================== TOURNAMENT CRUD ====================

    @staticmethod
    async def create_tournament(tournament_data: Dict[str, Any]) -> int:
        """
        Create a new tournament
        
        Args:
            tournament_data: Dictionary containing:
                - name: str
                - type: str (daily, weekly, monthly, special)
                - entry_fee: float
                - prize_pool: float
                - start_time: datetime
                - end_time: datetime
                - description: str (optional)
                - max_players: int (optional)
                - min_players: int (optional)
                - status: str (default 'active')
        
        Returns:
            int: Tournament ID
        """
        query = """
            INSERT INTO tournaments (
                name, type, entry_fee, prize_pool, start_time, end_time,
                description, max_players, min_players, status, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            tournament_data['name'],
            tournament_data['type'],
            tournament_data['entry_fee'],
            tournament_data['prize_pool'],
            tournament_data['start_time'],
            tournament_data['end_time'],
            tournament_data.get('description'),
            tournament_data.get('max_players', 1000),
            tournament_data.get('min_players', 2),
            tournament_data.get('status', 'active')
        )
        
        tournament_id = result['id'] if result else None
        logger.info(f"Created tournament #{tournament_id}: {tournament_data['name']}")
        
        return tournament_id

    @staticmethod
    async def get_tournament(tournament_id: int) -> Optional[Dict[str, Any]]:
        """
        Get tournament by ID
        
        Args:
            tournament_id: int - Tournament ID
        
        Returns:
            dict: Tournament data or None if not found
        """
        query = """
            SELECT 
                t.*,
                COUNT(tr.id) as player_count,
                COALESCE(SUM(tr.entry_fee), 0) as total_collected
            FROM tournaments t
            LEFT JOIN tournament_registrations tr ON t.id = tr.tournament_id AND tr.status = 'active'
            WHERE t.id = $1
            GROUP BY t.id
        """
        
        result = await Database.fetch_one(query, tournament_id)
        return dict(result) if result else None

    @staticmethod
    async def get_tournament_by_type(tournament_type: str) -> Optional[Dict[str, Any]]:
        """
        Get active tournament by type
        
        Args:
            tournament_type: str - Type of tournament (daily, weekly, monthly, special)
        
        Returns:
            dict: Tournament data or None if not found
        """
        query = """
            SELECT 
                t.*,
                COUNT(tr.id) as player_count,
                COALESCE(SUM(tr.entry_fee), 0) as total_collected
            FROM tournaments t
            LEFT JOIN tournament_registrations tr ON t.id = tr.tournament_id AND tr.status = 'active'
            WHERE t.type = $1 AND t.status = 'active'
            GROUP BY t.id
            ORDER BY t.start_time DESC
            LIMIT 1
        """
        
        result = await Database.fetch_one(query, tournament_type)
        return dict(result) if result else None

    @staticmethod
    async def get_active_tournaments() -> List[Dict[str, Any]]:
        """
        Get all active tournaments
        
        Returns:
            list: List of active tournaments
        """
        query = """
            SELECT 
                t.*,
                COUNT(tr.id) as player_count,
                COALESCE(SUM(tr.entry_fee), 0) as total_collected
            FROM tournaments t
            LEFT JOIN tournament_registrations tr ON t.id = tr.tournament_id AND tr.status = 'active'
            WHERE t.status = 'active' AND t.end_time > NOW()
            GROUP BY t.id
            ORDER BY t.start_time ASC
        """
        
        results = await Database.fetch_all(query)
        return [dict(row) for row in results]

    @staticmethod
    async def get_upcoming_tournaments(limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get upcoming tournaments (not started yet)
        
        Args:
            limit: int - Maximum number of records
        
        Returns:
            list: List of upcoming tournaments
        """
        query = """
            SELECT 
                t.*,
                0 as player_count,
                0 as total_collected
            FROM tournaments t
            WHERE t.status = 'pending' AND t.start_time > NOW()
            ORDER BY t.start_time ASC
            LIMIT $1
        """
        
        results = await Database.fetch_all(query, limit)
        return [dict(row) for row in results]

    @staticmethod
    async def get_ended_tournaments(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get ended tournaments
        
        Args:
            limit: int - Maximum number of records
            offset: int - Pagination offset
        
        Returns:
            list: List of ended tournaments
        """
        query = """
            SELECT 
                t.*,
                COUNT(tr.id) as player_count,
                COALESCE(SUM(tr.entry_fee), 0) as total_collected
            FROM tournaments t
            LEFT JOIN tournament_registrations tr ON t.id = tr.tournament_id
            WHERE t.status = 'ended'
            GROUP BY t.id
            ORDER BY t.end_time DESC
            LIMIT $1 OFFSET $2
        """
        
        results = await Database.fetch_all(query, limit, offset)
        return [dict(row) for row in results]

    @staticmethod
    async def update_tournament(tournament_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update tournament information
        
        Args:
            tournament_id: int - Tournament ID
            updates: dict - Fields to update
        
        Returns:
            bool: True if successful
        """
        set_clauses = []
        params = []
        param_index = 2
        
        allowed_fields = ['name', 'type', 'entry_fee', 'prize_pool', 
                         'description', 'max_players', 'min_players', 'status']
        
        for key, value in updates.items():
            if key in allowed_fields:
                set_clauses.append(f"{key} = ${param_index}")
                params.append(value)
                param_index += 1
        
        if not set_clauses:
            return False
        
        set_clauses.append("updated_at = NOW()")
        params.insert(0, tournament_id)
        
        query = f"""
            UPDATE tournaments
            SET {', '.join(set_clauses)}
            WHERE id = $1
            RETURNING id
        """
        
        result = await Database.fetch_one(query, *params)
        
        if result:
            logger.info(f"Tournament #{tournament_id} updated")
            return True
        
        return False

    @staticmethod
    async def end_tournament(tournament_id: int) -> bool:
        """
        Mark tournament as ended
        
        Args:
            tournament_id: int - Tournament ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE tournaments
            SET status = 'ended', end_time = NOW(), updated_at = NOW()
            WHERE id = $1
            RETURNING id
        """
        
        result = await Database.fetch_one(query, tournament_id)
        
        if result:
            logger.info(f"Tournament #{tournament_id} ended")
            return True
        
        return False

    @staticmethod
    async def delete_tournament(tournament_id: int) -> bool:
        """
        Delete tournament (admin only)
        
        Args:
            tournament_id: int - Tournament ID
        
        Returns:
            bool: True if successful
        """
        # First delete registrations
        await Database.execute(
            "DELETE FROM tournament_registrations WHERE tournament_id = $1",
            tournament_id
        )
        
        # Then delete tournament
        query = "DELETE FROM tournaments WHERE id = $1 RETURNING id"
        result = await Database.fetch_one(query, tournament_id)
        
        if result:
            logger.info(f"Tournament #{tournament_id} deleted")
            return True
        
        return False

    # ==================== TOURNAMENT REGISTRATIONS ====================

    @staticmethod
    async def register_user(
        telegram_id: int,
        tournament_id: int,
        entry_fee: float
    ) -> int:
        """
        Register a user for a tournament
        
        Args:
            telegram_id: int - User's Telegram ID
            tournament_id: int - Tournament ID
            entry_fee: float - Entry fee paid
        
        Returns:
            int: Registration ID
        """
        # Check if already registered
        existing = await TournamentRepository.is_user_registered(telegram_id, tournament_id)
        if existing:
            logger.warning(f"User {telegram_id} already registered for tournament #{tournament_id}")
            return None
        
        query = """
            INSERT INTO tournament_registrations (
                telegram_id, tournament_id, entry_fee, registered_at, status
            )
            VALUES ($1, $2, $3, NOW(), 'active')
            RETURNING id
        """
        
        result = await Database.fetch_one(query, telegram_id, tournament_id, entry_fee)
        registration_id = result['id'] if result else None
        
        if registration_id:
            logger.info(f"User {telegram_id} registered for tournament #{tournament_id}")
            
            # Update player count
            await Database.execute(
                "UPDATE tournaments SET player_count = player_count + 1 WHERE id = $1",
                tournament_id
            )
        
        return registration_id

    @staticmethod
    async def unregister_user(telegram_id: int, tournament_id: int) -> bool:
        """
        Unregister a user from a tournament
        
        Args:
            telegram_id: int - User's Telegram ID
            tournament_id: int - Tournament ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE tournament_registrations
            SET status = 'cancelled', updated_at = NOW()
            WHERE telegram_id = $1 AND tournament_id = $2 AND status = 'active'
            RETURNING id
        """
        
        result = await Database.fetch_one(query, telegram_id, tournament_id)
        
        if result:
            logger.info(f"User {telegram_id} unregistered from tournament #{tournament_id}")
            
            # Update player count
            await Database.execute(
                "UPDATE tournaments SET player_count = player_count - 1 WHERE id = $1",
                tournament_id
            )
            
            return True
        
        return False

    @staticmethod
    async def is_user_registered(telegram_id: int, tournament_id: int) -> bool:
        """
        Check if user is registered for tournament
        
        Args:
            telegram_id: int - User's Telegram ID
            tournament_id: int - Tournament ID
        
        Returns:
            bool: True if registered
        """
        query = """
            SELECT id FROM tournament_registrations
            WHERE telegram_id = $1 AND tournament_id = $2 AND status = 'active'
        """
        
        result = await Database.fetch_one(query, telegram_id, tournament_id)
        return result is not None

    @staticmethod
    async def get_user_registrations(telegram_id: int) -> List[Dict[str, Any]]:
        """
        Get all tournament registrations for a user
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            list: List of registrations with tournament info
        """
        query = """
            SELECT 
                tr.*,
                t.name as tournament_name,
                t.type as tournament_type,
                t.start_time,
                t.end_time,
                t.status as tournament_status,
                t.prize_pool
            FROM tournament_registrations tr
            JOIN tournaments t ON tr.tournament_id = t.id
            WHERE tr.telegram_id = $1
            ORDER BY t.start_time DESC
        """
        
        results = await Database.fetch_all(query, telegram_id)
        return [dict(row) for row in results]

    @staticmethod
    async def get_tournament_players(tournament_id: int) -> List[Dict[str, Any]]:
        """
        Get all players registered for a tournament
        
        Args:
            tournament_id: int - Tournament ID
        
        Returns:
            list: List of players with user info
        """
        query = """
            SELECT 
                tr.*,
                u.first_name,
                u.username,
                u.phone_last4
            FROM tournament_registrations tr
            JOIN users u ON tr.telegram_id = u.telegram_id
            WHERE tr.tournament_id = $1 AND tr.status = 'active'
            ORDER BY tr.registered_at ASC
        """
        
        results = await Database.fetch_all(query, tournament_id)
        return [dict(row) for row in results]

    @staticmethod
    async def get_tournament_player_count(tournament_id: int) -> int:
        """
        Get number of players in tournament
        
        Args:
            tournament_id: int - Tournament ID
        
        Returns:
            int: Number of players
        """
        query = """
            SELECT COUNT(*) as count
            FROM tournament_registrations
            WHERE tournament_id = $1 AND status = 'active'
        """
        
        result = await Database.fetch_one(query, tournament_id)
        return result['count'] if result else 0

    # ==================== TOURNAMENT POINTS & SCORES ====================

    @staticmethod
    async def update_user_points(
        telegram_id: int,
        tournament_id: int,
        points: int,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Update user's tournament points
        
        Args:
            telegram_id: int - User's Telegram ID
            tournament_id: int - Tournament ID
            points: int - Points to add
            metadata: dict - Additional metadata
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE tournament_registrations
            SET points = points + $3, 
                games_played = games_played + 1,
                updated_at = NOW()
            WHERE telegram_id = $1 AND tournament_id = $2 AND status = 'active'
            RETURNING id
        """
        
        result = await Database.fetch_one(query, telegram_id, tournament_id, points)
        
        if result:
            logger.debug(f"Added {points} points to user {telegram_id} in tournament #{tournament_id}")
            return True
        
        return False

    @staticmethod
    async def set_user_points(
        telegram_id: int,
        tournament_id: int,
        points: int
    ) -> bool:
        """
        Set user's tournament points (overwrite)
        
        Args:
            telegram_id: int - User's Telegram ID
            tournament_id: int - Tournament ID
            points: int - New points value
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE tournament_registrations
            SET points = $3, updated_at = NOW()
            WHERE telegram_id = $1 AND tournament_id = $2 AND status = 'active'
            RETURNING id
        """
        
        result = await Database.fetch_one(query, telegram_id, tournament_id, points)
        
        if result:
            logger.info(f"Set points to {points} for user {telegram_id} in tournament #{tournament_id}")
            return True
        
        return False

    @staticmethod
    async def get_user_points(telegram_id: int, tournament_id: int) -> int:
        """
        Get user's points in tournament
        
        Args:
            telegram_id: int - User's Telegram ID
            tournament_id: int - Tournament ID
        
        Returns:
            int: User's points
        """
        query = """
            SELECT points FROM tournament_registrations
            WHERE telegram_id = $1 AND tournament_id = $2 AND status = 'active'
        """
        
        result = await Database.fetch_one(query, telegram_id, tournament_id)
        return result['points'] if result else 0

    @staticmethod
    async def get_leaderboard(
        tournament_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get tournament leaderboard
        
        Args:
            tournament_id: int - Tournament ID
            limit: int - Maximum number of records
            offset: int - Pagination offset
        
        Returns:
            list: Leaderboard entries
        """
        query = """
            SELECT 
                tr.telegram_id,
                tr.points,
                tr.games_played,
                tr.entry_fee,
                tr.registered_at,
                u.first_name,
                u.username,
                u.phone_last4
            FROM tournament_registrations tr
            JOIN users u ON tr.telegram_id = u.telegram_id
            WHERE tr.tournament_id = $1 AND tr.status = 'active'
            ORDER BY tr.points DESC, tr.games_played ASC
            LIMIT $2 OFFSET $3
        """
        
        results = await Database.fetch_all(query, tournament_id, limit, offset)
        leaderboard = []
        
        for idx, row in enumerate(results, 1):
            entry = dict(row)
            entry['rank'] = idx
            leaderboard.append(entry)
        
        return leaderboard

    @staticmethod
    async def get_user_rank(
        telegram_id: int,
        tournament_id: int
    ) -> Optional[int]:
        """
        Get user's rank in tournament
        
        Args:
            telegram_id: int - User's Telegram ID
            tournament_id: int - Tournament ID
        
        Returns:
            int: User's rank or None
        """
        query = """
            SELECT rank FROM (
                SELECT 
                    telegram_id,
                    ROW_NUMBER() OVER (ORDER BY points DESC, games_played ASC) as rank
                FROM tournament_registrations
                WHERE tournament_id = $1 AND status = 'active'
            ) ranked
            WHERE telegram_id = $2
        """
        
        result = await Database.fetch_one(query, tournament_id, telegram_id)
        return result['rank'] if result else None

    # ==================== PRIZE DISTRIBUTION ====================

    @staticmethod
    async def distribute_prizes(
        tournament_id: int,
        prize_distribution: List[Dict[str, Any]]
    ) -> bool:
        """
        Distribute prizes to tournament winners
        
        Args:
            tournament_id: int - Tournament ID
            prize_distribution: list - List of {rank, telegram_id, prize_amount}
        
        Returns:
            bool: True if successful
        """
        # Record prizes in database
        for prize in prize_distribution:
            query = """
                INSERT INTO tournament_prizes (
                    tournament_id, telegram_id, rank, prize_amount, awarded_at
                )
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (tournament_id, telegram_id, rank) DO UPDATE
                SET prize_amount = $4, awarded_at = NOW()
            """
            
            await Database.execute(
                query,
                tournament_id,
                prize['telegram_id'],
                prize['rank'],
                prize['prize_amount']
            )
        
        # Update tournament as prize_distributed
        query = """
            UPDATE tournaments
            SET prize_distributed = TRUE, updated_at = NOW()
            WHERE id = $1
        """
        
        result = await Database.fetch_one(query, tournament_id)
        
        if result:
            logger.info(f"Prizes distributed for tournament #{tournament_id}")
            return True
        
        return False

    @staticmethod
    async def get_prize_winners(tournament_id: int) -> List[Dict[str, Any]]:
        """
        Get prize winners for a tournament
        
        Args:
            tournament_id: int - Tournament ID
        
        Returns:
            list: List of winners with prize amounts
        """
        query = """
            SELECT 
                tp.*,
                u.first_name,
                u.username
            FROM tournament_prizes tp
            JOIN users u ON tp.telegram_id = u.telegram_id
            WHERE tp.tournament_id = $1
            ORDER BY tp.rank ASC
        """
        
        results = await Database.fetch_all(query, tournament_id)
        return [dict(row) for row in results]

    # ==================== TOURNAMENT STATISTICS ====================

    @staticmethod
    async def get_tournament_stats(tournament_id: int) -> Dict[str, Any]:
        """
        Get comprehensive tournament statistics
        
        Args:
            tournament_id: int - Tournament ID
        
        Returns:
            dict: Tournament statistics
        """
        query = """
            SELECT 
                t.*,
                COUNT(DISTINCT tr.telegram_id) as total_players,
                COALESCE(SUM(tr.entry_fee), 0) as total_entry_fees,
                COALESCE(SUM(tr.points), 0) as total_points,
                AVG(tr.points) as average_points,
                MAX(tr.points) as highest_points,
                COUNT(tp.id) as prize_winners,
                COALESCE(SUM(tp.prize_amount), 0) as total_prizes_paid
            FROM tournaments t
            LEFT JOIN tournament_registrations tr ON t.id = tr.tournament_id AND tr.status = 'active'
            LEFT JOIN tournament_prizes tp ON t.id = tp.tournament_id
            WHERE t.id = $1
            GROUP BY t.id
        """
        
        result = await Database.fetch_one(query, tournament_id)
        
        if result:
            stats = dict(result)
            stats['house_profit'] = stats['total_entry_fees'] - stats['total_prizes_paid']
            return stats
        
        return {}

    @staticmethod
    async def get_daily_tournament_stats(date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get daily tournament statistics
        
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
                COUNT(*) as total_tournaments,
                COALESCE(SUM(player_count), 0) as total_players,
                COALESCE(SUM(entry_fee * player_count), 0) as total_entry_fees,
                COALESCE(SUM(prize_pool), 0) as total_prize_pools
            FROM tournaments
            WHERE start_time >= $1 AND start_time < $2
        """
        
        result = await Database.fetch_one(query, date, next_date)
        
        if result:
            return {
                'date': date,
                'total_tournaments': result['total_tournaments'] or 0,
                'total_players': result['total_players'] or 0,
                'total_entry_fees': float(result['total_entry_fees'] or 0),
                'total_prize_pools': float(result['total_prize_pools'] or 0)
            }
        
        return {
            'date': date,
            'total_tournaments': 0,
            'total_players': 0,
            'total_entry_fees': 0.0,
            'total_prize_pools': 0.0
        }

    @staticmethod
    async def get_active_tournaments_count() -> int:
        """
        Get count of active tournaments
        
        Returns:
            int: Number of active tournaments
        """
        query = """
            SELECT COUNT(*) as count
            FROM tournaments
            WHERE status = 'active' AND end_time > NOW()
        """
        
        result = await Database.fetch_one(query)
        return result['count'] if result else 0

    @staticmethod
    async def cleanup_expired_tournaments() -> int:
        """
        Mark expired tournaments as ended
        
        Returns:
            int: Number of tournaments ended
        """
        query = """
            UPDATE tournaments
            SET status = 'ended', updated_at = NOW()
            WHERE status = 'active' AND end_time <= NOW()
            RETURNING id
        """
        
        results = await Database.fetch_all(query)
        ended_count = len(results)
        
        if ended_count > 0:
            logger.info(f"Ended {ended_count} expired tournaments")
        
        return ended_count


# Import timedelta for date calculations
from datetime import timedelta