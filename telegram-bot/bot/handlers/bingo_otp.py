# telegram-bot/bot/handlers/bingo_otp.py
# Estif Bingo 24/7 - OTP Generation and Verification for Game Web Login

import logging
import random
import string
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.auth_repo import AuthRepository
from bot.db.repository.audit_repo import AuditRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import menu
from bot.config import config
from bot.utils.logger import logger
from bot.utils.security import generate_otp, hash_otp
from bot.texts.emojis import get_emoji

# Conversation states
WAITING_FOR_OTP = 1

# OTP settings
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 3

logger = logging.getLogger(__name__)


async def bingo_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Generate and send OTP for game web login.
    User requests OTP, system sends code via Telegram, user enters on web.
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
        return ConversationHandler.END
    
    # Check rate limiting - prevent OTP spam
    recent_otp = await AuthRepository.get_recent_otp(telegram_id, minutes=1)
    if recent_otp and len(recent_otp) >= 3:
        await update.message.reply_text(
            f"{get_emoji('warning')} *Too many OTP requests*\n\n"
            f"Please wait 1 minute before requesting another code.\n\n"
            f"{get_emoji('info')} You can also use the WebApp button from /play for instant access.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Generate OTP
    otp_code = generate_otp(length=OTP_LENGTH)
    otp_hash = hash_otp(otp_code)
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    # Store OTP in database
    await AuthRepository.create_otp(
        telegram_id=telegram_id,
        otp_hash=otp_hash,
        expires_at=expires_at,
        purpose="game_login"
    )
    
    # Create game URL with OTP (user will enter code on web)
    game_url = f"{config.BASE_URL}/advanced_bingo.html"
    
    # Create inline keyboard with game link and copy button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_emoji('game')} Open Game", url=game_url)],
        [InlineKeyboardButton(f"{get_emoji('copy')} Copy OTP", callback_data=f"copy_otp_{otp_code}")],
        [InlineKeyboardButton(f"{get_emoji('cancel')} Cancel", callback_data="cancel_otp")]
    ])
    
    # Send OTP to user
    await update.message.reply_text(
        f"{get_emoji('key')} *Game Login OTP*\n\n"
        f"Your one-time password for Bingo game login:\n\n"
        f"`{otp_code}`\n\n"
        f"*Valid for:* {OTP_EXPIRY_MINUTES} minutes\n"
        f"*Valid attempts:* {MAX_OTP_ATTEMPTS}\n\n"
        f"{get_emoji('info')} How to use:\n"
        f"1️⃣ Click the **Open Game** button below\n"
        f"2️⃣ Enter this code on the login screen\n"
        f"3️⃣ Start playing!\n\n"
        f"{get_emoji('warning')} Never share this code with anyone!",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    # Audit log
    await AuditRepository.log(
        user_id=telegram_id,
        action="otp_generated",
        entity_type="auth",
        entity_id=str(telegram_id),
        metadata={'purpose': 'game_login'}
    )
    
    logger.info(f"OTP generated for user {telegram_id}, expires at {expires_at}")
    
    # Store in context for verification
    context.user_data['otp_pending'] = True
    context.user_data['otp_expires'] = expires_at.timestamp()
    context.user_data['otp_attempts'] = 0
    
    return WAITING_FOR_OTP


async def verify_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verify OTP entered by user (this is called from the web app via API,
    but we also handle manual verification via Telegram for testing).
    """
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    if not context.user_data.get('otp_pending'):
        await update.message.reply_text(
            f"{get_emoji('error')} No active OTP request.\n\n"
            f"Use `/bingo` to generate a new code.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Get user input
    user_otp = update.message.text.strip()
    
    # Validate format
    if not user_otp.isdigit() or len(user_otp) != OTP_LENGTH:
        await update.message.reply_text(
            f"{get_emoji('error')} Invalid OTP format.\n\n"
            f"Please enter the {OTP_LENGTH}-digit code you received.\n"
            f"Example: `123456`\n\n"
            f"Type /cancel to abort.",
            parse_mode='Markdown'
        )
        return WAITING_FOR_OTP
    
    # Check expiry
    expires_at = context.user_data.get('otp_expires', 0)
    if datetime.utcnow().timestamp() > expires_at:
        await update.message.reply_text(
            f"{get_emoji('error')} OTP has expired.\n\n"
            f"Please use `/bingo` to generate a new code.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Check attempts
    attempts = context.user_data.get('otp_attempts', 0)
    if attempts >= MAX_OTP_ATTEMPTS:
        await update.message.reply_text(
            f"{get_emoji('error')} Too many failed attempts.\n\n"
            f"Please use `/bingo` to generate a new code.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Verify OTP
    otp_hash = hash_otp(user_otp)
    valid_otp = await AuthRepository.verify_otp(
        telegram_id=telegram_id,
        otp_hash=otp_hash,
        purpose="game_login"
    )
    
    if not valid_otp:
        # Increment attempts
        context.user_data['otp_attempts'] = attempts + 1
        remaining = MAX_OTP_ATTEMPTS - (attempts + 1)
        
        await update.message.reply_text(
            f"{get_emoji('error')} *Invalid OTP*\n\n"
            f"Remaining attempts: `{remaining}`\n\n"
            f"Please try again or use `/bingo` to get a new code.",
            parse_mode='Markdown'
        )
        return WAITING_FOR_OTP
    
    # OTP verified successfully
    # Mark OTP as used
    await AuthRepository.mark_otp_used(telegram_id, purpose="game_login")
    
    # Generate JWT for game session
    from bot.utils.security import generate_jwt_for_game
    jwt_token = await generate_jwt_for_game(telegram_id)
    
    # Create game URL with JWT
    game_url = f"{config.BASE_URL}/advanced_bingo.html?token={jwt_token}"
    
    # Clear context
    context.user_data.clear()
    
    # Audit log
    await AuditRepository.log(
        user_id=telegram_id,
        action="otp_verified",
        entity_type="auth",
        entity_id=str(telegram_id),
        metadata={'purpose': 'game_login'}
    )
    
    # Send success message with game link
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_emoji('game')} Play Now", url=game_url)]
    ])
    
    await update.message.reply_text(
        f"{get_emoji('success')} *OTP Verified!*\n\n"
        f"You have successfully authenticated.\n\n"
        f"Click the button below to start playing:\n\n"
        f"{get_emoji('link')} Or copy this link:\n`{game_url}`",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    logger.info(f"OTP verified for user {telegram_id}")
    
    return ConversationHandler.END


async def cancel_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel OTP verification process"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Clear context
    context.user_data.clear()
    
    await query.edit_message_text(
        f"{get_emoji('warning')} OTP verification cancelled.\n\n"
        f"Use `/bingo` to generate a new code or `/play` for instant access.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    
    logger.info(f"OTP cancelled for user {telegram_id}")


async def copy_otp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle copy OTP button - sends OTP again for easy copying"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    
    # Extract OTP from callback data
    otp_code = query.data.split("_")[2]
    
    # Send OTP as a separate message for easy copying
    await query.message.reply_text(
        f"{get_emoji('key')} *Your OTP Code:*\n\n"
        f"`{otp_code}`\n\n"
        f"Copy this code and paste it on the game login page.\n"
        f"Valid for {OTP_EXPIRY_MINUTES} minutes.",
        parse_mode='Markdown'
    )
    
    # Also show the original message was copied
    await query.edit_message_reply_markup(reply_markup=None)


async def resend_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resend OTP code (if user didn't receive or lost it)"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Check if there's an existing pending OTP
    pending_otp = await AuthRepository.get_pending_otp(telegram_id, purpose="game_login")
    
    if pending_otp:
        # Check if it's still valid
        if pending_otp['expires_at'] > datetime.utcnow():
            # Resend the same OTP (but don't reveal it here - user must use /bingo again)
            await update.message.reply_text(
                f"{get_emoji('info')} *OTP Already Active*\n\n"
                f"You have an active OTP that expires at `{pending_otp['expires_at'].strftime('%H:%M:%S')}`.\n\n"
                f"Use `/bingo` to generate a new code if needed.",
                parse_mode='Markdown'
            )
            return
    
    # Generate new OTP
    await bingo_otp(update, context)


# API function for web app to verify OTP (called via Flask API)
async def verify_otp_api(telegram_id: int, otp_code: str) -> dict:
    """
    Verify OTP for web app login (called from API endpoint).
    Returns JWT token if successful.
    """
    try:
        # Validate OTP format
        if not otp_code.isdigit() or len(otp_code) != OTP_LENGTH:
            return {'success': False, 'error': 'Invalid OTP format'}
        
        # Verify OTP
        otp_hash = hash_otp(otp_code)
        valid = await AuthRepository.verify_otp(
            telegram_id=telegram_id,
            otp_hash=otp_hash,
            purpose="game_login"
        )
        
        if not valid:
            return {'success': False, 'error': 'Invalid or expired OTP'}
        
        # Mark OTP as used
        await AuthRepository.mark_otp_used(telegram_id, purpose="game_login")
        
        # Generate JWT
        from bot.utils.security import generate_jwt_for_game
        jwt_token = await generate_jwt_for_game(telegram_id)
        
        # Audit log
        await AuditRepository.log(
            user_id=telegram_id,
            action="otp_api_verified",
            entity_type="auth",
            entity_id=str(telegram_id),
            metadata={'purpose': 'game_login'}
        )
        
        logger.info(f"OTP API verified for user {telegram_id}")
        
        return {
            'success': True,
            'token': jwt_token,
            'user_id': telegram_id,
            'expires_in': 7200  # 2 hours in seconds
        }
        
    except Exception as e:
        logger.error(f"OTP API verification error for {telegram_id}: {e}")
        return {'success': False, 'error': 'Internal server error'}


# Export all
__all__ = [
    'bingo_otp',
    'verify_otp',
    'cancel_otp',
    'copy_otp_callback',
    'resend_otp',
    'verify_otp_api',
    'WAITING_FOR_OTP',
]