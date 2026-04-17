# telegram-bot/bot/handlers/contact.py
"""Contact center handler with working channel and group buttons"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.db.repository.user_repo import UserRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import menu
from bot.config import config
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

logger = logging.getLogger(__name__)


async def contact_center(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show contact and support information with clickable buttons"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Log that user accessed contact center
    logger.info(f"User {telegram_id} accessed contact center")
    
    # Create inline keyboard with channel and group buttons
    keyboard = []
    
    # Support Channel Button
    if config.SUPPORT_CHANNEL_LINK:
        keyboard.append([
            InlineKeyboardButton(
                f"{get_emoji('channel')} Official Channel", 
                url=config.SUPPORT_CHANNEL_LINK
            )
        ])
    else:
        logger.warning("SUPPORT_CHANNEL_LINK not set in config")
    
    # Support Group Button
    if config.SUPPORT_GROUP_LINK:
        keyboard.append([
            InlineKeyboardButton(
                f"{get_emoji('group')} Support Group", 
                url=config.SUPPORT_GROUP_LINK
            )
        ])
    else:
        logger.warning("SUPPORT_GROUP_LINK not set in config")
    
    # Admin Contact Button (always show as fallback)
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('admin')} Contact Admin", 
            callback_data="contact_admin"
        )
    ])
    
    # Back to Menu Button
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('back')} Back to Menu", 
            callback_data="back_to_menu"
        )
    ])
    
    # Prepare contact message
    contact_text = (
        f"{get_emoji('support')} *{TEXTS[lang]['contact_title']}*\n\n"
        f"{get_emoji('info')} Choose an option below:\n\n"
        f"• 📢 **Channel**: Updates and announcements\n"
        f"• 👥 **Group**: Get help from community\n"
        f"• 👑 **Admin**: Direct message to support team\n\n"
        f"{get_emoji('clock')} Response time: Usually within 24 hours"
    )
    
    # If both links are missing, show a different message
    if not config.SUPPORT_CHANNEL_LINK and not config.SUPPORT_GROUP_LINK:
        contact_text = (
            f"{get_emoji('support')} *Contact Support*\n\n"
            f"{get_emoji('info')} Official channels are being set up.\n\n"
            f"{get_emoji('admin')} Please use the **Contact Admin** button below to reach support directly.\n\n"
            f"{get_emoji('clock')} Response time: Usually within 24 hours"
        )
    
    await update.message.reply_text(
        contact_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def contact_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contact admin button - forward message to admin"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user_obj = query.from_user
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Store that user wants to contact admin
    context.user_data['contacting_admin'] = True
    
    # Create cancel keyboard
    cancel_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_emoji('cancel')} Cancel", callback_data="cancel_contact")]
    ])
    
    await query.edit_message_text(
        f"{get_emoji('admin')} *Contact Admin*\n\n"
        f"Please type your message below.\n"
        f"The admin will respond to you as soon as possible.\n\n"
        f"{get_emoji('info')} You can send:\n"
        f"• Questions about the game\n"
        f"• Deposit/withdrawal issues\n"
        f"• Bug reports\n"
        f"• Feature requests\n\n"
        f"{get_emoji('warning')} Please do not send spam or abusive messages.",
        reply_markup=cancel_keyboard,
        parse_mode='Markdown'
    )
    
    logger.info(f"User {telegram_id} initiated admin contact")


async def handle_contact_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward user message to admin when in contact mode"""
    if not context.user_data.get('contacting_admin'):
        return False
    
    telegram_id = update.effective_user.id
    user_obj = update.effective_user
    message_text = update.message.text
    
    # Get user info
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Create response keyboard for admin
    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{get_emoji('reply')} Reply to User", 
                callback_data=f"reply_user_{telegram_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('check')} Mark Resolved", 
                callback_data=f"resolve_ticket_{telegram_id}"
            )
        ]
    ])
    
    # Forward to admin
    await context.bot.send_message(
        chat_id=config.ADMIN_CHAT_ID,
        text=(
            f"{get_emoji('support')} *NEW SUPPORT TICKET*\n\n"
            f"{get_emoji('user')} User: {user_obj.first_name} {user_obj.last_name or ''}\n"
            f"{get_emoji('id')} ID: `{telegram_id}`\n"
            f"{get_emoji('user')} Username: @{user_obj.username or 'N/A'}\n\n"
            f"{get_emoji('message')} *Message:*\n{message_text}\n\n"
            f"{get_emoji('clock')} Sent: {update.message.date}"
        ),
        reply_markup=admin_keyboard,
        parse_mode='Markdown'
    )
    
    # Confirm to user
    await update.message.reply_text(
        f"{get_emoji('success')} *Message Sent!*\n\n"
        f"Your message has been forwarded to support.\n"
        f"You will receive a response here as soon as possible.\n\n"
        f"{get_emoji('info')} Ticket ID: `{telegram_id}_{update.message.date.timestamp()}`\n\n"
        f"Use /contact to send another message.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    
    # Clear contact mode
    context.user_data['contacting_admin'] = False
    
    logger.info(f"Support ticket from {telegram_id}: {message_text[:50]}...")
    
    return True


async def cancel_contact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel contact mode"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    context.user_data['contacting_admin'] = False
    
    await query.edit_message_text(
        f"{get_emoji('warning')} Contact cancelled.\n\n"
        f"Use /contact if you need help later.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    
    logger.info(f"User {telegram_id} cancelled contact")


async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu from contact center"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    await query.edit_message_text(
        f"{get_emoji('back')} Returning to main menu...",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )


# Admin reply handler (to be added to admin_commands.py)
async def admin_reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               user_id: int, reply_text: str):
    """Send reply from admin to user"""
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"{get_emoji('admin')} *Support Response*\n\n"
                f"{reply_text}\n\n"
                f"{get_emoji('info')} Reply to this message to continue the conversation."
            ),
            parse_mode='Markdown'
        )
        
        # Log the reply
        logger.info(f"Admin replied to user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to send reply to user {user_id}: {e}")


# Export all
__all__ = [
    'contact_center',
    'contact_admin_callback',
    'handle_contact_message',
    'cancel_contact_callback',
    'back_to_menu_callback',
    'admin_reply_to_user',
]