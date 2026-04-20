# telegram-bot/run.py
# Estif Bingo 24/7 - ULTIMATE MAIN APPLICATION ENTRY POINT
# Features: Zero downtime, auto-recovery, fast response, no conflicts

import os
import sys
import time
import asyncio
import threading
import signal
from datetime import datetime
from typing import Optional
from functools import wraps

# ==================== FORCE ENVIRONMENT SETTINGS ====================
os.environ["EVENTLET_NO_GREENDNS"] = "yes"
os.environ["PYTHONASYNCIODEBUG"] = "0"

# ==================== FIX EVENT LOOP CONFLICTS ====================
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# ==================== IMPORTS ====================
import eventlet
eventlet.monkey_patch()

from flask import Flask, send_from_directory, jsonify
from flask_socketio import SocketIO
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


# ==================== FLASK APP CREATION ====================
def create_flask_app() -> Flask:
    """Create and configure the Flask application with optimized settings."""
    app = Flask(__name__, static_folder='bot/static')
    app.config['SECRET_KEY'] = config.JWT_SECRET
    app.config['JSON_SORT_KEYS'] = False
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    
    if config.CORS_ORIGINS:
        CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)
    else:
        CORS(app, supports_credentials=True)
    
    register_blueprints(app)
    
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory('bot/static', filename)
    
    @app.route('/advanced_bingo.html')
    def serve_advanced_bingo():
        return send_from_directory('bot/static', 'advanced_bingo.html')
    
    @app.route('/mini_bingo.html')
    def serve_mini_bingo():
        return send_from_directory('bot/static', 'mini_bingo.html')
    
    @app.route('/admin.html')
    def serve_admin():
        return send_from_directory('bot/static', 'admin.html')
    
    @app.route('/')
    def index():
        return jsonify({
            'name': 'Estif Bingo 24/7 API',
            'version': '5.0.0',
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
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': db.health_check() if db._pool else {'status': 'not_initialized'}
        })
    
    return app


# ==================== ULTIMATE APPLICATION CLASS ====================
class Application:
    """
    ULTIMATE APPLICATION CLASS
    Features: Zero downtime, auto-recovery, fast response, no conflicts
    """
    
    def __init__(self):
        self.flask_app = None
        self.socketio = None
        self.bot = None
        self.bot_thread: Optional[threading.Thread] = None
        self.health_monitor_thread: Optional[threading.Thread] = None
        self.is_running = False
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
        # Recovery settings
        self.MAX_DB_RETRIES = 10
        self.MAX_BOT_RETRIES = 999
        self.BASE_RETRY_DELAY = 1
        self.HEALTH_CHECK_INTERVAL = 30
        
        # Metrics
        self.startup_time = None
        self.metrics = {
            'db_attempts': 0,
            'bot_restarts': 0,
            'health_check_failures': 0
        }
    
    async def initialize(self) -> bool:
        """Initialize all application components with aggressive retry."""
        try:
            logger.info("=" * 60)
            logger.info("🚀 ESTIF BINGO 24/7 - ULTIMATE INITIALIZATION")
            logger.info("=" * 60)
            
            start_time = time.time()
            
            # Validate configuration
            errors = config.validate()
            if errors:
                logger.error(f"❌ Configuration errors: {errors}")
                return False
            logger.info("✓ Configuration validated")
            
            # Force fix database URL
            self._fix_database_url()
            
            # Initialize database with aggressive retry
            await self._init_database_aggressive()
            logger.info("✓ Database connected")
            
            # Run migrations
            if not config.SKIP_AUTO_MIGRATIONS:
                await db.run_migrations("bot/db/migrations")
                logger.info("✓ Migrations completed")
            
            # Initialize repositories
            await initialize_repositories("data/cartelas_1000.json")
            logger.info("✓ Repositories initialized")
            
            # Create Flask app
            self.flask_app = create_flask_app()
            
            # Create optimized SocketIO
            self.socketio = SocketIO(
                self.flask_app,
                cors_allowed_origins="*",
                async_mode='eventlet',
                ping_timeout=config.WS_PING_TIMEOUT,
                ping_interval=config.WS_PING_INTERVAL,
                max_http_buffer_size=1_000_000,
                logger=False,
                engineio_logger=False
            )
            logger.info("✓ Flask & SocketIO created")
            
            # Initialize game engine
            bingo_room.init(self.socketio)
            register_socket_events(self.socketio, bingo_room)
            asyncio.create_task(bingo_room.start())
            logger.info("✓ Game engine started")
            
            # Create and initialize bot
            self.bot = EstifBingoBot()
            bot_success = await self.bot.initialize()
            if not bot_success:
                logger.error("Failed to initialize bot")
                return False
            logger.info("✓ Bot initialized")
            
            self.is_running = True
            self.startup_time = time.time()
            
            elapsed_ms = (time.time() - start_time) * 1000
            logger.info("=" * 60)
            logger.info(f"✅ APPLICATION READY! (Startup: {elapsed_ms:.0f}ms)")
            logger.info(f"🤖 Bot: @estif_bingo_bot")
            logger.info(f"🌐 Web: {config.BASE_URL}")
            logger.info(f"👑 Admin: {config.BASE_URL}/admin.html")
            logger.info(f"🎮 Game: {config.BASE_URL}/advanced_bingo.html")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}", exc_info=True)
            return False
    
    def _fix_database_url(self):
        """Force fix DATABASE_URL format."""
        import re
        
        url = config.DATABASE_URL
        if not url:
            return
        
        # Add sslmode=require if missing
        if '?sslmode=require' not in url and 'sslmode=require' not in url:
            url = url + '?sslmode=require'
            logger.info("🔧 Added sslmode=require")
        
        # Convert internal to external hostname if needed
        if 'dpg-' in url and '.oregon-postgres.render.com' not in url:
            match = re.search(r'@(dpg-[^:]+):', url)
            if match:
                internal = match.group(1)
                external = f"{internal}.oregon-postgres.render.com"
                url = url.replace(internal, external)
                logger.info(f"🔧 Converted hostname: {external}")
        
        config.DATABASE_URL = url
        os.environ['DATABASE_URL'] = url
    
    async def _init_database_aggressive(self):
        """Initialize database with aggressive retry logic."""
        for attempt in range(self.MAX_DB_RETRIES):
            try:
                self.metrics['db_attempts'] += 1
                logger.info(f"🔌 DB attempt {attempt + 1}/{self.MAX_DB_RETRIES}...")
                
                await db.initialize()
                
                # Test connection
                result = await db.fetch_val("SELECT 1")
                if result == 1:
                    logger.info(f"✅ Database connected (attempt {attempt + 1})")
                    return
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)[:100]}")
                
                if attempt < self.MAX_DB_RETRIES - 1:
                    delay = min(self.BASE_RETRY_DELAY * (2 ** attempt), 30)
                    import random
                    delay = delay * (0.8 + 0.4 * random.random())
                    logger.info(f"🔄 Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    raise
    
    def run_bot_isolated(self):
        """Run bot in completely isolated thread - NO EVENT LOOP CONFLICTS."""
        def _run():
            # Create brand new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            retries = 0
            while not self._stop_event.is_set():
                try:
                    loop.run_until_complete(self.bot.start_polling())
                    break
                except Exception as e:
                    retries += 1
                    self.metrics['bot_restarts'] += 1
                    logger.error(f"Bot error (restart #{retries}): {e}")
                    
                    if retries < self.MAX_BOT_RETRIES:
                        delay = min(2 ** min(retries, 5), 60)
                        logger.info(f"🔄 Restarting bot in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.critical("❌ Bot failed permanently!")
                        break
            
            loop.close()
        
        self.bot_thread = threading.Thread(target=_run, daemon=True)
        self.bot_thread.start()
        logger.info("🤖 Bot running in isolated thread")
    
    def _health_monitor(self):
        """Background health monitor for bot."""
        while not self._stop_event.is_set():
            time.sleep(self.HEALTH_CHECK_INTERVAL)
            
            try:
                if self.bot_thread and not self.bot_thread.is_alive():
                    self.metrics['health_check_failures'] += 1
                    logger.warning("⚠️ Bot thread died! Restarting...")
                    self.run_bot_isolated()
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
    
    def run_flask_sync(self):
        """Run Flask server with optimal settings."""
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
            logger.error(f"🔥 Flask error: {e}", exc_info=True)
            raise
    
    def start(self):
        """Start all components with health monitoring."""
        if not self.is_running:
            logger.error("Application not initialized!")
            return
        
        logger.info("▶️ Starting application with zero-downtime mode...")
        
        # Start bot
        self.run_bot_isolated()
        
        # Start health monitor
        self.health_monitor_thread = threading.Thread(
            target=self._health_monitor, 
            daemon=True
        )
        self.health_monitor_thread.start()
        logger.info(f"🩺 Health monitor active ({self.HEALTH_CHECK_INTERVAL}s interval)")
        
        # Start Flask (blocks)
        logger.info(f"🌐 Starting Flask on port {config.PORT}...")
        self.run_flask_sync()
    
    async def shutdown(self):
        """Graceful shutdown with timeout."""
        logger.info("🛑 Shutting down...")
        self.is_running = False
        self._stop_event.set()
        
        # Stop game engine
        try:
            await asyncio.wait_for(bingo_room.force_stop(), timeout=5)
            logger.info("✓ Game engine stopped")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Game engine stop timeout")
        
        # Stop bot
        if self.bot:
            try:
                await asyncio.wait_for(self.bot.shutdown(), timeout=5)
                logger.info("✓ Bot stopped")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Bot stop timeout")
        
        # Wait for threads
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=3)
        
        # Close database
        await db.close()
        logger.info("✓ Database closed")
        
        logger.info("✅ Shutdown complete")


# ==================== UTILITY FUNCTIONS ====================
async def fix_column_names():
    """Auto-rename metadata columns if they exist."""
    try:
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
            print("✅ Columns already correct")
    except Exception as e:
        print(f"⚠️ Note: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


# ==================== MAIN ENTRY POINT ====================
async def main():
    """Main async entry point."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    app = Application()
    
    success = await app.initialize()
    if not success:
        logger.error("Failed to initialize application. Exiting...")
        sys.exit(1)
    
    await fix_column_names()
    app.start()


def run():
    """Synchronous entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    run()