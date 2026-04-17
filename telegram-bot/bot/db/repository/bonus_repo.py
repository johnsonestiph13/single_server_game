# telegram-bot/bot/db/repository/bonus_repo.py
# Estif Bingo 24/7 - Bonus Repository
# Handles all database operations for bonus claims and tracking

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bot.db.database import Database

logger = logging.getLogger(__name__)


class BonusRepository:
    """Repository for bonus-related database operations"""

    # ==================== BONUS CLAIMS ====================

    @staticmethod
    async def record_bonus_claim(
        telegram_id: int,
        bonus_type: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = 'claimed'
    ) -> int:
        """
        Record a bonus claim
        
        Args:
            telegram_id: int - User's Telegram ID
            bonus_type: str - Type of bonus (welcome, daily, admin, compensation)
            amount: float - Bonus amount
            metadata: dict - Additional metadata
            status: str - Status (claimed, pending, expired)
        
        Returns:
            int: ID of the bonus claim record
        """
        query = """
            INSERT INTO bonus_claims (
                telegram_id, bonus_type, amount, metadata, status, claimed_at
            )
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            telegram_id,
            bonus_type,
            amount,
            metadata,
            status
        )
        
        bonus_id = result['id'] if result else None
        
        if bonus_id:
            logger.info(f"Bonus claim recorded: {bonus_type} of {amount} ETB for user {telegram_id}")
        
        return bonus_id

    @staticmethod
    async def get_bonus_claim(bonus_id: int) -> Optional[Dict[str, Any]]:
        """
        Get bonus claim by ID
        
        Args:
            bonus_id: int - Bonus claim ID
        
        Returns:
            dict: Bonus claim data or None if not found
        """
        query = """
            SELECT 
                b.*,
                u.first_name,
                u.username
            FROM bonus_claims b
            LEFT JOIN users u ON b.telegram_id = u.telegram_id
            WHERE b.id = $1
        """
        
        result = await Database.fetch_one(query, bonus_id)
        return dict(result) if result else None

    @staticmethod
    async def get_user_bonus_claims(
        telegram_id: int,
        limit: int = 50,
        offset: int = 0,
        bonus_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all bonus claims for a user
        
        Args:
            telegram_id: int - User's Telegram ID
            limit: int - Maximum number of records
            offset: int - Pagination offset
            bonus_type: str - Filter by bonus type
        
        Returns:
            list: List of bonus claims
        """
        query = """
            SELECT * FROM bonus_claims
            WHERE telegram_id = $1
        """
        params = [telegram_id]
        param_index = 2
        
        if bonus_type:
            query += f" AND bonus_type = ${param_index}"
            params.append(bonus_type)
            param_index += 1
        
        query += f" ORDER BY claimed_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.append(limit)
        params.append(offset)
        
        results = await Database.fetch_all(query, *params)
        return [dict(row) for row in results]

    @staticmethod
    async def get_user_bonus_total(telegram_id: int, bonus_type: Optional[str] = None) -> float:
        """
        Get total bonus amount claimed by user
        
        Args:
            telegram_id: int - User's Telegram ID
            bonus_type: str - Filter by bonus type
        
        Returns:
            float: Total bonus amount
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM bonus_claims
            WHERE telegram_id = $1 AND status = 'claimed'
        """
        params = [telegram_id]
        
        if bonus_type:
            query += f" AND bonus_type = $2"
            params.append(bonus_type)
        
        result = await Database.fetch_one(query, *params)
        return float(result['total']) if result else 0.0

    # ==================== WELCOME BONUS ====================

    @staticmethod
    async def get_welcome_bonus_status(telegram_id: int) -> Dict[str, Any]:
        """
        Get welcome bonus status for user
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            dict: Welcome bonus status
        """
        query = """
            SELECT 
                CASE WHEN welcome_bonus_claimed THEN 'claimed' ELSE 'available' END as status,
                CASE WHEN registered THEN 'registered' ELSE 'not_registered' END as registration_status,
                created_at as user_created_at
            FROM users
            WHERE telegram_id = $1
        """
        
        result = await Database.fetch_one(query, telegram_id)
        
        if result:
            return {
                'status': result['status'],
                'registration_status': result['registration_status'],
                'user_created_at': result['user_created_at'],
                'amount': 30  # Default welcome bonus amount
            }
        
        return {
            'status': 'not_found',
            'registration_status': 'not_registered',
            'user_created_at': None,
            'amount': 30
        }

    @staticmethod
    async def claim_welcome_bonus(telegram_id: int, amount: float) -> bool:
        """
        Claim welcome bonus for user
        
        Args:
            telegram_id: int - User's Telegram ID
            amount: float - Bonus amount
        
        Returns:
            bool: True if successful
        """
        # Check if already claimed
        query_check = """
            SELECT welcome_bonus_claimed FROM users
            WHERE telegram_id = $1
        """
        
        result = await Database.fetch_one(query_check, telegram_id)
        
        if not result or result['welcome_bonus_claimed']:
            logger.warning(f"Welcome bonus already claimed for user {telegram_id}")
            return False
        
        # Mark as claimed
        query_update = """
            UPDATE users
            SET welcome_bonus_claimed = TRUE, updated_at = NOW()
            WHERE telegram_id = $1
            RETURNING telegram_id
        """
        
        update_result = await Database.fetch_one(query_update, telegram_id)
        
        if update_result:
            # Record bonus claim
            await BonusRepository.record_bonus_claim(
                telegram_id=telegram_id,
                bonus_type='welcome',
                amount=amount,
                metadata={'claimed_via': 'auto_on_register'}
            )
            
            logger.info(f"Welcome bonus of {amount} ETB claimed for user {telegram_id}")
            return True
        
        return False

    @staticmethod
    async def has_claimed_welcome_bonus(telegram_id: int) -> bool:
        """
        Check if user has claimed welcome bonus
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            bool: True if welcome bonus already claimed
        """
        query = """
            SELECT welcome_bonus_claimed FROM users
            WHERE telegram_id = $1
        """
        
        result = await Database.fetch_one(query, telegram_id)
        return result['welcome_bonus_claimed'] if result else False

    # ==================== DAILY BONUS ====================

    @staticmethod
    async def get_daily_bonus_status(telegram_id: int) -> Dict[str, Any]:
        """
        Get daily bonus status for user
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            dict: Daily bonus status
        """
        query = """
            SELECT 
                claimed_at,
                amount
            FROM bonus_claims
            WHERE telegram_id = $1
            AND bonus_type = 'daily'
            AND status = 'claimed'
            ORDER BY claimed_at DESC
            LIMIT 1
        """
        
        result = await Database.fetch_one(query, telegram_id)
        
        if result:
            last_claimed = result['claimed_at']
            now = datetime.utcnow()
            next_available = last_claimed + timedelta(days=1)
            
            if now >= next_available:
                return {
                    'available': True,
                    'last_claimed_at': last_claimed,
                    'next_available_at': next_available,
                    'amount': 5,
                    'cooldown_hours': 0,
                    'cooldown_minutes': 0
                }
            else:
                remaining = next_available - now
                return {
                    'available': False,
                    'last_claimed_at': last_claimed,
                    'next_available_at': next_available,
                    'amount': 5,
                    'cooldown_hours': remaining.seconds // 3600,
                    'cooldown_minutes': (remaining.seconds % 3600) // 60
                }
        
        return {
            'available': True,
            'last_claimed_at': None,
            'next_available_at': None,
            'amount': 5,
            'cooldown_hours': 0,
            'cooldown_minutes': 0
        }

    @staticmethod
    async def claim_daily_bonus(telegram_id: int, amount: float) -> bool:
        """
        Claim daily bonus for user
        
        Args:
            telegram_id: int - User's Telegram ID
            amount: float - Bonus amount
        
        Returns:
            bool: True if successful
        """
        # Check if already claimed today
        status = await BonusRepository.get_daily_bonus_status(telegram_id)
        
        if not status['available']:
            logger.warning(f"Daily bonus not available for user {telegram_id}")
            return False
        
        # Record bonus claim
        bonus_id = await BonusRepository.record_bonus_claim(
            telegram_id=telegram_id,
            bonus_type='daily',
            amount=amount,
            metadata={'claimed_via': 'user_command'}
        )
        
        if bonus_id:
            logger.info(f"Daily bonus of {amount} ETB claimed for user {telegram_id}")
            return True
        
        return False

    @staticmethod
    async def get_daily_bonus_streak(telegram_id: int) -> int:
        """
        Get user's daily bonus claim streak
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            int: Current streak count
        """
        query = """
            SELECT claimed_at
            FROM bonus_claims
            WHERE telegram_id = $1
            AND bonus_type = 'daily'
            AND status = 'claimed'
            ORDER BY claimed_at DESC
        """
        
        results = await Database.fetch_all(query, telegram_id)
        
        if not results:
            return 0
        
        streak = 1
        prev_date = results[0]['claimed_at'].date()
        
        for row in results[1:]:
            current_date = row['claimed_at'].date()
            if (prev_date - current_date).days == 1:
                streak += 1
                prev_date = current_date
            else:
                break
        
        return streak

    # ==================== ADMIN BONUS ====================

    @staticmethod
    async def grant_admin_bonus(
        telegram_id: int,
        amount: float,
        admin_id: int,
        reason: str
    ) -> bool:
        """
        Grant admin bonus to user
        
        Args:
            telegram_id: int - User's Telegram ID
            amount: float - Bonus amount
            admin_id: int - Admin's Telegram ID
            reason: str - Reason for bonus
        
        Returns:
            bool: True if successful
        """
        # Record bonus claim
        bonus_id = await BonusRepository.record_bonus_claim(
            telegram_id=telegram_id,
            bonus_type='admin',
            amount=amount,
            metadata={
                'admin_id': admin_id,
                'reason': reason,
                'granted_at': datetime.utcnow().isoformat()
            },
            status='claimed'
        )
        
        if bonus_id:
            logger.info(f"Admin {admin_id} granted {amount} ETB bonus to user {telegram_id} - Reason: {reason}")
            return True
        
        return False

    # ==================== BONUS STATISTICS ====================

    @staticmethod
    async def get_bonus_stats(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        bonus_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get bonus statistics for reporting
        
        Args:
            start_date: datetime - Start date
            end_date: datetime - End date
            bonus_type: str - Filter by bonus type
        
        Returns:
            dict: Bonus statistics
        """
        query = """
            SELECT 
                COUNT(*) as total_claims,
                COUNT(DISTINCT telegram_id) as unique_users,
                COALESCE(SUM(amount), 0) as total_amount,
                AVG(amount) as average_amount
            FROM bonus_claims
            WHERE status = 'claimed'
        """
        params = []
        param_index = 1
        
        if start_date:
            query += f" AND claimed_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND claimed_at <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        if bonus_type:
            query += f" AND bonus_type = ${param_index}"
            params.append(bonus_type)
            param_index += 1
        
        result = await Database.fetch_one(query, *params)
        
        stats = {
            'total_claims': result['total_claims'] if result else 0,
            'unique_users': result['unique_users'] if result else 0,
            'total_amount': float(result['total_amount']) if result else 0.0,
            'average_amount': float(result['average_amount']) if result and result['average_amount'] else 0.0
        }
        
        # Get breakdown by bonus type
        breakdown_query = """
            SELECT 
                bonus_type,
                COUNT(*) as claim_count,
                COALESCE(SUM(amount), 0) as total_amount
            FROM bonus_claims
            WHERE status = 'claimed'
        """
        breakdown_params = []
        breakdown_index = 1
        
        if start_date:
            breakdown_query += f" AND claimed_at >= ${breakdown_index}"
            breakdown_params.append(start_date)
            breakdown_index += 1
        
        if end_date:
            breakdown_query += f" AND claimed_at <= ${breakdown_index}"
            breakdown_params.append(end_date)
            breakdown_index += 1
        
        breakdown_query += " GROUP BY bonus_type ORDER BY total_amount DESC"
        
        breakdown_results = await Database.fetch_all(breakdown_query, *breakdown_params)
        stats['breakdown'] = [dict(row) for row in breakdown_results]
        
        return stats

    @staticmethod
    async def get_daily_bonus_stats(date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get daily bonus statistics
        
        Args:
            date: datetime - Specific date (default: today)
        
        Returns:
            dict: Daily bonus statistics
        """
        if date is None:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        next_date = date.replace(day=date.day + 1) if date.day < 31 else date.replace(month=date.month + 1, day=1)
        
        query = """
            SELECT 
                COUNT(*) as total_claims,
                COUNT(DISTINCT telegram_id) as unique_users,
                COALESCE(SUM(amount), 0) as total_amount
            FROM bonus_claims
            WHERE bonus_type = 'daily'
            AND status = 'claimed'
            AND claimed_at >= $1 AND claimed_at < $2
        """
        
        result = await Database.fetch_one(query, date, next_date)
        
        if result:
            return {
                'date': date,
                'total_claims': result['total_claims'] or 0,
                'unique_users': result['unique_users'] or 0,
                'total_amount': float(result['total_amount'] or 0)
            }
        
        return {
            'date': date,
            'total_claims': 0,
            'unique_users': 0,
            'total_amount': 0.0
        }

    @staticmethod
    async def get_weekly_bonus_stats() -> List[Dict[str, Any]]:
        """
        Get weekly bonus statistics (last 7 days)
        
        Returns:
            list: Weekly statistics by day
        """
        stats = []
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            daily_stats = await BonusRepository.get_daily_bonus_stats(date)
            stats.append(daily_stats)
        
        return stats

    @staticmethod
    async def get_monthly_bonus_stats(year: int, month: int) -> List[Dict[str, Any]]:
        """
        Get monthly bonus statistics
        
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
            daily_stats = await BonusRepository.get_daily_bonus_stats(date)
            stats.append(daily_stats)
        
        return stats

    @staticmethod
    async def get_top_bonus_recipients(
        bonus_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get users who received the most bonus amounts
        
        Args:
            bonus_type: str - Filter by bonus type
            limit: int - Number of users to return
        
        Returns:
            list: List of top bonus recipients
        """
        query = """
            SELECT 
                b.telegram_id,
                u.first_name,
                u.username,
                COUNT(*) as total_claims,
                COALESCE(SUM(b.amount), 0) as total_amount
            FROM bonus_claims b
            LEFT JOIN users u ON b.telegram_id = u.telegram_id
            WHERE b.status = 'claimed'
        """
        params = []
        param_index = 1
        
        if bonus_type:
            query += f" AND b.bonus_type = ${param_index}"
            params.append(bonus_type)
            param_index += 1
        
        query += f" GROUP BY b.telegram_id, u.first_name, u.username"
        query += f" ORDER BY total_amount DESC LIMIT ${param_index}"
        params.append(limit)
        
        results = await Database.fetch_all(query, *params)
        return [dict(row) for row in results]

    # ==================== BONUS VALIDATION ====================

    @staticmethod
    async def is_bonus_eligible(
        telegram_id: int,
        bonus_type: str
    ) -> Dict[str, Any]:
        """
        Check if user is eligible for a specific bonus
        
        Args:
            telegram_id: int - User's Telegram ID
            bonus_type: str - Type of bonus (welcome, daily)
        
        Returns:
            dict: Eligibility status with reason
        """
        if bonus_type == 'welcome':
            user = await Database.fetch_one(
                "SELECT registered, welcome_bonus_claimed FROM users WHERE telegram_id = $1",
                telegram_id
            )
            
            if not user:
                return {'eligible': False, 'reason': 'User not found'}
            
            if not user['registered']:
                return {'eligible': False, 'reason': 'Complete registration first'}
            
            if user['welcome_bonus_claimed']:
                return {'eligible': False, 'reason': 'Welcome bonus already claimed'}
            
            return {'eligible': True, 'reason': 'Available'}
        
        elif bonus_type == 'daily':
            status = await BonusRepository.get_daily_bonus_status(telegram_id)
            
            if status['available']:
                return {'eligible': True, 'reason': 'Available'}
            else:
                return {
                    'eligible': False,
                    'reason': f"Next available in {status['cooldown_hours']}h {status['cooldown_minutes']}m"
                }
        
        return {'eligible': False, 'reason': 'Invalid bonus type'}

    @staticmethod
    async def expire_old_pending_bonuses(days: int = 7) -> int:
        """
        Expire old pending bonus claims
        
        Args:
            days: int - Days after which pending bonuses expire
        
        Returns:
            int: Number of expired bonuses
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = """
            UPDATE bonus_claims
            SET status = 'expired', updated_at = NOW()
            WHERE status = 'pending'
            AND claimed_at < $1
            RETURNING id
        """
        
        results = await Database.fetch_all(query, cutoff_date)
        expired_count = len(results)
        
        if expired_count > 0:
            logger.info(f"Expired {expired_count} old pending bonus claims")
        
        return expired_count


# Import timedelta for date calculations
from datetime import timedelta