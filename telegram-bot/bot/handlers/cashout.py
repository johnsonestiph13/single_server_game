# telegram-bot/bot/handlers/cashout.py
# Estif Bingo 24/7 - Withdrawal/Cashout Request Handler
# Supported methods: CBE, Abyssinia, Telebirr, M-Pesa

import logging
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.withdrawal_repo import WithdrawalRepository
from bot.db.repository.audit_repo import AuditRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import menu
from bot.config import config
from bot.utils.crypto import encrypt_bank_details
from bot.utils.validators import validate_amount, validate_phone_number, validate_account_number
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

# Conversation states
AMOUNT = 1
METHOD = 2
ACCOUNT_DETAILS = 3
CONFIRMATION = 4

# Withdrawal limits
MIN_WITHDRAWAL = getattr(config, 'MIN_WITHDRAWAL', 50)
MAX_WITHDRAWAL = getattr(config, 'MAX_WITHDRAWAL', 10000)

# Supported methods
WITHDRAWAL_METHODS = {
    'CBE': {
        'name': 'Commercial Bank of Ethiopia (CBE)',
        'emoji': '🏦',
        'fields': ['account_number', 'account_holder']
    },
    'ABYSSINIA': {
        'name': 'Abyssinia Bank',
        'emoji': '🏦',
        'fields': ['account_number', 'account_holder']
    },
    'TELEBIRR': {
        'name': 'Telebirr',
        'emoji': '📱',
        'fields': ['phone_number', 'account_holder']
    },
    'MPESA': {
        'name': 'M-Pesa',
        'emoji': '📱',
        'fields': ['phone_number', 'account_holder']
    }
}

logger = logging.getLogger(__name__)


async def cashout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start withdrawal process"""
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
    
    # Check if user has sufficient balance
    from bot.api.balance_ops import get_balance
    balance = await get_balance(telegram_id)
    
    if balance < MIN_WITHDRAWAL:
        await update.message.reply_text(
            f"{get_emoji('error')} *Insufficient balance for withdrawal*\n\n"
            f"Minimum withdrawal amount: `{MIN_WITHDRAWAL}` ETB\n"
            f"Your current balance: `{balance:.2f}` ETB\n\n"
            f"{get_emoji('deposit')} Use /deposit to add funds.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Generate withdrawal session ID
    context.user_data['withdrawal_session'] = str(uuid.uuid4())
    
    # Ask for amount
    await update.message.reply_text(
        f"{get_emoji('money')} *Withdrawal Request*\n\n"
        f"Your balance: `{balance:.2f}` ETB\n\n"
        f"Please enter the amount you want to withdraw:\n"
        f"• Minimum: `{MIN_WITHDRAWAL}` ETB\n"
        f"• Maximum: `{MAX_WITHDRAWAL}` ETB\n\n"
        f"{get_emoji('info')} Enter amount in ETB (e.g., `100` or `500.50`):",
        parse_mode='Markdown'
    )
    return AMOUNT


async def withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process withdrawal amount entry"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    text = update.message.text.strip()
    
    # Parse amount
    try:
        amount = float(text.replace(',', ''))
    except ValueError:
        await update.message.reply_text(
            f"{get_emoji('error')} Please enter a valid number (e.g., `100` or `500.50`).",
            parse_mode='Markdown'
        )
        return AMOUNT
    
    # Validate amount
    from bot.api.balance_ops import get_balance
    balance = await get_balance(telegram_id)
    
    if amount < MIN_WITHDRAWAL:
        await update.message.reply_text(
            f"{get_emoji('error')} Minimum withdrawal amount is `{MIN_WITHDRAWAL}` ETB.\n\n"
            f"Please enter a higher amount.",
            parse_mode='Markdown'
        )
        return AMOUNT
    
    if amount > MAX_WITHDRAWAL:
        await update.message.reply_text(
            f"{get_emoji('error')} Maximum withdrawal amount is `{MAX_WITHDRAWAL}` ETB.\n\n"
            f"Please enter a lower amount.",
            parse_mode='Markdown'
        )
        return AMOUNT
    
    if amount > balance:
        await update.message.reply_text(
            f"{get_emoji('error')} Insufficient balance.\n\n"
            f"Your balance: `{balance:.2f}` ETB\n"
            f"Requested: `{amount:.2f}` ETB\n\n"
            f"Please enter a smaller amount.",
            parse_mode='Markdown'
        )
        return AMOUNT
    
    # Store amount
    context.user_data['withdrawal_amount'] = amount
    
    # Show withdrawal method selection
    keyboard = []
    for method_key, method_info in WITHDRAWAL_METHODS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{method_info['emoji']} {method_info['name']}", 
                callback_data=f"withdraw_method_{method_key.lower()}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(f"{get_emoji('cancel')} Cancel", callback_data="cancel_withdrawal")
    ])
    
    await update.message.reply_text(
        f"{get_emoji('bank')} *Select Withdrawal Method:*\n\n"
        f"Amount: `{amount:.2f}` ETB\n\n"
        f"Choose how you want to receive your funds:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return METHOD


async def withdrawal_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal method selection callback"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    callback_data = query.data
    
    if callback_data == "cancel_withdrawal":
        await query.edit_message_text(
            f"{get_emoji('warning')} Withdrawal cancelled.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Extract method
    if callback_data.startswith("withdraw_method_"):
        method_key = callback_data.split("_")[2].upper()
        
        if method_key not in WITHDRAWAL_METHODS:
            await query.edit_message_text(
                f"{get_emoji('error')} Invalid withdrawal method.",
                parse_mode='Markdown'
            )
            return METHOD
        
        method_info = WITHDRAWAL_METHODS[method_key]
        context.user_data['withdrawal_method'] = method_key
        context.user_data['withdrawal_method_name'] = method_info['name']
        
        # Store method-specific field requirements
        context.user_data['withdrawal_required_fields'] = method_info['fields']
        
        # Clear any existing details
        context.user_data['withdrawal_details'] = {}
        
        # Start asking for required fields
        return await ask_next_field(update, context, query)
    
    return METHOD


async def ask_next_field(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    """Ask for the next required field based on method"""
    telegram_id = update.effective_user.id if update.effective_user else query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    method_key = context.user_data.get('withdrawal_method')
    method_info = WITHDRAWAL_METHODS.get(method_key, {})
    required_fields = context.user_data.get('withdrawal_required_fields', [])
    collected_details = context.user_data.get('withdrawal_details', {})
    
    # Find the next field not yet collected
    for field in required_fields:
        if field not in collected_details:
            # Ask for this field
            field_prompts = {
                'account_number': f"{get_emoji('receipt')} Please enter your **account number**:",
                'account_holder': f"{get_emoji('user')} Please enter the **account holder name** (exactly as on the account):",
                'phone_number': f"{get_emoji('phone')} Please enter your **registered phone number** (e.g., `0912345678`):"
            }
            
            field_examples = {
                'account_number': "\n\nExample: `1000123456789`",
                'account_holder': "\n\nExample: `John Doe`",
                'phone_number': "\n\nExample: `0912345678`"
            }
            
            prompt = field_prompts.get(field, f"Please enter your {field.replace('_', ' ')}:")
            example = field_examples.get(field, "")
            
            if query:
                await query.edit_message_text(
                    f"{get_emoji('info')} *{method_info['name']} Withdrawal*\n\n"
                    f"Amount: `{context.user_data['withdrawal_amount']:.2f}` ETB\n\n"
                    f"{prompt}{example}\n\n"
                    f"{get_emoji('cancel')} Type /cancel to abort.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"{get_emoji('info')} *{method_info['name']} Withdrawal*\n\n"
                    f"Amount: `{context.user_data['withdrawal_amount']:.2f}` ETB\n\n"
                    f"{prompt}{example}\n\n"
                    f"{get_emoji('cancel')} Type /cancel to abort.",
                    parse_mode='Markdown'
                )
            
            # Store which field we're asking for
            context.user_data['current_field'] = field
            return ACCOUNT_DETAILS
    
    # All fields collected, show confirmation
    return await show_confirmation(update, context, query)


async def withdrawal_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process account details entry"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    current_field = context.user_data.get('current_field')
    value = update.message.text.strip()
    
    if not current_field:
        await update.message.reply_text(
            f"{get_emoji('error')} Session expired. Please start over with /cashout.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Validate based on field type
    is_valid = True
    error_msg = None
    
    if current_field == 'account_number':
        is_valid, error_msg = validate_account_number(value)
    elif current_field == 'phone_number':
        is_valid, error_msg = validate_phone_number(value)
    elif current_field == 'account_holder':
        if len(value) < 3 or len(value) > 100:
            is_valid = False
            error_msg = "Account holder name must be between 3 and 100 characters."
    
    if not is_valid:
        await update.message.reply_text(
            f"{get_emoji('error')} {error_msg or 'Invalid input.'}\n\nPlease try again:",
            parse_mode='Markdown'
        )
        return ACCOUNT_DETAILS
    
    # Store the value
    if 'withdrawal_details' not in context.user_data:
        context.user_data['withdrawal_details'] = {}
    context.user_data['withdrawal_details'][current_field] = value
    
    # Clear current field
    context.user_data['current_field'] = None
    
    # Ask for next field or show confirmation
    return await ask_next_field(update, context)


async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    """Show withdrawal confirmation and create request"""
    telegram_id = update.effective_user.id if update.effective_user else query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    amount = context.user_data.get('withdrawal_amount')
    method = context.user_data.get('withdrawal_method')
    method_name = context.user_data.get('withdrawal_method_name')
    details = context.user_data.get('withdrawal_details', {})
    
    # Format details for display
    details_text = ""
    for key, value in details.items():
        display_key = key.replace('_', ' ').title()
        # Mask sensitive info partially
        if key == 'account_number' and len(value) > 4:
            display_value = f"****{value[-4:]}"
        elif key == 'phone_number' and len(value) > 4:
            display_value = f"****{value[-4:]}"
        else:
            display_value = value
        details_text += f"• *{display_key}:* `{display_value}`\n"
    
    confirmation_text = (
        f"{get_emoji('warning')} *Please confirm your withdrawal details:*\n\n"
        f"{get_emoji('money')} *Amount:* `{amount:.2f}` ETB\n"
        f"{get_emoji('bank')} *Method:* `{method_name}`\n"
        f"{details_text}\n"
        f"{get_emoji('clock')} *Processing time:* 24-48 hours\n"
        f"{get_emoji('info')} *Note:* A small processing fee may apply.\n\n"
        f"Confirm your withdrawal request?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{get_emoji('check')} Confirm", callback_data="confirm_withdrawal"),
            InlineKeyboardButton(f"{get_emoji('cancel')} Cancel", callback_data="cancel_withdrawal")
        ]
    ])
    
    if query:
        await query.edit_message_text(
            confirmation_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            confirmation_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    return CONFIRMATION


async def confirm_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal confirmation and create withdrawal request"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user_obj = query.from_user
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    amount = context.user_data.get('withdrawal_amount')
    method = context.user_data.get('withdrawal_method')
    method_name = context.user_data.get('withdrawal_method_name')
    details = context.user_data.get('withdrawal_details', {})
    session_id = context.user_data.get('withdrawal_session')
    
    if not all([amount, method, details]):
        await query.edit_message_text(
            f"{get_emoji('error')} Session expired. Please start over with /cashout.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Check balance again before finalizing
    from bot.api.balance_ops import get_balance, deduct_balance
    balance = await get_balance(telegram_id)
    
    if amount > balance:
        await query.edit_message_text(
            f"{get_emoji('error')} Insufficient balance.\n\n"
            f"Your balance has changed. Current balance: `{balance:.2f}` ETB\n\n"
            f"Please start a new withdrawal request with /cashout.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Encrypt sensitive details
    encrypted_details = encrypt_bank_details(details)
    
    # Create withdrawal request in database
    withdrawal_id = await WithdrawalRepository.create({
        'telegram_id': telegram_id,
        'amount': amount,
        'method': method,
        'method_name': method_name,
        'details_encrypted': encrypted_details,
        'session_id': session_id,
        'status': 'pending',
        'created_at': datetime.utcnow()
    })
    
    # Deduct balance immediately (pending withdrawal)
    await deduct_balance(
        telegram_id=telegram_id,
        amount=amount,
        reason=f"withdrawal_{withdrawal_id}",
        metadata={'withdrawal_id': withdrawal_id, 'method': method}
    )
    
    # Audit log
    await AuditRepository.log(
        user_id=telegram_id,
        action="withdrawal_requested",
        entity_type="withdrawal",
        entity_id=str(withdrawal_id),
        new_value={'amount': amount, 'method': method}
    )
    
    # Prepare admin notification
    details_for_admin = ""
    for key, value in details.items():
        details_for_admin += f"• {key}: `{value}`\n"
    
    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{get_emoji('check')} Approve", callback_data=f"approve_withdrawal_{withdrawal_id}"),
            InlineKeyboardButton(f"{get_emoji('cancel')} Reject", callback_data=f"reject_withdrawal_{withdrawal_id}")
        ]
    ])
    
    # Notify admin
    await context.bot.send_message(
        chat_id=config.ADMIN_CHAT_ID,
        text=(
            f"{get_emoji('money')} *NEW WITHDRAWAL REQUEST* #{withdrawal_id}\n\n"
            f"{get_emoji('user')} User: {user_obj.first_name} (@{user_obj.username or 'N/A'})\n"
            f"{get_emoji('id')} ID: `{telegram_id}`\n"
            f"{get_emoji('money')} Amount: `{amount}` ETB\n"
            f"{get_emoji('bank')} Method: `{method_name}`\n\n"
            f"{get_emoji('receipt')} *Details:*\n{details_for_admin}\n"
            f"{get_emoji('clock')} Requested: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        ),
        reply_markup=admin_keyboard,
        parse_mode='Markdown'
    )
    
    # Confirm to user
    await query.edit_message_text(
        f"{get_emoji('success')} *Withdrawal Request Submitted!*\n\n"
        f"Request ID: `#{withdrawal_id}`\n"
        f"Amount: `{amount:.2f}` ETB\n"
        f"Method: `{method_name}`\n\n"
        f"{get_emoji('clock')} Processing time: 24-48 hours\n"
        f"{get_emoji('info')} You will be notified when your withdrawal is processed.\n\n"
        f"Contact support if you have any questions.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    
    logger.info(f"Withdrawal request #{withdrawal_id} created for user {telegram_id}: {amount} ETB via {method}")
    
    # Clear conversation data
    context.user_data.clear()
    
    return ConversationHandler.END


async def cancel_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel withdrawal process"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    await update.message.reply_text(
        f"{get_emoji('warning')} Withdrawal cancelled.\n\n"
        f"Use /cashout to start a new withdrawal request.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    context.user_data.clear()
    return ConversationHandler.END


# Admin approval callbacks (to be added to admin_commands.py)
async def approve_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin approval of withdrawal"""
    query = update.callback_query
    await query.answer()
    
    withdrawal_id = int(query.data.split("_")[2])
    
    # Get withdrawal request
    withdrawal = await WithdrawalRepository.get_by_id(withdrawal_id)
    if not withdrawal:
        await query.edit_message_text(f"❌ Withdrawal #{withdrawal_id} not found.")
        return
    
    if withdrawal['status'] != 'pending':
        await query.edit_message_text(f"⚠️ Withdrawal #{withdrawal_id} is already {withdrawal['status']}.")
        return
    
    # Update status
    await WithdrawalRepository.update_status(withdrawal_id, 'approved', admin_id=query.from_user.id)
    
    # Notify user
    await context.bot.send_message(
        chat_id=withdrawal['telegram_id'],
        text=(
            f"{get_emoji('success')} *WITHDRAWAL APPROVED!*\n\n"
            f"Request ID: `#{withdrawal_id}`\n"
            f"Amount: `{withdrawal['amount']:.2f}` ETB\n\n"
            f"Your funds will be sent to your selected account within 24 hours.\n"
            f"Contact support if you don't receive the funds."
        ),
        parse_mode='Markdown'
    )
    
    await query.edit_message_text(
        f"{get_emoji('success')} Withdrawal #{withdrawal_id} has been **APPROVED**.\n"
        f"User has been notified.",
        parse_mode='Markdown'
    )


async def reject_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin rejection of withdrawal"""
    query = update.callback_query
    await query.answer()
    
    withdrawal_id = int(query.data.split("_")[2])
    
    # Get withdrawal request
    withdrawal = await WithdrawalRepository.get_by_id(withdrawal_id)
    if not withdrawal:
        await query.edit_message_text(f"❌ Withdrawal #{withdrawal_id} not found.")
        return
    
    if withdrawal['status'] != 'pending':
        await query.edit_message_text(f"⚠️ Withdrawal #{withdrawal_id} is already {withdrawal['status']}.")
        return
    
    # Update status
    await WithdrawalRepository.update_status(withdrawal_id, 'rejected', admin_id=query.from_user.id)
    
    # Refund balance to user
    from bot.api.balance_ops import add_balance
    await add_balance(
        telegram_id=withdrawal['telegram_id'],
        amount=withdrawal['amount'],
        reason=f"withdrawal_rejected_{withdrawal_id}",
        metadata={'withdrawal_id': withdrawal_id}
    )
    
    # Notify user
    await context.bot.send_message(
        chat_id=withdrawal['telegram_id'],
        text=(
            f"{get_emoji('error')} *WITHDRAWAL REJECTED*\n\n"
            f"Request ID: `#{withdrawal_id}`\n"
            f"Amount: `{withdrawal['amount']:.2f}` ETB\n\n"
            f"Your withdrawal request was rejected. The amount has been returned to your balance.\n\n"
            f"Please contact support for more information."
        ),
        parse_mode='Markdown'
    )
    
    await query.edit_message_text(
        f"{get_emoji('error')} Withdrawal #{withdrawal_id} has been **REJECTED**.\n"
        f"User balance has been refunded.",
        parse_mode='Markdown'
    )


# Export all
__all__ = [
    'cashout',
    'withdrawal_amount',
    'withdrawal_method_callback',
    'withdrawal_details',
    'confirm_withdrawal_callback',
    'cancel_withdrawal',
    'approve_withdrawal_callback',
    'reject_withdrawal_callback',
    'AMOUNT',
    'METHOD',
    'ACCOUNT_DETAILS',
    'CONFIRMATION',
]