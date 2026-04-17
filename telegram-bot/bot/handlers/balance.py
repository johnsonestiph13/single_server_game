# telegram-bot/bot/handlers/balance.py
# Estif Bingo 24/7 - Balance Check Handler with Transaction History

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.transaction_repo import TransactionRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import menu
from bot.config import config
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

logger = logging.getLogger(__name__)


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's current balance and transaction summary"""
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
    
    from bot.api.balance_ops import get_balance
    
    # Get current balance
    current_balance = await get_balance(telegram_id)
    
    # Get transaction statistics
    stats = await TransactionRepository.get_stats(telegram_id)
    
    # Get recent transactions (last 5)
    recent_transactions = await TransactionRepository.get_recent(telegram_id, limit=5)
    
    # Format balance message
    balance_text = (
        f"{get_emoji('balance')} *YOUR BALANCE* {get_emoji('balance')}\n\n"
        f"{get_emoji('money')} Current Balance: `{current_balance:.2f}` ETB\n\n"
        f"{get_emoji('chart')} *Transaction Summary:*\n"
        f"• Total Deposited: `{stats.get('total_deposit', 0):.2f}` ETB\n"
        f"• Total Withdrawn: `{stats.get('total_withdrawal', 0):.2f}` ETB\n"
        f"• Total Won (Games): `{stats.get('total_won', 0):.2f}` ETB\n"
        f"• Total Spent (Cartelas): `{stats.get('total_spent', 0):.2f}` ETB\n"
        f"• Total Transfers Sent: `{stats.get('total_transfer_sent', 0):.2f}` ETB\n"
        f"• Total Transfers Received: `{stats.get('total_transfer_received', 0):.2f}` ETB\n\n"
    )
    
    # Add recent transactions if available
    if recent_transactions:
        balance_text += f"{get_emoji('history')} *Recent Transactions:*\n"
        for tx in recent_transactions:
            balance_text += format_transaction(tx)
        balance_text += f"\n{get_emoji('info')} Use /history to see full transaction history.\n\n"
    else:
        balance_text += f"{get_emoji('info')} No recent transactions.\n\n"
    
    # Add welcome bonus status if not claimed
    if not user.get('welcome_bonus_claimed', False):
        balance_text += f"{get_emoji('gift')} *Welcome Bonus Available!*\n"
        balance_text += f"Complete your registration to claim 30 ETB bonus.\n\n"
    
    # Create inline keyboard with action buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{get_emoji('history')} Full History", callback_data="view_full_history"),
            InlineKeyboardButton(f"{get_emoji('refresh')} Refresh", callback_data="refresh_balance")
        ],
        [
            InlineKeyboardButton(f"{get_emoji('deposit')} Deposit", callback_data="quick_deposit"),
            InlineKeyboardButton(f"{get_emoji('transfer')} Transfer", callback_data="quick_transfer")
        ],
        [
            InlineKeyboardButton(f"{get_emoji('back')} Back to Menu", callback_data="back_to_menu")
        ]
    ])
    
    await update.message.reply_text(
        balance_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    logger.info(f"User {telegram_id} checked balance: {current_balance:.2f} ETB")


def format_transaction(tx: dict) -> str:
    """Format a single transaction for display"""
    tx_type = tx.get('type', 'unknown')
    amount = tx.get('amount', 0)
    created_at = tx.get('created_at')
    
    # Format timestamp
    if created_at:
        if isinstance(created_at, datetime):
            time_str = created_at.strftime('%H:%M')
            date_str = created_at.strftime('%d/%m')
        else:
            time_str = str(created_at)[:5]
            date_str = str(created_at)[:10]
    else:
        time_str = "??:??"
        date_str = "??/??"
    
    # Emoji and prefix based on transaction type
    emoji_map = {
        'deposit': ('↓', get_emoji('deposit')),
        'withdrawal': ('↑', get_emoji('cashout')),
        'withdrawal_rejected': ('↺', get_emoji('warning')),
        'win': ('+', get_emoji('trophy')),
        'game_loss': ('-', get_emoji('game')),
        'cartela_purchase': ('-', get_emoji('cartela')),
        'transfer_sent': ('→', get_emoji('arrow_right')),
        'transfer_received': ('←', get_emoji('arrow_left')),
        'welcome_bonus': ('+', get_emoji('gift')),
        'admin_adjustment': ('±', get_emoji('admin')),
    }
    
    prefix, emoji = emoji_map.get(tx_type, ('•', get_emoji('info')))
    
    # Format amount with sign
    if prefix in ['+', '↓', '←']:
        amount_str = f"+{amount:.2f}"
    elif prefix in ['-', '↑', '→']:
        amount_str = f"-{amount:.2f}"
    else:
        amount_str = f"{amount:.2f}"
    
    # Get readable type name
    type_names = {
        'deposit': 'Deposit',
        'withdrawal': 'Withdrawal',
        'withdrawal_rejected': 'Withdrawal Rejected',
        'win': 'Game Win',
        'game_loss': 'Game Loss',
        'cartela_purchase': 'Cartela Purchase',
        'transfer_sent': 'Transfer Sent',
        'transfer_received': 'Transfer Received',
        'welcome_bonus': 'Welcome Bonus',
        'admin_adjustment': 'Admin Adjustment',
    }
    
    type_name = type_names.get(tx_type, tx_type.replace('_', ' ').title())
    
    return (
        f"`{date_str} {time_str}` "
        f"{emoji} *{type_name}*: "
        f"`{amount_str}` ETB\n"
    )


async def balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle balance menu callbacks"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    callback_data = query.data
    
    if callback_data == "refresh_balance":
        await show_balance_refresh(query, context, telegram_id, lang)
    
    elif callback_data == "view_full_history":
        await show_full_history(query, context, telegram_id, lang)
    
    elif callback_data == "quick_deposit":
        await query.edit_message_text(
            f"{get_emoji('deposit')} Redirecting to deposit...",
            parse_mode='Markdown'
        )
        # Import here to avoid circular import
        from bot.handlers.deposit import deposit
        await deposit(update, context)
    
    elif callback_data == "quick_transfer":
        await query.edit_message_text(
            f"{get_emoji('transfer')} Redirecting to transfer...",
            parse_mode='Markdown'
        )
        from bot.handlers.transfer import transfer
        await transfer(update, context)
    
    elif callback_data == "back_to_menu":
        await query.edit_message_text(
            f"{get_emoji('back')} Returning to main menu...",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )


async def show_balance_refresh(query, context, telegram_id: int, lang: str):
    """Show refreshed balance"""
    from bot.api.balance_ops import get_balance
    
    current_balance = await get_balance(telegram_id)
    
    await query.edit_message_text(
        f"{get_emoji('refresh')} *Balance Refreshed*\n\n"
        f"{get_emoji('money')} Current Balance: `{current_balance:.2f}` ETB\n\n"
        f"Use /balance to see full details.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_emoji('back')} Back", callback_data="back_to_balance")]
        ]),
        parse_mode='Markdown'
    )


async def show_full_history(query, context, telegram_id: int, lang: str, page: int = 1):
    """Show paginated transaction history"""
    from bot.api.balance_ops import get_balance
    from bot.db.repository.transaction_repo import TransactionRepository
    
    items_per_page = 10
    offset = (page - 1) * items_per_page
    
    # Get transactions with pagination
    transactions, total_count = await TransactionRepository.get_paginated(
        telegram_id, 
        limit=items_per_page, 
        offset=offset
    )
    
    current_balance = await get_balance(telegram_id)
    total_pages = (total_count + items_per_page - 1) // items_per_page
    
    if not transactions:
        await query.edit_message_text(
            f"{get_emoji('history')} *Transaction History*\n\n"
            f"No transactions found.\n\n"
            f"{get_emoji('money')} Current Balance: `{current_balance:.2f}` ETB",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{get_emoji('back')} Back", callback_data="back_to_balance")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    history_text = (
        f"{get_emoji('history')} *TRANSACTION HISTORY* {get_emoji('history')}\n\n"
        f"{get_emoji('money')} Current Balance: `{current_balance:.2f}` ETB\n"
        f"Page {page} of {total_pages} | Total: {total_count} transactions\n\n"
    )
    
    for tx in transactions:
        history_text += format_transaction(tx)
    
    # Create pagination buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"history_page_{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"history_page_{page + 1}"))
    
    keyboard = []
    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton(f"{get_emoji('back')} Back to Balance", callback_data="back_to_balance")])
    
    await query.edit_message_text(
        history_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def history_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle history pagination"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    page = int(query.data.split("_")[2])
    
    await show_full_history(query, context, telegram_id, lang, page)


async def back_to_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to balance view"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    from bot.api.balance_ops import get_balance
    current_balance = await get_balance(telegram_id)
    
    await query.edit_message_text(
        f"{get_emoji('balance')} *Your Balance*\n\n"
        f"{get_emoji('money')} Current Balance: `{current_balance:.2f}` ETB\n\n"
        f"Use /balance for full details.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )


# Export all
__all__ = [
    'balance',
    'balance_callback',
    'history_page_callback',
    'back_to_balance_callback',
]