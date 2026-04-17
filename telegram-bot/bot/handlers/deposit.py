# telegram-bot/bot/handlers/deposit.py
# Estif Bingo 24/7 - Deposit Request Handler with Payment Method Selection

import logging
import uuid
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot.db.database import Database
from bot.db.repository.user_repo import UserRepository
from bot.db.repository.deposit_repo import DepositRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import menu, deposit_methods_keyboard
from bot.config import config
from bot.utils.security import generate_idempotency_key
from bot.utils.validators import validate_amount, validate_transaction_id
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

# Conversation states
AMOUNT = 1
TRANSACTION_ID = 2
SCREENSHOT = 3

logger = logging.getLogger(__name__)


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show deposit payment methods"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    if not user or not user.get('registered'):
        await update.message.reply_text(
            f"{get_emoji('error')} Please register first using /register",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Generate idempotency key for this deposit session
    context.user_data['deposit_idempotency_key'] = generate_idempotency_key()
    
    # Show deposit methods using keyboard from menu.py
    keyboard = deposit_methods_keyboard(lang)
    await update.message.reply_text(
        f"{get_emoji('deposit')} {TEXTS[lang]['deposit_select'].format(config.ACCOUNT_HOLDER)}",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return AMOUNT


async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment method selection callback"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # Handle method selection (deposit_cbe, deposit_telebirr, etc.)
    if callback_data.startswith("deposit_"):
        method = callback_data.split("_")[1].upper()
        
        # Map method names to keys
        method_map = {
            'CBE': 'CBE',
            'ABYSSINIA': 'ABBISINIYA',
            'ABBISINIYA': 'ABBISINIYA',
            'TELEBIRR': 'TELEBIRR',
            'MPESA': 'MPESA'
        }
        
        method_key = method_map.get(method.upper(), method.upper())
        
        if method_key not in config.PAYMENT_ACCOUNTS:
            await query.edit_message_text(
                f"{get_emoji('error')} Invalid payment method selected.",
                parse_mode='Markdown'
            )
            return AMOUNT
        
        account_number = config.PAYMENT_ACCOUNTS[method_key]
        telegram_id = query.from_user.id
        
        user = await UserRepository.get_by_telegram_id(telegram_id)
        lang = user.get('lang', 'en') if user else 'en'
        
        # Store deposit info in context
        context.user_data['deposit_method'] = method_key
        context.user_data['deposit_account'] = account_number
        
        await query.edit_message_text(
            f"{get_emoji('info')} {TEXTS[lang]['deposit_selected'].format(method_key, config.ACCOUNT_HOLDER, account_number)}\n\n"
            f"{get_emoji('money')} Please enter the amount you want to deposit (Min: {config.MIN_DEPOSIT} ETB, Max: {config.MAX_DEPOSIT} ETB):",
            parse_mode='Markdown'
        )
        return AMOUNT
    
    return AMOUNT


async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process deposit amount entry"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    text = update.message.text.strip()
    nums = re.findall(r"\d+\.?\d*", text)
    
    if not nums:
        await update.message.reply_text(
            f"{get_emoji('error')} Please enter a valid amount (e.g., 100)",
            parse_mode='Markdown'
        )
        return AMOUNT
    
    amount = float(nums[0])
    
    # Validate amount
    is_valid, error_msg = validate_amount(amount, config.MIN_DEPOSIT, config.MAX_DEPOSIT)
    if not is_valid:
        await update.message.reply_text(
            f"{get_emoji('error')} {error_msg}",
            parse_mode='Markdown'
        )
        return AMOUNT
    
    # Store amount
    context.user_data['deposit_amount'] = amount
    
    await update.message.reply_text(
        f"{get_emoji('success')} Amount: {amount} ETB accepted.\n\n"
        f"{get_emoji('receipt')} Please enter the **transaction ID/reference number** from your payment:\n\n"
        f"📋 Send to: `{context.user_data['deposit_account']}`\n"
        f"👤 Account Holder: `{config.ACCOUNT_HOLDER}`\n\n"
        f"⚠️ Example: `TRX-123456789` or `REF-20241234`",
        parse_mode='Markdown'
    )
    return TRANSACTION_ID


async def deposit_transaction_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process transaction ID entry"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    transaction_id = update.message.text.strip()
    
    # Validate transaction ID format
    if not validate_transaction_id(transaction_id):
        await update.message.reply_text(
            f"{get_emoji('error')} Invalid transaction ID format.\n\n"
            f"Please enter a valid reference number (alphanumeric, 5-50 characters).\n"
            f"Example: `TRX-123456789`",
            parse_mode='Markdown'
        )
        return TRANSACTION_ID
    
    # Check for duplicate transaction ID
    existing = await DepositRepository.get_by_transaction_id(transaction_id)
    if existing:
        await update.message.reply_text(
            f"{get_emoji('error')} This transaction ID has already been used.\n"
            f"Please check your payment status or use a different transaction ID.",
            parse_mode='Markdown'
        )
        return TRANSACTION_ID
    
    context.user_data['deposit_transaction_id'] = transaction_id
    
    await update.message.reply_text(
        f"{get_emoji('camera')} Transaction ID accepted.\n\n"
        f"Now, please send a **screenshot** of your payment confirmation.\n\n"
        f"Make sure the transaction ID is clearly visible in the screenshot.",
        parse_mode='Markdown'
    )
    return SCREENSHOT


async def deposit_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process deposit screenshot and create deposit request"""
    telegram_id = update.effective_user.id
    user = update.effective_user
    user_data = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user_data.get('lang', 'en') if user_data else 'en'
    
    # Check if we have a photo
    if not update.message.photo:
        await update.message.reply_text(
            f"{get_emoji('error')} Please send a screenshot of your payment confirmation.",
            parse_mode='Markdown'
        )
        return SCREENSHOT
    
    method = context.user_data.get('deposit_method')
    amount = context.user_data.get('deposit_amount')
    account = context.user_data.get('deposit_account')
    transaction_id = context.user_data.get('deposit_transaction_id')
    idempotency_key = context.user_data.get('deposit_idempotency_key')
    
    if not all([method, amount, account, transaction_id]):
        await update.message.reply_text(
            f"{get_emoji('error')} Session expired. Please start deposit again with /deposit",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Get the largest photo
    photo = update.message.photo[-1]
    photo_file_id = photo.file_id
    
    # Create deposit request in database
    request_id = await DepositRepository.create({
        'telegram_id': telegram_id,
        'amount': amount,
        'method': method,
        'account_number': account,
        'transaction_id': transaction_id,
        'photo_file_id': photo_file_id,
        'idempotency_key': idempotency_key,
        'status': 'pending',
        'created_at': datetime.utcnow()
    })
    
    # Generate approval token (signed)
    approval_token = generate_idempotency_key()[:16]
    context.bot_data[f'approval_token_{request_id}'] = approval_token
    
    # Send to admin with approval buttons
    admin_msg = (
        f"{get_emoji('deposit')} *NEW DEPOSIT REQUEST* #{request_id}\n\n"
        f"{get_emoji('user')} User: {user.first_name} (@{user.username or 'N/A'})\n"
        f"{get_emoji('id')} ID: `{telegram_id}`\n"
        f"{get_emoji('money')} Amount: `{amount}` ETB\n"
        f"{get_emoji('bank')} Method: `{method}`\n"
        f"{get_emoji('phone')} Account: `{account}`\n"
        f"{get_emoji('receipt')} Transaction ID: `{transaction_id}`\n\n"
        f"{get_emoji('info')} Use the buttons below to approve/reject:"
    )
    
    # Create inline keyboard for admin approval
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"✅ Approve #{request_id}",
                callback_data=f"approve_deposit_{request_id}_{approval_token}"
            ),
            InlineKeyboardButton(
                f"❌ Reject #{request_id}",
                callback_data=f"reject_deposit_{request_id}_{approval_token}"
            )
        ]
    ])
    
    await context.bot.send_message(
        chat_id=config.ADMIN_CHAT_ID,
        text=admin_msg,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    # Send photo separately (Telegram doesn't inline photos in messages)
    await context.bot.send_photo(
        chat_id=config.ADMIN_CHAT_ID,
        photo=photo_file_id,
        caption=f"📸 Deposit proof from {user.first_name} (@{user.username or 'N/A'})\nTransaction ID: {transaction_id}"
    )
    
    # Confirm to user
    await update.message.reply_text(
        f"{get_emoji('success')} {TEXTS[lang]['deposit_sent']}\n\n"
        f"{get_emoji('clock')} Request ID: `#{request_id}`\n"
        f"{get_emoji('receipt')} Transaction ID: `{transaction_id}`\n"
        f"{get_emoji('info')} You will be notified once approved.\n\n"
        f"⚠️ Keep your transaction ID for reference.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    
    logger.info(f"Deposit request #{request_id} from {telegram_id}: {amount} ETB via {method}, TXID: {transaction_id}")
    
    # Clear flow data
    context.user_data.clear()
    
    return ConversationHandler.END


async def deposit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel deposit"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    await update.message.reply_text(
        f"{get_emoji('warning')} Deposit cancelled.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    context.user_data.clear()
    return ConversationHandler.END


# Admin approval handlers (to be added to admin_commands.py or as separate callbacks)
async def approve_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin approval of deposit via callback button"""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: approve_deposit_123_token
    parts = query.data.split('_')
    if len(parts) < 4:
        await query.edit_message_text("Invalid approval request.")
        return
    
    request_id = int(parts[2])
    provided_token = parts[3]
    
    # Verify token
    expected_token = context.bot_data.get(f'approval_token_{request_id}')
    if not expected_token or provided_token != expected_token:
        await query.edit_message_text("❌ Invalid or expired approval token.")
        return
    
    # Get deposit request
    deposit_request = await DepositRepository.get_by_id(request_id)
    if not deposit_request:
        await query.edit_message_text(f"❌ Deposit request #{request_id} not found.")
        return
    
    if deposit_request['status'] != 'pending':
        await query.edit_message_text(f"⚠️ Deposit request #{request_id} is already {deposit_request['status']}.")
        return
    
    # Update status to approved
    await DepositRepository.update_status(request_id, 'approved')
    
    # Add balance to user
    from bot.api.balance_ops import add_balance
    await add_balance(
        telegram_id=deposit_request['telegram_id'],
        amount=deposit_request['amount'],
        reason=f"deposit_{request_id}",
        metadata={'request_id': request_id, 'transaction_id': deposit_request['transaction_id']}
    )
    
    # Notify user
    user_lang = 'en'  # Fetch from user record
    await context.bot.send_message(
        chat_id=deposit_request['telegram_id'],
        text=(
            f"{get_emoji('success')} *DEPOSIT APPROVED!*\n\n"
            f"Your deposit of `{deposit_request['amount']}` ETB has been approved and added to your balance.\n"
            f"Request ID: `#{request_id}`\n"
            f"Transaction ID: `{deposit_request['transaction_id']}`\n\n"
            f"Thank you for playing!"
        ),
        parse_mode='Markdown'
    )
    
    # Update admin message
    await query.edit_message_text(
        f"{get_emoji('success')} Deposit request #{request_id} has been **APPROVED**.\n"
        f"Amount: {deposit_request['amount']} ETB added to user balance.",
        parse_mode='Markdown'
    )
    
    logger.info(f"Deposit #{request_id} approved by admin")


async def reject_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin rejection of deposit via callback button"""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data
    parts = query.data.split('_')
    if len(parts) < 4:
        await query.edit_message_text("Invalid rejection request.")
        return
    
    request_id = int(parts[2])
    provided_token = parts[3]
    
    # Verify token
    expected_token = context.bot_data.get(f'approval_token_{request_id}')
    if not expected_token or provided_token != expected_token:
        await query.edit_message_text("❌ Invalid or expired token.")
        return
    
    # Get deposit request
    deposit_request = await DepositRepository.get_by_id(request_id)
    if not deposit_request:
        await query.edit_message_text(f"❌ Deposit request #{request_id} not found.")
        return
    
    if deposit_request['status'] != 'pending':
        await query.edit_message_text(f"⚠️ Deposit request #{request_id} is already {deposit_request['status']}.")
        return
    
    # Update status to rejected
    await DepositRepository.update_status(request_id, 'rejected')
    
    # Notify user
    await context.bot.send_message(
        chat_id=deposit_request['telegram_id'],
        text=(
            f"{get_emoji('error')} *DEPOSIT REJECTED*\n\n"
            f"Your deposit request #{request_id} has been rejected.\n"
            f"Please contact support if you believe this is an error.\n\n"
            f"Support: {config.SUPPORT_CHANNEL_LINK}"
        ),
        parse_mode='Markdown'
    )
    
    # Update admin message
    await query.edit_message_text(
        f"{get_emoji('error')} Deposit request #{request_id} has been **REJECTED**.",
        parse_mode='Markdown'
    )
    
    logger.info(f"Deposit #{request_id} rejected by admin")


# Export all
__all__ = [
    'deposit',
    'deposit_callback',
    'deposit_amount',
    'deposit_transaction_id',
    'deposit_screenshot',
    'deposit_cancel',
    'approve_deposit_callback',
    'reject_deposit_callback',
    'AMOUNT',
    'TRANSACTION_ID',
    'SCREENSHOT',
]