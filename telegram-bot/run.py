# telegram-bot/run.py
# Estif Bingo 24/7 - Main Application Entry Point
# Combines Telegram bot, Flask API, WebSocket server, and game engine

import os
os.environ["EVENTLET_NO_GREENDNS"] = "yes"

import nest_asyncio
nest_asyncio.apply()

import asyncio
import logging
import sys
import time
import threading
from threading import Thread
from datetime import datetime
from typing import Optional

# Apply monkey patch for eventlet to handle async properly
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


def create_flask_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder='bot/static')
    app.config['SECRET_KEY'] = config.JWT_SECRET
    app.config['JSON_SORT_KEYS'] = False
    
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
    ⚡ ULTIMATE APPLICATION CLASS - ZERO DOWNTIME ⚡
    Hybrid, Fast, Efficient, Always Active
    """
    
    def __init__(self):
        self.flask_app = None
        self.socketio = None
        self.bot = None
        self.bot_thread: Optional[threading.Thread] = None
        self.health_monitor_thread: Optional[threading.Thread] = None
        self.flask_thread = None
        self.is_running = False
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
        # Recovery settings
        self.MAX_RETRIES = 999
        self.BASE_RETRY_DELAY = 1
        self.HEALTH_CHECK_INTERVAL = 30
        
        # Metrics
        self.metrics = {
            'bot_restarts': 0,
            'last_restart_time': None,
            'startup_time': None
        }
    
    async def initialize(self) -> bool:
        """Initialize all application components."""
        try:
            logger.info("=" * 50)
            logger.info("Initializing Estif Bingo 24/7 Application")
            logger.info("=" * 50)
            
            errors = config.validate()
            if errors:
                logger.error(f"Configuration errors: {errors}")
                return False
            logger.info("✓ Configuration validated")
            
            await db.initialize()
            logger.info("✓ Database connection established")
            
            if not config.SKIP_AUTO_MIGRATIONS:
                await db.run_migrations("bot/db/migrations")
                logger.info("✓ Database migrations completed")
            
            await initialize_repositories("data/cartelas_1000.json")
            logger.info("✓ Repositories initialized")
            
            self.flask_app = create_flask_app()
            logger.info("✓ Flask app created")
            
            self.socketio = SocketIO(
                self.flask_app,
                cors_allowed_origins="*",
                async_mode='eventlet',
                ping_timeout=config.WS_PING_TIMEOUT,
                ping_interval=config.WS_PING_INTERVAL
            )
            logger.info("✓ SocketIO instance created")
            
            bingo_room.init(self.socketio)
            register_socket_events(self.socketio, bingo_room)
            asyncio.create_task(bingo_room.start())
            logger.info("✓ Game engine started")
            
            self.bot = EstifBingoBot()
            bot_success = await self.bot.initialize()
            if not bot_success:
                logger.error("Failed to initialize bot")
                return False
            logger.info("✓ Bot initialized")
            
            self.is_running = True
            self.metrics['startup_time'] = time.time()
            
            logger.info("=" * 50)
            logger.info("Application initialized successfully!")
            logger.info(f"Bot URL: {config.BOT_API_URL}")
            logger.info(f"Web URL: {config.BASE_URL}")
            logger.info(f"Admin Panel: {config.BASE_URL}/admin.html")
            logger.info(f"Game URL: {config.BASE_URL}/advanced_bingo.html")
            logger.info("=" * 50)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}", exc_info=True)
            return False
    
def run_bot_sync(self):
    """
    Run bot in a way that works with eventlet's running event loop.
    Uses thread isolation to avoid loop conflicts.
    """
    import threading
    import asyncio
    
    def run_in_thread():
        """Run bot in completely isolated thread with new event loop"""
        # Create a brand new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.bot.start_polling())
        except Exception as e:
            logger.error(f"Bot thread error: {e}", exc_info=True)
        finally:
            loop.close()
    
    # Start bot in separate daemon thread
    bot_thread = threading.Thread(target=run_in_thread, daemon=True)
    bot_thread.start()
    logger.info("🤖 Bot started in isolated thread")
    
    def _health_monitor(self):
        """Background health monitor"""
        while not self._stop_event.is_set():
            time.sleep(self.HEALTH_CHECK_INTERVAL)
            
            if self.bot_thread and not self.bot_thread.is_alive():
                logger.warning("⚠️ Bot thread died! Restarting...")
                self.run_bot_sync()
    
    def run_flask_sync(self):
        """Run the Flask server"""
        try:
            self.socketio.run(
                self.flask_app,
                host='0.0.0.0',
                port=config.PORT,
                debug=False,
                use_reloader=False
            )
        except Exception as e:
            logger.error(f"Flask thread error: {e}", exc_info=True)
    
    def start(self):
        """Start both the bot and Flask server with health monitoring"""
        if not self.is_running:
            logger.error("Application not initialized. Call initialize() first.")
            return
        
        # Start bot with recovery
        self.run_bot_sync()
        
        # Start health monitor
        self.health_monitor_thread = threading.Thread(target=self._health_monitor, daemon=True)
        self.health_monitor_thread.start()
        logger.info(f"🩺 Health monitor started (interval: {self.HEALTH_CHECK_INTERVAL}s)")
        
        # Start Flask
        logger.info(f"Starting Flask server on port {config.PORT}...")
        self.run_flask_sync()
    
    async def shutdown(self):
        """Shutdown all components gracefully"""
        logger.info("Shutting down application...")
        self.is_running = False
        self._stop_event.set()
        
        await bingo_room.force_stop()
        logger.info("✓ Game engine stopped")
        
        if self.bot:
            await self.bot.shutdown()
            logger.info("✓ Bot stopped")
        
        await db.close()
        logger.info("✓ Database connection closed")
        
        logger.info("Application shutdown complete")


# ==================== MAIN ENTRY POINT ====================

async def fix_column_names():
    """Automatically rename metadata columns if they exist"""
    try:
        from bot.db.database import db
        
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


async def main():
    """Main async entry point"""
    app = Application()
    
    success = await app.initialize()
    if not success:
        logger.error("Failed to initialize application. Exiting...")
        sys.exit(1)
    
    await fix_column_names()
    
    app.start()


def run():
    """Synchronous entry point for running the application"""
    asyncio.run(main())


if __name__ == "__main__":
    run()