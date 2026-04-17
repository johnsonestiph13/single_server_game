# telegram-bot/bot/handlers/bonus.py
# Estif Bingo 24/7 - Bonus Handler (Welcome Bonus, Daily Bonus)

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.bonus_repo import BonusRepository
from bot.db.repository.audit_repo import AuditRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import menu
from bot.config import config
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

# Bonus amounts
WELCOME_BONUS_AMOUNT = getattr(config, 'WELCOME_BONUS_AMOUNT', 30)
DAILY_BONUS_AMOUNT = getattr(config, 'DAILY_BONUS_AMOUNT', 5)

# Feature flags
ENABLE_DAILY_BONUS = getattr(config, 'ENABLE_DAILY_BONUS', False)

logger = logging.getLogger(__name__)


async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bonus information and claim options"""
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
    
    # Get bonus status
    welcome_bonus_claimed = user.get('welcome_bonus_claimed', False)
    
    # Get daily bonus status if enabled
    daily_bonus_claimed = False
    daily_bonus_available = False
    next_daily_bonus = None
    
    if ENABLE_DAILY_BONUS:
        daily_bonus = await BonusRepository.get_daily_bonus_status(telegram_id)
        if daily_bonus:
            daily_bonus_claimed = daily_bonus.get('claimed', False)
            last_claimed = daily_bonus.get('last_claimed_at')
            if last_claimed:
                next_available = last_claimed + timedelta(days=1)
                if datetime.utcnow() >= next_available:
                    daily_bonus_available = True
                else:
                    next_daily_bonus = next_available
    
    # Build bonus message
    bonus_text = (
        f"{get_emoji('gift')} *BONUS CENTER* {get_emoji('gift')}\n\n"
    )
    
    # Welcome bonus section
    if welcome_bonus_claimed:
        bonus_text += (
            f"{get_emoji('check')} *Welcome Bonus:* `Claimed`\n"
            f"   Amount: `{WELCOME_BONUS_AMOUNT}` ETB\n\n"
        )
    else:
        bonus_text += (
            f"{get_emoji('new')} *Welcome Bonus:* `Available`\n"
            f"   Amount: `{WELCOME_BONUS_AMOUNT}` ETB\n"
            f"   Status: Complete registration to claim\n\n"
        )
    
    # Daily bonus section (if enabled)
    if ENABLE_DAILY_BONUS:
        if daily_bonus_available:
            bonus_text += (
                f"{get_emoji('calendar')} *Daily Bonus:* `Available`\n"
                f"   Amount: `{DAILY_BONUS_AMOUNT}` ETB\n"
                f"   Claim once every 24 hours\n\n"
            )
        elif daily_bonus_claimed and next_daily_bonus:
            hours_remaining = int((next_daily_bonus - datetime.utcnow()).total_seconds() / 3600)
            bonus_text += (
                f"{get_emoji('clock')} *Daily Bonus:* `Claimed`\n"
                f"   Next available in: `{hours_remaining}` hours\n\n"
            )
        else:
            bonus_text += (
                f"{get_emoji('calendar')} *Daily Bonus:* `Not Claimed`\n"
                f"   Amount: `{DAILY_BONUS_AMOUNT}` ETB\n"
                f"   Claim once every 24 hours\n\n"
            )
    else:
        bonus_text += (
            f"{get_emoji('info')} *Daily Bonus:* `Disabled`\n"
            f"   Only welcome bonus is currently available.\n\n"
        )
    
    # Create keyboard with claim buttons
    keyboard = []
    
    if not welcome_bonus_claimed and user.get('registered'):
        keyboard.append([InlineKeyboardButton(
            f"{get_emoji('gift')} Claim Welcome Bonus", 
            callback_data="claim_welcome_bonus"
        )])
    
    if ENABLE_DAILY_BONUS and daily_bonus_available:
        keyboard.append([InlineKeyboardButton(
            f"{get_emoji('calendar')} Claim Daily Bonus", 
            callback_data="claim_daily_bonus"
        )])
    
    if not keyboard:
        keyboard.append([InlineKeyboardButton(
            f"{get_emoji('info')} No Bonuses Available", 
            callback_data="no_bonus"
        )])
    
    keyboard.append([InlineKeyboardButton(
        f"{get_emoji('back')} Back to Menu", 
        callback_data="back_to_menu"
    )])
    
    await update.message.reply_text(
        bonus_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def claim_welcome_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Claim welcome bonus for new users"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Check if already claimed
    if user.get('welcome_bonus_claimed', False):
        await query.edit_message_text(
            f"{get_emoji('warning')} *Welcome Bonus Already Claimed*\n\n"
            f"You have already received your welcome bonus.\n\n"
            f"Use /play to start playing!",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Check if user is registered
    if not user.get('registered', False):
        await query.edit_message_text(
            f"{get_emoji('error')} *Registration Required*\n\n"
            f"Please complete your registration using /register first.\n\n"
            f"After registration, you can claim your welcome bonus.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Add welcome bonus
    from bot.api.balance_ops import add_balance
    await add_balance(
        telegram_id=telegram_id,
        amount=WELCOME_BONUS_AMOUNT,
        reason="welcome_bonus",
        metadata={'claimed_via': 'bonus_command'}
    )
    
    # Mark as claimed
    await UserRepository.mark_welcome_bonus_claimed(telegram_id)
    
    # Record bonus claim
    await BonusRepository.record_bonus_claim(
        telegram_id=telegram_id,
        bonus_type='welcome',
        amount=WELCOME_BONUS_AMOUNT
    )
    
    # Audit log
    await AuditRepository.log(
        user_id=telegram_id,
        action="welcome_bonus_claimed",
        entity_type="bonus",
        entity_id=str(telegram_id),
        new_value={'amount': WELCOME_BONUS_AMOUNT}
    )
    
    # Get updated balance
    from bot.api.balance_ops import get_balance
    new_balance = await get_balance(telegram_id)
    
    await query.edit_message_text(
        f"{get_emoji('success')} *Welcome Bonus Claimed!*\n\n"
        f"Amount: `{WELCOME_BONUS_AMOUNT}` ETB\n"
        f"Your new balance: `{new_balance:.2f}` ETB\n\n"
        f"{get_emoji('game')} Use /play to start playing!",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    
    logger.info(f"Welcome bonus claimed for user {telegram_id}: {WELCOME_BONUS_AMOUNT} ETB")


async def claim_daily_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Claim daily bonus (if enabled)"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    if not ENABLE_DAILY_BONUS:
        await query.edit_message_text(
            f"{get_emoji('error')} *Daily Bonus Disabled*\n\n"
            f"Daily bonus is currently not available.\n\n"
            f"Only welcome bonus is active.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Check if already claimed today
    last_claim = await BonusRepository.get_last_daily_claim(telegram_id)
    
    if last_claim:
        last_claim_date = last_claim.get('claimed_at')
        next_available = last_claim_date + timedelta(days=1)
        
        if datetime.utcnow() < next_available:
            hours_remaining = int((next_available - datetime.utcnow()).total_seconds() / 3600)
            minutes_remaining = int(((next_available - datetime.utcnow()).total_seconds() % 3600) / 60)
            
            await query.edit_message_text(
                f"{get_emoji('clock')} *Daily Bonus Already Claimed*\n\n"
                f"Next bonus available in: `{hours_remaining}` hours `{minutes_remaining}` minutes\n\n"
                f"Come back tomorrow for your daily bonus!",
                reply_markup=menu(lang),
                parse_mode='Markdown'
            )
            return
    
    # Add daily bonus
    from bot.api.balance_ops import add_balance
    await add_balance(
        telegram_id=telegram_id,
        amount=DAILY_BONUS_AMOUNT,
        reason="daily_bonus",
        metadata={'claimed_via': 'bonus_command'}
    )
    
    # Record bonus claim
    await BonusRepository.record_bonus_claim(
        telegram_id=telegram_id,
        bonus_type='daily',
        amount=DAILY_BONUS_AMOUNT
    )
    
    # Audit log
    await AuditRepository.log(
        user_id=telegram_id,
        action="daily_bonus_claimed",
        entity_type="bonus",
        entity_id=str(telegram_id),
        new_value={'amount': DAILY_BONUS_AMOUNT}
    )
    
    # Get updated balance
    from bot.api.balance_ops import get_balance
    new_balance = await get_balance(telegram_id)
    
    await query.edit_message_text(
        f"{get_emoji('success')} *Daily Bonus Claimed!*\n\n"
        f"Amount: `{DAILY_BONUS_AMOUNT}` ETB\n"
        f"Your new balance: `{new_balance:.2f}` ETB\n\n"
        f"Come back tomorrow for another bonus!\n\n"
        f"{get_emoji('game')} Use /play to start playing!",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    
    logger.info(f"Daily bonus claimed for user {telegram_id}: {DAILY_BONUS_AMOUNT} ETB")


async def check_bonus_eligibility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user is eligible for any bonuses (called on /start and /register)"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    
    if not user:
        return
    
    # Check welcome bonus
    if not user.get('welcome_bonus_claimed', False) and user.get('registered', False):
        # Auto-claim welcome bonus on registration
        from bot.api.balance_ops import add_balance
        await add_balance(
            telegram_id=telegram_id,
            amount=WELCOME_BONUS_AMOUNT,
            reason="welcome_bonus",
            metadata={'claimed_via': 'auto_on_register'}
        )
        
        await UserRepository.mark_welcome_bonus_claimed(telegram_id)
        
        await BonusRepository.record_bonus_claim(
            telegram_id=telegram_id,
            bonus_type='welcome',
            amount=WELCOME_BONUS_AMOUNT
        )
        
        logger.info(f"Welcome bonus auto-claimed for user {telegram_id} on registration")
        
        # Notify user
        if update.callback_query:
            await update.callback_query.message.reply_text(
                f"{get_emoji('gift')} *Welcome Bonus!*\n\n"
                f"You received `{WELCOME_BONUS_AMOUNT}` ETB welcome bonus!\n\n"
                f"Use /play to start playing!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"{get_emoji('gift')} *Welcome Bonus!*\n\n"
                f"You received `{WELCOME_BONUS_AMOUNT}` ETB welcome bonus!\n\n"
                f"Use /play to start playing!",
                parse_mode='Markdown'
            )


async def bonus_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed bonus information and terms"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    info_text = (
        f"{get_emoji('info')} *BONUS INFORMATION* {get_emoji('info')}\n\n"
        
        f"*🎁 Welcome Bonus*\n"
        f"• Amount: `{WELCOME_BONUS_AMOUNT}` ETB\n"
        f"• Eligibility: New users only\n"
        f"• Requirements: Complete phone verification\n"
        f"• One-time only\n\n"
    )
    
    if ENABLE_DAILY_BONUS:
        info_text += (
            f"*📅 Daily Bonus*\n"
            f"• Amount: `{DAILY_BONUS_AMOUNT}` ETB\n"
            f"• Eligibility: All registered users\n"
            f"• Frequency: Once every 24 hours\n"
            f"• Reset time: 00:00 UTC\n\n"
        )
    
    info_text += (
        f"*📋 Terms & Conditions*\n"
        f"• Bonuses are non-transferable\n"
        f"• Bonus funds must be used for gameplay\n"
        f"• Withdrawal requires minimum wagering\n"
        f"• Abuse may result in bonus forfeiture\n\n"
        
        f"{get_emoji('support')} Questions? Contact support."
    )
    
    await update.message.reply_text(
        info_text,
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )


async def no_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle no bonus available button"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    await query.edit_message_text(
        f"{get_emoji('info')} *No Bonuses Available*\n\n"
        f"You have already claimed all available bonuses.\n\n"
        f"{get_emoji('game')} Use /play to start playing!\n"
        f"{get_emoji('deposit')} Use /deposit to add more funds.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )


# Admin command to grant manual bonus
async def grant_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Grant manual bonus to user (admin only)"""
    telegram_id = update.effective_user.id
    
    if str(telegram_id) != str(config.ADMIN_CHAT_ID):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/grant_bonus <user_id> <amount> [reason]`\n\n"
            f"Example: `/grant_bonus 123456789 50 compensation`",
            parse_mode='Markdown'
        )
        return
    
    try:
        target_user_id = int(args[0])
        amount = float(args[1])
        reason = ' '.join(args[2:]) if len(args) > 2 else 'admin_grant'
    except ValueError:
        await update.message.reply_text(
            f"{get_emoji('error')} Invalid user ID or amount.",
            parse_mode='Markdown'
        )
        return
    
    # Check if user exists
    user = await UserRepository.get_by_telegram_id(target_user_id)
    if not user:
        await update.message.reply_text(
            f"{get_emoji('error')} User `{target_user_id}` not found.",
            parse_mode='Markdown'
        )
        return
    
    # Add bonus
    from bot.api.balance_ops import add_balance
    await add_balance(
        telegram_id=target_user_id,
        amount=amount,
        reason=f"admin_bonus_{reason}",
        metadata={'admin_id': telegram_id, 'reason': reason}
    )
    
    # Record bonus claim
    await BonusRepository.record_bonus_claim(
        telegram_id=target_user_id,
        bonus_type='admin',
        amount=amount,
        metadata={'admin_id': telegram_id, 'reason': reason}
    )
    
    # Audit log
    await AuditRepository.log(
        user_id=telegram_id,
        action="admin_grant_bonus",
        entity_type="bonus",
        entity_id=str(target_user_id),
        new_value={'amount': amount, 'reason': reason}
    )
    
    # Notify user
    await context.bot.send_message(
        chat_id=target_user_id,
        text=(
            f"{get_emoji('gift')} *Bonus Received!*\n\n"
            f"You have received a bonus of `{amount:.2f}` ETB.\n"
            f"Reason: `{reason}`\n\n"
            f"Your balance has been updated."
        ),
        parse_mode='Markdown'
    )
    
    await update.message.reply_text(
        f"{get_emoji('success')} Bonus of `{amount:.2f}` ETB granted to user `{target_user_id}`.",
        parse_mode='Markdown'
    )
    
    logger.info(f"Admin {telegram_id} granted {amount} ETB bonus to user {target_user_id}")


# Export all
__all__ = [
    'bonus',
    'claim_welcome_bonus_callback',
    'claim_daily_bonus_callback',
    'check_bonus_eligibility',
    'bonus_info_command',
    'grant_bonus',
    'no_bonus_callback',
]