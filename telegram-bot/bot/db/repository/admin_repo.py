# telegram-bot/bot/db/repository/admin_repo.py
# Estif Bingo 24/7 - Admin Repository
# Handles all database operations for admin actions, system settings, and reports

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from bot.db.database import Database

logger = logging.getLogger(__name__)


class AdminRepository:
    """Repository for admin-related database operations"""

    # ==================== ADMIN ACTIONS LOG ====================

    @staticmethod
    async def log_admin_action(
        admin_id: int,
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> int:
        """
        Log an admin action for audit trail
        
        Args:
            admin_id: int - Admin's Telegram ID
            action: str - Action performed (e.g., 'approve_deposit', 'ban_user')
            target_type: str - Type of target (e.g., 'user', 'deposit', 'withdrawal')
            target_id: str - ID of the target
            details: dict - Additional details about the action
            ip_address: str - Admin's IP address
        
        Returns:
            int: Admin log ID
        """
        query = """
            INSERT INTO admin_log (
                admin_id, action, target_type, target_id, 
                details, ip_address, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            admin_id,
            action,
            target_type,
            target_id,
            details,
            ip_address
        )
        
        log_id = result['id'] if result else None
        
        if log_id:
            logger.info(f"Admin action logged: {action} by {admin_id} on {target_type} {target_id}")
        
        return log_id

    @staticmethod
    async def get_admin_logs(
        limit: int = 100,
        offset: int = 0,
        admin_id: Optional[int] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get admin action logs with filters
        
        Args:
            limit: int - Maximum number of records
            offset: int - Pagination offset
            admin_id: int - Filter by admin ID
            action: str - Filter by action
            start_date: datetime - Start date
            end_date: datetime - End date
        
        Returns:
            list: List of admin log entries
        """
        query = """
            SELECT 
                al.*,
                u.first_name as admin_first_name,
                u.username as admin_username
            FROM admin_log al
            LEFT JOIN users u ON al.admin_id = u.telegram_id
            WHERE 1=1
        """
        params = []
        param_index = 1
        
        if admin_id:
            query += f" AND al.admin_id = ${param_index}"
            params.append(admin_id)
            param_index += 1
        
        if action:
            query += f" AND al.action = ${param_index}"
            params.append(action)
            param_index += 1
        
        if start_date:
            query += f" AND al.created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND al.created_at <= ${param_index}"
            params.append(end_date)
            param_index += 1
        
        query += f" ORDER BY al.created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
        params.append(limit)
        params.append(offset)
        
        results = await Database.fetch_all(query, *params)
        return [dict(row) for row in results]

    @staticmethod
    async def get_admin_action_stats(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics of admin actions
        
        Args:
            start_date: datetime - Start date
            end_date: datetime - End date
        
        Returns:
            dict: Admin action statistics
        """
        query = """
            SELECT 
                action,
                COUNT(*) as count,
                COUNT(DISTINCT admin_id) as unique_admins
            FROM admin_log
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
        
        query += " GROUP BY action ORDER BY count DESC"
        
        results = await Database.fetch_all(query, *params)
        
        stats = {
            'total_actions': sum(row['count'] for row in results),
            'unique_actions': len(results),
            'action_breakdown': [dict(row) for row in results]
        }
        
        return stats

    @staticmethod
    async def cleanup_old_admin_logs(days: int = 180) -> int:
        """
        Delete old admin logs (older than X days)
        
        Args:
            days: int - Age in days for deletion
        
        Returns:
            int: Number of deleted records
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = """
            DELETE FROM admin_log
            WHERE created_at < $1
            RETURNING id
        """
        
        results = await Database.fetch_all(query, cutoff)
        deleted_count = len(results)
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old admin logs older than {days} days")
        
        return deleted_count

    # ==================== SYSTEM SETTINGS ====================

    @staticmethod
    async def get_setting(key: str, default: Any = None) -> Any:
        """
        Get a system setting value
        
        Args:
            key: str - Setting key
            default: any - Default value if not found
        
        Returns:
            any: Setting value or default
        """
        query = "SELECT value FROM system_settings WHERE key = $1"
        result = await Database.fetch_one(query, key)
        
        if result:
            # Try to parse JSON
            try:
                import json
                return json.loads(result['value'])
            except (json.JSONDecodeError, TypeError):
                return result['value']
        
        return default

    @staticmethod
    async def set_setting(key: str, value: Any, updated_by: Optional[int] = None) -> bool:
        """
        Set a system setting value
        
        Args:
            key: str - Setting key
            value: any - Setting value (will be JSON serialized)
            updated_by: int - Admin ID who updated the setting
        
        Returns:
            bool: True if successful
        """
        import json
        
        query = """
            INSERT INTO system_settings (key, value, updated_by, updated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value, 
                updated_by = EXCLUDED.updated_by,
                updated_at = NOW()
            RETURNING key
        """
        
        value_json = json.dumps(value) if not isinstance(value, str) else value
        
        result = await Database.fetch_one(query, key, value_json, updated_by)
        
        if result:
            logger.info(f"System setting updated: {key} = {value}")
            return True
        
        return False

    @staticmethod
    async def get_all_settings() -> Dict[str, Any]:
        """
        Get all system settings
        
        Returns:
            dict: All system settings
        """
        query = "SELECT key, value FROM system_settings"
        results = await Database.fetch_all(query)
        
        import json
        settings = {}
        for row in results:
            try:
                settings[row['key']] = json.loads(row['value'])
            except (json.JSONDecodeError, TypeError):
                settings[row['key']] = row['value']
        
        return settings

    @staticmethod
    async def delete_setting(key: str) -> bool:
        """
        Delete a system setting
        
        Args:
            key: str - Setting key
        
        Returns:
            bool: True if successful
        """
        query = "DELETE FROM system_settings WHERE key = $1 RETURNING key"
        result = await Database.fetch_one(query, key)
        
        if result:
            logger.info(f"System setting deleted: {key}")
            return True
        
        return False

    # ==================== SYSTEM REPORTS ====================

    @staticmethod
    async def get_system_report() -> Dict[str, Any]:
        """
        Get comprehensive system report
        
        Returns:
            dict: System report with various metrics
        """
        report = {}
        
        # User statistics
        user_query = """
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN registered = TRUE THEN 1 END) as registered_users,
                COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_users,
                COUNT(CASE WHEN is_admin = TRUE THEN 1 END) as admin_users,
                COUNT(CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN 1 END) as new_users_24h,
                COUNT(CASE WHEN last_seen > NOW() - INTERVAL '24 hours' THEN 1 END) as active_24h
            FROM users
        """
        user_result = await Database.fetch_one(user_query)
        report['users'] = dict(user_result) if user_result else {}
        
        # Financial statistics
        finance_query = """
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'deposit' THEN amount ELSE 0 END), 0) as total_deposits,
                COALESCE(SUM(CASE WHEN type = 'withdrawal' THEN ABS(amount) ELSE 0 END), 0) as total_withdrawals,
                COALESCE(SUM(CASE WHEN type = 'win' THEN amount ELSE 0 END), 0) as total_wins,
                COALESCE(SUM(CASE WHEN type = 'cartela_purchase' THEN ABS(amount) ELSE 0 END), 0) as total_bets,
                COALESCE(SUM(balance), 0) as total_balance
            FROM users u
            LEFT JOIN transactions t ON u.telegram_id = t.user_id
        """
        finance_result = await Database.fetch_one(finance_query)
        report['finance'] = dict(finance_result) if finance_result else {}
        
        # Game statistics
        game_query = """
            SELECT 
                COUNT(*) as total_rounds,
                COALESCE(SUM(total_cartelas), 0) as total_cartelas_sold,
                COALESCE(SUM(prize_pool), 0) as total_prize_pool,
                COUNT(CASE WHEN status = 'ended' THEN 1 END) as completed_rounds
            FROM game_rounds
        """
        game_result = await Database.fetch_one(game_query)
        report['games'] = dict(game_result) if game_result else {}
        
        # Pending requests
        pending_query = """
            SELECT 
                (SELECT COUNT(*) FROM deposits WHERE status = 'pending') as pending_deposits,
                (SELECT COALESCE(SUM(amount), 0) FROM deposits WHERE status = 'pending') as pending_deposit_amount,
                (SELECT COUNT(*) FROM withdrawals WHERE status = 'pending') as pending_withdrawals,
                (SELECT COALESCE(SUM(amount), 0) FROM withdrawals WHERE status = 'pending') as pending_withdrawal_amount
        """
        pending_result = await Database.fetch_one(pending_query)
        report['pending'] = dict(pending_result) if pending_result else {}
        
        # System health
        report['health'] = {
            'status': 'healthy',
            'last_check': datetime.utcnow(),
            'database_connected': True
        }
        
        return report

    @staticmethod
    async def get_daily_report(date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get daily report for a specific date
        
        Args:
            date: datetime - Date for report (default: today)
        
        Returns:
            dict: Daily report
        """
        if date is None:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        next_date = date + timedelta(days=1)
        
        report = {
            'date': date,
            'new_users': 0,
            'active_users': 0,
            'total_deposits': 0.0,
            'total_withdrawals': 0.0,
            'total_bets': 0.0,
            'total_wins': 0.0,
            'rounds_played': 0,
            'admin_actions': 0
        }
        
        # New users
        user_query = """
            SELECT COUNT(*) as count FROM users
            WHERE created_at >= $1 AND created_at < $2
        """
        user_result = await Database.fetch_one(user_query, date, next_date)
        report['new_users'] = user_result['count'] if user_result else 0
        
        # Active users
        active_query = """
            SELECT COUNT(*) as count FROM users
            WHERE last_seen >= $1 AND last_seen < $2
        """
        active_result = await Database.fetch_one(active_query, date, next_date)
        report['active_users'] = active_result['count'] if active_result else 0
        
        # Transactions
        tx_query = """
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'deposit' THEN amount ELSE 0 END), 0) as deposits,
                COALESCE(SUM(CASE WHEN type = 'withdrawal' THEN ABS(amount) ELSE 0 END), 0) as withdrawals,
                COALESCE(SUM(CASE WHEN type = 'cartela_purchase' THEN ABS(amount) ELSE 0 END), 0) as bets,
                COALESCE(SUM(CASE WHEN type = 'win' THEN amount ELSE 0 END), 0) as wins
            FROM transactions
            WHERE created_at >= $1 AND created_at < $2
        """
        tx_result = await Database.fetch_one(tx_query, date, next_date)
        
        if tx_result:
            report['total_deposits'] = float(tx_result['deposits'] or 0)
            report['total_withdrawals'] = float(tx_result['withdrawals'] or 0)
            report['total_bets'] = float(tx_result['bets'] or 0)
            report['total_wins'] = float(tx_result['wins'] or 0)
        
        # Rounds played
        round_query = """
            SELECT COUNT(*) as count FROM game_rounds
            WHERE start_time >= $1 AND start_time < $2
        """
        round_result = await Database.fetch_one(round_query, date, next_date)
        report['rounds_played'] = round_result['count'] if round_result else 0
        
        # Admin actions
        admin_query = """
            SELECT COUNT(*) as count FROM admin_log
            WHERE created_at >= $1 AND created_at < $2
        """
        admin_result = await Database.fetch_one(admin_query, date, next_date)
        report['admin_actions'] = admin_result['count'] if admin_result else 0
        
        return report

    @staticmethod
    async def get_weekly_report() -> List[Dict[str, Any]]:
        """
        Get weekly report (last 7 days)
        
        Returns:
            list: Weekly report by day
        """
        reports = []
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            daily_report = await AdminRepository.get_daily_report(date)
            reports.append(daily_report)
        
        return reports

    @staticmethod
    async def get_monthly_report(year: int, month: int) -> List[Dict[str, Any]]:
        """
        Get monthly report
        
        Args:
            year: int - Year
            month: int - Month (1-12)
        
        Returns:
            list: Monthly report by day
        """
        from calendar import monthrange
        
        reports = []
        days_in_month = monthrange(year, month)[1]
        
        for day in range(1, days_in_month + 1):
            date = datetime(year, month, day, 0, 0, 0)
            daily_report = await AdminRepository.get_daily_report(date)
            reports.append(daily_report)
        
        return reports

    # ==================== MAINTENANCE MODE ====================

    @staticmethod
    async def set_maintenance_mode(
        enabled: bool,
        reason: Optional[str] = None,
        set_by: Optional[int] = None
    ) -> bool:
        """
        Enable or disable maintenance mode
        
        Args:
            enabled: bool - Enable maintenance mode
            reason: str - Reason for maintenance
            set_by: int - Admin ID who set maintenance mode
        
        Returns:
            bool: True if successful
        """
        # Update system setting
        success = await AdminRepository.set_setting(
            'maintenance_mode',
            {
                'enabled': enabled,
                'reason': reason,
                'set_by': set_by,
                'set_at': datetime.utcnow().isoformat()
            },
            updated_by=set_by
        )
        
        if success:
            # Log admin action
            if set_by:
                await AdminRepository.log_admin_action(
                    admin_id=set_by,
                    action='maintenance_mode',
                    target_type='system',
                    details={'enabled': enabled, 'reason': reason}
                )
            
            status = "enabled" if enabled else "disabled"
            logger.info(f"Maintenance mode {status}")
        
        return success

    @staticmethod
    async def get_maintenance_status() -> Dict[str, Any]:
        """
        Get maintenance mode status
        
        Returns:
            dict: Maintenance mode status
        """
        status = await AdminRepository.get_setting('maintenance_mode', {})
        
        return {
            'enabled': status.get('enabled', False) if isinstance(status, dict) else False,
            'reason': status.get('reason') if isinstance(status, dict) else None,
            'set_by': status.get('set_by') if isinstance(status, dict) else None,
            'set_at': status.get('set_at') if isinstance(status, dict) else None
        }

    # ==================== BROADCAST MANAGEMENT ====================

    @staticmethod
    async def log_broadcast(
        admin_id: int,
        message: str,
        recipient_count: int,
        success_count: int,
        fail_count: int
    ) -> int:
        """
        Log a broadcast message
        
        Args:
            admin_id: int - Admin who sent the broadcast
            message: str - Broadcast message content
            recipient_count: int - Number of recipients
            success_count: int - Successful deliveries
            fail_count: int - Failed deliveries
        
        Returns:
            int: Broadcast log ID
        """
        query = """
            INSERT INTO broadcast_log (
                admin_id, message, recipient_count, 
                success_count, fail_count, sent_at
            )
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            admin_id,
            message,
            recipient_count,
            success_count,
            fail_count
        )
        
        broadcast_id = result['id'] if result else None
        
        if broadcast_id:
            logger.info(f"Broadcast #{broadcast_id} sent by admin {admin_id}")
        
        return broadcast_id

    @staticmethod
    async def get_broadcast_logs(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get broadcast logs
        
        Args:
            limit: int - Maximum number of records
            offset: int - Pagination offset
        
        Returns:
            list: List of broadcast logs
        """
        query = """
            SELECT 
                bl.*,
                u.first_name as admin_first_name,
                u.username as admin_username
            FROM broadcast_log bl
            LEFT JOIN users u ON bl.admin_id = u.telegram_id
            ORDER BY bl.sent_at DESC
            LIMIT $1 OFFSET $2
        """
        
        results = await Database.fetch_all(query, limit, offset)
        return [dict(row) for row in results]

    # ==================== ANNOUNCEMENTS ====================

    @staticmethod
    async def create_announcement(
        title: str,
        content: str,
        priority: str = 'normal',
        created_by: Optional[int] = None,
        expires_at: Optional[datetime] = None
    ) -> int:
        """
        Create a system announcement
        
        Args:
            title: str - Announcement title
            content: str - Announcement content
            priority: str - Priority (low, normal, high, urgent)
            created_by: int - Admin ID who created the announcement
            expires_at: datetime - Expiration timestamp
        
        Returns:
            int: Announcement ID
        """
        query = """
            INSERT INTO announcements (
                title, content, priority, created_by, expires_at, created_at
            )
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            title,
            content,
            priority,
            created_by,
            expires_at
        )
        
        announcement_id = result['id'] if result else None
        
        if announcement_id:
            logger.info(f"Announcement created: {title}")
        
        return announcement_id

    @staticmethod
    async def get_active_announcements() -> List[Dict[str, Any]]:
        """
        Get active (not expired) announcements
        
        Returns:
            list: List of active announcements
        """
        query = """
            SELECT 
                a.*,
                u.first_name as creator_name
            FROM announcements a
            LEFT JOIN users u ON a.created_by = u.telegram_id
            WHERE a.is_active = TRUE 
            AND (a.expires_at IS NULL OR a.expires_at > NOW())
            ORDER BY 
                CASE a.priority 
                    WHEN 'urgent' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'normal' THEN 3
                    WHEN 'low' THEN 4
                END ASC,
                a.created_at DESC
        """
        
        results = await Database.fetch_all(query)
        return [dict(row) for row in results]

    @staticmethod
    async def dismiss_announcement(announcement_id: int, user_id: int) -> bool:
        """
        Mark an announcement as dismissed by a user
        
        Args:
            announcement_id: int - Announcement ID
            user_id: int - User's Telegram ID
        
        Returns:
            bool: True if successful
        """
        query = """
            INSERT INTO announcement_dismissals (announcement_id, user_id, dismissed_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (announcement_id, user_id) DO NOTHING
            RETURNING id
        """
        
        result = await Database.fetch_one(query, announcement_id, user_id)
        return result is not None

    @staticmethod
    async def has_dismissed_announcement(announcement_id: int, user_id: int) -> bool:
        """
        Check if a user has dismissed an announcement
        
        Args:
            announcement_id: int - Announcement ID
            user_id: int - User's Telegram ID
        
        Returns:
            bool: True if dismissed
        """
        query = """
            SELECT id FROM announcement_dismissals
            WHERE announcement_id = $1 AND user_id = $2
        """
        
        result = await Database.fetch_one(query, announcement_id, user_id)
        return result is not None

    @staticmethod
    async def expire_announcement(announcement_id: int) -> bool:
        """
        Expire an announcement (mark as inactive)
        
        Args:
            announcement_id: int - Announcement ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE announcements
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = $1 AND is_active = TRUE
            RETURNING id
        """
        
        result = await Database.fetch_one(query, announcement_id)
        
        if result:
            logger.info(f"Announcement #{announcement_id} expired")
            return True
        
        return False

    @staticmethod
    async def cleanup_expired_announcements() -> int:
        """
        Auto-expire announcements that have passed their expiry date
        
        Returns:
            int: Number of expired announcements
        """
        query = """
            UPDATE announcements
            SET is_active = FALSE, updated_at = NOW()
            WHERE is_active = TRUE 
            AND expires_at IS NOT NULL 
            AND expires_at < NOW()
            RETURNING id
        """
        
        results = await Database.fetch_all(query)
        expired_count = len(results)
        
        if expired_count > 0:
            logger.info(f"Auto-expired {expired_count} announcements")
        
        return expired_count


# Import timedelta for date calculations
from datetime import timedelta