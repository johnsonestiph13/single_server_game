# telegram-bot/bot/db/repository/transaction_repo.py
# Estif Bingo 24/7 - Transaction Repository
# Handles all database operations for financial transactions

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bot.db.database import Database

logger = logging.getLogger(__name__)


class TransactionRepository:
    """Repository for transaction database operations"""

    # ==================== CREATE TRANSACTIONS ====================

    @staticmethod
    async def create(transaction_data: Dict[str, Any]) -> int:
        """
        Create a new transaction record
        
        Args:
            transaction_data: Dictionary containing:
                - user_id: int
                - type: str (deposit, withdrawal, win, cartela_purchase, 
                         transfer_sent, transfer_received, welcome_bonus, 
                         daily_bonus, admin_bonus, admin_adjustment)
                - amount: float (positive for credits, negative for debits)
                - balance_after: float (optional)
                - reference_id: str (optional)
                - metadata: dict (optional)
        
        Returns:
            int: Transaction ID
        """
        query = """
            INSERT INTO transactions (
                user_id, type, amount, balance_after, 
                reference_id, metadata, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            transaction_data['user_id'],
            transaction_data['type'],
            transaction_data['amount'],
            transaction_data.get('balance_after'),
            transaction_data.get('reference_id'),
            transaction_data.get('metadata')
        )
        
        transaction_id = result['id'] if result else None
        
        if transaction_id:
            logger.debug(f"Transaction #{transaction_id} created: {transaction_data['type']} of {transaction_data['amount']} for user {transaction_data['user_id']}")
        
        return transaction_id

    @staticmethod
    async def create_batch(transactions: List[Dict[str, Any]]) -> List[int]:
        """
        Create multiple transaction records in batch
        
        Args:
            transactions: list - List of transaction data dictionaries
        
        Returns:
            list: List of transaction IDs
        """
        transaction_ids = []
        
        for tx_data in transactions:
            tx_id = await TransactionRepository.create(tx_data)
            if tx_id:
                transaction_ids.append(tx_id)
        
        logger.info(f"Created {len(transaction_ids)} batch transactions")
        return transaction_ids

    # ==================== GET TRANSACTIONS ====================

    @staticmethod
    async def get_by_id(transaction_id: int) -> Optional[Dict[str, Any]]:
        """
        Get transaction by ID
        
        Args:
            transaction_id: int - Transaction ID
        
        Returns:
            dict: Transaction data or None if not found
        """
        query = """
            SELECT 
                t.*,
                u.first_name,
                u.username
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.telegram_id
            WHERE t.id = $1
        """
        
        result = await Database.fetch_one(query, transaction_id)
        
        if result:
            tx_dict = dict(result)
            tx_dict['metadata'] = tx_dict.get('metadata')
            return tx_dict
        
        return None

    @staticmethod
    async def get_by_user(
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transactions for a specific user
        
        Args:
            user_id: int - User's Telegram ID
            limit: int - Maximum number of records
            offset: int - Pagination offset
            transaction_type: str - Filter by transaction type
            start_date: datetime - Filter by start date
            end_date: datetime - Filter by end date
        
        Returns:
            list: List of transactions
        """
        query = """
            SELECT * FROM transactions
            WHERE user_id = $1
        """
        params = [user_id]
        param_index = 2
        
        if transaction_type:
            query += f" AND type = ${param_index}"
            params.append(transaction_type)
            param_index += 1
        
        if start_date:
            query += f" AND created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND created_at <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        query += f" ORDER BY created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.append(limit)
        params.append(offset)
        
        results = await Database.fetch_all(query, *params)
        
        transactions = []
        for row in results:
            tx_dict = dict(row)
            tx_dict['metadata'] = tx_dict.get('metadata')
            transactions.append(tx_dict)
        
        return transactions

    @staticmethod
    async def get_by_reference(reference_id: str) -> List[Dict[str, Any]]:
        """
        Get transactions by reference ID
        
        Args:
            reference_id: str - Reference ID (e.g., deposit_id, withdrawal_id)
        
        Returns:
            list: List of transactions
        """
        query = """
            SELECT 
                t.*,
                u.first_name,
                u.username
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.telegram_id
            WHERE t.reference_id = $1
            ORDER BY t.created_at DESC
        """
        
        results = await Database.fetch_all(query, reference_id)
        
        transactions = []
        for row in results:
            tx_dict = dict(row)
            tx_dict['metadata'] = tx_dict.get('metadata')
            transactions.append(tx_dict)
        
        return transactions

    @staticmethod
    async def get_recent(
        user_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent transactions for a user
        
        Args:
            user_id: int - User's Telegram ID
            limit: int - Maximum number of records
        
        Returns:
            list: List of recent transactions
        """
        return await TransactionRepository.get_by_user(user_id, limit=limit)

    @staticmethod
    async def get_paginated(
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> tuple:
        """
        Get paginated transactions with total count
        
        Args:
            user_id: int - User's Telegram ID
            limit: int - Maximum number of records
            offset: int - Pagination offset
        
        Returns:
            tuple: (transactions list, total count)
        """
        # Get total count
        count_query = """
            SELECT COUNT(*) as total
            FROM transactions
            WHERE user_id = $1
        """
        
        total_result = await Database.fetch_one(count_query, user_id)
        total = total_result['total'] if total_result else 0
        
        # Get transactions
        transactions = await TransactionRepository.get_by_user(
            user_id, 
            limit=limit, 
            offset=offset
        )
        
        return transactions, total

    # ==================== TRANSACTION STATISTICS ====================

    @staticmethod
    async def get_stats(user_id: int) -> Dict[str, Any]:
        """
        Get transaction statistics for a user
        
        Args:
            user_id: int - User's Telegram ID
        
        Returns:
            dict: Transaction statistics
        """
        query = """
            SELECT 
                COUNT(CASE WHEN type = 'deposit' THEN 1 END) as deposit_count,
                COALESCE(SUM(CASE WHEN type = 'deposit' THEN amount ELSE 0 END), 0) as deposit_total,
                COUNT(CASE WHEN type = 'withdrawal' THEN 1 END) as withdrawal_count,
                COALESCE(SUM(CASE WHEN type = 'withdrawal' THEN ABS(amount) ELSE 0 END), 0) as withdrawal_total,
                COUNT(CASE WHEN type = 'win' THEN 1 END) as win_count,
                COALESCE(SUM(CASE WHEN type = 'win' THEN amount ELSE 0 END), 0) as win_total,
                COUNT(CASE WHEN type = 'cartela_purchase' THEN 1 END) as cartela_count,
                COALESCE(SUM(CASE WHEN type = 'cartela_purchase' THEN ABS(amount) ELSE 0 END), 0) as cartela_total,
                COUNT(CASE WHEN type = 'transfer_sent' THEN 1 END) as transfer_sent_count,
                COALESCE(SUM(CASE WHEN type = 'transfer_sent' THEN ABS(amount) ELSE 0 END), 0) as transfer_sent_total,
                COUNT(CASE WHEN type = 'transfer_received' THEN 1 END) as transfer_received_count,
                COALESCE(SUM(CASE WHEN type = 'transfer_received' THEN amount ELSE 0 END), 0) as transfer_received_total,
                COUNT(CASE WHEN type LIKE '%bonus%' THEN 1 END) as bonus_count,
                COALESCE(SUM(CASE WHEN type LIKE '%bonus%' THEN amount ELSE 0 END), 0) as bonus_total
            FROM transactions
            WHERE user_id = $1
        """
        
        result = await Database.fetch_one(query, user_id)
        
        if result:
            return {
                'deposit_count': result['deposit_count'] or 0,
                'deposit_total': float(result['deposit_total'] or 0),
                'withdrawal_count': result['withdrawal_count'] or 0,
                'withdrawal_total': float(result['withdrawal_total'] or 0),
                'win_count': result['win_count'] or 0,
                'win_total': float(result['win_total'] or 0),
                'cartela_count': result['cartela_count'] or 0,
                'cartela_total': float(result['cartela_total'] or 0),
                'transfer_sent_count': result['transfer_sent_count'] or 0,
                'transfer_sent_total': float(result['transfer_sent_total'] or 0),
                'transfer_received_count': result['transfer_received_count'] or 0,
                'transfer_received_total': float(result['transfer_received_total'] or 0),
                'bonus_count': result['bonus_count'] or 0,
                'bonus_total': float(result['bonus_total'] or 0),
                'net_profit': float(result['win_total'] or 0) - float(result['cartela_total'] or 0)
            }
        
        return {
            'deposit_count': 0,
            'deposit_total': 0.0,
            'withdrawal_count': 0,
            'withdrawal_total': 0.0,
            'win_count': 0,
            'win_total': 0.0,
            'cartela_count': 0,
            'cartela_total': 0.0,
            'transfer_sent_count': 0,
            'transfer_sent_total': 0.0,
            'transfer_received_count': 0,
            'transfer_received_total': 0.0,
            'bonus_count': 0,
            'bonus_total': 0.0,
            'net_profit': 0.0
        }

    @staticmethod
    async def sum_by_type(transaction_type: str) -> float:
        """
        Get total amount for a specific transaction type across all users
        
        Args:
            transaction_type: str - Transaction type
        
        Returns:
            float: Total amount
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM transactions
            WHERE type = $1
        """
        
        result = await Database.fetch_one(query, transaction_type)
        return float(result['total']) if result else 0.0

    @staticmethod
    async def get_daily_stats(
        date: Optional[datetime] = None,
        transaction_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get daily transaction statistics
        
        Args:
            date: datetime - Specific date (default: today)
            transaction_type: str - Filter by transaction type
        
        Returns:
            dict: Daily statistics
        """
        if date is None:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        next_date = date + timedelta(days=1)
        
        query = """
            SELECT 
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as total_amount,
                COUNT(DISTINCT user_id) as unique_users
            FROM transactions
            WHERE created_at >= $1 AND created_at < $2
        """
        params = [date, next_date]
        
        if transaction_type:
            query += f" AND type = $3"
            params.append(transaction_type)
        
        result = await Database.fetch_one(query, *params)
        
        if result:
            return {
                'date': date,
                'count': result['count'] or 0,
                'total_amount': float(result['total_amount'] or 0),
                'unique_users': result['unique_users'] or 0
            }
        
        return {
            'date': date,
            'count': 0,
            'total_amount': 0.0,
            'unique_users': 0
        }

    @staticmethod
    async def get_weekly_stats(transaction_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get weekly transaction statistics (last 7 days)
        
        Args:
            transaction_type: str - Filter by transaction type
        
        Returns:
            list: Weekly statistics by day
        """
        stats = []
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            daily_stats = await TransactionRepository.get_daily_stats(date, transaction_type)
            stats.append(daily_stats)
        
        return stats

    @staticmethod
    async def get_monthly_stats(
        year: int,
        month: int,
        transaction_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get monthly transaction statistics
        
        Args:
            year: int - Year
            month: int - Month (1-12)
            transaction_type: str - Filter by transaction type
        
        Returns:
            list: Monthly statistics by day
        """
        from calendar import monthrange
        
        stats = []
        days_in_month = monthrange(year, month)[1]
        
        for day in range(1, days_in_month + 1):
            date = datetime(year, month, day, 0, 0, 0)
            daily_stats = await TransactionRepository.get_daily_stats(date, transaction_type)
            stats.append(daily_stats)
        
        return stats

    @staticmethod
    async def get_balance_history(
        user_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get user's balance history over time
        
        Args:
            user_id: int - User's Telegram ID
            days: int - Number of days to look back
        
        Returns:
            list: Balance history by day
        """
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
        
        query = """
            SELECT 
                DATE(created_at) as date,
                SUM(amount) as net_change,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE user_id = $1 AND created_at >= $2
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """
        
        results = await Database.fetch_all(query, user_id, start_date)
        
        # Calculate running balance
        history = []
        running_balance = 0.0
        
        # Get initial balance before the period
        init_query = """
            SELECT balance_after FROM transactions
            WHERE user_id = $1 AND created_at < $2
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        init_result = await Database.fetch_one(init_query, user_id, start_date)
        
        if init_result and init_result['balance_after']:
            running_balance = float(init_result['balance_after'])
        
        for row in results:
            running_balance += float(row['net_change'] or 0)
            history.append({
                'date': row['date'],
                'balance': running_balance,
                'net_change': float(row['net_change'] or 0),
                'transaction_count': row['transaction_count']
            })
        
        return history

    # ==================== ADMIN REPORTS ====================

    @staticmethod
    async def get_platform_stats(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get platform-wide transaction statistics
        
        Args:
            start_date: datetime - Start date
            end_date: datetime - End date
        
        Returns:
            dict: Platform statistics
        """
        query = """
            SELECT 
                COUNT(*) as total_transactions,
                COUNT(DISTINCT user_id) as unique_users,
                COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as total_credits,
                COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) as total_debits,
                COALESCE(SUM(amount), 0) as net_flow
            FROM transactions
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
                'total_transactions': result['total_transactions'] or 0,
                'unique_users': result['unique_users'] or 0,
                'total_credits': float(result['total_credits'] or 0),
                'total_debits': float(result['total_debits'] or 0),
                'net_flow': float(result['net_flow'] or 0)
            }
        
        return {
            'total_transactions': 0,
            'unique_users': 0,
            'total_credits': 0.0,
            'total_debits': 0.0,
            'net_flow': 0.0
        }

    @staticmethod
    async def get_transaction_breakdown(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transaction breakdown by type
        
        Args:
            start_date: datetime - Start date
            end_date: datetime - End date
        
        Returns:
            list: Breakdown by transaction type
        """
        query = """
            SELECT 
                type,
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as total_amount,
                COUNT(DISTINCT user_id) as unique_users
            FROM transactions
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
        
        query += " GROUP BY type ORDER BY total_amount DESC"
        
        results = await Database.fetch_all(query, *params)
        return [dict(row) for row in results]

    @staticmethod
    async def get_top_users_by_volume(
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top users by transaction volume
        
        Args:
            limit: int - Number of users to return
            start_date: datetime - Start date
            end_date: datetime - End date
        
        Returns:
            list: Top users by volume
        """
        query = """
            SELECT 
                t.user_id,
                u.first_name,
                u.username,
                COUNT(*) as transaction_count,
                COALESCE(SUM(t.amount), 0) as net_volume,
                COALESCE(SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END), 0) as total_credits,
                COALESCE(SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END), 0) as total_debits
            FROM transactions t
            JOIN users u ON t.user_id = u.telegram_id
            WHERE 1=1
        """
        params = []
        param_index = 1
        
        if start_date:
            query += f" AND t.created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND t.created_at <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        query += f" GROUP BY t.user_id, u.first_name, u.username"
        query += f" ORDER BY total_debits DESC LIMIT ${param_index}"
        params.append(limit)
        
        results = await Database.fetch_all(query, *params)
        return [dict(row) for row in results]

    # ==================== MAINTENANCE ====================

    @staticmethod
    async def delete_old_transactions(days: int = 365) -> int:
        """
        Delete old transaction records (older than X days)
        
        Args:
            days: int - Age in days for deletion
        
        Returns:
            int: Number of deleted records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = """
            DELETE FROM transactions
            WHERE created_at < $1
            RETURNING id
        """
        
        results = await Database.fetch_all(query, cutoff_date)
        deleted_count = len(results)
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old transaction records older than {days} days")
        
        return deleted_count

    @staticmethod
    async def get_transaction_count() -> int:
        """
        Get total number of transactions
        
        Returns:
            int: Total transaction count
        """
        query = "SELECT COUNT(*) as count FROM transactions"
        result = await Database.fetch_one(query)
        return result['count'] if result else 0


# Import timedelta for date calculations
from datetime import timedelta