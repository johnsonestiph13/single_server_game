# telegram-bot/bot/db/repository/audit_repo.py
# Estif Bingo 24/7 - Audit Repository
# Handles all database operations for audit logging and tracking

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bot.db.database import Database

logger = logging.getLogger(__name__)


class AuditRepository:
    """Repository for audit log database operations"""

    @staticmethod
    async def log(
        user_id: int,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        Create an audit log entry
        
        Args:
            user_id: int - User ID who performed the action
            action: str - Action performed (e.g., 'deposit_approved', 'user_registered')
            entity_type: str - Type of entity affected (e.g., 'user', 'deposit', 'game')
            entity_id: str - ID of the entity (optional)
            old_value: any - Previous value before change
            new_value: any - New value after change
            metadata: dict - Additional metadata
            ip_address: str - IP address of the user (optional)
            user_agent: str - User agent (optional)
        
        Returns:
            int: ID of the created audit log entry
        """
        query = """
            INSERT INTO audit_log (
                user_id, action, entity_type, entity_id,
                old_value, new_value, metadata, ip_address,
                user_agent, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
            RETURNING id
        """
        
        # Convert complex objects to JSON
        old_value_json = json.dumps(old_value) if old_value is not None else None
        new_value_json = json.dumps(new_value) if new_value is not None else None
        metadata_json = json.dumps(metadata) if metadata is not None else None
        
        result = await Database.fetch_one(
            query,
            user_id,
            action,
            entity_type,
            entity_id,
            old_value_json,
            new_value_json,
            metadata_json,
            ip_address,
            user_agent
        )
        
        audit_id = result['id'] if result else None
        
        if audit_id:
            logger.debug(f"Audit log created: {action} by user {user_id}")
        
        return audit_id

    @staticmethod
    async def get_by_id(audit_id: int) -> Optional[Dict[str, Any]]:
        """
        Get audit log entry by ID
        
        Args:
            audit_id: int - Audit log ID
        
        Returns:
            dict: Audit log entry or None if not found
        """
        query = """
            SELECT 
                a.*,
                u.first_name,
                u.username
            FROM audit_log a
            LEFT JOIN users u ON a.user_id = u.telegram_id
            WHERE a.id = $1
        """
        
        result = await Database.fetch_one(query, audit_id)
        
        if result:
            # Parse JSON fields
            result_dict = dict(result)
            result_dict['old_value'] = json.loads(result_dict['old_value']) if result_dict.get('old_value') else None
            result_dict['new_value'] = json.loads(result_dict['new_value']) if result_dict.get('new_value') else None
            result_dict['metadata'] = json.loads(result_dict['metadata']) if result_dict.get('metadata') else None
            return result_dict
        
        return None

    @staticmethod
    async def get_by_user(
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for a specific user
        
        Args:
            user_id: int - User ID
            limit: int - Maximum number of records
            offset: int - Pagination offset
            action: str - Filter by action
            start_date: datetime - Filter by start date
            end_date: datetime - Filter by end date
        
        Returns:
            list: List of audit log entries
        """
        query = """
            SELECT * FROM audit_log
            WHERE user_id = $1
        """
        params = [user_id]
        param_index = 2
        
        if action:
            query += f" AND action = ${param_index}"
            params.append(action)
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
        
        audit_logs = []
        for row in results:
            row_dict = dict(row)
            row_dict['old_value'] = json.loads(row_dict['old_value']) if row_dict.get('old_value') else None
            row_dict['new_value'] = json.loads(row_dict['new_value']) if row_dict.get('new_value') else None
            row_dict['metadata'] = json.loads(row_dict['metadata']) if row_dict.get('metadata') else None
            audit_logs.append(row_dict)
        
        return audit_logs

    @staticmethod
    async def get_by_entity(
        entity_type: str,
        entity_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for a specific entity
        
        Args:
            entity_type: str - Type of entity
            entity_id: str - ID of the entity
            limit: int - Maximum number of records
            offset: int - Pagination offset
        
        Returns:
            list: List of audit log entries
        """
        query = """
            SELECT 
                a.*,
                u.first_name,
                u.username
            FROM audit_log a
            LEFT JOIN users u ON a.user_id = u.telegram_id
            WHERE a.entity_type = $1 AND a.entity_id = $2
            ORDER BY a.created_at DESC
            LIMIT $3 OFFSET $4
        """
        
        results = await Database.fetch_all(query, entity_type, entity_id, limit, offset)
        
        audit_logs = []
        for row in results:
            row_dict = dict(row)
            row_dict['old_value'] = json.loads(row_dict['old_value']) if row_dict.get('old_value') else None
            row_dict['new_value'] = json.loads(row_dict['new_value']) if row_dict.get('new_value') else None
            row_dict['metadata'] = json.loads(row_dict['metadata']) if row_dict.get('metadata') else None
            audit_logs.append(row_dict)
        
        return audit_logs

    @staticmethod
    async def get_by_action(
        action: str,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs by action type
        
        Args:
            action: str - Action name
            limit: int - Maximum number of records
            offset: int - Pagination offset
            start_date: datetime - Filter by start date
            end_date: datetime - Filter by end date
        
        Returns:
            list: List of audit log entries
        """
        query = """
            SELECT 
                a.*,
                u.first_name,
                u.username
            FROM audit_log a
            LEFT JOIN users u ON a.user_id = u.telegram_id
            WHERE a.action = $1
        """
        params = [action]
        param_index = 2
        
        if start_date:
            query += f" AND a.created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND a.created_at <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        query += f" ORDER BY a.created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.append(limit)
        params.append(offset)
        
        results = await Database.fetch_all(query, *params)
        
        audit_logs = []
        for row in results:
            row_dict = dict(row)
            row_dict['old_value'] = json.loads(row_dict['old_value']) if row_dict.get('old_value') else None
            row_dict['new_value'] = json.loads(row_dict['new_value']) if row_dict.get('new_value') else None
            row_dict['metadata'] = json.loads(row_dict['metadata']) if row_dict.get('metadata') else None
            audit_logs.append(row_dict)
        
        return audit_logs

    @staticmethod
    async def get_recent(limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get most recent audit logs
        
        Args:
            limit: int - Maximum number of records
        
        Returns:
            list: List of recent audit log entries
        """
        query = """
            SELECT 
                a.*,
                u.first_name,
                u.username
            FROM audit_log a
            LEFT JOIN users u ON a.user_id = u.telegram_id
            ORDER BY a.created_at DESC
            LIMIT $1
        """
        
        results = await Database.fetch_all(query, limit)
        
        audit_logs = []
        for row in results:
            row_dict = dict(row)
            row_dict['old_value'] = json.loads(row_dict['old_value']) if row_dict.get('old_value') else None
            row_dict['new_value'] = json.loads(row_dict['new_value']) if row_dict.get('new_value') else None
            row_dict['metadata'] = json.loads(row_dict['metadata']) if row_dict.get('metadata') else None
            audit_logs.append(row_dict)
        
        return audit_logs

    @staticmethod
    async def get_stats(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit log statistics
        
        Args:
            start_date: datetime - Start date
            end_date: datetime - End date
        
        Returns:
            dict: Statistics including counts by action
        """
        query = """
            SELECT 
                COUNT(*) as total_logs,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(DISTINCT action) as unique_actions
            FROM audit_log
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
        
        stats = {
            'total_logs': result['total_logs'] if result else 0,
            'unique_users': result['unique_users'] if result else 0,
            'unique_actions': result['unique_actions'] if result else 0
        }
        
        # Get action breakdown
        action_query = """
            SELECT action, COUNT(*) as count
            FROM audit_log
            WHERE 1=1
        """
        action_params = []
        action_param_index = 1
        
        if start_date:
            action_query += f" AND created_at >= ${action_param_index}"
            action_params.append(start_date)
            action_param_index += 1
        
        if end_date:
            action_query += f" AND created_at <= ${action_param_index}"
            action_params.append(end_date)
            action_param_index += 1
        
        action_query += " GROUP BY action ORDER BY count DESC LIMIT 20"
        
        action_results = await Database.fetch_all(action_query, *action_params)
        stats['action_breakdown'] = [dict(row) for row in action_results]
        
        return stats

    @staticmethod
    async def get_daily_stats(date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get daily audit log statistics
        
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
                COUNT(*) as total_logs,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(DISTINCT action) as unique_actions
            FROM audit_log
            WHERE created_at >= $1 AND created_at < $2
        """
        
        result = await Database.fetch_one(query, date, next_date)
        
        if result:
            return {
                'date': date,
                'total_logs': result['total_logs'] or 0,
                'unique_users': result['unique_users'] or 0,
                'unique_actions': result['unique_actions'] or 0
            }
        
        return {
            'date': date,
            'total_logs': 0,
            'unique_users': 0,
            'unique_actions': 0
        }

    @staticmethod
    async def get_user_action_summary(
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get summary of user's actions over a period
        
        Args:
            user_id: int - User ID
            days: int - Number of days to look back
        
        Returns:
            dict: Summary of user's actions
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = """
            SELECT 
                action,
                COUNT(*) as count,
                MIN(created_at) as first_occurrence,
                MAX(created_at) as last_occurrence
            FROM audit_log
            WHERE user_id = $1 AND created_at >= $2
            GROUP BY action
            ORDER BY count DESC
        """
        
        results = await Database.fetch_all(query, user_id, start_date)
        
        summary = {
            'user_id': user_id,
            'period_days': days,
            'total_actions': sum(row['count'] for row in results),
            'unique_actions': len(results),
            'actions': [dict(row) for row in results]
        }
        
        return summary

    @staticmethod
    async def search(
        query: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search audit logs by action, entity_type, or entity_id
        
        Args:
            query: str - Search query
            limit: int - Maximum number of records
            offset: int - Pagination offset
        
        Returns:
            list: List of matching audit log entries
        """
        search_query = f"%{query}%"
        
        sql = """
            SELECT 
                a.*,
                u.first_name,
                u.username
            FROM audit_log a
            LEFT JOIN users u ON a.user_id = u.telegram_id
            WHERE a.action ILIKE $1
               OR a.entity_type ILIKE $1
               OR a.entity_id ILIKE $1
               OR CAST(a.metadata AS TEXT) ILIKE $1
            ORDER BY a.created_at DESC
            LIMIT $2 OFFSET $3
        """
        
        results = await Database.fetch_all(sql, search_query, limit, offset)
        
        audit_logs = []
        for row in results:
            row_dict = dict(row)
            row_dict['old_value'] = json.loads(row_dict['old_value']) if row_dict.get('old_value') else None
            row_dict['new_value'] = json.loads(row_dict['new_value']) if row_dict.get('new_value') else None
            row_dict['metadata'] = json.loads(row_dict['metadata']) if row_dict.get('metadata') else None
            audit_logs.append(row_dict)
        
        return audit_logs

    @staticmethod
    async def delete_old_logs(days: int = 90) -> int:
        """
        Delete audit logs older than specified days
        
        Args:
            days: int - Age in days for deletion (default 90)
        
        Returns:
            int: Number of deleted records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = """
            DELETE FROM audit_log
            WHERE created_at < $1
            RETURNING id
        """
        
        results = await Database.fetch_all(query, cutoff_date)
        deleted_count = len(results)
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} audit log records older than {days} days")
        
        return deleted_count

    @staticmethod
    async def export_logs(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Export audit logs for reporting
        
        Args:
            start_date: datetime - Start date
            end_date: datetime - End date
            action: str - Filter by action
            user_id: int - Filter by user ID
        
        Returns:
            list: List of audit log entries for export
        """
        query = """
            SELECT 
                a.id,
                a.user_id,
                u.first_name,
                u.username,
                a.action,
                a.entity_type,
                a.entity_id,
                a.old_value,
                a.new_value,
                a.metadata,
                a.ip_address,
                a.user_agent,
                a.created_at
            FROM audit_log a
            LEFT JOIN users u ON a.user_id = u.telegram_id
            WHERE 1=1
        """
        params = []
        param_index = 1
        
        if start_date:
            query += f" AND a.created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND a.created_at <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        if action:
            query += f" AND a.action = ${param_index}"
            params.append(action)
            param_index += 1
        
        if user_id:
            query += f" AND a.user_id = ${param_index}"
            params.append(user_id)
            param_index += 1
        
        query += " ORDER BY a.created_at ASC"
        
        results = await Database.fetch_all(query, *params)
        
        audit_logs = []
        for row in results:
            row_dict = dict(row)
            row_dict['old_value'] = json.loads(row_dict['old_value']) if row_dict.get('old_value') else None
            row_dict['new_value'] = json.loads(row_dict['new_value']) if row_dict.get('new_value') else None
            row_dict['metadata'] = json.loads(row_dict['metadata']) if row_dict.get('metadata') else None
            audit_logs.append(row_dict)
        
        return audit_logs


# Import timedelta for date calculations
from datetime import timedelta