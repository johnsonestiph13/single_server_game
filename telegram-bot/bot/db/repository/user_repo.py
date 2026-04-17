# telegram-bot/bot/db/repository/user_repo.py
# Estif Bingo 24/7 - User Repository
# Handles all database operations for users

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bot.db.database import Database
from bot.utils.crypto import encrypt_phone, decrypt_phone, hash_phone

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user database operations"""

    @staticmethod
    async def create(user_data: Dict[str, Any]) -> int:
        """
        Create a new user
        
        Args:
            user_data: Dictionary containing:
                - telegram_id: int
                - username: str (optional)
                - first_name: str
                - last_name: str (optional)
                - phone_encrypted: str (optional)
                - phone_hash: str (optional)
                - phone_last4: str (optional)
                - lang: str (default 'en')
                - registered: bool (default False)
                - welcome_bonus_claimed: bool (default False)
                - sound_pack: str (default 'pack1')
                - balance: float (default 0)
        
        Returns:
            int: Telegram ID of created user
        """
        query = """
            INSERT INTO users (
                telegram_id, username, first_name, last_name,
                phone_encrypted, phone_hash, phone_last4,
                lang, registered, welcome_bonus_claimed,
                sound_pack, balance, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
            ON CONFLICT (telegram_id) DO UPDATE
            SET 
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                updated_at = NOW()
            RETURNING telegram_id
        """
        
        result = await Database.fetch_one(
            query,
            user_data['telegram_id'],
            user_data.get('username', ''),
            user_data.get('first_name', ''),
            user_data.get('last_name', ''),
            user_data.get('phone_encrypted'),
            user_data.get('phone_hash'),
            user_data.get('phone_last4'),
            user_data.get('lang', 'en'),
            user_data.get('registered', False),
            user_data.get('welcome_bonus_claimed', False),
            user_data.get('sound_pack', 'pack1'),
            user_data.get('balance', 0)
        )
        
        telegram_id = result['telegram_id'] if result else None
        logger.info(f"User created/updated: {telegram_id}")
        
        return telegram_id

    @staticmethod
    async def get_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by Telegram ID
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            dict: User data or None if not found
        """
        query = """
            SELECT 
                telegram_id, username, first_name, last_name,
                phone_encrypted, phone_hash, phone_last4,
                lang, registered, welcome_bonus_claimed,
                sound_pack, balance, is_active, is_admin,
                total_games_played, total_wagered, total_won,
                created_at, last_seen, updated_at
            FROM users
            WHERE telegram_id = $1
        """
        
        result = await Database.fetch_one(query, telegram_id)
        
        if result:
            user_dict = dict(result)
            # Don't decrypt phone automatically for security
            # Only decrypt when needed with explicit method
            return user_dict
        
        return None

    @staticmethod
    async def get_by_username(username: str) -> Optional[Dict[str, Any]]:
        """
        Get user by username
        
        Args:
            username: str - Telegram username (without @)
        
        Returns:
            dict: User data or None if not found
        """
        query = """
            SELECT 
                telegram_id, username, first_name, last_name,
                phone_encrypted, phone_hash, phone_last4,
                lang, registered, welcome_bonus_claimed,
                sound_pack, balance, is_active, is_admin,
                total_games_played, total_wagered, total_won,
                created_at, last_seen, updated_at
            FROM users
            WHERE LOWER(username) = LOWER($1)
        """
        
        result = await Database.fetch_one(query, username)
        return dict(result) if result else None

    @staticmethod
    async def get_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get user by phone number (exact match)
        
        Args:
            phone_number: str - Phone number (will be hashed for lookup)
        
        Returns:
            dict: User data or None if not found
        """
        # Hash the phone number for lookup (security)
        phone_hash = hash_phone(phone_number)
        
        query = """
            SELECT 
                telegram_id, username, first_name, last_name,
                phone_encrypted, phone_hash, phone_last4,
                lang, registered, welcome_bonus_claimed,
                sound_pack, balance, is_active, is_admin,
                total_games_played, total_wagered, total_won,
                created_at, last_seen, updated_at
            FROM users
            WHERE phone_hash = $1
        """
        
        result = await Database.fetch_one(query, phone_hash)
        return dict(result) if result else None

    @staticmethod
    async def get_by_phone_last4(last4: str) -> List[Dict[str, Any]]:
        """
        Get users by last 4 digits of phone number
        
        Args:
            last4: str - Last 4 digits of phone number
        
        Returns:
            list: List of matching users
        """
        query = """
            SELECT 
                telegram_id, username, first_name, last_name,
                phone_last4, lang, registered, welcome_bonus_claimed,
                sound_pack, balance, is_active, created_at, last_seen
            FROM users
            WHERE phone_last4 = $1
            ORDER BY created_at DESC
        """
        
        results = await Database.fetch_all(query, last4)
        return [dict(row) for row in results]

    @staticmethod
    async def get_all_registered(
        limit: int = 100,
        offset: int = 0,
        sort_by: str = 'created_at',
        sort_order: str = 'DESC'
    ) -> List[Dict[str, Any]]:
        """
        Get all registered users with pagination
        
        Args:
            limit: int - Maximum number of records
            offset: int - Pagination offset
            sort_by: str - Field to sort by
            sort_order: str - 'ASC' or 'DESC'
        
        Returns:
            list: List of users
        """
        allowed_sort_fields = ['created_at', 'balance', 'username', 'first_name']
        if sort_by not in allowed_sort_fields:
            sort_by = 'created_at'
        
        sort_order = 'DESC' if sort_order.upper() == 'DESC' else 'ASC'
        
        query = f"""
            SELECT 
                telegram_id, username, first_name, last_name,
                phone_last4, lang, registered, welcome_bonus_claimed,
                sound_pack, balance, is_active, is_admin,
                total_games_played, total_wagered, total_won,
                created_at, last_seen
            FROM users
            WHERE registered = TRUE
            ORDER BY {sort_by} {sort_order}
            LIMIT $1 OFFSET $2
        """
        
        results = await Database.fetch_all(query, limit, offset)
        return [dict(row) for row in results]

    @staticmethod
    async def count_registered() -> int:
        """
        Count total registered users
        
        Returns:
            int: Number of registered users
        """
        query = "SELECT COUNT(*) as count FROM users WHERE registered = TRUE"
        result = await Database.fetch_one(query)
        return result['count'] if result else 0

    @staticmethod
    async def count_active(last_hours: int = 24) -> int:
        """
        Count active users (seen within last X hours)
        
        Args:
            last_hours: int - Hours to look back
        
        Returns:
            int: Number of active users
        """
        cutoff = datetime.utcnow() - timedelta(hours=last_hours)
        
        query = """
            SELECT COUNT(*) as count FROM users
            WHERE registered = TRUE AND last_seen >= $1
        """
        
        result = await Database.fetch_one(query, cutoff)
        return result['count'] if result else 0

    @staticmethod
    async def count_new_since(since_date: datetime) -> int:
        """
        Count new users since a specific date
        
        Args:
            since_date: datetime - Start date
        
        Returns:
            int: Number of new users
        """
        query = """
            SELECT COUNT(*) as count FROM users
            WHERE registered = TRUE AND created_at >= $1
        """
        
        result = await Database.fetch_one(query, since_date)
        return result['count'] if result else 0

    @staticmethod
    async def update(telegram_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update user information
        
        Args:
            telegram_id: int - User's Telegram ID
            updates: dict - Fields to update
        
        Returns:
            bool: True if successful
        """
        set_clauses = []
        params = []
        param_index = 2
        
        for key, value in updates.items():
            if key in ['phone_encrypted', 'phone_hash', 'phone_last4']:
                set_clauses.append(f"{key} = ${param_index}")
                params.append(value)
                param_index += 1
            elif key in ['username', 'first_name', 'last_name', 'lang', 'sound_pack']:
                set_clauses.append(f"{key} = ${param_index}")
                params.append(value)
                param_index += 1
            elif key in ['registered', 'welcome_bonus_claimed', 'is_active', 'is_admin']:
                set_clauses.append(f"{key} = ${param_index}")
                params.append(value)
                param_index += 1
            elif key in ['balance', 'total_games_played', 'total_wagered', 'total_won']:
                set_clauses.append(f"{key} = ${param_index}")
                params.append(value)
                param_index += 1
        
        if not set_clauses:
            return False
        
        set_clauses.append("updated_at = NOW()")
        params.insert(0, telegram_id)
        
        query = f"""
            UPDATE users
            SET {', '.join(set_clauses)}
            WHERE telegram_id = $1
            RETURNING telegram_id
        """
        
        result = await Database.fetch_one(query, *params)
        
        if result:
            logger.debug(f"User {telegram_id} updated with fields: {list(updates.keys())}")
            return True
        
        return False

    @staticmethod
    async def update_balance(
        telegram_id: int,
        amount: float,
        operation: str = 'add'  # 'add', 'subtract', 'set'
    ) -> Optional[float]:
        """
        Update user balance atomically
        
        Args:
            telegram_id: int - User's Telegram ID
            amount: float - Amount to add/subtract/set
            operation: str - 'add', 'subtract', or 'set'
        
        Returns:
            float: New balance or None if failed
        """
        if operation == 'add':
            query = """
                UPDATE users
                SET balance = balance + $2, updated_at = NOW()
                WHERE telegram_id = $1
                RETURNING balance
            """
        elif operation == 'subtract':
            query = """
                UPDATE users
                SET balance = balance - $2, updated_at = NOW()
                WHERE telegram_id = $1 AND balance >= $2
                RETURNING balance
            """
        else:  # set
            query = """
                UPDATE users
                SET balance = $2, updated_at = NOW()
                WHERE telegram_id = $1
                RETURNING balance
            """
        
        result = await Database.fetch_one(query, telegram_id, amount)
        
        if result:
            logger.debug(f"User {telegram_id} balance updated: {operation} {amount} -> {result['balance']}")
            return float(result['balance'])
        
        return None

    @staticmethod
    async def get_balance(telegram_id: int) -> float:
        """
        Get user balance
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            float: User balance
        """
        query = "SELECT balance FROM users WHERE telegram_id = $1"
        result = await Database.fetch_one(query, telegram_id)
        return float(result['balance']) if result else 0.0

    @staticmethod
    async def update_last_seen(telegram_id: int) -> bool:
        """
        Update user's last seen timestamp
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE users
            SET last_seen = NOW()
            WHERE telegram_id = $1
            RETURNING telegram_id
        """
        
        result = await Database.fetch_one(query, telegram_id)
        return result is not None

    @staticmethod
    async def increment_game_stats(
        telegram_id: int,
        wagered: float = 0,
        won: float = 0,
        games_played: int = 0
    ) -> bool:
        """
        Increment user game statistics
        
        Args:
            telegram_id: int - User's Telegram ID
            wagered: float - Amount wagered (cartelas purchased)
            won: float - Amount won
            games_played: int - Number of games played
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE users
            SET 
                total_wagered = total_wagered + $2,
                total_won = total_won + $3,
                total_games_played = total_games_played + $4,
                updated_at = NOW()
            WHERE telegram_id = $1
            RETURNING telegram_id
        """
        
        result = await Database.fetch_one(query, telegram_id, wagered, won, games_played)
        return result is not None

    @staticmethod
    async def mark_welcome_bonus_claimed(telegram_id: int) -> bool:
        """
        Mark that user has claimed welcome bonus
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE users
            SET welcome_bonus_claimed = TRUE, updated_at = NOW()
            WHERE telegram_id = $1
            RETURNING telegram_id
        """
        
        result = await Database.fetch_one(query, telegram_id)
        
        if result:
            logger.info(f"Welcome bonus marked as claimed for user {telegram_id}")
            return True
        
        return False

    @staticmethod
    async def update_sound_pack(telegram_id: int, sound_pack: str) -> bool:
        """
        Update user's preferred sound pack
        
        Args:
            telegram_id: int - User's Telegram ID
            sound_pack: str - Sound pack name (pack1, pack2, pack3, pack4)
        
        Returns:
            bool: True if successful
        """
        valid_packs = ['pack1', 'pack2', 'pack3', 'pack4']
        if sound_pack not in valid_packs:
            logger.warning(f"Invalid sound pack: {sound_pack}")
            return False
        
        query = """
            UPDATE users
            SET sound_pack = $2, updated_at = NOW()
            WHERE telegram_id = $1
            RETURNING telegram_id
        """
        
        result = await Database.fetch_one(query, telegram_id, sound_pack)
        
        if result:
            logger.debug(f"User {telegram_id} sound pack updated to {sound_pack}")
            return True
        
        return False

    @staticmethod
    async def get_user_rank_by_balance(telegram_id: int) -> Optional[int]:
        """
        Get user's rank based on balance
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            int: Rank (1 = highest balance)
        """
        query = """
            SELECT rank FROM (
                SELECT 
                    telegram_id,
                    ROW_NUMBER() OVER (ORDER BY balance DESC) as rank
                FROM users
                WHERE registered = TRUE
            ) ranked
            WHERE telegram_id = $1
        """
        
        result = await Database.fetch_one(query, telegram_id)
        return result['rank'] if result else None

    @staticmethod
    async def get_top_users_by_balance(limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top users by balance (leaderboard)
        
        Args:
            limit: int - Number of users to return
        
        Returns:
            list: List of top users
        """
        query = """
            SELECT 
                telegram_id, username, first_name, last_name,
                balance, total_games_played, total_won
            FROM users
            WHERE registered = TRUE
            ORDER BY balance DESC
            LIMIT $1
        """
        
        results = await Database.fetch_all(query, limit)
        return [dict(row) for row in results]

    @staticmethod
    async def get_top_users_by_wins(limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top users by total winnings
        
        Args:
            limit: int - Number of users to return
        
        Returns:
            list: List of top users
        """
        query = """
            SELECT 
                telegram_id, username, first_name, last_name,
                balance, total_games_played, total_won
            FROM users
            WHERE registered = TRUE
            ORDER BY total_won DESC
            LIMIT $1
        """
        
        results = await Database.fetch_all(query, limit)
        return [dict(row) for row in results]

    @staticmethod
    async def get_top_users_by_games(limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top users by games played
        
        Args:
            limit: int - Number of users to return
        
        Returns:
            list: List of top users
        """
        query = """
            SELECT 
                telegram_id, username, first_name, last_name,
                balance, total_games_played, total_won
            FROM users
            WHERE registered = TRUE
            ORDER BY total_games_played DESC
            LIMIT $1
        """
        
        results = await Database.fetch_all(query, limit)
        return [dict(row) for row in results]

    @staticmethod
    async def search_users(
        search_term: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search users by username, first name, or last name
        
        Args:
            search_term: str - Search term
            limit: int - Maximum number of records
            offset: int - Pagination offset
        
        Returns:
            list: List of matching users
        """
        search_pattern = f"%{search_term}%"
        
        query = """
            SELECT 
                telegram_id, username, first_name, last_name,
                phone_last4, lang, registered, welcome_bonus_claimed,
                sound_pack, balance, is_active, is_admin,
                total_games_played, total_wagered, total_won,
                created_at, last_seen
            FROM users
            WHERE registered = TRUE
            AND (
                username ILIKE $1 OR
                first_name ILIKE $1 OR
                last_name ILIKE $1 OR
                CAST(telegram_id AS TEXT) = $2
            )
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
        """
        
        results = await Database.fetch_all(query, search_pattern, search_term, limit, offset)
        return [dict(row) for row in results]

    @staticmethod
    async def get_phone_decrypted(telegram_id: int) -> Optional[str]:
        """
        Get user's phone number (decrypted) - Use with caution
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            str: Decrypted phone number or None
        """
        query = "SELECT phone_encrypted FROM users WHERE telegram_id = $1"
        result = await Database.fetch_one(query, telegram_id)
        
        if result and result['phone_encrypted']:
            return decrypt_phone(result['phone_encrypted'])
        
        return None

    @staticmethod
    async def set_admin(telegram_id: int, is_admin: bool = True) -> bool:
        """
        Set user as admin or remove admin status
        
        Args:
            telegram_id: int - User's Telegram ID
            is_admin: bool - Admin status
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE users
            SET is_admin = $2, updated_at = NOW()
            WHERE telegram_id = $1
            RETURNING telegram_id
        """
        
        result = await Database.fetch_one(query, telegram_id, is_admin)
        
        if result:
            status = "granted" if is_admin else "revoked"
            logger.info(f"Admin privileges {status} for user {telegram_id}")
            return True
        
        return False

    @staticmethod
    async def deactivate_user(telegram_id: int) -> bool:
        """
        Deactivate user account (soft delete)
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE users
            SET is_active = FALSE, registered = FALSE, updated_at = NOW()
            WHERE telegram_id = $1
            RETURNING telegram_id
        """
        
        result = await Database.fetch_one(query, telegram_id)
        
        if result:
            logger.info(f"User {telegram_id} deactivated")
            return True
        
        return False

    @staticmethod
    async def get_user_stats(telegram_id: int) -> Dict[str, Any]:
        """
        Get comprehensive user statistics
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            dict: User statistics
        """
        query = """
            SELECT 
                balance,
                total_games_played,
                total_wagered,
                total_won,
                (total_won - total_wagered) as net_profit,
                created_at,
                last_seen
            FROM users
            WHERE telegram_id = $1
        """
        
        result = await Database.fetch_one(query, telegram_id)
        
        if result:
            return {
                'balance': float(result['balance']),
                'total_games_played': result['total_games_played'] or 0,
                'total_wagered': float(result['total_wagered'] or 0),
                'total_won': float(result['total_won'] or 0),
                'net_profit': float(result['net_profit'] or 0),
                'created_at': result['created_at'],
                'last_seen': result['last_seen']
            }
        
        return {
            'balance': 0.0,
            'total_games_played': 0,
            'total_wagered': 0.0,
            'total_won': 0.0,
            'net_profit': 0.0,
            'created_at': None,
            'last_seen': None
        }


# Import timedelta for date calculations
from datetime import timedelta