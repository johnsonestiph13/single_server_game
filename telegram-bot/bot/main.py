# telegram-bot/bot/main.py
# Estif Bingo 24/7 - Main Bot Entry Point
# Initializes and runs the Telegram bot with all handlers

import asyncio
import logging
import sys
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from bot.config import config
from bot.utils.logger import setup_logger
from bot.db.database import db
from bot.db.repository import initialize_repositories
from bot.handlers import (
    # Core handlers
    start,
    language_callback,
    help_command,
    about_command,
    
    # Registration
    register,
    handle_contact,
    register_phone,
    register_cancel,
    
    # Financial
    balance,
    balance_callback,
    deposit,
    deposit_callback,
    deposit_amount,
    deposit_screenshot,
    deposit_cancel,
    cashout,
    withdrawal_amount,
    withdrawal_method_callback,
    withdrawal_details,
    confirm_withdrawal_callback,
    cancel_withdrawal,
    transfer,
    transfer_phone_number,
    transfer_amount,
    confirm_transfer_callback,
    cancel_transfer_callback,
    cancel_transfer,
    
    # Game
    play_game,
    game_rules_callback,
    back_to_game_callback,
    quick_deposit_callback,
    mini_bingo,
    play_mini_bingo_callback,
    back_to_mini_bingo_callback,
    bingo_otp,
    verify_otp,
    cancel_otp,
    
    # Social
    invite,
    copy_invite_link_callback,
    back_to_invite_callback,
    contact_center,
    contact_admin_callback,
    handle_contact_message,
    cancel_contact_callback,
    back_to_menu_callback,
    
    # Bonus
    bonus,
    claim_welcome_bonus_callback,
    claim_daily_bonus_callback,
    bonus_info_command,
    
    # Tournament (optional)
    tournament,
    tournament_register_callback,
    tournament_confirm_register_callback,
    tournament_play_callback,
    tournament_leaderboard_callback,
    cancel_tournament_register_callback,
    back_to_tournament_callback,
    
    # Admin
    admin_command,
    set_win_percent,
    force_start,
    force_stop,
    set_sound_pack,
    search_player,
    stats_command,
    approve_deposit,
    reject_deposit,
    approve_withdrawal,
    reject_withdrawal,
    broadcast_command,
    broadcast_message,
    broadcast_confirm_callback,
    broadcast_cancel_callback,
    maintenance_command,
    reset_game_command,
    cancel_broadcast,
    grant_bonus,
    
    # Conversation states
    REGISTER_PHONE,
    DEPOSIT_AMOUNT,
    DEPOSIT_SCREENSHOT,
    CASHOUT_AMOUNT,
    CASHOUT_METHOD,
    CASHOUT_ACCOUNT_DETAILS,
    CASHOUT_CONFIRMATION,
    TRANSFER_PHONE_NUMBER,
    TRANSFER_AMOUNT,
    TRANSFER_CONFIRMATION,
    WAITING_FOR_OTP,
    BROADCAST_MESSAGE,
    BROADCAST_CONFIRM,
)

from bot.game_engine.bingo_room import bingo_room
from bot.game_engine.events import register_socket_events

# Setup logger
logger = setup_logger(__name__)


class EstifBingoBot:
    """Main bot application class"""
    
    def __init__(self):
        self.application = None
        self.is_running = False
    
    async def initialize(self) -> bool:
        """
        Initialize the bot and all components.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info("Initializing Estif Bingo 24/7 Bot...")
            
            # Validate configuration
            errors = config.validate()
            if errors:
                logger.error(f"Configuration errors: {errors}")
                return False
            
            logger.info("Configuration validated")
            
            # Initialize database
            await db.initialize()
            logger.info("Database connection established")
            
            # Run migrations if needed
            if not config.SKIP_AUTO_MIGRATIONS:
                await db.run_migrations("bot/db/migrations")
                logger.info("Database migrations completed")
            
            # Initialize repositories (load cartelas, settings)
            await initialize_repositories("data/cartelas_1000.json")
            logger.info("Repositories initialized")
            
            # Create bot application
            self.application = (
                Application.builder()
                .token(config.BOT_TOKEN)
                .build()
            )
            
            # Register all handlers
            self._register_handlers()
            logger.info("Handlers registered")
            
            # Initialize game engine (will be started when Flask runs)
            # Game engine is handled separately in run.py
            
            self.is_running = True
            logger.info("Bot initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}", exc_info=True)
            return False
    
    def _register_handlers(self):
        """Register all command and callback handlers"""
        app = self.application
        
        # ==================== COMMAND HANDLERS ====================
        
        # Core commands
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("about", about_command))
        
        # Registration
        register_conv = ConversationHandler(
            entry_points=[CommandHandler("register", register)],
            states={
                REGISTER_PHONE: [
                    MessageHandler(filters.CONTACT, handle_contact),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, register_phone),
                ],
            },
            fallbacks=[CommandHandler("cancel", register_cancel)],
        )
        app.add_handler(register_conv)
        
        # Deposit
        deposit_conv = ConversationHandler(
            entry_points=[
                CommandHandler("deposit", deposit),
                CallbackQueryHandler(deposit, pattern="^deposit_menu$"),
            ],
            states={
                DEPOSIT_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_amount),
                    CallbackQueryHandler(deposit_amount, pattern="^deposit_amount_"),
                ],
                DEPOSIT_SCREENSHOT: [
                    MessageHandler(filters.PHOTO, deposit_screenshot),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_screenshot),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", deposit_cancel),
                CallbackQueryHandler(deposit_cancel, pattern="^cancel_deposit$"),
            ],
        )
        app.add_handler(deposit_conv)
        
        # Cashout
        cashout_conv = ConversationHandler(
            entry_points=[
                CommandHandler("cashout", cashout),
                CallbackQueryHandler(cashout, pattern="^cashout_menu$"),
            ],
            states={
                CASHOUT_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, withdrawal_amount),
                    CallbackQueryHandler(withdrawal_amount, pattern="^cashout_amount_"),
                ],
                CASHOUT_METHOD: [
                    CallbackQueryHandler(withdrawal_method_callback, pattern="^cashout_"),
                ],
                CASHOUT_ACCOUNT_DETAILS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, withdrawal_details),
                ],
                CASHOUT_CONFIRMATION: [
                    CallbackQueryHandler(confirm_withdrawal_callback, pattern="^confirm_withdrawal$"),
                    CallbackQueryHandler(cancel_withdrawal, pattern="^cancel_cashout$"),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", cancel_withdrawal),
                CallbackQueryHandler(cancel_withdrawal, pattern="^cancel_cashout$"),
            ],
        )
        app.add_handler(cashout_conv)
        
        # Transfer
        transfer_conv = ConversationHandler(
            entry_points=[
                CommandHandler("transfer", transfer),
                CallbackQueryHandler(transfer, pattern="^transfer_menu$"),
            ],
            states={
                TRANSFER_PHONE_NUMBER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_phone_number),
                ],
                TRANSFER_AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_amount),
                    CallbackQueryHandler(transfer_amount, pattern="^transfer_amount_"),
                ],
                TRANSFER_CONFIRMATION: [
                    CallbackQueryHandler(confirm_transfer_callback, pattern="^confirm_transfer$"),
                    CallbackQueryHandler(cancel_transfer, pattern="^cancel_transfer$"),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", cancel_transfer),
                CallbackQueryHandler(cancel_transfer, pattern="^cancel_transfer$"),
            ],
        )
        app.add_handler(transfer_conv)
        
        # Bingo OTP
        otp_conv = ConversationHandler(
            entry_points=[CommandHandler("bingo", bingo_otp)],
            states={
                WAITING_FOR_OTP: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, verify_otp),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", cancel_otp),
                CallbackQueryHandler(cancel_otp, pattern="^cancel_otp$"),
            ],
        )
        app.add_handler(otp_conv)
        
        # Broadcast (admin only)
        broadcast_conv = ConversationHandler(
            entry_points=[CommandHandler("broadcast", broadcast_command)],
            states={
                BROADCAST_MESSAGE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message),
                ],
                BROADCAST_CONFIRM: [
                    CallbackQueryHandler(broadcast_confirm_callback, pattern="^broadcast_confirm$"),
                    CallbackQueryHandler(broadcast_cancel_callback, pattern="^broadcast_cancel$"),
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel_broadcast)],
        )
        app.add_handler(broadcast_conv)
        
        # ==================== SIMPLE COMMANDS ====================
        app.add_handler(CommandHandler("balance", balance))
        app.add_handler(CommandHandler("bonus", bonus))
        app.add_handler(CommandHandler("bonus_info", bonus_info_command))
        app.add_handler(CommandHandler("play", play_game))
        app.add_handler(CommandHandler("mini_bingo", mini_bingo))
        app.add_handler(CommandHandler("invite", invite))
        app.add_handler(CommandHandler("contact", contact_center))
        
        # Tournament commands (if enabled)
        if config.ENABLE_TOURNAMENT:
            app.add_handler(CommandHandler("tournament", tournament))
            app.add_handler(CommandHandler("create_tournament", admin_create_tournament))
            app.add_handler(CommandHandler("end_tournament", admin_end_tournament))
        
        # Admin commands
        app.add_handler(CommandHandler("admin", admin_command))
        app.add_handler(CommandHandler("set_win_percent", set_win_percent))
        app.add_handler(CommandHandler("force_start", force_start))
        app.add_handler(CommandHandler("force_stop", force_stop))
        app.add_handler(CommandHandler("set_sound_pack", set_sound_pack))
        app.add_handler(CommandHandler("search_player", search_player))
        app.add_handler(CommandHandler("stats", stats_command))
        app.add_handler(CommandHandler("approve_deposit", approve_deposit))
        app.add_handler(CommandHandler("reject_deposit", reject_deposit))
        app.add_handler(CommandHandler("approve_withdrawal", approve_withdrawal))
        app.add_handler(CommandHandler("reject_withdrawal", reject_withdrawal))
        app.add_handler(CommandHandler("maintenance", maintenance_command))
        app.add_handler(CommandHandler("reset_game", reset_game_command))
        app.add_handler(CommandHandler("grant_bonus", grant_bonus))
        
        # ==================== CALLBACK QUERY HANDLERS ====================
        app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
        app.add_handler(CallbackQueryHandler(balance_callback, pattern="^balance_"))
        app.add_handler(CallbackQueryHandler(deposit_callback, pattern="^deposit_"))
        app.add_handler(CallbackQueryHandler(game_rules_callback, pattern="^game_rules$"))
        app.add_handler(CallbackQueryHandler(back_to_game_callback, pattern="^back_to_game$"))
        app.add_handler(CallbackQueryHandler(quick_deposit_callback, pattern="^quick_deposit$"))
        app.add_handler(CallbackQueryHandler(play_mini_bingo_callback, pattern="^play_mini_bingo$"))
        app.add_handler(CallbackQueryHandler(back_to_mini_bingo_callback, pattern="^back_to_mini_bingo$"))
        app.add_handler(CallbackQueryHandler(copy_invite_link_callback, pattern="^copy_invite_link$"))
        app.add_handler(CallbackQueryHandler(back_to_invite_callback, pattern="^back_to_invite$"))
        app.add_handler(CallbackQueryHandler(contact_admin_callback, pattern="^contact_admin$"))
        app.add_handler(CallbackQueryHandler(cancel_contact_callback, pattern="^cancel_contact$"))
        app.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$"))
        app.add_handler(CallbackQueryHandler(claim_welcome_bonus_callback, pattern="^claim_welcome_bonus$"))
        app.add_handler(CallbackQueryHandler(claim_daily_bonus_callback, pattern="^claim_daily_bonus$"))
        app.add_handler(CallbackQueryHandler(bonus_info_command, pattern="^bonus_info$"))
        app.add_handler(CallbackQueryHandler(no_bonus_callback, pattern="^no_bonus$"))
        
        # Tournament callbacks
        if config.ENABLE_TOURNAMENT:
            app.add_handler(CallbackQueryHandler(tournament_register_callback, pattern="^tourney_register_"))
            app.add_handler(CallbackQueryHandler(tournament_confirm_register_callback, pattern="^tourney_confirm_register$"))
            app.add_handler(CallbackQueryHandler(tournament_play_callback, pattern="^tourney_play_"))
            app.add_handler(CallbackQueryHandler(tournament_leaderboard_callback, pattern="^tourney_leaderboard$"))
            app.add_handler(CallbackQueryHandler(cancel_tournament_register_callback, pattern="^cancel_tournament_register$"))
            app.add_handler(CallbackQueryHandler(back_to_tournament_callback, pattern="^back_to_tournament$"))
        
        # ==================== MESSAGE HANDLERS ====================
        
        # Contact message handler (forward to admin)
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_contact_message,
        ), group=1)
    
    async def start_polling(self):
        """Start the bot in polling mode"""
        if not self.application:
            logger.error("Bot not initialized")
            return
        
        try:
            logger.info("Starting bot polling...")
            await self.application.initialize()
            await self.application.start()
            
            # Start polling
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )
            
            logger.info("Bot is running!")
            self.is_running = True
            
            # Keep the bot running
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot polling error: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the bot gracefully"""
        logger.info("Shutting down bot...")
        self.is_running = False
        
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        
        # Close database connection
        await db.close()
        
        logger.info("Bot shutdown complete")


# ==================== FLASK INTEGRATION ====================

def create_flask_app():
    """Create Flask app for web interface and API"""
    from flask import Flask, send_from_directory
    
    app = Flask(__name__, static_folder='static')
    app.config['SECRET_KEY'] = config.JWT_SECRET
    
    # Register API blueprints
    from bot.api import register_blueprints
    register_blueprints(app)
    
    # Serve static files
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory('static', filename)
    
    # Root endpoint
    @app.route('/')
    def index():
        return send_from_directory('static', 'advanced_bingo.html')
    
    return app


# ==================== MAIN ENTRY POINT ====================

async def main():
    """Main entry point for the bot"""
    bot = EstifBingoBot()
    
    # Initialize bot
    success = await bot.initialize()
    if not success:
        logger.error("Failed to initialize bot. Exiting...")
        sys.exit(1)
    
    # Start bot polling
    await bot.start_polling()


def run_bot():
    """Run the bot (entry point for run.py)"""
    asyncio.run(main())


if __name__ == "__main__":
    run_bot()