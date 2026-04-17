# telegram-bot/bot/utils/otp.py
# Estif Bingo 24/7 - OTP (One-Time Password) Utilities
# Handles OTP generation, validation, rate limiting, and storage

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from collections import defaultdict

from bot.config import config
from bot.utils.logger import logger

# OTP Configuration
OTP_LENGTH = 6
OTP_EXPIRY_SECONDS = 300  # 5 minutes
MAX_OTP_ATTEMPTS = 5
OTP_RATE_LIMIT_SECONDS = 60  # 1 minute
MAX_OTP_PER_HOUR = 10


# In-memory OTP storage (for development)
# In production, use Redis or database
_otp_storage: Dict[str, Dict] = {}
_otp_attempts: Dict[str, int] = {}
_otp_rate_limit: Dict[str, list] = defaultdict(list)


# ==================== OTP GENERATION ====================

def generate_otp(length: int = OTP_LENGTH) -> str:
    """
    Generate a numeric OTP code.
    
    Args:
        length: Length of OTP (default: 6)
    
    Returns:
        str: OTP code
    """
    return ''.join(secrets.choice('0123456789') for _ in range(length))


def generate_alphanumeric_otp(length: int = 8) -> str:
    """
    Generate an alphanumeric OTP code.
    
    Args:
        length: Length of OTP (default: 8)
    
    Returns:
        str: Alphanumeric OTP code
    """
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_otp_hash(otp: str, salt: Optional[str] = None) -> str:
    """
    Generate a hash of the OTP for secure storage.
    
    Args:
        otp: OTP code
        salt: Optional salt (uses JWT_SECRET if not provided)
    
    Returns:
        str: Hashed OTP
    """
    if salt is None:
        salt = config.JWT_SECRET[:16]
    
    return hashlib.sha256(f"{salt}{otp}".encode()).hexdigest()


def verify_otp_hash(otp: str, otp_hash: str, salt: Optional[str] = None) -> bool:
    """
    Verify OTP against its hash.
    
    Args:
        otp: OTP code to verify
        otp_hash: Stored OTP hash
        salt: Optional salt
    
    Returns:
        bool: True if OTP matches
    """
    return generate_otp_hash(otp, salt) == otp_hash


# ==================== OTP STORAGE (Memory) ====================

def store_otp(
    key: str,
    otp: str,
    expiry_seconds: int = OTP_EXPIRY_SECONDS,
    purpose: str = "general"
) -> None:
    """
    Store OTP in memory with expiry.
    
    Args:
        key: Unique identifier (e.g., user_id + purpose)
        otp: OTP code
        expiry_seconds: Expiry time in seconds
        purpose: Purpose of OTP (e.g., 'login', 'verification')
    """
    _otp_storage[key] = {
        'otp_hash': generate_otp_hash(otp),
        'expires_at': time.time() + expiry_seconds,
        'purpose': purpose,
        'created_at': time.time()
    }
    logger.debug(f"OTP stored for key: {key}, expires in {expiry_seconds}s")


def get_stored_otp(key: str) -> Optional[Dict]:
    """
    Get stored OTP data.
    
    Args:
        key: Unique identifier
    
    Returns:
        dict: OTP data or None if not found/expired
    """
    otp_data = _otp_storage.get(key)
    
    if not otp_data:
        return None
    
    # Check if expired
    if time.time() > otp_data['expires_at']:
        del _otp_storage[key]
        return None
    
    return otp_data


def verify_stored_otp(key: str, otp: str, consume: bool = True) -> bool:
    """
    Verify OTP against stored value.
    
    Args:
        key: Unique identifier
        otp: OTP to verify
        consume: Whether to consume the OTP after verification
    
    Returns:
        bool: True if OTP is valid
    """
    otp_data = get_stored_otp(key)
    
    if not otp_data:
        logger.warning(f"OTP not found or expired for key: {key}")
        return False
    
    # Verify OTP
    is_valid = verify_otp_hash(otp, otp_data['otp_hash'])
    
    # Consume OTP if valid and consume is True
    if is_valid and consume:
        del _otp_storage[key]
    
    return is_valid


def delete_stored_otp(key: str) -> bool:
    """
    Delete stored OTP.
    
    Args:
        key: Unique identifier
    
    Returns:
        bool: True if deleted
    """
    if key in _otp_storage:
        del _otp_storage[key]
        return True
    return False


def clear_expired_otps() -> int:
    """
    Clear all expired OTPs from memory.
    
    Returns:
        int: Number of OTPs cleared
    """
    current_time = time.time()
    expired_keys = [
        key for key, data in _otp_storage.items()
        if current_time > data['expires_at']
    ]
    
    for key in expired_keys:
        del _otp_storage[key]
    
    if expired_keys:
        logger.debug(f"Cleared {len(expired_keys)} expired OTPs")
    
    return len(expired_keys)


# ==================== OTP ATTEMPT TRACKING ====================

def record_otp_attempt(key: str) -> int:
    """
    Record an OTP verification attempt.
    
    Args:
        key: Unique identifier
    
    Returns:
        int: Number of attempts made
    """
    _otp_attempts[key] = _otp_attempts.get(key, 0) + 1
    return _otp_attempts[key]


def get_otp_attempts(key: str) -> int:
    """
    Get number of OTP verification attempts.
    
    Args:
        key: Unique identifier
    
    Returns:
        int: Number of attempts
    """
    return _otp_attempts.get(key, 0)


def reset_otp_attempts(key: str) -> None:
    """
    Reset OTP verification attempts.
    
    Args:
        key: Unique identifier
    """
    if key in _otp_attempts:
        del _otp_attempts[key]


def is_otp_locked(key: str, max_attempts: int = MAX_OTP_ATTEMPTS) -> bool:
    """
    Check if OTP is locked due to too many attempts.
    
    Args:
        key: Unique identifier
        max_attempts: Maximum allowed attempts
    
    Returns:
        bool: True if locked
    """
    attempts = get_otp_attempts(key)
    return attempts >= max_attempts


# ==================== OTP RATE LIMITING ====================

def check_otp_rate_limit(key: str) -> Tuple[bool, int]:
    """
    Check if OTP generation rate limit is exceeded.
    
    Args:
        key: Unique identifier
    
    Returns:
        tuple: (is_allowed, seconds_to_wait)
    """
    now = time.time()
    recent_requests = _otp_rate_limit[key]
    
    # Remove old requests
    recent_requests = [t for t in recent_requests if now - t < OTP_RATE_LIMIT_SECONDS]
    _otp_rate_limit[key] = recent_requests
    
    if len(recent_requests) >= MAX_OTP_PER_HOUR:
        oldest = min(recent_requests)
        wait_seconds = int(OTP_RATE_LIMIT_SECONDS - (now - oldest))
        return False, max(0, wait_seconds)
    
    return True, 0


def record_otp_request(key: str) -> None:
    """
    Record an OTP generation request for rate limiting.
    
    Args:
        key: Unique identifier
    """
    _otp_rate_limit[key].append(time.time())


# ==================== COMPLETE OTP WORKFLOW ====================

def create_otp(
    identifier: str,
    purpose: str = "verification",
    length: int = OTP_LENGTH,
    expiry_seconds: int = OTP_EXPIRY_SECONDS
) -> Tuple[str, str]:
    """
    Create a new OTP and return both the raw OTP and its hash.
    
    Args:
        identifier: User identifier (e.g., telegram_id)
        purpose: Purpose of OTP
        length: OTP length
        expiry_seconds: Expiry time in seconds
    
    Returns:
        tuple: (raw_otp, otp_hash)
    """
    otp = generate_otp(length)
    otp_hash = generate_otp_hash(otp)
    key = f"{identifier}:{purpose}"
    
    _otp_storage[key] = {
        'otp_hash': otp_hash,
        'expires_at': time.time() + expiry_seconds,
        'purpose': purpose,
        'created_at': time.time()
    }
    
    logger.debug(f"OTP created for {identifier}:{purpose}")
    return otp, otp_hash


def validate_otp(
    identifier: str,
    otp: str,
    purpose: str = "verification",
    consume: bool = True,
    max_attempts: int = MAX_OTP_ATTEMPTS
) -> Tuple[bool, str]:
    """
    Validate an OTP with attempt tracking.
    
    Args:
        identifier: User identifier
        otp: OTP to validate
        purpose: Purpose of OTP
        consume: Whether to consume the OTP after validation
        max_attempts: Maximum allowed attempts
    
    Returns:
        tuple: (is_valid, message)
    """
    key = f"{identifier}:{purpose}"
    
    # Check if locked
    if is_otp_locked(key, max_attempts):
        return False, "Too many failed attempts. Please request a new OTP."
    
    # Get stored OTP
    otp_data = get_stored_otp(key)
    
    if not otp_data:
        record_otp_attempt(key)
        return False, "OTP expired or not found. Please request a new OTP."
    
    # Verify OTP
    is_valid = verify_otp_hash(otp, otp_data['otp_hash'])
    
    if is_valid:
        reset_otp_attempts(key)
        if consume:
            delete_stored_otp(key)
        return True, "OTP verified successfully"
    else:
        attempts = record_otp_attempt(key)
        remaining = max_attempts - attempts
        return False, f"Invalid OTP. {remaining} attempts remaining."


def request_new_otp(
    identifier: str,
    purpose: str = "verification",
    length: int = OTP_LENGTH,
    expiry_seconds: int = OTP_EXPIRY_SECONDS
) -> Tuple[bool, str, Optional[str]]:
    """
    Request a new OTP with rate limiting.
    
    Args:
        identifier: User identifier
        purpose: Purpose of OTP
        length: OTP length
        expiry_seconds: Expiry time in seconds
    
    Returns:
        tuple: (success, message, otp)
    """
    key = f"{identifier}:{purpose}"
    
    # Check rate limit
    is_allowed, wait_seconds = check_otp_rate_limit(key)
    
    if not is_allowed:
        return False, f"Rate limit exceeded. Please wait {wait_seconds} seconds.", None
    
    # Delete old OTP if exists
    delete_stored_otp(key)
    reset_otp_attempts(key)
    
    # Create new OTP
    otp, otp_hash = create_otp(identifier, purpose, length, expiry_seconds)
    record_otp_request(key)
    
    logger.info(f"New OTP requested for {identifier}:{purpose}")
    return True, "OTP sent successfully", otp


# ==================== TIME-BASED OTP (TOTP) ====================

class TOTP:
    """
    Time-based One-Time Password (TOTP) generator.
    Compatible with Google Authenticator.
    """
    
    def __init__(self, secret_key: Optional[str] = None, digits: int = 6, interval: int = 30):
        """
        Initialize TOTP generator.
        
        Args:
            secret_key: Secret key for TOTP
            digits: Number of digits (default: 6)
            interval: Time interval in seconds (default: 30)
        """
        self.secret_key = secret_key or secrets.token_hex(20)
        self.digits = digits
        self.interval = interval
    
    def get_secret_key(self) -> str:
        """Get the secret key."""
        return self.secret_key
    
    def _get_time_counter(self, timestamp: Optional[int] = None) -> int:
        """Get the time counter for TOTP."""
        if timestamp is None:
            timestamp = int(time.time())
        return timestamp // self.interval
    
    def _hotp(self, counter: int) -> str:
        """Generate HOTP (HMAC-based OTP)."""
        counter_bytes = counter.to_bytes(8, 'big')
        hmac_hash = hmac.new(
            self.secret_key.encode(),
            counter_bytes,
            hashlib.sha1
        ).digest()
        
        offset = hmac_hash[-1] & 0x0f
        code = (
            (hmac_hash[offset] & 0x7f) << 24 |
            (hmac_hash[offset + 1] & 0xff) << 16 |
            (hmac_hash[offset + 2] & 0xff) << 8 |
            (hmac_hash[offset + 3] & 0xff)
        )
        
        return str(code % (10 ** self.digits)).zfill(self.digits)
    
    def generate(self, timestamp: Optional[int] = None) -> str:
        """
        Generate TOTP code.
        
        Args:
            timestamp: Optional timestamp (default: current time)
        
        Returns:
            str: TOTP code
        """
        counter = self._get_time_counter(timestamp)
        return self._hotp(counter)
    
    def verify(self, otp: str, timestamp: Optional[int] = None, window: int = 1) -> bool:
        """
        Verify TOTP code.
        
        Args:
            otp: OTP to verify
            timestamp: Optional timestamp
            window: Time window (number of intervals before/after)
        
        Returns:
            bool: True if valid
        """
        counter = self._get_time_counter(timestamp)
        
        for i in range(-window, window + 1):
            if self._hotp(counter + i) == otp:
                return True
        
        return False
    
    def get_provisioning_uri(self, account_name: str, issuer: str = "Estif Bingo") -> str:
        """
        Get provisioning URI for QR code generation.
        
        Args:
            account_name: User account name
            issuer: Issuer name
        
        Returns:
            str: Provisioning URI
        """
        return f"otpauth://totp/{issuer}:{account_name}?secret={self.secret_key}&issuer={issuer}&digits={self.digits}"


# ==================== UTILITY FUNCTIONS ====================

def format_otp_message(otp: str, purpose: str = "verification", expiry_minutes: int = 5) -> str:
    """
    Format OTP message for sending to user.
    
    Args:
        otp: OTP code
        purpose: Purpose of OTP
        expiry_minutes: Expiry time in minutes
    
    Returns:
        str: Formatted message
    """
    messages = {
        "login": f"Your login code is: {otp}\nValid for {expiry_minutes} minutes.",
        "verification": f"Your verification code is: {otp}\nValid for {expiry_minutes} minutes.",
        "withdrawal": f"Your withdrawal confirmation code is: {otp}\nValid for {expiry_minutes} minutes.",
        "transfer": f"Your transfer confirmation code is: {otp}\nValid for {expiry_minutes} minutes.",
    }
    
    return messages.get(purpose, f"Your OTP code is: {otp}\nValid for {expiry_minutes} minutes.")


def cleanup_otp_storage() -> Dict[str, int]:
    """
    Clean up expired OTPs and old rate limit data.
    
    Returns:
        dict: Cleanup statistics
    """
    expired_otps = clear_expired_otps()
    
    # Clean up old rate limit data
    current_time = time.time()
    for key in list(_otp_rate_limit.keys()):
        _otp_rate_limit[key] = [t for t in _otp_rate_limit[key] if current_time - t < OTP_RATE_LIMIT_SECONDS]
        if not _otp_rate_limit[key]:
            del _otp_rate_limit[key]
    
    return {
        'expired_otps': expired_otps,
        'rate_limit_keys': len(_otp_rate_limit)
    }


# ==================== EXPORTS ====================

__all__ = [
    # Generation
    'generate_otp',
    'generate_alphanumeric_otp',
    'generate_otp_hash',
    'verify_otp_hash',
    
    # Storage
    'store_otp',
    'get_stored_otp',
    'verify_stored_otp',
    'delete_stored_otp',
    'clear_expired_otps',
    
    # Attempt tracking
    'record_otp_attempt',
    'get_otp_attempts',
    'reset_otp_attempts',
    'is_otp_locked',
    
    # Rate limiting
    'check_otp_rate_limit',
    'record_otp_request',
    
    # Complete workflow
    'create_otp',
    'validate_otp',
    'request_new_otp',
    
    # TOTP
    'TOTP',
    
    # Utility
    'format_otp_message',
    'cleanup_otp_storage',
    
    # Constants
    'OTP_LENGTH',
    'OTP_EXPIRY_SECONDS',
    'MAX_OTP_ATTEMPTS',
    'OTP_RATE_LIMIT_SECONDS',
    'MAX_OTP_PER_HOUR',
]