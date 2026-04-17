# telegram-bot/bot/api/__init__.py
# Estif Bingo 24/7 - API Package Initializer
# Registers all API blueprints and middleware

import logging
from flask import Blueprint, jsonify, request, g
from datetime import datetime
from bot.config import config
from bot.utils.logger import logger


# ==================== AUTH IMPORTS ====================
from bot.api.auth import (
    generate_jwt,
    generate_refresh_token,
    verify_jwt,
    refresh_jwt,
    generate_jwt_for_game,
    generate_ws_token,
    verify_ws_token,
    token_required,
    optional_token_required,
    api_key_required,
    get_current_user_from_request,
    generate_api_key,
    hash_api_key,
    register_auth_routes,
)

# ==================== BALANCE OPS IMPORTS ====================
from bot.api.balance_ops import (
    get_balance,
    add_balance,
    deduct_balance,
    set_balance,
    add_balance_bulk,
    deduct_balance_bulk,
    check_sufficient_balance,
    validate_and_deduct,
    get_balance_history,
    get_balance_summary,
    admin_adjust_balance,
    transfer_balance,
)

# ==================== COMMISSION IMPORTS ====================
from bot.api.commission import (
    calculate_commission,
    calculate_round_commission,
)
from bot.api.game_api import game_api_bp
from bot.api.webhooks import webhook_bp
from bot.api.commission import commission_bp
from bot.api.mini_bingo_api import mini_bingo_bp
from bot.api.admin_api import admin_api_bp


# Create main API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')


# ==================== MIDDLEWARE ====================

@api_bp.before_request
def before_request():
    """Execute before each API request"""
    # Log API request
    logger.debug(f"API Request: {request.method} {request.path}")
    
    # Add request start time for performance tracking
    g.start_time = datetime.utcnow()


@api_bp.after_request
def after_request(response):
    """Execute after each API request"""
    # Add response headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Calculate request duration
    if hasattr(g, 'start_time'):
        duration = (datetime.utcnow() - g.start_time).total_seconds() * 1000
        response.headers['X-Response-Time-MS'] = str(int(duration))
        
        # Log slow requests
        if duration > 1000:
            logger.warning(f"Slow API request: {request.method} {request.path} - {duration:.0f}ms")
    
    return response


@api_bp.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors"""
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'message': str(error.description) if hasattr(error, 'description') else 'Invalid request parameters'
    }), 400


@api_bp.errorhandler(401)
def unauthorized(error):
    """Handle 401 Unauthorized errors"""
    return jsonify({
        'success': False,
        'error': 'Unauthorized',
        'message': 'Authentication required'
    }), 401


@api_bp.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors"""
    return jsonify({
        'success': False,
        'error': 'Forbidden',
        'message': 'You do not have permission to access this resource'
    }), 403


@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors"""
    return jsonify({
        'success': False,
        'error': 'Not found',
        'message': 'The requested endpoint does not exist'
    }), 404


@api_bp.errorhandler(429)
def too_many_requests(error):
    """Handle 429 Too Many Requests errors"""
    return jsonify({
        'success': False,
        'error': 'Too many requests',
        'message': 'Rate limit exceeded. Please try again later.'
    }), 429


@api_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server Error"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again later.'
    }), 500


# ==================== HEALTH CHECK ENDPOINTS ====================

@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    API health check endpoint
    
    Returns:
        JSON: Health status
    """
    return jsonify({
        'success': True,
        'status': 'healthy',
        'version': '4.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'environment': config.NODE_ENV
    }), 200


@api_bp.route('/ping', methods=['GET'])
def ping():
    """
    Simple ping endpoint for connectivity testing
    
    Returns:
        JSON: Pong response
    """
    return jsonify({
        'success': True,
        'message': 'pong',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# ==================== ROOT ENDPOINT ====================

@api_bp.route('/', methods=['GET'])
def api_root():
    """
    API root endpoint with available endpoints
    
    Returns:
        JSON: API information
    """
    return jsonify({
        'success': True,
        'name': 'Estif Bingo 24/7 API',
        'version': '4.0.0',
        'description': 'Telegram Bot and Bingo Game API',
        'endpoints': {
            'auth': '/api/auth/*',
            'game': '/api/game/*',
            'mini-bingo': '/api/mini-bingo/*',
            'commission': '/api/commission/*',
            'admin': '/api/admin/*',
            'webhooks': '/api/webhooks/*',
            'health': '/api/health',
            'ping': '/api/ping'
        },
        'documentation': 'https://github.com/estif-bingo-247'
    }), 200


# ==================== BLUEPRINT REGISTRATION ====================

def register_blueprints(app):
    """
    Register all API blueprints with the Flask application
    
    Args:
        app: Flask application instance
    """
    # Register main API blueprint
    app.register_blueprint(api_bp)
    
    # Create auth blueprint and register routes
    from flask import Blueprint
    auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
    register_auth_routes(auth_bp)
    app.register_blueprint(auth_bp)
    
    # Register other blueprints
    app.register_blueprint(game_api_bp)
    app.register_blueprint(webhook_bp)
    app.register_blueprint(commission_bp)
    app.register_blueprint(mini_bingo_bp)
    app.register_blueprint(admin_api_bp)
    
    logger.info("All API blueprints registered successfully")
    
    # Log registered endpoints for debugging
    if app.debug:
        print_registered_endpoints(app)


def print_registered_endpoints(app):
    """Print all registered API endpoints for debugging"""
    endpoints = []
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/api'):
            endpoints.append(f"{rule.methods} {rule.rule}")
    
    logger.debug(f"Registered API endpoints: {len(endpoints)}")
    for endpoint in sorted(endpoints):
        logger.debug(f"  {endpoint}")


# ==================== RATE LIMITING MIDDLEWARE ====================

# Simple in-memory rate limiting (for production, use Redis)
_rate_limit_cache = {}


def rate_limit(limit=100, window=60):
    """
    Rate limiting decorator for API endpoints
    
    Args:
        limit: int - Maximum requests per window
        window: int - Time window in seconds
    
    Returns:
        decorator: Rate limiting decorator
    """
    def decorator(f):
        from functools import wraps
        
        @wraps(f)
        async def decorated(*args, **kwargs):
            # Get client identifier (IP address or API key)
            client_id = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            # Clean up old entries
            now = datetime.utcnow().timestamp()
            if client_id in _rate_limit_cache:
                _rate_limit_cache[client_id] = [
                    t for t in _rate_limit_cache[client_id] 
                    if now - t < window
                ]
            else:
                _rate_limit_cache[client_id] = []
            
            # Check rate limit
            if len(_rate_limit_cache[client_id]) >= limit:
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


# ==================== API VERSIONING ====================

class API_VERSION:
    """API version constants"""
    V1 = 'v1'
    V2 = 'v2'
    LATEST = V2


def get_api_version():
    """Get API version from request header or query param"""
    # Check header
    version = request.headers.get('X-API-Version', '')
    
    # Check query param
    if not version:
        version = request.args.get('api_version', '')
    
    # Default to latest
    if not version:
        version = API_VERSION.LATEST
    
    return version


# ==================== EXPORTS ====================

__all__ = [
    # Auth functions
    'generate_jwt',
    'generate_refresh_token',
    'verify_jwt',
    'refresh_jwt',
    'generate_jwt_for_game',
    'generate_ws_token',
    'verify_ws_token',
    'token_required',
    'optional_token_required',
    'api_key_required',
    'get_current_user_from_request',
    'generate_api_key',
    'hash_api_key',
    'register_auth_routes',
    
    # Blueprints
    'api_bp',
    'game_api_bp',
    'webhook_bp',
    'commission_bp',
    'mini_bingo_bp',
    'admin_api_bp',
    
    # Functions
    'register_blueprints',
    'rate_limit',
    'get_api_version',
    
    # Constants
    'API_VERSION',
    
    # Balance operations
    'get_balance',
    'add_balance',
    'deduct_balance',
    'set_balance',
    'add_balance_bulk',
    'deduct_balance_bulk',
    'check_sufficient_balance',
    'validate_and_deduct',
    'get_balance_history',
    'get_balance_summary',
    'admin_adjust_balance',
    'transfer_balance',
    
    # Commission calculation
    'calculate_commission',
    'calculate_round_commission',
]


# ==================== LOGGER ====================

logger.info("API package initialized")