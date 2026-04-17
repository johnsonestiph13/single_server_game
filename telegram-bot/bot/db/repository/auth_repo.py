# telegram-bot/bot/db/repository/auth_repo.py
# Estif Bingo 24/7 - Authentication Repository
# Handles all database operations for OTP codes, JWT tokens, sessions, and API keys

import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from bot.db.database import Database

logger = logging.getLogger(__name__)


class AuthRepository:
    """Repository for authentication database operations"""

    # ==================== OTP (One-Time Password) ====================

    @staticmethod
    async def create_otp(
        telegram_id: int,
        otp_hash: str,
        expires_at: datetime,
        purpose: str = "game_login",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        Create an OTP record
        
        Args:
            telegram_id: int - User's Telegram ID
            otp_hash: str - Hashed OTP value
            expires_at: datetime - Expiration timestamp
            purpose: str - Purpose (game_login, phone_verification, password_reset)
            ip_address: str - User's IP address (optional)
            user_agent: str - User agent (optional)
        
        Returns:
            int: OTP record ID
        """
        query = """
            INSERT INTO auth_codes (
                telegram_id, code_hash, expires_at, purpose, 
                ip_address, user_agent, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            telegram_id,
            otp_hash,
            expires_at,
            purpose,
            ip_address,
            user_agent
        )
        
        otp_id = result['id'] if result else None
        
        if otp_id:
            logger.debug(f"OTP created for user {telegram_id} - Purpose: {purpose}")
        
        return otp_id

    @staticmethod
    async def verify_otp(
        telegram_id: int,
        otp_hash: str,
        purpose: str = "game_login",
        mark_used: bool = True
    ) -> bool:
        """
        Verify an OTP code
        
        Args:
            telegram_id: int - User's Telegram ID
            otp_hash: str - Hashed OTP value to verify
            purpose: str - Purpose of the OTP
            mark_used: bool - Whether to mark the OTP as used
        
        Returns:
            bool: True if OTP is valid and not expired
        """
        query = """
            SELECT id, expires_at, used, attempts
            FROM auth_codes
            WHERE telegram_id = $1 
            AND code_hash = $2 
            AND purpose = $3
            AND used = FALSE
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = await Database.fetch_one(query, telegram_id, otp_hash, purpose)
        
        if not result:
            logger.warning(f"OTP not found for user {telegram_id} - Purpose: {purpose}")
            return False
        
        # Check if expired
        if result['expires_at'] < datetime.utcnow():
            logger.warning(f"OTP expired for user {telegram_id}")
            return False
        
        # Check attempts
        attempts = result.get('attempts', 0)
        if attempts >= 5:
            logger.warning(f"OTP max attempts exceeded for user {telegram_id}")
            return False
        
        # Mark as used if requested
        if mark_used:
            await AuthRepository.mark_otp_used(result['id'])
        
        logger.info(f"OTP verified for user {telegram_id} - Purpose: {purpose}")
        return True

    @staticmethod
    async def mark_otp_used(otp_id: int) -> bool:
        """
        Mark an OTP as used
        
        Args:
            otp_id: int - OTP record ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE auth_codes
            SET used = TRUE, used_at = NOW()
            WHERE id = $1 AND used = FALSE
            RETURNING id
        """
        
        result = await Database.fetch_one(query, otp_id)
        return result is not None

    @staticmethod
    async def increment_otp_attempts(otp_id: int) -> int:
        """
        Increment OTP verification attempts counter
        
        Args:
            otp_id: int - OTP record ID
        
        Returns:
            int: New attempts count
        """
        query = """
            UPDATE auth_codes
            SET attempts = attempts + 1
            WHERE id = $1
            RETURNING attempts
        """
        
        result = await Database.fetch_one(query, otp_id)
        return result['attempts'] if result else 0

    @staticmethod
    async def get_pending_otp(
        telegram_id: int,
        purpose: str = "game_login"
    ) -> Optional[Dict[str, Any]]:
        """
        Get pending (unused, not expired) OTP for a user
        
        Args:
            telegram_id: int - User's Telegram ID
            purpose: str - Purpose of the OTP
        
        Returns:
            dict: OTP data or None if not found
        """
        query = """
            SELECT id, code_hash, expires_at, purpose, attempts, created_at
            FROM auth_codes
            WHERE telegram_id = $1 
            AND purpose = $2
            AND used = FALSE
            AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = await Database.fetch_one(query, telegram_id, purpose)
        return dict(result) if result else None

    @staticmethod
    async def get_recent_otp(
        telegram_id: int,
        minutes: int = 1,
        purpose: str = "game_login"
    ) -> List[Dict[str, Any]]:
        """
        Get recent OTP requests for rate limiting
        
        Args:
            telegram_id: int - User's Telegram ID
            minutes: int - Time window in minutes
            purpose: str - Purpose of the OTP
        
        Returns:
            list: List of recent OTP records
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        query = """
            SELECT id, created_at, used
            FROM auth_codes
            WHERE telegram_id = $1 
            AND purpose = $2
            AND created_at > $3
            ORDER BY created_at DESC
        """
        
        results = await Database.fetch_all(query, telegram_id, purpose, cutoff)
        return [dict(row) for row in results]

    @staticmethod
    async def cleanup_expired_otp() -> int:
        """
        Delete expired OTP records
        
        Returns:
            int: Number of deleted records
        """
        query = """
            DELETE FROM auth_codes
            WHERE expires_at < NOW()
            RETURNING id
        """
        
        results = await Database.fetch_all(query)
        deleted_count = len(results)
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired OTP records")
        
        return deleted_count

    # ==================== SESSION MANAGEMENT ====================

    @staticmethod
    async def create_session(
        telegram_id: int,
        session_token: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """
        Create a user session
        
        Args:
            telegram_id: int - User's Telegram ID
            session_token: str - Hashed session token
            expires_at: datetime - Expiration timestamp
            ip_address: str - User's IP address
            user_agent: str - User agent
        
        Returns:
            int: Session ID
        """
        query = """
            INSERT INTO user_sessions (
                telegram_id, session_token, expires_at, 
                ip_address, user_agent, created_at
            )
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            telegram_id,
            session_token,
            expires_at,
            ip_address,
            user_agent
        )
        
        session_id = result['id'] if result else None
        
        if session_id:
            logger.debug(f"Session created for user {telegram_id}")
        
        return session_id

    @staticmethod
    async def verify_session(session_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a session token
        
        Args:
            session_token: str - Session token to verify
        
        Returns:
            dict: Session data with user info if valid, None otherwise
        """
        query = """
            SELECT 
                s.*,
                u.telegram_id,
                u.username,
                u.first_name,
                u.is_admin
            FROM user_sessions s
            JOIN users u ON s.telegram_id = u.telegram_id
            WHERE s.session_token = $1 
            AND s.is_active = TRUE
            AND s.expires_at > NOW()
        """
        
        result = await Database.fetch_one(query, session_token)
        
        if result:
            session_dict = dict(result)
            # Update last activity
            await AuthRepository.update_session_activity(session_dict['id'])
            return session_dict
        
        return None

    @staticmethod
    async def update_session_activity(session_id: int) -> bool:
        """
        Update session's last activity timestamp
        
        Args:
            session_id: int - Session ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE user_sessions
            SET last_activity = NOW()
            WHERE id = $1
            RETURNING id
        """
        
        result = await Database.fetch_one(query, session_id)
        return result is not None

    @staticmethod
    async def revoke_session(session_id: int) -> bool:
        """
        Revoke/invalidate a session
        
        Args:
            session_id: int - Session ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE user_sessions
            SET is_active = FALSE, revoked_at = NOW()
            WHERE id = $1 AND is_active = TRUE
            RETURNING id
        """
        
        result = await Database.fetch_one(query, session_id)
        
        if result:
            logger.info(f"Session {session_id} revoked")
            return True
        
        return False

    @staticmethod
    async def revoke_all_user_sessions(telegram_id: int) -> int:
        """
        Revoke all sessions for a user
        
        Args:
            telegram_id: int - User's Telegram ID
        
        Returns:
            int: Number of sessions revoked
        """
        query = """
            UPDATE user_sessions
            SET is_active = FALSE, revoked_at = NOW()
            WHERE telegram_id = $1 AND is_active = TRUE
            RETURNING id
        """
        
        results = await Database.fetch_all(query, telegram_id)
        revoked_count = len(results)
        
        if revoked_count > 0:
            logger.info(f"Revoked {revoked_count} sessions for user {telegram_id}")
        
        return revoked_count

    @staticmethod
    async def cleanup_expired_sessions() -> int:
        """
        Delete expired sessions
        
        Returns:
            int: Number of deleted records
        """
        query = """
            DELETE FROM user_sessions
            WHERE expires_at < NOW() OR (is_active = FALSE AND revoked_at < NOW() - INTERVAL '30 days')
            RETURNING id
        """
        
        results = await Database.fetch_all(query)
        deleted_count = len(results)
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired sessions")
        
        return deleted_count

    # ==================== API KEYS ====================

    @staticmethod
    async def create_api_key(
        name: str,
        key_hash: str,
        expires_at: Optional[datetime] = None,
        permissions: Optional[List[str]] = None,
        created_by: Optional[int] = None
    ) -> int:
        """
        Create an API key
        
        Args:
            name: str - API key name/description
            key_hash: str - Hashed API key
            expires_at: datetime - Expiration timestamp (None = never expires)
            permissions: list - List of permissions (e.g., ['read', 'write'])
            created_by: int - User ID who created this key
        
        Returns:
            int: API key ID
        """
        query = """
            INSERT INTO api_keys (name, key_hash, expires_at, permissions, created_by, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(
            query,
            name,
            key_hash,
            expires_at,
            permissions or ['read'],
            created_by
        )
        
        api_key_id = result['id'] if result else None
        
        if api_key_id:
            logger.info(f"API key created: {name}")
        
        return api_key_id

    @staticmethod
    async def verify_api_key(key_hash: str, required_permission: str = "read") -> bool:
        """
        Verify an API key
        
        Args:
            key_hash: str - Hashed API key
            required_permission: str - Permission required
        
        Returns:
            bool: True if API key is valid and has required permission
        """
        query = """
            SELECT id, permissions, expires_at, is_active
            FROM api_keys
            WHERE key_hash = $1
        """
        
        result = await Database.fetch_one(query, key_hash)
        
        if not result:
            return False
        
        # Check if active
        if not result['is_active']:
            logger.warning(f"API key is inactive")
            return False
        
        # Check expiration
        if result['expires_at'] and result['expires_at'] < datetime.utcnow():
            logger.warning(f"API key expired")
            return False
        
        # Check permission
        permissions = result['permissions'] or []
        if required_permission not in permissions and 'admin' not in permissions:
            logger.warning(f"API key missing permission: {required_permission}")
            return False
        
        # Update last used timestamp
        await AuthRepository.update_api_key_usage(result['id'])
        
        return True

    @staticmethod
    async def update_api_key_usage(api_key_id: int) -> bool:
        """
        Update API key's last used timestamp
        
        Args:
            api_key_id: int - API key ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE api_keys
            SET last_used = NOW(), usage_count = usage_count + 1
            WHERE id = $1
            RETURNING id
        """
        
        result = await Database.fetch_one(query, api_key_id)
        return result is not None

    @staticmethod
    async def revoke_api_key(api_key_id: int) -> bool:
        """
        Revoke/invalidate an API key
        
        Args:
            api_key_id: int - API key ID
        
        Returns:
            bool: True if successful
        """
        query = """
            UPDATE api_keys
            SET is_active = FALSE, revoked_at = NOW()
            WHERE id = $1 AND is_active = TRUE
            RETURNING id
        """
        
        result = await Database.fetch_one(query, api_key_id)
        
        if result:
            logger.info(f"API key {api_key_id} revoked")
            return True
        
        return False

    @staticmethod
    async def get_api_keys(include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get all API keys
        
        Args:
            include_inactive: bool - Include inactive keys
        
        Returns:
            list: List of API keys
        """
        query = """
            SELECT id, name, permissions, is_active, expires_at, 
                   created_at, last_used, usage_count
            FROM api_keys
            WHERE 1=1
        """
        
        if not include_inactive:
            query += " AND is_active = TRUE"
        
        query += " ORDER BY created_at DESC"
        
        results = await Database.fetch_all(query)
        return [dict(row) for row in results]

    @staticmethod
    async def cleanup_expired_api_keys() -> int:
        """
        Delete expired API keys
        
        Returns:
            int: Number of deleted records
        """
        query = """
            DELETE FROM api_keys
            WHERE expires_at < NOW() OR (is_active = FALSE AND revoked_at < NOW() - INTERVAL '90 days')
            RETURNING id
        """
        
        results = await Database.fetch_all(query)
        deleted_count = len(results)
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired API keys")
        
        return deleted_count

    # ==================== RATE LIMITING ====================

    @staticmethod
    async def record_rate_limit(
        identifier: str,
        action: str,
        ip_address: Optional[str] = None
    ) -> int:
        """
        Record a rate limit event
        
        Args:
            identifier: str - User ID or IP address
            action: str - Action being rate limited
            ip_address: str - IP address (optional)
        
        Returns:
            int: Record ID
        """
        query = """
            INSERT INTO rate_limits (identifier, action, ip_address, created_at)
            VALUES ($1, $2, $3, NOW())
            RETURNING id
        """
        
        result = await Database.fetch_one(query, identifier, action, ip_address)
        return result['id'] if result else 0

    @staticmethod
    async def check_rate_limit(
        identifier: str,
        action: str,
        max_requests: int = 10,
        window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """
        Check if an action exceeds rate limit
        
        Args:
            identifier: str - User ID or IP address
            action: str - Action being rate limited
            max_requests: int - Maximum requests allowed
            window_seconds: int - Time window in seconds
        
        Returns:
            tuple: (is_allowed, current_count)
        """
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        
        query = """
            SELECT COUNT(*) as count
            FROM rate_limits
            WHERE identifier = $1 
            AND action = $2
            AND created_at > $3
        """
        
        result = await Database.fetch_one(query, identifier, action, cutoff)
        current_count = result['count'] if result else 0
        
        is_allowed = current_count < max_requests
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {identifier} - Action: {action} ({current_count}/{max_requests})")
        
        return is_allowed, current_count

    @staticmethod
    async def cleanup_old_rate_limits(days: int = 7) -> int:
        """
        Delete old rate limit records
        
        Args:
            days: int - Age in days for deletion
        
        Returns:
            int: Number of deleted records
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = """
            DELETE FROM rate_limits
            WHERE created_at < $1
            RETURNING id
        """
        
        results = await Database.fetch_all(query, cutoff)
        deleted_count = len(results)
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old rate limit records")
        
        return deleted_count

    # ==================== UTILITY FUNCTIONS ====================

    @staticmethod
    def hash_token(token: str, salt: Optional[str] = None) -> str:
        """
        Hash a token (OTP, session, API key) for secure storage
        
        Args:
            token: str - Token to hash
            salt: str - Optional salt
        
        Returns:
            str: Hashed token
        """
        if salt:
            to_hash = f"{salt}{token}"
        else:
            to_hash = token
        
        return hashlib.sha256(to_hash.encode()).hexdigest()

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token
        
        Args:
            length: int - Token length in bytes (resulting hex length = length * 2)
        
        Returns:
            str: Hex token
        """
        return secrets.token_hex(length)

    @staticmethod
    async def get_auth_stats() -> Dict[str, Any]:
        """
        Get authentication statistics
        
        Returns:
            dict: Authentication statistics
        """
        query = """
            SELECT 
                (SELECT COUNT(*) FROM auth_codes WHERE used = FALSE AND expires_at > NOW()) as active_otp,
                (SELECT COUNT(*) FROM user_sessions WHERE is_active = TRUE AND expires_at > NOW()) as active_sessions,
                (SELECT COUNT(*) FROM api_keys WHERE is_active = TRUE AND (expires_at IS NULL OR expires_at > NOW())) as active_api_keys,
                (SELECT COUNT(*) FROM rate_limits WHERE created_at > NOW() - INTERVAL '1 hour') as rate_limits_last_hour
        """
        
        result = await Database.fetch_one(query)
        
        if result:
            return {
                'active_otp': result['active_otp'] or 0,
                'active_sessions': result['active_sessions'] or 0,
                'active_api_keys': result['active_api_keys'] or 0,
                'rate_limits_last_hour': result['rate_limits_last_hour'] or 0
            }
        
        return {
            'active_otp': 0,
            'active_sessions': 0,
            'active_api_keys': 0,
            'rate_limits_last_hour': 0
        }


# Import timedelta for date calculations
from datetime import timedelta