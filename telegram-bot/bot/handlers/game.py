# telegram-bot/bot/handlers/game.py
# Estif Bingo 24/7 - Game WebApp Handler
# Sends WebApp button with JWT authentication for instant game access

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.game_repo import GameRepository
from bot.db.repository.audit_repo import AuditRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import menu
from bot.config import config
from bot.utils.logger import logger
from bot.utils.security import generate_jwt_for_game
from bot.texts.emojis import get_emoji

logger = logging.getLogger(__name__)


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send game link with WebApp button for instant access.
    Generates JWT token and embeds it in the WebApp URL.
    """
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Check if user is registered
    if not user or not user.get('registered'):
        await update.message.reply_text(
            f"{get_emoji('error')} Please register first using /register",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Check if game is in maintenance mode
    maintenance_mode = await GameRepository.get_maintenance_mode()
    if maintenance_mode and not is_admin(telegram_id):
        await update.message.reply_text(
            f"{get_emoji('warning')} *Game Under Maintenance*\n\n"
            f"The game is currently under maintenance.\n"
            f"Please check back later.\n\n"
            f"{get_emoji('support')} Contact support for more information.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Check if user has sufficient balance to play
    from bot.api.balance_ops import get_balance
    balance = await get_balance(telegram_id)
    
    if balance < config.MIN_BALANCE_FOR_PLAY:
        # Show insufficient balance message with deposit option
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_emoji('deposit')} Deposit Now", callback_data="quick_deposit")],
            [InlineKeyboardButton(f"{get_emoji('back')} Back to Menu", callback_data="back_to_menu")]
        ])
        
        await update.message.reply_text(
            f"{get_emoji('error')} *Insufficient Balance*\n\n"
            f"Minimum balance to play: `{config.MIN_BALANCE_FOR_PLAY}` ETB\n"
            f"Your current balance: `{balance:.2f}` ETB\n\n"
            f"{get_emoji('deposit')} Please deposit funds to start playing.\n\n"
            f"Each cartela costs `{config.CARTELA_PRICE}` ETB.\n"
            f"You can select up to `{config.MAX_CARTELAS}` cartelas per round.\n\n"
            f"{get_emoji('info')} New players get a `{config.WELCOME_BONUS_AMOUNT}` ETB welcome bonus!",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    try:
        # Generate JWT token for game authentication
        jwt_token = await generate_jwt_for_game(telegram_id)
        
        # Build WebApp URL with token
        webapp_url = f"{config.BASE_URL}/advanced_bingo.html?token={jwt_token}"
        
        # Create WebApp button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{get_emoji('game')} PLAY NOW {get_emoji('game')}",
                web_app=WebAppInfo(url=webapp_url)
            )],
            [InlineKeyboardButton(
                f"{get_emoji('info')} Game Rules",
                callback_data="game_rules"
            )],
            [InlineKeyboardButton(
                f"{get_emoji('back')} Back to Menu",
                callback_data="back_to_menu"
            )]
        ])
        
        # Get active game stats
        active_players = await GameRepository.get_active_players_count()
        current_round = await GameRepository.get_current_round_number()
        win_percentage = await GameRepository.get_win_percentage()
        
        # Send game message
        await update.message.reply_text(
            f"{get_emoji('game')} *ESTIF BINGO 24/7* {get_emoji('game')}\n\n"
            f"{get_emoji('money')} Your balance: `{balance:.2f}` ETB\n"
            f"{get_emoji('cartela')} Cartela price: `{config.CARTELA_PRICE}` ETB\n"
            f"{get_emoji('max')} Max cartelas per round: `{config.MAX_CARTELAS}`\n"
            f"{get_emoji('trophy')} Win rate: up to `{win_percentage}`%\n\n"
            f"*Game Info:*\n"
            f"• 🎯 Active players: `{active_players}`\n"
            f"• 🔢 Current round: `{current_round or 'New round starting'}`\n"
            f"• ⏱️ Selection time: `{config.SELECTION_TIME}` seconds\n"
            f"• 🎲 Numbers: 1-75 random draw\n\n"
            f"{get_emoji('info')} *How to play:*\n"
            f"1️⃣ Click the PLAY NOW button below\n"
            f"2️⃣ Select up to {config.MAX_CARTELAS} cartelas\n"
            f"3️⃣ Wait for numbers to be called\n"
            f"4️⃣ Get a line (horizontal/vertical/diagonal) to win!\n\n"
            f"{get_emoji('warning')} *Note:* Each cartela costs {config.CARTELA_PRICE} ETB.\n"
            f"Balance is deducted immediately upon selection.\n\n"
            f"Good luck! 🍀",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        # Audit log
        await AuditRepository.log(
            user_id=telegram_id,
            action="game_launched",
            entity_type="game",
            entity_id=str(telegram_id),
            metadata={'balance': balance}
        )
        
        logger.info(f"Game launched for user {telegram_id} with balance {balance}")
        
    except Exception as e:
        logger.error(f"Error in play command for user {telegram_id}: {e}", exc_info=True)
        await update.message.reply_text(
            f"{get_emoji('error')} *Failed to start game*\n\n"
            f"An error occurred while launching the game.\n"
            f"Please try again later.\n\n"
            f"{get_emoji('support')} If the problem persists, contact support.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )


async def game_rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed game rules"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    rules_text = (
        f"{get_emoji('info')} *BINGO GAME RULES* {get_emoji('info')}\n\n"
        
        f"*🎯 Objective*\n"
        f"Complete a line (horizontal, vertical, or diagonal) on your cartela(s) before other players.\n\n"
        
        f"*📋 Game Flow*\n"
        f"1️⃣ *Selection Phase ({config.SELECTION_TIME} seconds)*\n"
        f"   • Choose 1 to {config.MAX_CARTELAS} cartelas from 1000 available\n"
        f"   • Each cartela costs `{config.CARTELA_PRICE}` ETB\n"
        f"   • Cartelas shown in:\n"
        f"     - 🟢 Green = Your selected cartelas\n"
        f"     - 🔴 Red = Taken by other players\n"
        f"     - ⚪ Grey = Available\n"
        f"   • Timer turns red and blinks at 10 seconds\n\n"
        
        f"2️⃣ *Drawing Phase*\n"
        f"   • Numbers 1-75 are called randomly\n"
        f"   • Called numbers are marked automatically on your cartelas\n"
        f"   • Sound plays for each number (customizable)\n\n"
        
        f"3️⃣ *Winning*\n"
        f"   • First player(s) to complete a line wins\n"
        f"   • Winning patterns:\n"
        f"     - Horizontal line (any row)\n"
        f"     - Vertical line (any column)\n"
        f"     - Diagonal line (both directions)\n"
        f"   • Prize pool = Total cartelas selected × {config.CARTELA_PRICE} ETB\n"
        f"   • Win amount = Prize pool × Win percentage / 100\n"
        f"   • If multiple winners: prize split equally\n\n"
        
        f"*💰 Prizes*\n"
        f"• Win percentage: `{await GameRepository.get_win_percentage()}%`\n"
        f"• House edge: `{100 - await GameRepository.get_win_percentage()}%`\n\n"
        
        f"*🎮 Controls*\n"
        f"• Select/Deselect cartelas by clicking\n"
        f"• Choose your preferred sound pack\n"
        f"• Watch only mode (if balance < {config.MIN_BALANCE_FOR_PLAY} ETB)\n\n"
        
        f"*⚠️ Important Notes*\n"
        f"• Balance deducted immediately when selecting cartelas\n"
        f"• No refunds after selection\n"
        f"• Winnings credited automatically\n"
        f"• Minimum balance to play: `{config.MIN_BALANCE_FOR_PLAY}` ETB\n\n"
        
        f"{get_emoji('support')} Need help? Contact support."
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_emoji('back')} Back to Game", callback_data="back_to_game")],
        [InlineKeyboardButton(f"{get_emoji('menu')} Main Menu", callback_data="back_to_menu")]
    ])
    
    await query.edit_message_text(
        rules_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def back_to_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to game launch screen"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Regenerate game link
    from bot.api.balance_ops import get_balance
    balance = await get_balance(telegram_id)
    
    try:
        jwt_token = await generate_jwt_for_game(telegram_id)
        webapp_url = f"{config.BASE_URL}/advanced_bingo.html?token={jwt_token}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                f"{get_emoji('game')} PLAY NOW {get_emoji('game')}",
                web_app=WebAppInfo(url=webapp_url)
            )],
            [InlineKeyboardButton(
                f"{get_emoji('info')} Game Rules",
                callback_data="game_rules"
            )],
            [InlineKeyboardButton(
                f"{get_emoji('back')} Back to Menu",
                callback_data="back_to_menu"
            )]
        ])
        
        await query.edit_message_text(
            f"{get_emoji('game')} *ESTIF BINGO 24/7* {get_emoji('game')}\n\n"
            f"{get_emoji('money')} Your balance: `{balance:.2f}` ETB\n"
            f"{get_emoji('cartela')} Cartela price: `{config.CARTELA_PRICE}` ETB\n"
            f"{get_emoji('max')} Max cartelas: `{config.MAX_CARTELAS}`\n\n"
            f"Click PLAY NOW to start!",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in back_to_game: {e}")
        await query.edit_message_text(
            f"{get_emoji('error')} Failed to load game. Please use /play again.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )


async def quick_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick deposit from game menu"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Import deposit handler
    from bot.handlers.deposit import deposit
    
    # Clear current message and start deposit
    await query.edit_message_text(
        f"{get_emoji('deposit')} Redirecting to deposit...",
        parse_mode='Markdown'
    )
    
    # Create a fake update to pass to deposit
    # This is a simplified approach - in production, you'd want to handle this better
    await deposit(update, context)


def is_admin(telegram_id: int) -> bool:
    """Check if user is admin"""
    return str(telegram_id) == str(config.ADMIN_CHAT_ID)


async def game_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current game status (for debugging)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    from bot.game_engine.bingo_room import bingo_room
    
    state = bingo_room.get_state()
    
    status_text = (
        f"{get_emoji('game')} *Game Status*\n\n"
        f"Status: `{state.get('status', 'unknown')}`\n"
        f"Players: `{state.get('player_count', 0)}`\n"
        f"Selected Cartelas: `{state.get('selected_count', 0)}`\n"
        f"Timer: `{state.get('timer', 0)}` seconds\n"
        f"Called Numbers: `{len(state.get('called_numbers', []))}`\n"
    )
    
    await update.message.reply_text(
        status_text,
        parse_mode='Markdown'
    )


# Export all
__all__ = [
    'play',
    'game_rules_callback',
    'back_to_game_callback',
    'quick_deposit_callback',
    'game_status',
]