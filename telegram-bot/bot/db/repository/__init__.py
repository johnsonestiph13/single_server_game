# telegram-bot/bot/db/repository/__init__.py
# Estif Bingo 24/7 - Database Repositories Package
# Exports all repository classes for database operations

# ==================== CORE REPOSITORIES ====================

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.transaction_repo import TransactionRepository
from bot.db.repository.audit_repo import AuditRepository

# ==================== AUTHENTICATION REPOSITORIES ====================

from bot.db.repository.auth_repo import AuthRepository

# ==================== FINANCIAL REPOSITORIES ====================

from bot.db.repository.deposit_repo import DepositRepository
from bot.db.repository.withdrawal_repo import WithdrawalRepository
from bot.db.repository.transfer_repo import TransferRepository

# ==================== GAME REPOSITORIES ====================

from bot.db.repository.game_repo import GameRepository
from bot.db.repository.cartela_repo import CartelaRepository, active_game_cartelas

# ==================== BONUS REPOSITORIES ====================

from bot.db.repository.bonus_repo import BonusRepository

# ==================== TOURNAMENT REPOSITORIES ====================

from bot.db.repository.tournament_repo import TournamentRepository

# ==================== ADMIN REPOSITORIES ====================

from bot.db.repository.admin_repo import AdminRepository

# ==================== CONVENIENCE DICTIONARY ====================

# Dictionary mapping repository names to their classes for dynamic access
REPOSITORY_MAP = {
    'user': UserRepository,
    'transaction': TransactionRepository,
    'audit': AuditRepository,
    'auth': AuthRepository,
    'deposit': DepositRepository,
    'withdrawal': WithdrawalRepository,
    'transfer': TransferRepository,
    'game': GameRepository,
    'cartela': CartelaRepository,
    'bonus': BonusRepository,
    'tournament': TournamentRepository,
    'admin': AdminRepository,
}

# ==================== INITIALIZATION FUNCTION ====================

async def initialize_repositories(json_path: str = "data/cartelas_1000.json") -> dict:
    """
    Initialize all repositories (load cartelas, create default settings, etc.)
    
    Args:
        json_path: str - Path to cartelas JSON file
    
    Returns:
        dict: Initialization results
    """
    results = {
        'cartelas_loaded': 0,
        'settings_initialized': False,
        'errors': []
    }
    
    try:
        # Initialize cartelas
        cartelas_count = await CartelaRepository.initialize_cartelas(json_path)
        results['cartelas_loaded'] = cartelas_count
    except Exception as e:
        results['errors'].append(f"Cartela initialization failed: {e}")
    
    try:
        # Initialize default system settings if not exists
        from bot.config import config
        
        # Check if settings exist
        existing_settings = await AdminRepository.get_all_settings()
        
        if not existing_settings:
            # Create default settings
            default_settings = {
                'winning_percentage': getattr(config, 'DEFAULT_WIN_PERCENTAGE', 80),
                'default_sound_pack': getattr(config, 'DEFAULT_SOUND_PACK', 'pack1'),
                'maintenance_mode': {'enabled': False},
                'min_deposit': getattr(config, 'MIN_DEPOSIT', 10),
                'max_deposit': getattr(config, 'MAX_DEPOSIT', 10000),
                'min_withdrawal': getattr(config, 'MIN_WITHDRAWAL', 50),
                'max_withdrawal': getattr(config, 'MAX_WITHDRAWAL', 10000),
                'min_transfer': getattr(config, 'MIN_TRANSFER', 10),
                'max_transfer': getattr(config, 'MAX_TRANSFER', 5000),
                'cartela_price': getattr(config, 'CARTELA_PRICE', 10),
                'max_cartelas_per_player': getattr(config, 'MAX_CARTELAS', 4),
                'selection_time': getattr(config, 'SELECTION_TIME', 50),
                'draw_interval': getattr(config, 'DRAW_INTERVAL', 3000),
                'next_round_delay': getattr(config, 'NEXT_ROUND_DELAY', 6000),
                'welcome_bonus_amount': getattr(config, 'WELCOME_BONUS_AMOUNT', 30),
                'daily_bonus_amount': getattr(config, 'DAILY_BONUS_AMOUNT', 5),
                'enable_daily_bonus': getattr(config, 'ENABLE_DAILY_BONUS', False),
                'enable_tournaments': getattr(config, 'ENABLE_TOURNAMENT', False),
            }
            
            for key, value in default_settings.items():
                await AdminRepository.set_setting(key, value)
            
            results['settings_initialized'] = True
            logger.info("Default system settings initialized")
    
    except Exception as e:
        results['errors'].append(f"Settings initialization failed: {e}")
    
    return results

# ==================== HEALTH CHECK FUNCTION ====================

async def check_database_health() -> dict:
    """
    Check database connection health and basic table counts
    
    Returns:
        dict: Health status
    """
    health = {
        'database_connected': False,
        'table_counts': {},
        'errors': []
    }
    
    try:
        from bot.db.database import Database
        
        # Test connection
        result = await Database.fetch_one("SELECT 1 as connected")
        health['database_connected'] = result is not None and result.get('connected') == 1
        
        if health['database_connected']:
            # Get table counts
            tables = [
                'users', 'transactions', 'game_rounds', 'cartelas',
                'deposits', 'withdrawals', 'auth_codes', 'admin_log'
            ]
            
            for table in tables:
                try:
                    count_result = await Database.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
                    health['table_counts'][table] = count_result['count'] if count_result else 0
                except Exception as e:
                    health['table_counts'][table] = -1
                    health['errors'].append(f"Table {table}: {e}")
    
    except Exception as e:
        health['errors'].append(f"Database connection failed: {e}")
    
    return health

# ==================== CLEANUP FUNCTION ====================

async def cleanup_old_records(days: int = 90) -> dict:
    """
    Clean up old records from various tables
    
    Args:
        days: int - Age in days for deletion
    
    Returns:
        dict: Cleanup results
    """
    results = {
        'auth_codes': 0,
        'user_sessions': 0,
        'rate_limits': 0,
        'admin_logs': 0,
        'transactions': 0,
        'errors': []
    }
    
    try:
        # Cleanup expired OTP codes
        results['auth_codes'] = await AuthRepository.cleanup_expired_otp()
    except Exception as e:
        results['errors'].append(f"Auth codes cleanup failed: {e}")
    
    try:
        # Cleanup expired sessions
        results['user_sessions'] = await AuthRepository.cleanup_expired_sessions()
    except Exception as e:
        results['errors'].append(f"Sessions cleanup failed: {e}")
    
    try:
        # Cleanup old rate limits
        results['rate_limits'] = await AuthRepository.cleanup_old_rate_limits(days=7)
    except Exception as e:
        results['errors'].append(f"Rate limits cleanup failed: {e}")
    
    try:
        # Cleanup old admin logs
        results['admin_logs'] = await AdminRepository.cleanup_old_admin_logs(days=days)
    except Exception as e:
        results['errors'].append(f"Admin logs cleanup failed: {e}")
    
    try:
        # Cleanup old transactions
        results['transactions'] = await TransactionRepository.delete_old_transactions(days=days)
    except Exception as e:
        results['errors'].append(f"Transactions cleanup failed: {e}")
    
    logger.info(f"Cleanup completed: {results}")
    
    return results

# ==================== EXPORTS ====================

__all__ = [
    # Core Repositories
    'UserRepository',
    'TransactionRepository',
    'AuditRepository',
    
    # Authentication Repository
    'AuthRepository',
    
    # Financial Repositories
    'DepositRepository',
    'WithdrawalRepository',
    'TransferRepository',
    
    # Game Repositories
    'GameRepository',
    'CartelaRepository',
    'active_game_cartelas',
    
    # Bonus Repository
    'BonusRepository',
    
    # Tournament Repository
    'TournamentRepository',
    
    # Admin Repository
    'AdminRepository',
    
    # Utility Functions
    'REPOSITORY_MAP',
    'initialize_repositories',
    'check_database_health',
    'cleanup_old_records',
]

# ==================== LOGGER ====================

import logging
logger = logging.getLogger(__name__)
logger.info("Database repositories package initialized")