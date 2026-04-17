# telegram-bot/run.py
# Estif Bingo 24/7 - Main Application Entry Point
# Combines Telegram bot, Flask API, WebSocket server, and game engine

import asyncio
import logging
import sys
import os
from threading import Thread
from datetime import datetime

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
    Main application class that manages both the Telegram bot and Flask server.
    """
    
    def __init__(self):
        self.flask_app = None
        self.socketio = None
        self.bot = None
        self.bot_thread = None
        self.flask_thread = None
        self.is_running = False
    
    async def initialize(self) -> bool:
        """
        Initialize all application components.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info("=" * 50)
            logger.info("Initializing Estif Bingo 24/7 Application")
            logger.info("=" * 50)
            
            # Validate configuration
            errors = config.validate()
            if errors:
                logger.error(f"Configuration errors: {errors}")
                return False
            
            logger.info("✓ Configuration validated")
            
            # Initialize database
            await db.initialize()
            logger.info("✓ Database connection established")
            
            # Run migrations if needed
            if not config.SKIP_AUTO_MIGRATIONS:
                await db.run_migrations("bot/db/migrations")
                logger.info("✓ Database migrations completed")
            
            # Initialize repositories (load cartelas, settings)
            await initialize_repositories("data/cartelas_1000.json")
            logger.info("✓ Repositories initialized")
            
            # Create Flask app
            self.flask_app = create_flask_app()
            logger.info("✓ Flask app created")
            
            # Create SocketIO instance
            self.socketio = SocketIO(
                self.flask_app,
                cors_allowed_origins="*",
                async_mode='eventlet',
                ping_timeout=config.WS_PING_TIMEOUT,
                ping_interval=config.WS_PING_INTERVAL
            )
            logger.info("✓ SocketIO instance created")
            
            # Initialize bingo room with SocketIO
            bingo_room.init(self.socketio)
            logger.info("✓ Bingo room initialized")
            
            # Register SocketIO events
            register_socket_events(self.socketio, bingo_room)
            logger.info("✓ SocketIO events registered")
            
            # Start game loop
            asyncio.create_task(bingo_room.start())
            logger.info("✓ Game loop started")
            
            # Create bot instance
            self.bot = EstifBingoBot()
            
            # Initialize bot (without starting polling yet)
            bot_success = await self.bot.initialize()
            if not bot_success:
                logger.error("Failed to initialize bot")
                return False
            
            logger.info("✓ Bot initialized")
            
            self.is_running = True
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
        """Run the bot in synchronous mode (for threading)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.bot.start_polling())
        except Exception as e:
            logger.error(f"Bot thread error: {e}", exc_info=True)
        finally:
            loop.close()
    
    def run_flask_sync(self):
        """Run the Flask server in synchronous mode (for threading)"""
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
        """Start both the bot and Flask server in separate threads"""
        if not self.is_running:
            logger.error("Application not initialized. Call initialize() first.")
            return
        
        # Start bot in separate thread
        self.bot_thread = Thread(target=self.run_bot_sync, daemon=True)
        self.bot_thread.start()
        logger.info(f"Bot polling started (Thread: {self.bot_thread.name})")
        
        # Start Flask in main thread (or separate thread)
        logger.info(f"Starting Flask server on port {config.PORT}...")
        self.run_flask_sync()
    
    async def shutdown(self):
        """Shutdown all application components gracefully"""
        logger.info("Shutting down application...")
        self.is_running = False
        
        # Stop game engine
        await bingo_room.force_stop()
        logger.info("✓ Game engine stopped")
        
        # Stop bot
        if self.bot:
            await self.bot.shutdown()
            logger.info("✓ Bot stopped")
        
        # Close database
        await db.close()
        logger.info("✓ Database connection closed")
        
        logger.info("Application shutdown complete")


# ==================== MAIN ENTRY POINT ====================

async def main():
    """Main async entry point"""
    app = Application()
    
    # Initialize application
    success = await app.initialize()
    if not success:
        logger.error("Failed to initialize application. Exiting...")
        sys.exit(1)
    
    # Start application (blocks until Flask server stops)
    app.start()


def run():
    """Synchronous entry point for running the application"""
    asyncio.run(main())


if __name__ == "__main__":
    run()