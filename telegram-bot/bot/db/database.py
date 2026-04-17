# telegram-bot/bot/db/database.py
# Estif Bingo 24/7 - Database Connection Manager
# Handles PostgreSQL connection pooling and database operations

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime
import asyncpg
from asyncpg import Pool, Connection, Record

from bot.config import config

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager with connection pooling"""
    
    _instance = None
    _pool: Optional[Pool] = None
    
    def __new__(cls):
        """Singleton pattern to ensure single database connection pool"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize database configuration"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.database_url = config.DATABASE_URL
            self.min_pool_size = getattr(config, 'DB_MIN_SIZE', 2)
            self.max_pool_size = getattr(config, 'DB_MAX_SIZE', 10)
            self.command_timeout = getattr(config, 'DB_COMMAND_TIMEOUT', 60)
            self._pool = None
            logger.info("Database instance created")
    
    async def initialize(self) -> None:
        """Initialize connection pool"""
        if self._pool is None:
            try:
                self._pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=self.min_pool_size,
                    max_size=self.max_pool_size,
                    command_timeout=self.command_timeout,
                    max_queries=50000,
                    max_inactive_connection_lifetime=300,
                    setup=self._setup_connection
                )
                logger.info(f"Database connection pool created (min={self.min_pool_size}, max={self.max_pool_size})")
            except Exception as e:
                logger.error(f"Failed to create database connection pool: {e}")
                raise
    
    async def _setup_connection(self, connection: Connection) -> None:
        """Setup connection settings"""
        # Set timezone
        await connection.execute("SET TIMEZONE = 'UTC'")
        # Set application name
        await connection.execute("SET application_name = 'estif_bingo_bot'")
        logger.debug("Connection setup completed")
    
    async def close(self) -> None:
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")
    
    @property
    def pool(self) -> Pool:
        """Get connection pool"""
        if self._pool is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._pool
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool (context manager)"""
        async with self.pool.acquire() as connection:
            yield connection
    
    # ==================== QUERY EXECUTION METHODS ====================
    
    async def execute(self, query: str, *args) -> str:
        """
        Execute a query that doesn't return rows (INSERT, UPDATE, DELETE)
        
        Args:
            query: SQL query string
            *args: Query parameters
        
        Returns:
            str: Command status
        """
        try:
            async with self.get_connection() as conn:
                result = await conn.execute(query, *args)
                logger.debug(f"Execute successful: {query[:100]}...")
                return result
        except Exception as e:
            logger.error(f"Execute error: {e}\nQuery: {query[:200]}")
            raise
    
    async def fetch_one(self, query: str, *args) -> Optional[Record]:
        """
        Fetch a single row from the database
        
        Args:
            query: SQL query string
            *args: Query parameters
        
        Returns:
            Record: Single row or None if not found
        """
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchrow(query, *args)
                logger.debug(f"Fetch one successful: {query[:100]}...")
                return result
        except Exception as e:
            logger.error(f"Fetch one error: {e}\nQuery: {query[:200]}")
            raise
    
    async def fetch_all(self, query: str, *args) -> List[Record]:
        """
        Fetch all rows from the database
        
        Args:
            query: SQL query string
            *args: Query parameters
        
        Returns:
            list: List of Record objects
        """
        try:
            async with self.get_connection() as conn:
                results = await conn.fetch(query, *args)
                logger.debug(f"Fetch all successful: {len(results)} rows")
                return results
        except Exception as e:
            logger.error(f"Fetch all error: {e}\nQuery: {query[:200]}")
            raise
    
    async def fetch_val(self, query: str, *args) -> Any:
        """
        Fetch a single value from the database
        
        Args:
            query: SQL query string
            *args: Query parameters
        
        Returns:
            Any: Single value or None
        """
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchval(query, *args)
                logger.debug(f"Fetch val successful: {result}")
                return result
        except Exception as e:
            logger.error(f"Fetch val error: {e}\nQuery: {query[:200]}")
            raise
    
    # ==================== TRANSACTION METHODS ====================
    
    @asynccontextmanager
    async def transaction(self):
        """
        Start a database transaction (context manager)
        
        Usage:
            async with db.transaction():
                await db.execute("INSERT INTO ...")
                await db.execute("UPDATE ...")
        """
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield
    
    async def begin_transaction(self) -> Connection:
        """
        Begin a manual transaction (returns connection for manual control)
        
        Returns:
            Connection: Database connection with active transaction
        """
        conn = await self.pool.acquire()
        await conn.execute("BEGIN")
        return conn
    
    async def commit_transaction(self, conn: Connection) -> None:
        """Commit a manual transaction"""
        await conn.execute("COMMIT")
        await self.pool.release(conn)
    
    async def rollback_transaction(self, conn: Connection) -> None:
        """Rollback a manual transaction"""
        await conn.execute("ROLLBACK")
        await self.pool.release(conn)
    
    # ==================== BATCH OPERATIONS ====================
    
    async def execute_many(self, query: str, args_list: List[tuple]) -> List[str]:
        """
        Execute the same query with multiple parameter sets
        
        Args:
            query: SQL query string
            args_list: List of parameter tuples
        
        Returns:
            list: List of command statuses
        """
        try:
            async with self.get_connection() as conn:
                results = await conn.executemany(query, args_list)
                logger.debug(f"Execute many successful: {len(args_list)} operations")
                return results
        except Exception as e:
            logger.error(f"Execute many error: {e}")
            raise
    
    async def copy_records(self, table_name: str, records: List[Dict], columns: List[str]) -> int:
        """
        Bulk insert records using COPY command (much faster for large datasets)
        
        Args:
            table_name: Target table name
            records: List of record dictionaries
            columns: List of column names to insert
        
        Returns:
            int: Number of records inserted
        """
        if not records:
            return 0
        
        try:
            async with self.get_connection() as conn:
                # Create COPY statement
                copy_stmt = await conn.copy_records_to_table(
                    table_name,
                    columns=columns,
                    records=records
                )
                logger.info(f"Copied {len(records)} records to {table_name}")
                return len(records)
        except Exception as e:
            logger.error(f"Copy records error: {e}")
            raise
    
    # ==================== HEALTH CHECK ====================
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check database health
        
        Returns:
            dict: Health status information
        """
        try:
            start_time = datetime.utcnow()
            result = await self.fetch_one("SELECT 1 as connected, NOW() as server_time")
            end_time = datetime.utcnow()
            
            if result and result.get('connected') == 1:
                return {
                    'status': 'healthy',
                    'response_time_ms': (end_time - start_time).total_seconds() * 1000,
                    'server_time': result.get('server_time'),
                    'pool_size': self._pool.get_size() if self._pool else 0,
                    'pool_free': self._pool.get_free_size() if self._pool else 0
                }
            else:
                return {'status': 'unhealthy', 'error': 'Database returned unexpected result'}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {'status': 'unhealthy', 'error': str(e)}
    
    # ==================== UTILITY METHODS ====================
    
    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database
        
        Args:
            table_name: Name of the table
        
        Returns:
            bool: True if table exists
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = $1
            )
        """
        result = await self.fetch_val(query, table_name)
        return result if result else False
    
    async def get_table_count(self, table_name: str) -> int:
        """
        Get row count for a table
        
        Args:
            table_name: Name of the table
        
        Returns:
            int: Number of rows
        """
        try:
            result = await self.fetch_val(f"SELECT COUNT(*) FROM {table_name}")
            return result if result else 0
        except Exception as e:
            logger.error(f"Failed to get count for table {table_name}: {e}")
            return -1
    
    async def vacuum_analyze(self, table_name: Optional[str] = None) -> None:
        """
        Run VACUUM ANALYZE to clean up and update statistics
        
        Args:
            table_name: Optional specific table name
        """
        try:
            if table_name:
                await self.execute(f"VACUUM ANALYZE {table_name}")
                logger.info(f"VACUUM ANALYZE completed on {table_name}")
            else:
                await self.execute("VACUUM ANALYZE")
                logger.info("VACUUM ANALYZE completed on all tables")
        except Exception as e:
            logger.warning(f"VACUUM ANALYZE failed: {e}")
    
    # ==================== MIGRATION METHODS ====================
    
    async def run_migrations(self, migrations_path: str = "bot/db/migrations") -> List[str]:
        """
        Run pending database migrations
        
        Args:
            migrations_path: Path to migration SQL files
        
        Returns:
            list: List of applied migrations
        """
        applied = []
        
        try:
            # Create migrations table if not exists
            await self.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Get already applied migrations
            applied_migrations = await self.fetch_all(
                "SELECT migration_name FROM schema_migrations"
            )
            applied_set = {row['migration_name'] for row in applied_migrations}
            
            # Get migration files
            import os
            import re
            
            if not os.path.exists(migrations_path):
                logger.warning(f"Migrations path not found: {migrations_path}")
                return applied
            
            migration_files = sorted([f for f in os.listdir(migrations_path) if f.endswith('.sql')])
            
            for migration_file in migration_files:
                if migration_file not in applied_set:
                    # Read and execute migration
                    with open(os.path.join(migrations_path, migration_file), 'r') as f:
                        sql = f.read()
                    
                    # Split SQL statements (basic splitting by semicolon)
                    statements = re.split(r';\s*\n', sql)
                    
                    async with self.transaction():
                        for stmt in statements:
                            stmt = stmt.strip()
                            if stmt:
                                await self.execute(stmt)
                        
                        # Record migration
                        await self.execute(
                            "INSERT INTO schema_migrations (migration_name) VALUES ($1)",
                            migration_file
                        )
                    
                    applied.append(migration_file)
                    logger.info(f"Applied migration: {migration_file}")
            
            return applied
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise


# ==================== SINGLETON INSTANCE ====================

# Create global database instance
db = Database()


# ==================== CONVENIENCE FUNCTIONS ====================

async def get_db() -> Database:
    """
    Get the global database instance (ensures initialization)
    
    Returns:
        Database: Global database instance
    """
    if db._pool is None:
        await db.initialize()
    return db


async def close_db() -> None:
    """Close the global database connection"""
    await db.close()


async def execute(query: str, *args) -> str:
    """Convenience function for execute"""
    return await db.execute(query, *args)


async def fetch_one(query: str, *args) -> Optional[Record]:
    """Convenience function for fetch_one"""
    return await db.fetch_one(query, *args)


async def fetch_all(query: str, *args) -> List[Record]:
    """Convenience function for fetch_all"""
    return await db.fetch_all(query, *args)


async def fetch_val(query: str, *args) -> Any:
    """Convenience function for fetch_val"""
    return await db.fetch_val(query, *args)


# ==================== EXPORTS ====================

__all__ = [
    'Database',
    'db',
    'get_db',
    'close_db',
    'execute',
    'fetch_one',
    'fetch_all',
    'fetch_val',
]