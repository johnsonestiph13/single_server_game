# telegram-bot/bot/api/auth.py
# Estif Bingo 24/7 - API Authentication Module
# Handles JWT tokens, API key validation, and user authentication for API endpoints

import jwt
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app, session
from bot.config import config
from bot.db.repository import UserRepository, AuthRepository
from bot.utils.logger import logger

# JWT configuration
JWT_SECRET = config.JWT_SECRET
JWT_EXPIRY_HOURS = int(config.JWT_EXPIRY.replace('h', '')) if config.JWT_EXPIRY else 2
JWT_REFRESH_EXPIRY_DAYS = int(config.JWT_REFRESH_EXPIRY.replace('d', '')) if config.JWT_REFRESH_EXPIRY else 7


# ==================== JWT TOKEN FUNCTIONS ====================

def generate_jwt(user_id: int, expires_in_hours: int = None) -> str:
    """
    Generate JWT token for a user
    
    Args:
        user_id: int - User's Telegram ID
        expires_in_hours: int - Token expiry in hours (default: JWT_EXPIRY_HOURS)
    
    Returns:
        str: JWT token
    """
    if expires_in_hours is None:
        expires_in_hours = JWT_EXPIRY_HOURS
    
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    logger.debug(f"JWT generated for user {user_id}, expires in {expires_in_hours}h")
    return token


def generate_refresh_token(user_id: int) -> str:
    """
    Generate refresh token for a user
    
    Args:
        user_id: int - User's Telegram ID
    
    Returns:
        str: Refresh token
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=JWT_REFRESH_EXPIRY_DAYS),
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    logger.debug(f"Refresh token generated for user {user_id}")
    return token


def verify_jwt(token: str) -> dict:
    """
    Verify JWT token and return payload
    
    Args:
        token: str - JWT token
    
    Returns:
        dict: Token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
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


def refresh_jwt(refresh_token: str) -> dict:
    """
    Refresh JWT access token using refresh token
    
    Args:
        refresh_token: str - Refresh token
    
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
        'expires_in_hours': JWT_EXPIRY_HOURS
    }


# ==================== TOKEN REQUIRED DECORATOR ====================

def token_required(f):
    """
    Decorator to require JWT token for API endpoints
    
    Usage:
        @token_required
        async def my_endpoint(current_user):
            ...
    """
    @wraps(f)
    async def decorated(*args, **kwargs):
        # Get token from header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header:
            return jsonify({'success': False, 'error': 'Missing authorization header'}), 401
        
        # Extract token (Bearer scheme)
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'success': False, 'error': 'Invalid authorization header format. Use: Bearer <token>'}), 401
        
        token = parts[1]
        
        # Verify token
        payload = verify_jwt(token)
        
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        
        # Get user from database
        user_id = payload.get('user_id')
        user = await UserRepository.get_by_telegram_id(user_id)
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 401
        
        if not user.get('is_active', True):
            return jsonify({'success': False, 'error': 'Account is deactivated'}), 401
        
        # Add user to kwargs
        kwargs['current_user'] = user
        
        return await f(*args, **kwargs)
    
    return decorated


def optional_token_required(f):
    """
    Decorator that optionally requires JWT token (for public endpoints)
    
    Usage:
        @optional_token_required
        async def my_endpoint(current_user):
            # current_user may be None
            ...
    """
    @wraps(f)
    async def decorated(*args, **kwargs):
        current_user = None
        
        # Get token from header
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
                payload = verify_jwt(token)
                
                if payload:
                    user_id = payload.get('user_id')
                    user = await UserRepository.get_by_telegram_id(user_id)
                    if user and user.get('is_active', True):
                        current_user = user
        
        kwargs['current_user'] = current_user
        
        return await f(*args, **kwargs)
    
    return decorated


# ==================== API KEY AUTHENTICATION ====================

def api_key_required(f):
    """
    Decorator to require API key for endpoints (for external services)
    
    Usage:
        @api_key_required
        async def webhook_endpoint():
            ...
    """
    @wraps(f)
    async def decorated(*args, **kwargs):
        # Get API key from header
        api_key = request.headers.get('X-API-Key', '')
        
        if not api_key:
            return jsonify({'success': False, 'error': 'Missing API key'}), 401
        
        # Hash the API key for comparison
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Verify API key
        is_valid = await AuthRepository.verify_api_key(api_key_hash, required_permission='write')
        
        if not is_valid:
            return jsonify({'success': False, 'error': 'Invalid or expired API key'}), 401
        
        return await f(*args, **kwargs)
    
    return decorated


# ==================== AUTHENTICATION ENDPOINTS ====================

def register_auth_routes(bp):
    """
    Register authentication routes on a blueprint
    
    Args:
        bp: Flask Blueprint
    """
    
    @bp.route('/login', methods=['POST'])
    async def login():
        """
        Login endpoint - generates JWT token for game access
        
        Request body:
            {
                "telegram_id": 123456789,
                "otp": "123456"  # optional, if using OTP
            }
        
        Returns:
            JSON: Access token and user info
        """
        try:
            data = request.get_json()
            telegram_id = data.get('telegram_id')
            otp_code = data.get('otp')
            
            if not telegram_id:
                return jsonify({'success': False, 'error': 'Missing telegram_id'}), 400
            
            # Verify user exists
            user = await UserRepository.get_by_telegram_id(telegram_id)
            
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            if not user.get('registered'):
                return jsonify({'success': False, 'error': 'User not registered'}), 403
            
            # If OTP provided, verify it
            if otp_code:
                from bot.utils.security import hash_otp
                otp_hash = hash_otp(otp_code)
                is_valid = await AuthRepository.verify_otp(
                    telegram_id=telegram_id,
                    otp_hash=otp_hash,
                    purpose='game_login',
                    mark_used=True
                )
                
                if not is_valid:
                    return jsonify({'success': False, 'error': 'Invalid OTP'}), 401
            
            # Generate tokens
            access_token = generate_jwt(telegram_id)
            refresh_token = generate_refresh_token(telegram_id)
            
            return jsonify({
                'success': True,
                'data': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'expires_in_hours': JWT_EXPIRY_HOURS,
                    'user': {
                        'telegram_id': user['telegram_id'],
                        'username': user.get('username'),
                        'first_name': user.get('first_name'),
                        'balance': float(user.get('balance', 0)),
                        'is_admin': user.get('is_admin', False)
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/refresh', methods=['POST'])
    async def refresh():
        """
        Refresh access token endpoint
        
        Request body:
            {
                "refresh_token": "xxx"
            }
        
        Returns:
            JSON: New access token
        """
        try:
            data = request.get_json()
            refresh_token = data.get('refresh_token')
            
            if not refresh_token:
                return jsonify({'success': False, 'error': 'Missing refresh_token'}), 400
            
            result = refresh_jwt(refresh_token)
            
            if not result['success']:
                return jsonify({'success': False, 'error': result['error']}), 401
            
            return jsonify({
                'success': True,
                'data': {
                    'access_token': result['access_token'],
                    'expires_in_hours': result['expires_in_hours']
                }
            })
            
        except Exception as e:
            logger.error(f"Refresh error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/logout', methods=['POST'])
    @token_required
    async def logout(current_user):
        """
        Logout endpoint - invalidates current session
        """
        try:
            # Get token from header
            auth_header = request.headers.get('Authorization', '')
            token = auth_header.split()[1] if auth_header else None
            
            if token:
                # Add token to blacklist (you can implement token blacklist in Redis)
                # For now, just log the logout
                logger.info(f"User {current_user['telegram_id']} logged out")
            
            return jsonify({'success': True, 'message': 'Logged out successfully'})
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/verify', methods=['GET'])
    @token_required
    async def verify_token(current_user):
        """
        Verify token validity endpoint
        
        Returns:
            JSON: Token valid status and user info
        """
        return jsonify({
            'success': True,
            'data': {
                'valid': True,
                'user': {
                    'telegram_id': current_user['telegram_id'],
                    'username': current_user.get('username'),
                    'first_name': current_user.get('first_name'),
                    'is_admin': current_user.get('is_admin', False)
                }
            }
        })


# ==================== WEBSOCKET AUTHENTICATION ====================
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
    
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token


def generate_ws_token(user_id: int) -> str:
    """
    Generate a short-lived token for WebSocket connection
    
    Args:
        user_id: int - User's Telegram ID
    
    Returns:
        str: WebSocket token
    """
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(minutes=5),
        'iat': datetime.utcnow(),
        'type': 'websocket'
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token


def verify_ws_token(token: str) -> dict:
    """
    Verify WebSocket token
    
    Args:
        token: str - WebSocket token
    
    Returns:
        dict: Token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        
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


# ==================== UTILITY FUNCTIONS ====================

async def get_current_user_from_request() -> dict:
    """
    Get current user from request Authorization header
    
    Returns:
        dict: User data or None if not authenticated
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    token = parts[1]
    payload = verify_jwt(token)
    
    if not payload:
        return None
    
    user_id = payload.get('user_id')
    user = await UserRepository.get_by_telegram_id(user_id)
    
    return user


def generate_api_key() -> str:
    """
    Generate a new API key
    
    Returns:
        str: API key (32 characters)
    """
    return secrets.token_hex(16)


def hash_api_key(api_key: str) -> str:
    """
    Hash API key for storage
    
    Args:
        api_key: str - Raw API key
    
    Returns:
        str: Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()

# ==================== EXPORTS ====================

__all__ = [
    # JWT functions
    'generate_jwt',
    'generate_refresh_token',
    'verify_jwt',
    'refresh_jwt',
    'generate_jwt_for_game',  # ← ADD THIS
 
    # Decorators
    'token_required',
    'optional_token_required',
    'api_key_required',
    
    # WebSocket functions
    'generate_ws_token',
    'verify_ws_token',
    
    # Utility functions
    'get_current_user_from_request',
    'generate_api_key',
    'hash_api_key',
    
    # Route registration
    'register_auth_routes',
    
    # Constants
    'JWT_SECRET',
    'JWT_EXPIRY_HOURS',
    'JWT_REFRESH_EXPIRY_DAYS',
]