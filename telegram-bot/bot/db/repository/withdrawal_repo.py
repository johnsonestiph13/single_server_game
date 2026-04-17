# telegram-bot/bot/db/repository/withdrawal_repo.py
# Estif Bingo 24/7 - Withdrawal Repository
# Handles all database operations for withdrawal requests

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from bot.db.database import Database

logger = logging.getLogger(__name__)


class WithdrawalRepository:
    """Repository for withdrawal request database operations"""

    @staticmethod
    async def create(withdrawal_data: Dict[str, Any]) -> int:
        """
        Create a new withdrawal request
        
        Args:
            withdrawal_data: Dictionary containing:
                - telegram_id: int
                - amount: float
                - method: str (CBE, ABYSSINIA, TELEBIRR, MPESA)
                - method_name: str (full name)
                - details_encrypted: str (encrypted bank/phone details)
                - session_id: str (unique session identifier)
                - status: str (default 'pending')
                - created_at: datetime (optional)
        
        Returns:
            int: ID of the created withdrawal request
        """
        query = """
            INSERT INTO withdrawals (
                telegram_id, amount, method, method_name, 
                details_encrypted, session_id, status, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, COALESCE($8, NOW()))
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            withdrawal_data['telegram_id'],
            withdrawal_data['amount'],
            withdrawal_data['method'],
            withdrawal_data.get('method_name', withdrawal_data['method']),
            withdrawal_data['details_encrypted'],
            withdrawal_data.get('session_id'),
            withdrawal_data.get('status', 'pending'),
            withdrawal_data.get('created_at')
        )
        
        withdrawal_id = result['id'] if result else None
        logger.info(f"Created withdrawal request #{withdrawal_id} for user {withdrawal_data['telegram_id']}")
        
        return withdrawal_id

    @staticmethod
    async def get_by_id(withdrawal_id: int) -> Optional[Dict[str, Any]]:
        """
        Get withdrawal request by ID
        
        Args:
            withdrawal_id: int - Withdrawal request ID
        
        Returns:
            dict: Withdrawal request data or None if not found
        """
        query = """
            SELECT 
                w.*,
                u.first_name,
                u.username,
                u.phone_last4
            FROM withdrawals w
            LEFT JOIN users u ON w.telegram_id = u.telegram_id
            WHERE w.id = $1
        """
        
        result = await Database.fetch_one(query, withdrawal_id)
        return dict(result) if result else None

    @staticmethod
    async def get_by_session_id(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get withdrawal request by session ID
        
        Args:
            session_id: str - Unique session identifier
        
        Returns:
            dict: Withdrawal request data or None if not found
        """
        query = """
            SELECT * FROM withdrawals
            WHERE session_id = $1
        """
        
        result = await Database.fetch_one(query, session_id)
        return dict(result) if result else None

    @staticmethod
    async def get_by_telegram_id(
        telegram_id: int, 
        limit: int = 10, 
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get withdrawal requests for a specific user
        
        Args:
            telegram_id: int - User's Telegram ID
            limit: int - Maximum number of records
            offset: int - Pagination offset
            status: str - Filter by status (pending, approved, rejected)
        
        Returns:
            list: List of withdrawal requests
        """
        query = """
            SELECT * FROM withdrawals
            WHERE telegram_id = $1
        """
        params = [telegram_id]
        param_index = 2
        
        if status:
            query += f" AND status = ${param_index}"
            params.append(status)
            param_index += 1
        
        query += f" ORDER BY created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.append(limit)
        params.append(offset)
        
        results = await Database.fetch_all(query, *params)
        return [dict(row) for row in results]

    @staticmethod
    async def get_pending(limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all pending withdrawal requests
        
        Args:
            limit: int - Maximum number of records
        
        Returns:
            list: List of pending withdrawal requests
        """
        query = """
            SELECT 
                w.*,
                u.first_name,
                u.username,
                u.phone_last4
            FROM withdrawals w
            LEFT JOIN users u ON w.telegram_id = u.telegram_id
            WHERE w.status = 'pending'
            ORDER BY w.created_at ASC
            LIMIT $1
        """
        
        results = await Database.fetch_all(query, limit)
        return [dict(row) for row in results]

    @staticmethod
    async def count_pending() -> int:
        """
        Count pending withdrawal requests
        
        Returns:
            int: Number of pending requests
        """
        query = """
            SELECT COUNT(*) as count
            FROM withdrawals
            WHERE status = 'pending'
        """
        
        result = await Database.fetch_one(query)
        return result['count'] if result else 0

    @staticmethod
    async def sum_pending() -> float:
        """
        Get total amount of pending withdrawals
        
        Returns:
            float: Total pending amount
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM withdrawals
            WHERE status = 'pending'
        """
        
        result = await Database.fetch_one(query)
        return float(result['total']) if result else 0.0

    @staticmethod
    async def update_status(
        withdrawal_id: int, 
        status: str, 
        admin_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update withdrawal request status
        
        Args:
            withdrawal_id: int - Withdrawal request ID
            status: str - New status (pending, approved, rejected)
            admin_id: int - Admin who processed the request
            notes: str - Optional admin notes
        
        Returns:
            bool: True if successful, False otherwise
        """
        query = """
            UPDATE withdrawals
            SET 
                status = $2,
                admin_id = COALESCE($3, admin_id),
                notes = COALESCE($4, notes),
                processed_at = NOW(),
                updated_at = NOW()
            WHERE id = $1
            RETURNING id
        """
        
        result = await Database.fetch_one(query, withdrawal_id, status, admin_id, notes)
        
        if result:
            logger.info(f"Withdrawal #{withdrawal_id} status updated to {status}")
            return True
        
        logger.warning(f"Failed to update withdrawal #{withdrawal_id} status to {status}")
        return False

    @staticmethod
    async def get_stats(telegram_id: int) -> Dict[str, Any]:
        """
        Get withdrawal statistics for a user
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            dict: Statistics including total, count, etc.
        """
        query = """
            SELECT 
                COUNT(*) as total_requests,
                COALESCE(SUM(amount), 0) as total_amount,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                COALESCE(SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END), 0) as pending_amount,
                COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_count,
                COALESCE(SUM(CASE WHEN status = 'approved' THEN amount ELSE 0 END), 0) as approved_amount,
                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count,
                COALESCE(SUM(CASE WHEN status = 'rejected' THEN amount ELSE 0 END), 0) as rejected_amount,
                MAX(created_at) as last_request_at
            FROM withdrawals
            WHERE telegram_id = $1
        """
        
        result = await Database.fetch_one(query, telegram_id)
        
        if result:
            return {
                'total_requests': result['total_requests'] or 0,
                'total_amount': float(result['total_amount'] or 0),
                'pending_count': result['pending_count'] or 0,
                'pending_amount': float(result['pending_amount'] or 0),
                'approved_count': result['approved_count'] or 0,
                'approved_amount': float(result['approved_amount'] or 0),
                'rejected_count': result['rejected_count'] or 0,
                'rejected_amount': float(result['rejected_amount'] or 0),
                'last_request_at': result['last_request_at']
            }
        
        return {
            'total_requests': 0,
            'total_amount': 0.0,
            'pending_count': 0,
            'pending_amount': 0.0,
            'approved_count': 0,
            'approved_amount': 0.0,
            'rejected_count': 0,
            'rejected_amount': 0.0,
            'last_request_at': None
        }

    @staticmethod
    async def get_all(
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all withdrawal requests with filters (admin only)
        
        Args:
            limit: int - Maximum number of records
            offset: int - Pagination offset
            status: str - Filter by status
            start_date: datetime - Filter by start date
            end_date: datetime - Filter by end date
        
        Returns:
            list: List of withdrawal requests
        """
        query = """
            SELECT 
                w.*,
                u.first_name,
                u.username,
                u.phone_last4
            FROM withdrawals w
            LEFT JOIN users u ON w.telegram_id = u.telegram_id
            WHERE 1=1
        """
        params = []
        param_index = 1
        
        if status:
            query += f" AND w.status = ${param_index}"
            params.append(status)
            param_index += 1
        
        if start_date:
            query += f" AND w.created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND w.created_at <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        query += f" ORDER BY w.created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.append(limit)
        params.append(offset)
        
        results = await Database.fetch_all(query, *params)
        return [dict(row) for row in results]

    @staticmethod
    async def get_total_amount_by_status(status: str) -> float:
        """
        Get total amount for withdrawals with specific status
        
        Args:
            status: str - Status (pending, approved, rejected)
        
        Returns:
            float: Total amount
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM withdrawals
            WHERE status = $1
        """
        
        result = await Database.fetch_one(query, status)
        return float(result['total']) if result else 0.0

    @staticmethod
    async def get_daily_stats(date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get daily withdrawal statistics
        
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
                COUNT(*) as total_count,
                COALESCE(SUM(amount), 0) as total_amount,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
                COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved_count,
                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count
            FROM withdrawals
            WHERE created_at >= $1 AND created_at < $2
        """
        
        result = await Database.fetch_one(query, date, next_date)
        
        if result:
            return {
                'date': date,
                'total_count': result['total_count'] or 0,
                'total_amount': float(result['total_amount'] or 0),
                'pending_count': result['pending_count'] or 0,
                'approved_count': result['approved_count'] or 0,
                'rejected_count': result['rejected_count'] or 0
            }
        
        return {
            'date': date,
            'total_count': 0,
            'total_amount': 0.0,
            'pending_count': 0,
            'approved_count': 0,
            'rejected_count': 0
        }

    @staticmethod
    async def delete_old_completed(days: int = 90) -> int:
        """
        Delete old completed withdrawal records (approved/rejected older than X days)
        
        Args:
            days: int - Age in days for deletion
        
        Returns:
            int: Number of deleted records
        """
        cutoff_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=days)
        
        query = """
            DELETE FROM withdrawals
            WHERE status IN ('approved', 'rejected')
            AND created_at < $1
            RETURNING id
        """
        
        results = await Database.fetch_all(query, cutoff_date)
        deleted_count = len(results)
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old withdrawal records older than {days} days")
        
        return deleted_count

    @staticmethod
    async def get_user_last_withdrawal(telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's most recent withdrawal request
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            dict: Most recent withdrawal or None
        """
        query = """
            SELECT * FROM withdrawals
            WHERE telegram_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = await Database.fetch_one(query, telegram_id)
        return dict(result) if result else None

    @staticmethod
    async def is_duplicate_session(session_id: str) -> bool:
        """
        Check if a session ID already exists (prevent duplicates)
        
        Args:
            session_id: str - Session identifier
        
        Returns:
            bool: True if duplicate exists
        """
        query = """
            SELECT id FROM withdrawals
            WHERE session_id = $1
        """
        
        result = await Database.fetch_one(query, session_id)
        return result is not None


# Import timedelta for delete_old_completed
from datetime import timedelta