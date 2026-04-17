# telegram-bot/bot/db/repository/transfer_repo.py
# Estif Bingo 24/7 - Transfer Repository
# Handles all database operations for balance transfers between users

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bot.db.database import Database

logger = logging.getLogger(__name__)


class TransferRepository:
    """Repository for transfer record database operations"""

    @staticmethod
    async def create(transfer_data: Dict[str, Any]) -> str:
        """
        Create a new transfer record
        
        Args:
            transfer_data: Dictionary containing:
                - transfer_id: str (unique identifier)
                - sender_id: int
                - receiver_id: int
                - receiver_phone: str (optional)
                - amount: float
                - fee: float (default 0)
                - total: float (amount + fee)
                - status: str (default 'completed')
                - sender_balance_before: float (optional)
                - sender_balance_after: float (optional)
                - receiver_balance_before: float (optional)
                - receiver_balance_after: float (optional)
                - metadata: dict (optional)
                - created_at: datetime (optional)
        
        Returns:
            str: Transfer ID
        """
        query = """
            INSERT INTO transfers (
                transfer_id, sender_id, receiver_id, receiver_phone,
                amount, fee, total, status, sender_balance_before,
                sender_balance_after, receiver_balance_before,
                receiver_balance_after, metadata, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, COALESCE($14, NOW()))
            RETURNING transfer_id
        """
        
        result = await Database.fetch_one(
            query,
            transfer_data['transfer_id'],
            transfer_data['sender_id'],
            transfer_data['receiver_id'],
            transfer_data.get('receiver_phone'),
            transfer_data['amount'],
            transfer_data.get('fee', 0),
            transfer_data.get('total', transfer_data['amount']),
            transfer_data.get('status', 'completed'),
            transfer_data.get('sender_balance_before'),
            transfer_data.get('sender_balance_after'),
            transfer_data.get('receiver_balance_before'),
            transfer_data.get('receiver_balance_after'),
            transfer_data.get('metadata'),
            transfer_data.get('created_at')
        )
        
        transfer_id = result['transfer_id'] if result else None
        logger.info(f"Created transfer {transfer_id}: {transfer_data['amount']} ETB from {transfer_data['sender_id']} to {transfer_data['receiver_id']}")
        
        return transfer_id

    @staticmethod
    async def get_by_id(transfer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get transfer record by transfer ID
        
        Args:
            transfer_id: str - Unique transfer identifier
        
        Returns:
            dict: Transfer data or None if not found
        """
        query = """
            SELECT 
                t.*,
                s.first_name as sender_name,
                s.username as sender_username,
                r.first_name as receiver_name,
                r.username as receiver_username
            FROM transfers t
            LEFT JOIN users s ON t.sender_id = s.telegram_id
            LEFT JOIN users r ON t.receiver_id = r.telegram_id
            WHERE t.transfer_id = $1
        """
        
        result = await Database.fetch_one(query, transfer_id)
        return dict(result) if result else None

    @staticmethod
    async def get_by_sender(
        sender_id: int, 
        limit: int = 10, 
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transfers sent by a specific user
        
        Args:
            sender_id: int - Sender's Telegram ID
            limit: int - Maximum number of records
            offset: int - Pagination offset
            start_date: datetime - Filter by start date
            end_date: datetime - Filter by end date
        
        Returns:
            list: List of transfers sent by the user
        """
        query = """
            SELECT 
                t.*,
                r.first_name as receiver_name,
                r.username as receiver_username
            FROM transfers t
            LEFT JOIN users r ON t.receiver_id = r.telegram_id
            WHERE t.sender_id = $1
        """
        params = [sender_id]
        param_index = 2
        
        if start_date:
            query += f" AND t.created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND t.created_at <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        query += f" ORDER BY t.created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.append(limit)
        params.append(offset)
        
        results = await Database.fetch_all(query, *params)
        return [dict(row) for row in results]

    @staticmethod
    async def get_by_receiver(
        receiver_id: int, 
        limit: int = 10, 
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transfers received by a specific user
        
        Args:
            receiver_id: int - Receiver's Telegram ID
            limit: int - Maximum number of records
            offset: int - Pagination offset
            start_date: datetime - Filter by start date
            end_date: datetime - Filter by end date
        
        Returns:
            list: List of transfers received by the user
        """
        query = """
            SELECT 
                t.*,
                s.first_name as sender_name,
                s.username as sender_username
            FROM transfers t
            LEFT JOIN users s ON t.sender_id = s.telegram_id
            WHERE t.receiver_id = $1
        """
        params = [receiver_id]
        param_index = 2
        
        if start_date:
            query += f" AND t.created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND t.created_at <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        query += f" ORDER BY t.created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.append(limit)
        params.append(offset)
        
        results = await Database.fetch_all(query, *params)
        return [dict(row) for row in results]

    @staticmethod
    async def get_user_transfers(
        telegram_id: int, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all transfers (sent and received) for a user
        
        Args:
            telegram_id: int - User's Telegram ID
            limit: int - Maximum number of records
            offset: int - Pagination offset
        
        Returns:
            list: List of transfers (both sent and received)
        """
        query = """
            SELECT 
                t.*,
                CASE 
                    WHEN t.sender_id = $1 THEN 'sent'
                    ELSE 'received'
                END as direction,
                CASE 
                    WHEN t.sender_id = $1 THEN r.first_name
                    ELSE s.first_name
                END as other_party_name,
                CASE 
                    WHEN t.sender_id = $1 THEN r.username
                    ELSE s.username
                END as other_party_username
            FROM transfers t
            LEFT JOIN users s ON t.sender_id = s.telegram_id
            LEFT JOIN users r ON t.receiver_id = r.telegram_id
            WHERE t.sender_id = $1 OR t.receiver_id = $1
            ORDER BY t.created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        results = await Database.fetch_all(query, telegram_id, limit, offset)
        return [dict(row) for row in results]

    @staticmethod
    async def get_stats(telegram_id: int) -> Dict[str, Any]:
        """
        Get transfer statistics for a user
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            dict: Statistics including total sent, received, etc.
        """
        query = """
            SELECT 
                COUNT(CASE WHEN sender_id = $1 THEN 1 END) as sent_count,
                COALESCE(SUM(CASE WHEN sender_id = $1 THEN amount ELSE 0 END), 0) as sent_amount,
                COALESCE(SUM(CASE WHEN sender_id = $1 THEN fee ELSE 0 END), 0) as sent_fees,
                COUNT(CASE WHEN receiver_id = $1 THEN 1 END) as received_count,
                COALESCE(SUM(CASE WHEN receiver_id = $1 THEN amount ELSE 0 END), 0) as received_amount
            FROM transfers
            WHERE sender_id = $1 OR receiver_id = $1
        """
        
        result = await Database.fetch_one(query, telegram_id)
        
        if result:
            return {
                'sent_count': result['sent_count'] or 0,
                'sent_amount': float(result['sent_amount'] or 0),
                'sent_fees': float(result['sent_fees'] or 0),
                'received_count': result['received_count'] or 0,
                'received_amount': float(result['received_amount'] or 0)
            }
        
        return {
            'sent_count': 0,
            'sent_amount': 0.0,
            'sent_fees': 0.0,
            'received_count': 0,
            'received_amount': 0.0
        }

    @staticmethod
    async def get_daily_stats(date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get daily transfer statistics
        
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
                COALESCE(SUM(fee), 0) as total_fees,
                COUNT(DISTINCT sender_id) as unique_senders,
                COUNT(DISTINCT receiver_id) as unique_receivers
            FROM transfers
            WHERE created_at >= $1 AND created_at < $2
        """
        
        result = await Database.fetch_one(query, date, next_date)
        
        if result:
            return {
                'date': date,
                'total_count': result['total_count'] or 0,
                'total_amount': float(result['total_amount'] or 0),
                'total_fees': float(result['total_fees'] or 0),
                'unique_senders': result['unique_senders'] or 0,
                'unique_receivers': result['unique_receivers'] or 0
            }
        
        return {
            'date': date,
            'total_count': 0,
            'total_amount': 0.0,
            'total_fees': 0.0,
            'unique_senders': 0,
            'unique_receivers': 0
        }

    @staticmethod
    async def get_weekly_stats() -> List[Dict[str, Any]]:
        """
        Get weekly transfer statistics (last 7 days)
        
        Returns:
            list: Weekly statistics by day
        """
        stats = []
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            daily_stats = await TransferRepository.get_daily_stats(date)
            stats.append(daily_stats)
        
        return stats

    @staticmethod
    async def get_monthly_stats(year: int, month: int) -> List[Dict[str, Any]]:
        """
        Get monthly transfer statistics
        
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
            daily_stats = await TransferRepository.get_daily_stats(date)
            stats.append(daily_stats)
        
        return stats

    @staticmethod
    async def get_top_transfers(limit: int = 10, start_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get largest transfers (by amount)
        
        Args:
            limit: int - Maximum number of records
            start_date: datetime - Filter by start date
        
        Returns:
            list: List of largest transfers
        """
        query = """
            SELECT 
                t.*,
                s.first_name as sender_name,
                s.username as sender_username,
                r.first_name as receiver_name,
                r.username as receiver_username
            FROM transfers t
            LEFT JOIN users s ON t.sender_id = s.telegram_id
            LEFT JOIN users r ON t.receiver_id = r.telegram_id
            WHERE 1=1
        """
        params = []
        param_index = 1
        
        if start_date:
            query += f" AND t.created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        query += f" ORDER BY t.amount DESC LIMIT ${param_index}"
        params.append(limit)
        
        results = await Database.fetch_all(query, *params)
        return [dict(row) for row in results]

    @staticmethod
    async def get_frequent_transfers(limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most frequent transfer relationships
        
        Returns:
            list: List of frequent transfer pairs
        """
        query = """
            SELECT 
                sender_id,
                receiver_id,
                COUNT(*) as transfer_count,
                COALESCE(SUM(amount), 0) as total_amount,
                u1.first_name as sender_name,
                u2.first_name as receiver_name
            FROM transfers t
            LEFT JOIN users u1 ON t.sender_id = u1.telegram_id
            LEFT JOIN users u2 ON t.receiver_id = u2.telegram_id
            GROUP BY sender_id, receiver_id, u1.first_name, u2.first_name
            ORDER BY transfer_count DESC
            LIMIT $1
        """
        
        results = await Database.fetch_all(query, limit)
        return [dict(row) for row in results]

    @staticmethod
    async def is_duplicate_transfer(transfer_id: str) -> bool:
        """
        Check if a transfer ID already exists (prevent duplicates)
        
        Args:
            transfer_id: str - Transfer identifier
        
        Returns:
            bool: True if duplicate exists
        """
        query = """
            SELECT id FROM transfers
            WHERE transfer_id = $1
        """
        
        result = await Database.fetch_one(query, transfer_id)
        return result is not None

    @staticmethod
    async def get_total_transfer_volume(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get total transfer volume within date range
        
        Args:
            start_date: datetime - Start date
            end_date: datetime - End date
        
        Returns:
            dict: Total volume statistics
        """
        query = """
            SELECT 
                COUNT(*) as total_count,
                COALESCE(SUM(amount), 0) as total_amount,
                COALESCE(SUM(fee), 0) as total_fees,
                COUNT(DISTINCT sender_id) as unique_senders,
                COUNT(DISTINCT receiver_id) as unique_receivers
            FROM transfers
            WHERE 1=1
        """
        params = []
        param_index = 1
        
        if start_date:
            query += f" AND created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND created_at <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        result = await Database.fetch_one(query, *params)
        
        if result:
            return {
                'total_count': result['total_count'] or 0,
                'total_amount': float(result['total_amount'] or 0),
                'total_fees': float(result['total_fees'] or 0),
                'unique_senders': result['unique_senders'] or 0,
                'unique_receivers': result['unique_receivers'] or 0
            }
        
        return {
            'total_count': 0,
            'total_amount': 0.0,
            'total_fees': 0.0,
            'unique_senders': 0,
            'unique_receivers': 0
        }

    @staticmethod
    async def delete_old_transfers(days: int = 90) -> int:
        """
        Delete old transfer records (older than X days)
        
        Args:
            days: int - Age in days for deletion
        
        Returns:
            int: Number of deleted records
        """
        cutoff_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=days)
        
        query = """
            DELETE FROM transfers
            WHERE created_at < $1
            RETURNING id
        """
        
        results = await Database.fetch_all(query, cutoff_date)
        deleted_count = len(results)
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old transfer records older than {days} days")
        
        return deleted_count


# Import timedelta for date calculations
from datetime import timedelta