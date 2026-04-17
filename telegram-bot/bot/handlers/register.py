# telegram-bot/bot/handlers/register.py
# Estif Bingo 24/7 - User Registration Handler with Phone Verification

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.auth_repo import AuthRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import main_menu_keyboard as menu
from bot.config import config
from bot.utils.crypto import encrypt_phone, decrypt_phone
from bot.utils.validators import is_valid_phone, normalize_phone
from bot.utils.security import generate_otp
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

# Conversation states
PHONE = 1
OTP_VERIFICATION = 2

# Welcome bonus amount (moved to config in production)
WELCOME_BONUS_AMOUNT = 30

logger = logging.getLogger(__name__)


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start registration process with phone number"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Check if already registered
    if user and user.get('registered'):
        await update.message.reply_text(
            TEXTS[lang]['already_registered'],
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Check if welcome bonus already claimed (prevent double bonus)
    if user and user.get('welcome_bonus_claimed'):
        await update.message.reply_text(
            f"{get_emoji('info')} You have already claimed your welcome bonus.\n"
            f"Use /play to start the game!",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Show phone number input options
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton(f"{get_emoji('phone')} Share Contact", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        f"{get_emoji('info')} {TEXTS[lang]['register_prompt']}\n\n"
        f"{get_emoji('warning')} Your phone number is encrypted and stored securely.",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return PHONE


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process contact sharing, complete registration, and give welcome bonus"""
    try:
        contact = update.message.contact
        
        if not contact:
            await update.message.reply_text(
                f"{get_emoji('error')} No contact received. Please use the share contact button or type your phone number manually.",
                parse_mode='Markdown'
            )
            return PHONE
        
        telegram_id = update.effective_user.id
        user_obj = update.effective_user
        phone_number = contact.phone_number
        
        # Validate and normalize phone number
        if not is_valid_phone(phone_number):
            phone_number = normalize_phone(phone_number)
            if not is_valid_phone(phone_number):
                await update.message.reply_text(
                    f"{get_emoji('error')} Invalid phone number format. Please try again.",
                    parse_mode='Markdown'
                )
                return PHONE
        
        # Check if phone is already registered to another account
        encrypted_phone = encrypt_phone(phone_number)
        existing_user = await UserRepository.get_by_encrypted_phone(encrypted_phone)
        
        if existing_user and existing_user['telegram_id'] != telegram_id:
            await update.message.reply_text(
                f"{get_emoji('error')} This phone number is already registered to another account.\n\n"
                f"If this is a mistake, please contact support.",
                parse_mode='Markdown'
            )
            return PHONE
        
        # Get or create user
        user = await UserRepository.get_by_telegram_id(telegram_id)
        lang = user.get('lang', 'en') if user else 'en'
        
        if user:
            # Update existing user
            await UserRepository.update(
                telegram_id,
                phone_encrypted=encrypted_phone,
                registered=True,
                username=user_obj.username or "",
                first_name=user_obj.first_name or "",
                last_name=user_obj.last_name or ""
            )
            
            # Give welcome bonus only if not already claimed
            if not user.get('welcome_bonus_claimed'):
                from bot.api.balance_ops import add_balance
                await add_balance(
                    telegram_id=telegram_id,
                    amount=WELCOME_BONUS_AMOUNT,
                    reason="welcome_bonus",
                    metadata={"phone": phone_number}
                )
                await UserRepository.mark_welcome_bonus_claimed(telegram_id)
                
                await update.message.reply_text(
                    f"{get_emoji('gift')} *Welcome Bonus!*\n\n"
                    f"You received `{WELCOME_BONUS_AMOUNT}` ETB welcome bonus!",
                    parse_mode='Markdown'
                )
        else:
            # Create new user
            await UserRepository.create(
                telegram_id=telegram_id,
                username=user_obj.username or "",
                first_name=user_obj.first_name or "",
                last_name=user_obj.last_name or "",
                phone_encrypted=encrypted_phone,
                lang=lang,
                registered=True,
                welcome_bonus_claimed=True
            )
            
            # Add welcome bonus
            from bot.api.balance_ops import add_balance
            await add_balance(
                telegram_id=telegram_id,
                amount=WELCOME_BONUS_AMOUNT,
                reason="welcome_bonus",
                metadata={"phone": phone_number}
            )
            
            await update.message.reply_text(
                f"{get_emoji('gift')} *Welcome Bonus!*\n\n"
                f"You received `{WELCOME_BONUS_AMOUNT}` ETB welcome bonus!",
                parse_mode='Markdown'
            )
        
        # Get updated balance
        from bot.api.balance_ops import get_balance
        new_balance = await get_balance(telegram_id)
        
        # Send success message
        await update.message.reply_text(
            f"{get_emoji('success')} *Registration Successful!*\n\n"
            f"{get_emoji('phone')} Phone: `{phone_number[-4:]}` (last 4 digits)\n"
            f"{get_emoji('money')} Balance: `{new_balance:.2f}` ETB\n\n"
            f"{get_emoji('game')} Use /play to start playing!",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        
        # Notify admin (without full phone number for privacy)
        await context.bot.send_message(
            chat_id=config.ADMIN_CHAT_ID,
            text=f"{get_emoji('new')} *NEW REGISTRATION*\n"
                 f"{get_emoji('user')} Name: {user_obj.first_name} {user_obj.last_name or ''}\n"
                 f"{get_emoji('phone')} Phone: `****{phone_number[-4:]}`\n"
                 f"{get_emoji('id')} ID: `{telegram_id}`\n"
                 f"{get_emoji('gift')} Welcome Bonus: `{WELCOME_BONUS_AMOUNT}` ETB",
            parse_mode='Markdown'
        )
        
        logger.info(f"New user registered: {telegram_id} - {user_obj.first_name} - phone: ****{phone_number[-4:]}")
        
        # Clear any conversation data
        context.user_data.clear()
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in handle_contact: {e}", exc_info=True)
        await update.message.reply_text(
            f"{get_emoji('error')} Error processing registration. Please try again.\n\n"
            f"If the problem persists, contact support.",
            parse_mode='Markdown'
        )
        return PHONE


async def register_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process phone number input (manual entry without contact button)"""
    telegram_id = update.effective_user.id
    user_obj = update.effective_user
    phone = update.message.text.strip()
    
    # Validate phone format
    if not is_valid_phone(phone):
        await update.message.reply_text(
            f"{get_emoji('error')} Invalid phone number format.\n\n"
            f"Please enter a valid Ethiopian phone number (09XXXXXXXX or 07XXXXXXXX):\n\n"
            f"Example: `0912345678`\n\n"
            f"Or use the share contact button for automatic entry.",
            parse_mode='Markdown'
        )
        return PHONE
    
    phone = normalize_phone(phone)
    
    # Encrypt phone number
    encrypted_phone = encrypt_phone(phone)
    
    # Check if phone already registered
    existing_user = await UserRepository.get_by_encrypted_phone(encrypted_phone)
    if existing_user and existing_user['telegram_id'] != telegram_id:
        await update.message.reply_text(
            f"{get_emoji('error')} This phone number is already registered to another account.",
            parse_mode='Markdown'
        )
        return PHONE
    
    # Get or create user
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    if user:
        await UserRepository.update(
            telegram_id,
            phone_encrypted=encrypted_phone,
            registered=True
        )
        
        if not user.get('welcome_bonus_claimed'):
            from bot.api.balance_ops import add_balance
            await add_balance(telegram_id, WELCOME_BONUS_AMOUNT, "welcome_bonus")
            await UserRepository.mark_welcome_bonus_claimed(telegram_id)
            await update.message.reply_text(
                f"{get_emoji('gift')} *Welcome Bonus!*\n\nYou received `{WELCOME_BONUS_AMOUNT}` ETB!",
                parse_mode='Markdown'
            )
    else:
        await UserRepository.create(
            telegram_id=telegram_id,
            username=user_obj.username or "",
            first_name=user_obj.first_name or "",
            last_name=user_obj.last_name or "",
            phone_encrypted=encrypted_phone,
            lang=lang,
            registered=True,
            welcome_bonus_claimed=True
        )
        from bot.api.balance_ops import add_balance
        await add_balance(telegram_id, WELCOME_BONUS_AMOUNT, "welcome_bonus")
        await update.message.reply_text(
            f"{get_emoji('gift')} *Welcome Bonus!*\n\nYou received `{WELCOME_BONUS_AMOUNT}` ETB!",
            parse_mode='Markdown'
        )
    
    from bot.api.balance_ops import get_balance
    new_balance = await get_balance(telegram_id)
    
    await update.message.reply_text(
        f"{get_emoji('success')} *Registration Successful!*\n\n"
        f"{get_emoji('phone')} Phone: `{phone[-4:]}` (last 4 digits)\n"
        f"{get_emoji('money')} Balance: `{new_balance:.2f}` ETB\n\n"
        f"{get_emoji('game')} Use /play to start playing!",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    
    await context.bot.send_message(
        chat_id=config.ADMIN_CHAT_ID,
        text=f"{get_emoji('new')} *NEW REGISTRATION*\n"
             f"{get_emoji('user')} Name: {user_obj.first_name} {user_obj.last_name or ''}\n"
             f"{get_emoji('phone')} Phone: `****{phone[-4:]}`\n"
             f"{get_emoji('id')} ID: `{telegram_id}`\n"
             f"{get_emoji('gift')} Welcome Bonus: `{WELCOME_BONUS_AMOUNT}` ETB",
        parse_mode='Markdown'
    )
    
    logger.info(f"New user registered: {telegram_id} - {user_obj.first_name}")
    
    context.user_data.clear()
    return ConversationHandler.END


async def register_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel registration"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    await update.message.reply_text(
        f"{get_emoji('warning')} Registration cancelled. Use /register to try again.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    context.user_data.clear()
    return ConversationHandler.END


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send game link with authentication code (JWT instead of simple code)"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    if not user or not user.get('registered'):
        await update.message.reply_text(
            f"{get_emoji('error')} Please register first using /register",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    try:
        # Generate JWT instead of simple OTP (more secure)
        from bot.utils.security import generate_jwt_for_game
        jwt_token = await generate_jwt_for_game(telegram_id)
        
        # Use BASE_URL instead of GAME_WEB_URL
        game_url = f"{config.BASE_URL}/advanced_bingo.html?token={jwt_token}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_emoji('game')} Play Now {get_emoji('game')}", url=game_url)]
        ])
        
        await update.message.reply_text(
            f"{get_emoji('game')} *Click the button below to start playing!*\n\n"
            f"{get_emoji('info')} You will be automatically logged in.\n"
            f"{get_emoji('link')} Or copy this link:\n`{game_url}`",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        logger.info(f"Game link generated for user {telegram_id}")
        
    except Exception as e:
        logger.error(f"Play error: {e}", exc_info=True)
        await update.message.reply_text(
            f"{get_emoji('error')} Failed to generate game link. Please try again later.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )


# Export all
__all__ = [
    'register',
    'handle_contact',
    'register_phone',
    'register_cancel',
    'play',
    'PHONE',
    'OTP_VERIFICATION',
]