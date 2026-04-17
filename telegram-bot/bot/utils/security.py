# telegram-bot/bot/utils/security.py
# Estif Bingo 24/7 - Security Utilities
# Handles JWT tokens, password hashing, OTP generation, and security functions

import hashlib
import hmac
import secrets
import re
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from functools import wraps
from flask import request, jsonify

import jwt
from passlib.context import CryptContext

from bot.config import config
from bot.utils.logger import logger

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
JWT_SECRET = config.JWT_SECRET
JWT_ALGORITHM = "HS256"


# ==================== JWT TOKEN FUNCTIONS ====================

def generate_jwt(user_id: int, expires_in_hours: int = 2) -> str:
    """
    Generate JWT token for a user.
    
    Args:
        user_id: User's Telegram ID
        expires_in_hours: Token expiry in hours
    
    Returns:
        str: JWT token
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.debug(f"JWT generated for user {user_id}, expires in {expires_in_hours}h")
    return token


def generate_refresh_token(user_id: int) -> str:
    """
    Generate refresh token for a user.
    
    Args:
        user_id: User's Telegram ID
    
    Returns:
        str: Refresh token
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.debug(f"Refresh token generated for user {user_id}")
    return token


def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token and return payload.
    
    Args:
        token: JWT token
    
    Returns:
        dict: Token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Check if token is expired
        if payload.get('exp', 0) < datetime.utcnow().timestamp():
            logger.warning("JWT token expired")
            return None
        
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


def refresh_jwt(refresh_token: str) -> Dict[str, Any]:
    """
    Refresh JWT access token using refresh token.
    
    Args:
        refresh_token: Refresh token
    
    Returns:
        dict: New access token or error
    """
    payload = verify_jwt(refresh_token)
    
    if not payload:
        return {'success': False, 'error': 'Invalid or expired refresh token'}
    
    if payload.get('type') != 'refresh':
        return {'success': False, 'error': 'Invalid token type'}
    
    user_id = payload.get('user_id')
    
    if not user_id:
        return {'success': False, 'error': 'Invalid token payload'}
    
    # Generate new access token
    new_access_token = generate_jwt(user_id)
    
    return {
        'success': True,
        'access_token': new_access_token,
        'expires_in_hours': 2
    }


def generate_jwt_for_game(telegram_id: int) -> str:
    """
    Generate JWT token specifically for game access.
    
    Args:
        telegram_id: User's Telegram ID
    
    Returns:
        str: JWT token for game
    """
    payload = {
        'user_id': telegram_id,
        'exp': datetime.utcnow() + timedelta(hours=2),
        'iat': datetime.utcnow(),
        'purpose': 'game_access',
        'type': 'game'
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def generate_ws_token(telegram_id: int) -> str:
    """
    Generate short-lived token for WebSocket connection.
    
    Args:
        telegram_id: User's Telegram ID
    
    Returns:
        str: WebSocket token
    """
    payload = {
        'user_id': telegram_id,
        'exp': datetime.utcnow() + timedelta(minutes=5),
        'iat': datetime.utcnow(),
        'purpose': 'websocket',
        'type': 'websocket'
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_ws_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify WebSocket token.
    
    Args:
        token: WebSocket token
    
    Returns:
        dict: Token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        if payload.get('type') != 'websocket':
            logger.warning("Invalid WS token type")
            return None
        
        if payload.get('exp', 0) < datetime.utcnow().timestamp():
            logger.warning("WS token expired")
            return None
        
        return payload
    except Exception as e:
        logger.warning(f"Invalid WS token: {e}")
        return None


# ==================== PASSWORD HASHING ====================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password
        password_hash: Hashed password
    
    Returns:
        bool: True if password matches
    """
    try:
        return pwd_context.verify(password, password_hash)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# ==================== OTP FUNCTIONS ====================

def generate_otp(length: int = 6) -> str:
    """
    Generate numeric OTP code.
    
    Args:
        length: Length of OTP (default: 6)
    
    Returns:
        str: OTP code
    """
    return ''.join(secrets.choice('0123456789') for _ in range(length))


def hash_otp(otp: str, salt: Optional[str] = None) -> str:
    """
    Hash OTP for secure storage.
    
    Args:
        otp: OTP code
        salt: Optional salt (uses JWT_SECRET if not provided)
    
    Returns:
        str: Hashed OTP
    """
    if salt is None:
        salt = JWT_SECRET[:16]
    
    return hashlib.sha256(f"{salt}{otp}".encode()).hexdigest()


def verify_otp(otp: str, otp_hash: str, salt: Optional[str] = None) -> bool:
    """
    Verify OTP against its hash.
    
    Args:
        otp: OTP code to verify
        otp_hash: Stored OTP hash
        salt: Optional salt
    
    Returns:
        bool: True if OTP matches
    """
    return hash_otp(otp, salt) == otp_hash


# ==================== API KEY FUNCTIONS ====================

def generate_api_key() -> str:
    """
    Generate a new API key.
    
    Returns:
        str: API key (32 characters hex)
    """
    return secrets.token_hex(32)


def hash_api_key(api_key: str) -> str:
    """
    Hash API key for storage.
    
    Args:
        api_key: Raw API key
    
    Returns:
        str: Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, api_key_hash: str) -> bool:
    """
    Verify API key against its hash.
    
    Args:
        api_key: Raw API key
        api_key_hash: Stored API key hash
    
    Returns:
        bool: True if API key matches
    """
    return hash_api_key(api_key) == api_key_hash


# ==================== IDEMPOTENCY KEY ====================

def generate_idempotency_key(prefix: str = "ik") -> str:
    """
    Generate a unique idempotency key.
    
    Args:
        prefix: Prefix for the key
    
    Returns:
        str: Idempotency key
    """
    timestamp = int(time.time() * 1000)
    random_part = secrets.token_hex(8)
    return f"{prefix}_{timestamp}_{random_part}"


# ==================== RATE LIMITING ====================

# Simple in-memory rate limiting (for production, use Redis)
_rate_limit_cache: Dict[str, list] = {}


def rate_limit(limit: int = 100, window: int = 60):
    """
    Rate limiting decorator for API endpoints.
    
    Args:
        limit: Maximum requests per window
        window: Time window in seconds
    
    Returns:
        decorator: Rate limiting decorator
    """
    def decorator(f):
        @wraps(f)
        async def decorated(*args, **kwargs):
            # Get client identifier
            client_id = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            # Clean up old entries
            now = time.time()
            if client_id in _rate_limit_cache:
                _rate_limit_cache[client_id] = [
                    t for t in _rate_limit_cache[client_id] 
                    if now - t < window
                ]
            else:
                _rate_limit_cache[client_id] = []
            
            # Check rate limit
            if len(_rate_limit_cache[client_id]) >= limit:
                logger.warning(f"Rate limit exceeded for {client_id}")
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {limit} requests per {window} seconds'
                }), 429
            
            # Add current request
            _rate_limit_cache[client_id].append(now)
            
            return await f(*args, **kwargs)
        
        return decorated
    return decorator


def clear_rate_limit_cache():
    """Clear the rate limit cache."""
    global _rate_limit_cache
    _rate_limit_cache.clear()
    logger.info("Rate limit cache cleared")


# ==================== INPUT SANITIZATION ====================

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
    
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Truncate
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove dangerous characters
    text = re.sub(r'[<>]', '', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    
    return text.strip()


def sanitize_phone(phone: str) -> str:
    """
    Sanitize phone number input.
    
    Args:
        phone: Phone number string
    
    Returns:
        str: Sanitized phone number
    """
    if not phone:
        return ""
    
    # Keep only digits and plus sign
    phone = re.sub(r'[^\d+]', '', phone)
    
    return phone


def sanitize_amount(amount: str) -> Optional[float]:
    """
    Sanitize and parse amount input.
    
    Args:
        amount: Amount string
    
    Returns:
        float: Parsed amount or None if invalid
    """
    if not amount:
        return None
    
    # Remove commas and spaces
    amount = amount.replace(',', '').replace(' ', '')
    
    # Check if valid number
    try:
        value = float(amount)
        if value <= 0:
            return None
        return round(value, 2)
    except ValueError:
        return None


# ==================== SIGNATURE VERIFICATION ====================

def generate_signature(payload: str, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook verification.
    
    Args:
        payload: Raw payload string
        secret: Secret key
    
    Returns:
        str: Signature
    """
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify webhook signature.
    
    Args:
        payload: Raw payload string
        signature: Signature from header
        secret: Secret key
    
    Returns:
        bool: True if signature is valid
    """
    if not signature or not secret:
        return False
    
    expected = generate_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


# ==================== TOKEN GENERATION ====================

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes
    
    Returns:
        str: Hex token
    """
    return secrets.token_hex(length)


def generate_short_code(prefix: str = "", length: int = 8) -> str:
    """
    Generate a short alphanumeric code.
    
    Args:
        prefix: Optional prefix
        length: Length of the random part
    
    Returns:
        str: Short code
    """
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    if prefix:
        return f"{prefix}_{random_part}"
    return random_part


# ==================== ENCRYPTION HELPERS ====================

def simple_encrypt(text: str, key: str) -> str:
    """
    Simple XOR encryption for non-critical data.
    Note: For sensitive data, use proper encryption (crypto.py).
    
    Args:
        text: Text to encrypt
        key: Encryption key
    
    Returns:
        str: Encrypted text (hex)
    """
    if not text:
        return ""
    
    key_bytes = key.encode()
    text_bytes = text.encode()
    result = bytearray()
    
    for i, byte in enumerate(text_bytes):
        result.append(byte ^ key_bytes[i % len(key_bytes)])
    
    return result.hex()


def simple_decrypt(hex_text: str, key: str) -> str:
    """
    Simple XOR decryption for non-critical data.
    
    Args:
        hex_text: Encrypted hex text
        key: Encryption key
    
    Returns:
        str: Decrypted text
    """
    if not hex_text:
        return ""
    
    try:
        text_bytes = bytes.fromhex(hex_text)
        key_bytes = key.encode()
        result = bytearray()
        
        for i, byte in enumerate(text_bytes):
            result.append(byte ^ key_bytes[i % len(key_bytes)])
        
        return result.decode()
    except Exception:
        return ""


# ==================== EXPORTS ====================

__all__ = [
    # JWT functions
    'generate_jwt',
    'generate_refresh_token',
    'verify_jwt',
    'refresh_jwt',
    'generate_jwt_for_game',
    'generate_ws_token',
    'verify_ws_token',
    
    # Password functions
    'hash_password',
    'verify_password',
    
    # OTP functions
    'generate_otp',
    'hash_otp',
    'verify_otp',
    
    # API key functions
    'generate_api_key',
    'hash_api_key',
    'verify_api_key',
    
    # Idempotency
    'generate_idempotency_key',
    
    # Rate limiting
    'rate_limit',
    'clear_rate_limit_cache',
    
    # Input sanitization
    'sanitize_input',
    'sanitize_phone',
    'sanitize_amount',
    
    # Signature verification
    'generate_signature',
    'verify_signature',
    
    # Token generation
    'generate_secure_token',
    'generate_short_code',
    
    # Simple encryption
    'simple_encrypt',
    'simple_decrypt',
]