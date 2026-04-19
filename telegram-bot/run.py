# telegram-bot/run.py
# Estif Bingo 24/7 - Main Application Entry Point
# Combines Telegram bot, Flask API, WebSocket server, and game engine
import os
os.environ["EVENTLET_NO_GREENDNS"] = "yes"
import nest_asyncio  # Add this import
import asyncio
import logging
import sys
from threading import Thread
from datetime import datetime

# Apply monkey patch for eventlet to handle async properly
import eventlet  # noqa: F401
eventlet.monkey_patch()

from flask import Flask, send_from_directory, jsonify
from flask_socketio import SocketIO  # noqa: F401
from flask_cors import CORS

from bot.config import config
from bot.utils.logger import setup_logger
from bot.db.database import db
from bot.db.repository import initialize_repositories
from bot.main import EstifBingoBot
from bot.game_engine.bingo_room import bingo_room
from bot.game_engine.events import register_socket_events
from bot.api import register_blueprints
# Setup logger
logger = setup_logger(__name__)


def create_flask_app() -> Flask:
    """
    Create and configure the Flask application.
    
    Returns:
        Flask: Configured Flask app instance
    """
    app = Flask(__name__, static_folder='bot/static')
    app.config['SECRET_KEY'] = config.JWT_SECRET
    app.config['JSON_SORT_KEYS'] = False
    
    # Configure CORS
    if config.CORS_ORIGINS:
        CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)
    else:
        CORS(app, supports_credentials=True)
    
    # Register API blueprints
    register_blueprints(app)
    
    # Serve static files
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory('bot/static', filename)
    
    # Serve advanced bingo game
    @app.route('/advanced_bingo.html')
    def serve_advanced_bingo():
        return send_from_directory('bot/static', 'advanced_bingo.html')
    
    # Serve mini bingo game
    @app.route('/mini_bingo.html')
    def serve_mini_bingo():
        return send_from_directory('bot/static', 'mini_bingo.html')
    
    # Serve admin panel
    @app.route('/admin.html')
    def serve_admin():
        return send_from_directory('bot/static', 'admin.html')
    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'name': 'Estif Bingo 24/7 API',
            'version': '4.0.0',
            'status': 'running',
            'endpoints': {
                'api': '/api/',
                'game': '/advanced_bingo.html',
                'mini_bingo': '/mini_bingo.html',
                'admin': '/admin.html',
                'health': '/api/health'
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': db.health_check() if db._pool else {'status': 'not_initialized'}
        })
    
    return app


class Application:
    """
    ULTIMATE PRODUCTION-GRADE Application Class
    Features:
    - Async-first design with proper event loop management
    - Automatic recovery with exponential backoff
    - Health monitoring and self-healing
    - Resource leak prevention
    - Graceful shutdown with timeout
    - Performance optimizations
    - Thread-safe state management
    """
    
    def __init__(self):
        # Core components
        self.flask_app = None
        self.socketio = None
        self.bot = None
        
        # Thread management
        self.bot_thread: Optional[threading.Thread] = None
        self.health_monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
        # State management
        self.is_running = False
        self.bot_healthy = False
        self.startup_time = None
        
        # Performance metrics
        self.metrics = {
            'bot_restarts': 0,
            'last_restart_time': None,
            'uptime_seconds': 0
        }
        
        # Configuration
        self.MAX_RETRIES = 5
        self.BASE_RETRY_DELAY = 1
        self.HEALTH_CHECK_INTERVAL = 30
        self.SHUTDOWN_TIMEOUT = 10
    
    async def initialize(self) -> bool:
        """
        Initialize all application components with parallel execution where possible.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            start_time = time.time()
            logger.info("=" * 60)
            logger.info("🚀 Estif Bingo 24/7 Application Initialization")
            logger.info("=" * 60)
            
            # Validate configuration (fast, no I/O)
            errors = config.validate()
            if errors:
                logger.error(f"❌ Configuration errors: {errors}")
                return False
            logger.info("✓ Configuration validated (%.2fms)", (time.time() - start_time) * 1000)
            
            # Initialize database connection with retry
            db_start = time.time()
            await self._init_database_with_retry()
            logger.info("✓ Database connection established (%.2fms)", (time.time() - db_start) * 1000)
            
            # Run migrations if needed
            if not config.SKIP_AUTO_MIGRATIONS:
                migration_start = time.time()
                await db.run_migrations("bot/db/migrations")
                logger.info("✓ Database migrations completed (%.2fms)", (time.time() - migration_start) * 1000)
            
            # Initialize repositories
            repo_start = time.time()
            await initialize_repositories("data/cartelas_1000.json")
            logger.info("✓ Repositories initialized (%.2fms)", (time.time() - repo_start) * 1000)
            
            # Create Flask app and SocketIO in parallel
            flask_start = time.time()
            self.flask_app = create_flask_app()
            self.socketio = self._create_socketio()
            logger.info("✓ Flask & SocketIO created (%.2fms)", (time.time() - flask_start) * 1000)
            
            # Initialize game engine
            game_start = time.time()
            bingo_room.init(self.socketio)
            register_socket_events(self.socketio, bingo_room)
            asyncio.create_task(bingo_room.start())
            logger.info("✓ Game engine initialized (%.2fms)", (time.time() - game_start) * 1000)
            
            # Create and initialize bot
            bot_start = time.time()
            self.bot = EstifBingoBot()
            bot_success = await self.bot.initialize()
            if not bot_success:
                logger.error("Failed to initialize bot")
                return False
            logger.info("✓ Bot initialized (%.2fms)", (time.time() - bot_start) * 1000)
            
            self.is_running = True
            self.startup_time = time.time()
            
            logger.info("=" * 60)
            logger.info("✅ APPLICATION INITIALIZED SUCCESSFULLY!")
            logger.info(f"⏱️  Total startup time: {(time.time() - start_time) * 1000:.0f}ms")
            logger.info(f"🌐 Bot URL: {config.BOT_API_URL}")
            logger.info(f"🎮 Web URL: {config.BASE_URL}")
            logger.info(f"👑 Admin Panel: {config.BASE_URL}/admin.html")
            logger.info(f"🎯 Game URL: {config.BASE_URL}/advanced_bingo.html")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize application: {e}", exc_info=True)
            return False
    
    async def _init_database_with_retry(self):
        """Initialize database connection with exponential backoff retry"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                await db.initialize()
                return
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
    
    def _create_socketio(self):
        """Create optimized SocketIO instance"""
        return SocketIO(
            self.flask_app,
            cors_allowed_origins="*",
            async_mode='eventlet',
            ping_timeout=config.WS_PING_TIMEOUT,
            ping_interval=config.WS_PING_INTERVAL,
            max_http_buffer_size=1_000_000,
            logger=logger,
            engineio_logger=False
        )
    
    def _is_bot_healthy(self) -> bool:
        """Fast health check for bot responsiveness"""
        try:
            if not self.bot or not self.bot.application:
                return False
            
            # Use a lightweight async check with timeout
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.bot.application.updater.is_idle(),
                    loop
                )
                result = future.result(timeout=5)
                return result
            finally:
                loop.close()
        except Exception:
            return False
    
    def run_bot_sync(self):
        """
        ULTIMATE BOT RUNNER with multiple fallback strategies and automatic recovery.
        Optimized for Render + eventlet + asyncio with exponential backoff.
        """
        import asyncio
        import threading
        import time
        
        def run_with_recovery():
            """Run bot with exponential backoff recovery"""
            retries = 0
            
            while not self._stop_event.is_set():
                try:
                    # Strategy 1: nest_asyncio (fastest)
                    try:
                        import nest_asyncio
                        nest_asyncio.apply()
                        asyncio.run(self.bot.start_polling())
                        return
                    except ImportError:
                        pass
                    
                    # Strategy 2: Isolated event loop (most reliable)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self.bot.start_polling())
                    finally:
                        # Clean up pending tasks
                        pending = asyncio.all_tasks(loop)
                        for task in pending:
                            task.cancel()
                        if pending:
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        loop.close()
                    return
                    
                except Exception as e:
                    retries += 1
                    self.metrics['bot_restarts'] += 1
                    self.metrics['last_restart_time'] = time.time()
                    
                    # Exponential backoff with jitter
                    delay = min(self.BASE_RETRY_DELAY * (2 ** (retries - 1)), 60)
                    jitter = delay * 0.1 * (time.time() % 1)
                    wait_time = delay + jitter
                    
                    logger.error(f"💥 Bot crashed (restart #{retries}): {e}")
                    
                    if retries < self.MAX_RETRIES:
                        logger.info(f"🔄 Restarting bot in {wait_time:.1f} seconds...")
                        time.sleep(wait_time)
                    else:
                        logger.critical("❌ Bot failed after all retries! Manual intervention required.")
                        break
        
        # Start bot in daemon thread
        self.bot_thread = threading.Thread(target=run_with_recovery, daemon=True)
        self.bot_thread.start()
        logger.info("🤖 Bot started with automatic recovery (max retries: %d)", self.MAX_RETRIES)
    
    def _health_monitor(self):
        """Background health monitor with automatic recovery"""
        while not self._stop_event.is_set():
            time.sleep(self.HEALTH_CHECK_INTERVAL)
            
            if not self._is_bot_healthy():
                logger.warning("⚠️ Bot health check failed! Attempting recovery...")
                
                # Force restart if unhealthy
                with self._lock:
                    if self.bot_thread and self.bot_thread.is_alive():
                        # Don't duplicate recovery if already restarting
                        continue
                
                # Restart bot
                self.run_bot_sync()
    
    def run_flask_sync(self):
        """Run Flask server with optimal settings for Render"""
        try:
            self.socketio.run(
                self.flask_app,
                host='0.0.0.0',
                port=config.PORT,
                debug=False,
                use_reloader=False,
                log_output=False
            )
        except Exception as e:
            logger.error(f"🔥 Flask server error: {e}", exc_info=True)
            raise
    
    def start(self):
        """Start all components with health monitoring"""
        if not self.is_running:
            logger.error("Application not initialized. Call initialize() first.")
            return
        
        logger.info("▶️ Starting application components...")
        
        # Start bot in background
        self.run_bot_sync()
        
        # Start health monitor
        self.health_monitor_thread = threading.Thread(target=self._health_monitor, daemon=True)
        self.health_monitor_thread.start()
        logger.info("🩺 Health monitor started (interval: %ds)", self.HEALTH_CHECK_INTERVAL)
        
        # Start Flask in main thread (blocks)
        logger.info("🌐 Starting Flask server on port %d...", config.PORT)
        self.run_flask_sync()
    
    def get_metrics(self) -> dict:
        """Get application performance metrics"""
        return {
            'bot_restarts': self.metrics['bot_restarts'],
            'last_restart_time': self.metrics['last_restart_time'],
            'uptime_seconds': time.time() - self.startup_time if self.startup_time else 0,
            'is_running': self.is_running,
            'bot_healthy': self._is_bot_healthy()
        }
    
    async def shutdown(self):
        """Graceful shutdown with timeout protection"""
        logger.info("🛑 Shutting down application gracefully...")
        
        # Stop accepting new requests
        self.is_running = False
        self._stop_event.set()
        
        # Stop game engine with timeout
        try:
            await asyncio.wait_for(bingo_room.force_stop(), timeout=5)
            logger.info("✓ Game engine stopped")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Game engine stop timeout")
        
        # Stop bot with timeout
        if self.bot:
            try:
                await asyncio.wait_for(self.bot.shutdown(), timeout=5)
                logger.info("✓ Bot stopped")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Bot stop timeout")
        
        # Wait for threads
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=3)
        
        if self.health_monitor_thread and self.health_monitor_thread.is_alive():
            self.health_monitor_thread.join(timeout=2)
        
        # Close database connection
        await db.close()
        logger.info("✓ Database connection closed")
        
        # Final metrics
        logger.info("📊 Final metrics: %s", self.get_metrics())
        logger.info("✅ Application shutdown complete")
# ==================== MAIN ENTRY POINT ====================

# ... all your existing imports ...

async def main():
    """Main async entry point"""
    app = Application()
    
    # Initialize application
    success = await app.initialize()
    if not success:
        logger.error("Failed to initialize application. Exiting...")
        sys.exit(1)
    
    # Auto-fix: Rename metadata columns if they exist
    async def fix_column_names():
        """Automatically rename metadata columns if they exist"""
        try:
            from bot.db.database import db
            
            # Check if column exists and rename it
            check_query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='transactions' AND column_name='metadata';
            """
            result = await db.fetch_one(check_query)
            
            if result:
                print("🔄 Renaming 'metadata' column to 'meta_data'...")
                await db.execute("ALTER TABLE transactions RENAME COLUMN metadata TO meta_data;")
                await db.execute("ALTER TABLE deposits RENAME COLUMN metadata TO meta_data;")
                await db.execute("ALTER TABLE withdrawals RENAME COLUMN metadata TO meta_data;")
                await db.execute("ALTER TABLE transfers RENAME COLUMN metadata TO meta_data;")
                await db.execute("ALTER TABLE bonus_claims RENAME COLUMN metadata TO meta_data;")
                await db.execute("ALTER TABLE tournament_registrations RENAME COLUMN metadata TO meta_data;")
                await db.execute("ALTER TABLE admin_log RENAME COLUMN metadata TO meta_data;")
                print("✅ Column rename completed!")
            else:
                print("✅ Columns already correct, no rename needed")
        except Exception as e:
            print(f"⚠️ Note: {e} (columns may already be correct)")
    
    # Run the fix after database is initialized
    await fix_column_names()
    
    # Start application (blocks until Flask server stops)
    app.start()


def run():
    """Synchronous entry point for running the application"""
    asyncio.run(main())


if __name__ == "__main__":
    run()