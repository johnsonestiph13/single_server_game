# telegram-bot/bot/db/__init__.py
# Estif Bingo 24/7 - Database Package
# Initializes database connection and exports all database modules

import logging
from typing import Optional, Dict, Any

from bot.db.database import (
    Database,
    db,
    get_db,
    close_db,
    execute,
    fetch_one,
    fetch_all,
    fetch_val,
)

from bot.db.models import Base

# Import all models for SQLAlchemy metadata
from bot.db.models import (
    User,
    AuthCode,
    UserSession,
    Transaction,
    Deposit,
    Withdrawal,
    Transfer,
    Cartela,
    GameRound,
    RoundSelection,
    BonusClaim,
    Tournament,
    TournamentRegistration,
    TournamentPrize,
    AdminLog,
    SystemSetting,
    BroadcastLog,
    Announcement,
    AnnouncementDismissal,
    RateLimit,
    ApiKey,
    SchemaMigration,
)

# Import all repositories
from bot.db.repository import (
    UserRepository,
    TransactionRepository,
    AuditRepository,
    AuthRepository,
    DepositRepository,
    WithdrawalRepository,
    TransferRepository,
    GameRepository,
    CartelaRepository,
    active_game_cartelas,
    BonusRepository,
    TournamentRepository,
    AdminRepository,
    REPOSITORY_MAP,
    initialize_repositories,
    check_database_health,
    cleanup_old_records,
)

logger = logging.getLogger(__name__)


# ==================== DATABASE INITIALIZATION FUNCTION ====================

async def init_db(
    run_migrations: bool = True,
    load_cartelas: bool = True,
    cartelas_path: str = "data/cartelas_1000.json"
) -> Dict[str, Any]:
    """
    Initialize the database connection and setup all tables
    
    Args:
        run_migrations: bool - Whether to run pending migrations
        load_cartelas: bool - Whether to load cartelas from JSON
        cartelas_path: str - Path to cartelas JSON file
    
    Returns:
        dict: Initialization results
    """
    results = {
        'database_connected': False,
        'migrations_run': False,
        'cartelas_loaded': 0,
        'repositories_initialized': False,
        'errors': []
    }
    
    try:
        # Initialize database connection
        await db.initialize()
        results['database_connected'] = True
        logger.info("Database connection initialized")
        
        # Test connection
        test_result = await fetch_val("SELECT 1")
        if test_result == 1:
            logger.info("Database connection test successful")
        
        # Run migrations
        if run_migrations:
            try:
                from bot.db.database import get_db
                db_instance = await get_db()
                applied = await db_instance.run_migrations("bot/db/migrations")
                results['migrations_run'] = True
                if applied:
                    logger.info(f"Applied {len(applied)} migrations: {applied}")
                else:
                    logger.info("No pending migrations")
            except Exception as e:
                results['errors'].append(f"Migration failed: {e}")
                logger.error(f"Migration failed: {e}")
        
        # Initialize repositories (load cartelas, settings)
        init_result = await initialize_repositories(cartelas_path)
        results['cartelas_loaded'] = init_result.get('cartelas_loaded', 0)
        results['repositories_initialized'] = init_result.get('settings_initialized', False)
        if init_result.get('errors'):
            results['errors'].extend(init_result['errors'])
        
        logger.info(f"Database initialization complete: {results}")
        
    except Exception as e:
        results['errors'].append(f"Database initialization failed: {e}")
        logger.error(f"Database initialization failed: {e}")
    
    return results


# ==================== DATABASE HEALTH CHECK ====================

async def health_check() -> Dict[str, Any]:
    """
    Check database health
    
    Returns:
        dict: Health status
    """
    try:
        # Check connection pool health
        pool_health = await db.health_check()
        
        # Check table counts
        from bot.db.repository import check_database_health
        table_counts = await check_database_health()
        
        return {
            'status': 'healthy' if pool_health.get('status') == 'healthy' else 'unhealthy',
            'pool': pool_health,
            'tables': table_counts.get('table_counts', {}),
            'errors': table_counts.get('errors', [])
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


# ==================== DATABASE CLEANUP ====================

async def cleanup_db(days: int = 90) -> Dict[str, Any]:
    """
    Clean up old database records
    
    Args:
        days: int - Age in days for deletion
    
    Returns:
        dict: Cleanup results
    """
    try:
        results = await cleanup_old_records(days)
        logger.info(f"Database cleanup completed: {results}")
        return results
    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")
        return {'error': str(e)}


# ==================== DATABASE SHUTDOWN ====================

async def shutdown_db() -> None:
    """
    Shutdown database connection properly
    """
    try:
        await close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


# ==================== CONVENIENCE EXPORTS ====================

# Database connection functions
__all__ = [
    # Database connection
    'Database',
    'db',
    'get_db',
    'close_db',
    'init_db',
    'shutdown_db',
    'health_check',
    'cleanup_db',
    
    # Query functions
    'execute',
    'fetch_one',
    'fetch_all',
    'fetch_val',
    
    # SQLAlchemy Base
    'Base',
    
    # Models
    'User',
    'AuthCode',
    'UserSession',
    'Transaction',
    'Deposit',
    'Withdrawal',
    'Transfer',
    'Cartela',
    'GameRound',
    'RoundSelection',
    'BonusClaim',
    'Tournament',
    'TournamentRegistration',
    'TournamentPrize',
    'AdminLog',
    'SystemSetting',
    'BroadcastLog',
    'Announcement',
    'AnnouncementDismissal',
    'RateLimit',
    'ApiKey',
    'SchemaMigration',
    
    # Repositories
    'UserRepository',
    'TransactionRepository',
    'AuditRepository',
    'AuthRepository',
    'DepositRepository',
    'WithdrawalRepository',
    'TransferRepository',
    'GameRepository',
    'CartelaRepository',
    'active_game_cartelas',
    'BonusRepository',
    'TournamentRepository',
    'AdminRepository',
    'REPOSITORY_MAP',
    'initialize_repositories',
    'check_database_health',
    'cleanup_old_records',
]


# ==================== LOGGER ====================

logger.info("Database package initialized")