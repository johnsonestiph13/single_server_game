# telegram-bot/bot/handlers/invite.py
"""Invite friends handler with forwardable message (no referral bonus)"""

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


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send forwardable invite message with game link (no bonus)"""
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
    
    # Generate invite link WITHOUT referral parameter (no tracking, no bonus)
    # Use BASE_URL to construct the game URL
    invite_link = f"{config.BASE_URL}/advanced_bingo.html"
    
    # Create an inline keyboard with a share button
    share_url = (
        f"https://t.me/share/url?"
        f"url={invite_link}&"
        f"text={get_emoji('game')}%20Play%20Estif%20Bingo!%20"
        f"Choose%20cartelas%2C%20win%20real%20prizes!%20"
        f"Join%20now%20and%20get%2030%20ETB%20welcome%20bonus!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_emoji('share')} Share / Forward", url=share_url)],
        [InlineKeyboardButton(f"{get_emoji('copy')} Copy Link", callback_data="copy_invite_link")]
    ])
    
    # Store the invite link in context for copy functionality
    context.user_data['invite_link'] = invite_link
    
    # Send a message that can be easily forwarded
    await update.message.reply_text(
        f"{get_emoji('game')} *Invite Friends to Estif Bingo!* {get_emoji('game')}\n\n"
        f"Share this link with your friends:\n"
        f"`{invite_link}`\n\n"
        f"{get_emoji('info')} *How to invite:*\n"
        f"1️⃣ Copy the link above\n"
        f"2️⃣ Send it to any friend, group, or channel\n"
        f"3️⃣ Or use the **Share** button below\n\n"
        f"{get_emoji('gift')} *New players get:*\n"
        f"• 30 ETB welcome bonus (one‑time)\n"
        f"• Exciting real‑time bingo games\n"
        f"• Secure deposits and withdrawals\n\n"
        f"{get_emoji('info')} *Note:* No referral bonus – just share for fun!",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    logger.info(f"User {telegram_id} used /invite command")


async def copy_invite_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle copy invite link button (shows the link for manual copy)"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    invite_link = context.user_data.get('invite_link', f"{config.BASE_URL}/advanced_bingo.html")
    
    await query.edit_message_text(
        f"{get_emoji('copy')} *Your invite link:*\n\n"
        f"`{invite_link}`\n\n"
        f"{get_emoji('info')} You can copy this link and share it anywhere!\n\n"
        f"{get_emoji('arrow')} Use the **Share** button to quickly send to Telegram contacts.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_emoji('share')} Share", url=f"https://t.me/share/url?url={invite_link}&text=Join%20me%20in%20Estif%20Bingo!")],
            [InlineKeyboardButton(f"{get_emoji('back')} Back", callback_data="back_to_invite")]
        ])
    )


async def back_to_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main invite menu"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    invite_link = context.user_data.get('invite_link', f"{config.BASE_URL}/advanced_bingo.html")
    
    share_url = (
        f"https://t.me/share/url?"
        f"url={invite_link}&"
        f"text={get_emoji('game')}%20Play%20Estif%20Bingo!%20"
        f"Join%20now%20and%20get%2030%20ETB%20welcome%20bonus!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_emoji('share')} Share / Forward", url=share_url)],
        [InlineKeyboardButton(f"{get_emoji('copy')} Copy Link", callback_data="copy_invite_link")]
    ])
    
    await query.edit_message_text(
        f"{get_emoji('game')} *Invite Friends to Estif Bingo!* {get_emoji('game')}\n\n"
        f"Share this link with your friends:\n"
        f"`{invite_link}`\n\n"
        f"{get_emoji('info')} *How to invite:*\n"
        f"1️⃣ Copy the link above\n"
        f"2️⃣ Send it to any friend, group, or channel\n"
        f"3️⃣ Or use the **Share** button below\n\n"
        f"{get_emoji('gift')} *New players get:*\n"
        f"• 30 ETB welcome bonus (one‑time)\n"
        f"• Exciting real‑time bingo games\n"
        f"• Secure deposits and withdrawals\n\n"
        f"{get_emoji('info')} *Note:* No referral bonus – just share for fun!",
        parse_mode='Markdown',
        reply_markup=keyboard
    )


# Export all
__all__ = [
    'invite',
    'copy_invite_link_callback',
    'back_to_invite_callback',
]