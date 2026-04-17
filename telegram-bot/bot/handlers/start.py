# telegram-bot/bot/handlers/start.py
# Estif Bingo 24/7 - Enhanced Language Selection Handler
# Features: Language selection, welcome bonus (one-time), user tracking

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.audit_repo import AuditRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import main_menu_keyboard as menu
from bot.config import config
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send language selection menu on /start - Always shows language options"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or ""
        first_name = update.effective_user.first_name or ""
        last_name = update.effective_user.last_name or ""
        
        logger.info(f"Start command from user: {user_id} (@{username})")
        
        # Update user's last seen timestamp
        await UserRepository.update_last_seen(user_id)
        
        # Show language selection keyboard (ALWAYS)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_emoji('uk')} English", callback_data="lang_en")],
            [InlineKeyboardButton(f"{get_emoji('ethiopia')} አማርኛ", callback_data="lang_am")]
        ])
        
        # Send language selection message
        await update.message.reply_text(
            f"{get_emoji('language')} *Select your language / ቋንቋ ይምረጡ:*\n\n"
            f"Choose your preferred language to continue using the bot.\n\n"
            f"🇬🇧 *English* - Full bot features\n"
            f"🇪🇹 *አማርኛ* - ሙሉ የቦት አገልግሎቶች\n\n"
            f"{get_emoji('info')} Your phone number will be requested after language selection.",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        logger.info(f"Language selection sent to user: {user_id}")
        
    except Exception as e:
        logger.error(f"Error in start command for user {update.effective_user.id}: {e}", exc_info=True)
        await update.message.reply_text(
            f"{get_emoji('error')} *An error occurred.*\n\n"
            f"Please try again later. If the problem persists, contact support.\n\n"
            f"{get_emoji('support')} Support: {config.SUPPORT_CHANNEL_LINK or 'Contact admin'}",
            parse_mode='Markdown'
        )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback with enhanced user setup"""
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or ""
    first_name = query.from_user.first_name or ""
    last_name = query.from_user.last_name or ""
    
    try:
        await query.answer()
        
        lang = query.data.split("_")[1]  # "lang_en" -> "en", "lang_am" -> "am"
        logger.info(f"Language selected: {lang} for user: {user_id} (@{username})")
        
        # Check if user exists
        user = await UserRepository.get_by_telegram_id(user_id)
        is_new_user = False
        welcome_bonus_given = False
        
        if not user:
            # Create new user (without phone - will be added in /register)
            logger.info(f"Creating new user: {user_id}")
            await UserRepository.create(
                telegram_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                phone_encrypted=None,  # Phone will be added during /register
                lang=lang,
                registered=False,  # Not fully registered until phone verification
                welcome_bonus_claimed=False
            )
            is_new_user = True
            
            # Audit log
            await AuditRepository.log(
                user_id=user_id,
                action="user_created",
                entity_type="user",
                entity_id=str(user_id),
                new_value={"username": username, "first_name": first_name, "last_name": last_name, "lang": lang}
            )
        else:
            # Update existing user's language
            logger.info(f"Updating language for existing user: {user_id}")
            await UserRepository.update(user_id, lang=lang)
            
            # Audit log for language change
            await AuditRepository.log(
                user_id=user_id,
                action="language_changed",
                entity_type="user",
                entity_id=str(user_id),
                old_value={"lang": user.get("lang")},
                new_value={"lang": lang}
            )
        
        # Get updated user data
        user_data = await UserRepository.get_by_telegram_id(user_id)
        
        # Check if welcome bonus should be given
        # Only give if user is NEW and welcome_bonus_claimed is False
        if is_new_user and not user_data.get('welcome_bonus_claimed', False):
            from bot.api.balance_ops import add_balance
            await add_balance(
                telegram_id=user_id,
                amount=config.WELCOME_BONUS_AMOUNT,
                reason="welcome_bonus",
                metadata={"lang": lang}
            )
            await UserRepository.mark_welcome_bonus_claimed(user_id)
            welcome_bonus_given = True
            logger.info(f"Welcome bonus of {config.WELCOME_BONUS_AMOUNT} ETB given to user {user_id}")
        
        # Get balance
        from bot.api.balance_ops import get_balance
        balance = await get_balance(user_id)
        
        # Edit the original message to show welcome text
        welcome_text = TEXTS[lang]['welcome']
        if welcome_bonus_given:
            welcome_text += f"\n\n{get_emoji('gift')} *Welcome Bonus!*\nYou received {config.WELCOME_BONUS_AMOUNT} ETB welcome bonus!"
        
        await query.edit_message_text(
            welcome_text,
            parse_mode='Markdown'
        )
        
        # Send personalized welcome message with balance
        await query.message.reply_text(
            f"{get_emoji('click')} *Choose an option from the menu below:*\n\n"
            f"{get_emoji('money')} Your balance: *{balance:.2f} ETB*\n"
            f"{get_emoji('game')} Ready to play? Use /play to start!",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        
        # Send helpful tips for new users
        if is_new_user:
            await query.message.reply_text(
                f"{get_emoji('info')} *Quick Tips:*\n\n"
                f"• Use /register to verify your phone number\n"
                f"• Use /play to start the Bingo game\n"
                f"• Use /deposit to add funds\n"
                f"• Use /balance to check your balance\n"
                f"• Use /invite to share the game with friends\n\n"
                f"{get_emoji('support')} Need help? Use /contact",
                parse_mode='Markdown'
            )
        
        logger.info(f"Language selection completed successfully for user: {user_id}")
        
    except Exception as e:
        logger.error(f"Error in language_callback for user {user_id}: {e}", exc_info=True)
        try:
            await query.edit_message_text(
                f"{get_emoji('error')} *An error occurred.*\n\n"
                f"Please try /start again.\n\n"
                f"{get_emoji('support')} If the problem persists, contact support.",
                parse_mode='Markdown'
            )
        except Exception as edit_error:
            logger.error(f"Could not edit message: {edit_error}")
            await query.message.reply_text(
                f"{get_emoji('error')} *An error occurred.*\n\n"
                f"Please try /start again.",
                parse_mode='Markdown'
            )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available commands and help information"""
    user_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(user_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    help_text = f"""
{get_emoji('help')} *ESTIF BINGO 24/7 - HELP CENTER* {get_emoji('help')}

*🎮 Game Commands:*
• /play - Start playing real-time Bingo

*💰 Financial Commands:*
• /balance - Check your balance
• /deposit - Add funds to your account
• /cashout - Withdraw your winnings
• /transfer - Send money to another player

*👤 Account Commands:*
• /register - Verify your phone number
• /invite - Share the game with friends
• /bonus - Check welcome bonus status

*📞 Support:*
• /contact - Contact support
• /help - Show this help message

{get_emoji('info')} *Need more help?* Use /contact to reach support.
    """
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=menu(lang)
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot information and version"""
    user_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(user_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Get game statistics
    from bot.db.repository.game_repo import GameRepository
    total_players = await UserRepository.count_registered()
    total_rounds = await GameRepository.count_rounds()
    total_payout = await GameRepository.total_payout()
    
    about_text = f"""
{get_emoji('game')} *ESTIF BINGO 24/7* {get_emoji('game')}

*Version:* 4.0.0
*Platform:* Telegram Bot + Real-time Web Game

*Features:*
• Real-time multiplayer Bingo
• 1000+ unique cartelas
• Multiple winning patterns
• Secure deposits & withdrawals
• One-time welcome bonus
• Multi-language support (English/Amharic)

*Game Statistics:*
• Total Players: {total_players}
• Games Played: {total_rounds}
• Total Payout: {total_payout:.2f} ETB
• Win Rate: Up to {config.DEFAULT_WIN_PERCENTAGE}%

{get_emoji('link')} *Game URL:* {config.BASE_URL}

*Thank you for playing with us!* 🎉
    """
    
    await update.message.reply_text(
        about_text,
        parse_mode='Markdown',
        reply_markup=menu(lang),
        disable_web_page_preview=True
    )


# Export all handlers
__all__ = [
    'start',
    'language_callback',
    'help_command',
    'about_command'
]