# telegram-bot/bot/config.py
# Estif Bingo 24/7 - Configuration Management
# Loads and manages all environment variables and bot settings

import os
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for the bot"""
    
    # ==================== BOT CONFIGURATION ====================
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    BOT_API_URL: str = os.getenv('BOT_API_URL', 'https://estif-bingo-bot-1.onrender.com')
    
    # ==================== API & SECURITY ====================
    API_SECRET: str = os.getenv('API_SECRET', '')
    JWT_SECRET: str = os.getenv('JWT_SECRET', '')
    JWT_EXPIRY: str = os.getenv('JWT_EXPIRY', '2h')
    JWT_REFRESH_EXPIRY: str = os.getenv('JWT_REFRESH_EXPIRY', '7d')
    
    # ==================== DATABASE ====================
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/estif_bingo')
    DB_POOL_MAX: int = int(os.getenv('DB_POOL_MAX', '20'))
    DB_CONNECTION_TIMEOUT: int = int(os.getenv('DB_CONNECTION_TIMEOUT', '5000'))
    DB_IDLE_TIMEOUT: int = int(os.getenv('DB_IDLE_TIMEOUT', '30000'))
    DB_COMMAND_TIMEOUT: int = int(os.getenv('DB_COMMAND_TIMEOUT', '60'))
    DB_MIN_SIZE: int = int(os.getenv('DB_MIN_SIZE', '2'))
    DB_MAX_SIZE: int = int(os.getenv('DB_MAX_SIZE', '10'))
    
    # ==================== GAME CONFIGURATION ====================
    CARTELA_PRICE: int = int(os.getenv('CARTELA_PRICE', '10'))
    MAX_CARTELAS: int = int(os.getenv('MAX_CARTELAS', '4'))
    MIN_BALANCE_FOR_PLAY: int = int(os.getenv('MIN_BALANCE_FOR_PLAY', '10'))
    SELECTION_TIME: int = int(os.getenv('SELECTION_TIME', '50'))
    DRAW_INTERVAL: int = int(os.getenv('DRAW_INTERVAL', '3000'))
    NEXT_ROUND_DELAY: int = int(os.getenv('NEXT_ROUND_DELAY', '6000'))
    TOTAL_CARTELAS: int = int(os.getenv('TOTAL_CARTELAS', '1000'))
    DEFAULT_WIN_PERCENTAGE: int = int(os.getenv('DEFAULT_WIN_PERCENTAGE', '80'))
    WIN_PERCENTAGES: List[int] = [int(x) for x in os.getenv('WIN_PERCENTAGES', '75,78,79,80').split(',')]
    
    # ==================== SOUND CONFIGURATION ====================
    DEFAULT_SOUND_PACK: str = os.getenv('DEFAULT_SOUND_PACK', 'pack1')
    SOUND_PACKS: List[str] = os.getenv('SOUND_PACKS', 'pack1,pack2,pack3,pack4').split(',')
    
    # ==================== ADMIN & SUPPORT ====================
    ADMIN_CHAT_ID: int = int(os.getenv('ADMIN_CHAT_ID', '0'))
    ADMIN_EMAIL: str = os.getenv('ADMIN_EMAIL', '')
    ADMIN_PASSWORD_HASH: str = os.getenv('ADMIN_PASSWORD_HASH', '')
    ADMIN_SESSION_EXPIRY: str = os.getenv('ADMIN_SESSION_EXPIRY', '24h')
    SUPPORT_CHANNEL_LINK: str = os.getenv('SUPPORT_CHANNEL_LINK', '')
    SUPPORT_GROUP_LINK: str = os.getenv('SUPPORT_GROUP_LINK', '')
    
    # ==================== URLS & CORS ====================
    BASE_URL: str = os.getenv('BASE_URL', 'http://localhost:5000')
    CORS_ORIGINS: List[str] = os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []
    
    # ==================== PAYMENT CONFIGURATION ====================
    PAYMENT_ACCOUNTS: Dict[str, str] = {
        'CBE': os.getenv('CBE_ACCOUNT', ''),
        'ABYSSINIA': os.getenv('ABYSSINIA_ACCOUNT', ''),
        'TELEBIRR': os.getenv('TELEBIRR_ACCOUNT', ''),
        'MPESA': os.getenv('MPESA_ACCOUNT', ''),
    }
    ACCOUNT_HOLDER: str = os.getenv('ACCOUNT_HOLDER', 'Estif Bingo 24/7')
    MIN_DEPOSIT: int = int(os.getenv('MIN_DEPOSIT', '10'))
    MAX_DEPOSIT: int = int(os.getenv('MAX_DEPOSIT', '10000'))
    MIN_WITHDRAWAL: int = int(os.getenv('MIN_WITHDRAWAL', '50'))
    MAX_WITHDRAWAL: int = int(os.getenv('MAX_WITHDRAWAL', '10000'))
    MIN_TRANSFER: int = int(os.getenv('MIN_TRANSFER', '10'))
    MAX_TRANSFER: int = int(os.getenv('MAX_TRANSFER', '5000'))
    TRANSFER_FEE_PERCENT: float = float(os.getenv('TRANSFER_FEE_PERCENT', '0'))
    
    # ==================== WEBHOOK SECRETS ====================
    TELEBIRR_WEBHOOK_SECRET: str = os.getenv('TELEBIRR_WEBHOOK_SECRET', '')
    CBE_WEBHOOK_SECRET: str = os.getenv('CBE_WEBHOOK_SECRET', '')
    ABYSSINIA_WEBHOOK_SECRET: str = os.getenv('ABYSSINIA_WEBHOOK_SECRET', '')
    MPESA_WEBHOOK_SECRET: str = os.getenv('MPESA_WEBHOOK_SECRET', '')
    
    # ==================== RATE LIMITING ====================
    RATE_LIMIT_MAX: int = int(os.getenv('RATE_LIMIT_MAX', '100'))
    RATE_LIMIT_WINDOW_MS: int = int(os.getenv('RATE_LIMIT_WINDOW_MS', '900000'))
    AUTH_RATE_LIMIT_MAX: int = int(os.getenv('AUTH_RATE_LIMIT_MAX', '5'))
    GAME_RATE_LIMIT_MAX: int = int(os.getenv('GAME_RATE_LIMIT_MAX', '30'))
    
    # ==================== WEBSOCKET ====================
    WS_PING_INTERVAL: int = int(os.getenv('WS_PING_INTERVAL', '25000'))
    WS_PING_TIMEOUT: int = int(os.getenv('WS_PING_TIMEOUT', '60000'))
    WS_RECONNECT_DELAY: int = int(os.getenv('WS_RECONNECT_DELAY', '1000'))
    WS_MAX_RECONNECT_ATTEMPTS: int = int(os.getenv('WS_MAX_RECONNECT_ATTEMPTS', '10'))
    
    # ==================== FEATURE FLAGS ====================
    ENABLE_REFERRAL: bool = os.getenv('ENABLE_REFERRAL', 'false').lower() == 'true'
    ENABLE_DAILY_BONUS: bool = os.getenv('ENABLE_DAILY_BONUS', 'false').lower() == 'true'
    ENABLE_TOURNAMENT: bool = os.getenv('ENABLE_TOURNAMENT', 'false').lower() == 'true'
    MANUAL_MIGRATION: bool = os.getenv('MANUAL_MIGRATION', 'false').lower() == 'true'
    SKIP_AUTO_MIGRATIONS: bool = os.getenv('SKIP_AUTO_MIGRATIONS', 'false').lower() == 'true'
    LOG_TO_FILE: bool = os.getenv('LOG_TO_FILE', 'false').lower() == 'true'
    
    # ==================== BONUS SETTINGS ====================
    WELCOME_BONUS_AMOUNT: int = int(os.getenv('WELCOME_BONUS_AMOUNT', '30'))
    DAILY_BONUS_AMOUNT: int = int(os.getenv('DAILY_BONUS_AMOUNT', '5'))
    
    # ==================== MINI BINGO SETTINGS ====================
    MINI_BINGO_PRICE: int = int(os.getenv('MINI_BINGO_PRICE', '5'))
    MINI_BINGO_WIN_PERCENTAGE: int = int(os.getenv('MINI_BINGO_WIN_PERCENTAGE', '80'))
    
    # ==================== LOGGING ====================
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'info')
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    NODE_ENV: str = os.getenv('NODE_ENV', 'production')
    
    # ==================== DEPLOYMENT ====================
    PORT: int = int(os.getenv('PORT', '10000'))
    PYTHON_VERSION: str = os.getenv('PYTHON_VERSION', '3.11.0')
    
    # ==================== VALIDATION ====================
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate required configuration settings"""
        errors = []
        
        # Required settings
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is required")
        
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        if not cls.JWT_SECRET:
            errors.append("JWT_SECRET is required")
        
        if not cls.API_SECRET:
            errors.append("API_SECRET is required")
        
        if cls.ADMIN_CHAT_ID == 0:
            errors.append("ADMIN_CHAT_ID is required")
        
        # Validate win percentages
        for percent in cls.WIN_PERCENTAGES:
            if percent < 1 or percent > 100:
                errors.append(f"Invalid WIN_PERCENTAGES value: {percent}")
        
        # Validate selection time
        if cls.SELECTION_TIME < 10 or cls.SELECTION_TIME > 120:
            errors.append(f"SELECTION_TIME must be between 10 and 120, got {cls.SELECTION_TIME}")
        
        # Validate draw interval
        if cls.DRAW_INTERVAL < 1000 or cls.DRAW_INTERVAL > 10000:
            errors.append(f"DRAW_INTERVAL must be between 1000 and 10000, got {cls.DRAW_INTERVAL}")
        
        return errors
    
    @classmethod
    def display_config(cls) -> Dict[str, Any]:
        """Display current configuration (hiding sensitive values)"""
        return {
            'bot_token': '***' if cls.BOT_TOKEN else 'NOT SET',
            'bot_api_url': cls.BOT_API_URL,
            'database_url': '***' if cls.DATABASE_URL else 'NOT SET',
            'jwt_secret': '***' if cls.JWT_SECRET else 'NOT SET',
            'api_secret': '***' if cls.API_SECRET else 'NOT SET',
            'admin_chat_id': cls.ADMIN_CHAT_ID,
            'base_url': cls.BASE_URL,
            'cartela_price': cls.CARTELA_PRICE,
            'max_cartelas': cls.MAX_CARTELAS,
            'selection_time': cls.SELECTION_TIME,
            'draw_interval': cls.DRAW_INTERVAL,
            'win_percentages': cls.WIN_PERCENTAGES,
            'default_win_percentage': cls.DEFAULT_WIN_PERCENTAGE,
            'enable_referral': cls.ENABLE_REFERRAL,
            'enable_daily_bonus': cls.ENABLE_DAILY_BONUS,
            'enable_tournament': cls.ENABLE_TOURNAMENT,
            'node_env': cls.NODE_ENV,
            'port': cls.PORT,
        }


# Create config instance for easy import
config = Config

# Export all
__all__ = [
    'Config',
    'config',
]