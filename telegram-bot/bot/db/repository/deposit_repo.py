# telegram-bot/bot/db/repository/deposit_repo.py
# Estif Bingo 24/7 - Deposit Repository
# Handles all database operations for deposit requests

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bot.db.database import Database

logger = logging.getLogger(__name__)


class DepositRepository:
    """Repository for deposit request database operations"""

    @staticmethod
    async def create(deposit_data: Dict[str, Any]) -> int:
        """
        Create a new deposit request
        
        Args:
            deposit_data: Dictionary containing:
                - telegram_id: int
                - amount: float
                - method: str (CBE, ABYSSINIA, TELEBIRR, MPESA)
                - account_number: str (bank account or phone number)
                - transaction_id: str (user's payment reference)
                - photo_file_id: str (Telegram file ID of screenshot)
                - idempotency_key: str (unique key to prevent duplicates)
                - status: str (default 'pending')
                - created_at: datetime (optional)
        
        Returns:
            int: ID of the created deposit request
        """
        query = """
            INSERT INTO deposits (
                telegram_id, amount, method, account_number,
                transaction_id, photo_file_id, idempotency_key, 
                status, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, COALESCE($9, NOW()))
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            deposit_data['telegram_id'],
            deposit_data['amount'],
            deposit_data['method'],
            deposit_data.get('account_number'),
            deposit_data['transaction_id'],
            deposit_data.get('photo_file_id'),
            deposit_data.get('idempotency_key'),
            deposit_data.get('status', 'pending'),
            deposit_data.get('created_at')
        )
        
        deposit_id = result['id'] if result else None
        logger.info(f"Created deposit request #{deposit_id} for user {deposit_data['telegram_id']} - {deposit_data['amount']} ETB")
        
        return deposit_id

    @staticmethod
    async def get_by_id(deposit_id: int) -> Optional[Dict[str, Any]]:
        """
        Get deposit request by ID
        
        Args:
            deposit_id: int - Deposit request ID
        
        Returns:
            dict: Deposit request data or None if not found
        """
        query = """
            SELECT 
                d.*,
                u.first_name,
                u.username,
                u.phone_last4
            FROM deposits d
            LEFT JOIN users u ON d.telegram_id = u.telegram_id
            WHERE d.id = $1
        """
        
        result = await Database.fetch_one(query, deposit_id)
        return dict(result) if result else None

    @staticmethod
    async def get_by_transaction_id(transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get deposit request by transaction ID
        
        Args:
            transaction_id: str - User's payment reference
        
        Returns:
            dict: Deposit request data or None if not found
        """
        query = """
            SELECT * FROM deposits
            WHERE transaction_id = $1
        """
        
        result = await Database.fetch_one(query, transaction_id)
        return dict(result) if result else None

    @staticmethod
    async def get_by_idempotency_key(idempotency_key: str) -> Optional[Dict[str, Any]]:
        """
        Get deposit request by idempotency key (prevent duplicates)
        
        Args:
            idempotency_key: str - Unique idempotency key
        
        Returns:
            dict: Deposit request data or None if not found
        """
        query = """
            SELECT * FROM deposits
            WHERE idempotency_key = $1
        """
        
        result = await Database.fetch_one(query, idempotency_key)
        return dict(result) if result else None

    @staticmethod
    async def get_by_telegram_id(
        telegram_id: int, 
        limit: int = 10, 
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get deposit requests for a specific user
        
        Args:
            telegram_id: int - User's Telegram ID
            limit: int - Maximum number of records
            offset: int - Pagination offset
            status: str - Filter by status (pending, approved, rejected)
        
        Returns:
            list: List of deposit requests
        """
        query = """
            SELECT * FROM deposits
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
        Get all pending deposit requests
        
        Args:
            limit: int - Maximum number of records
        
        Returns:
            list: List of pending deposit requests
        """
        query = """
            SELECT 
                d.*,
                u.first_name,
                u.username,
                u.phone_last4
            FROM deposits d
            LEFT JOIN users u ON d.telegram_id = u.telegram_id
            WHERE d.status = 'pending'
            ORDER BY d.created_at ASC
            LIMIT $1
        """
        
        results = await Database.fetch_all(query, limit)
        return [dict(row) for row in results]

    @staticmethod
    async def count_pending() -> int:
        """
        Count pending deposit requests
        
        Returns:
            int: Number of pending requests
        """
        query = """
            SELECT COUNT(*) as count
            FROM deposits
            WHERE status = 'pending'
        """
        
        result = await Database.fetch_one(query)
        return result['count'] if result else 0

    @staticmethod
    async def sum_pending() -> float:
        """
        Get total amount of pending deposits
        
        Returns:
            float: Total pending amount
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM deposits
            WHERE status = 'pending'
        """
        
        result = await Database.fetch_one(query)
        return float(result['total']) if result else 0.0

    @staticmethod
    async def update_status(
        deposit_id: int, 
        status: str, 
        admin_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update deposit request status
        
        Args:
            deposit_id: int - Deposit request ID
            status: str - New status (pending, approved, rejected)
            admin_id: int - Admin who processed the request
            notes: str - Optional admin notes
        
        Returns:
            bool: True if successful, False otherwise
        """
        query = """
            UPDATE deposits
            SET 
                status = $2,
                admin_id = COALESCE($3, admin_id),
                notes = COALESCE($4, notes),
                processed_at = NOW(),
                updated_at = NOW()
            WHERE id = $1
            RETURNING id
        """
        
        result = await Database.fetch_one(query, deposit_id, status, admin_id, notes)
        
        if result:
            logger.info(f"Deposit #{deposit_id} status updated to {status}")
            return True
        
        logger.warning(f"Failed to update deposit #{deposit_id} status to {status}")
        return False

    @staticmethod
    async def get_stats(telegram_id: int) -> Dict[str, Any]:
        """
        Get deposit statistics for a user
        
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
            FROM deposits
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
        Get all deposit requests with filters (admin only)
        
        Args:
            limit: int - Maximum number of records
            offset: int - Pagination offset
            status: str - Filter by status
            start_date: datetime - Filter by start date
            end_date: datetime - Filter by end date
        
        Returns:
            list: List of deposit requests
        """
        query = """
            SELECT 
                d.*,
                u.first_name,
                u.username,
                u.phone_last4
            FROM deposits d
            LEFT JOIN users u ON d.telegram_id = u.telegram_id
            WHERE 1=1
        """
        params = []
        param_index = 1
        
        if status:
            query += f" AND d.status = ${param_index}"
            params.append(status)
            param_index += 1
        
        if start_date:
            query += f" AND d.created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND d.created_at <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        query += f" ORDER BY d.created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.append(limit)
        params.append(offset)
        
        results = await Database.fetch_all(query, *params)
        return [dict(row) for row in results]

    @staticmethod
    async def get_total_amount_by_status(status: str) -> float:
        """
        Get total amount for deposits with specific status
        
        Args:
            status: str - Status (pending, approved, rejected)
        
        Returns:
            float: Total amount
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM deposits
            WHERE status = $1
        """
        
        result = await Database.fetch_one(query, status)
        return float(result['total']) if result else 0.0

    @staticmethod
    async def get_daily_stats(date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get daily deposit statistics
        
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
            FROM deposits
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
    async def get_weekly_stats() -> List[Dict[str, Any]]:
        """
        Get weekly deposit statistics (last 7 days)
        
        Returns:
            list: Weekly statistics by day
        """
        stats = []
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            daily_stats = await DepositRepository.get_daily_stats(date)
            stats.append(daily_stats)
        
        return stats

    @staticmethod
    async def get_monthly_stats(year: int, month: int) -> List[Dict[str, Any]]:
        """
        Get monthly deposit statistics
        
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
            daily_stats = await DepositRepository.get_daily_stats(date)
            stats.append(daily_stats)
        
        return stats

    @staticmethod
    async def delete_old_completed(days: int = 90) -> int:
        """
        Delete old completed deposit records (approved/rejected older than X days)
        
        Args:
            days: int - Age in days for deletion
        
        Returns:
            int: Number of deleted records
        """
        cutoff_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=days)
        
        query = """
            DELETE FROM deposits
            WHERE status IN ('approved', 'rejected')
            AND created_at < $1
            RETURNING id
        """
        
        results = await Database.fetch_all(query, cutoff_date)
        deleted_count = len(results)
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old deposit records older than {days} days")
        
        return deleted_count

    @staticmethod
    async def get_user_last_deposit(telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's most recent deposit request
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            dict: Most recent deposit or None
        """
        query = """
            SELECT * FROM deposits
            WHERE telegram_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = await Database.fetch_one(query, telegram_id)
        return dict(result) if result else None

    @staticmethod
    async def is_duplicate_transaction(transaction_id: str) -> bool:
        """
        Check if a transaction ID already exists (prevent duplicates)
        
        Args:
            transaction_id: str - Transaction reference
        
        Returns:
            bool: True if duplicate exists
        """
        query = """
            SELECT id FROM deposits
            WHERE transaction_id = $1
        """
        
        result = await Database.fetch_one(query, transaction_id)
        return result is not None

    @staticmethod
    async def is_duplicate_idempotency(idempotency_key: str) -> bool:
        """
        Check if an idempotency key already exists
        
        Args:
            idempotency_key: str - Idempotency key
        
        Returns:
            bool: True if duplicate exists
        """
        query = """
            SELECT id FROM deposits
            WHERE idempotency_key = $1
        """
        
        result = await Database.fetch_one(query, idempotency_key)
        return result is not None

    @staticmethod
    async def get_photo_file_id(deposit_id: int) -> Optional[str]:
        """
        Get photo file ID for a deposit request
        
        Args:
            deposit_id: int - Deposit request ID
        
        Returns:
            str: Telegram file ID or None
        """
        query = """
            SELECT photo_file_id FROM deposits
            WHERE id = $1
        """
        
        result = await Database.fetch_one(query, deposit_id)
        return result['photo_file_id'] if result else None


# Import timedelta for date calculations
from datetime import timedelta