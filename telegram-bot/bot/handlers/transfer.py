# telegram-bot/bot/handlers/transfer.py
# Estif Bingo 24/7 - Balance Transfer Between Players
# Supported: Safaricom (Kenya) and Ethio Telecom (Ethiopia) phone numbers

import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.transfer_repo import TransferRepository
from bot.db.repository.audit_repo import AuditRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import menu
from bot.config import config
from bot.utils.validators import validate_amount, validate_phone_number
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

# Conversation states
PHONE_NUMBER = 1
AMOUNT = 2
CONFIRMATION = 3

# Transfer fee percentage (optional, set to 0 for no fee)
TRANSFER_FEE_PERCENT = getattr(config, 'TRANSFER_FEE_PERCENT', 0)

logger = logging.getLogger(__name__)


async def transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start balance transfer process"""
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
    
    if balance <= 0:
        await update.message.reply_text(
            f"{get_emoji('error')} *Insufficient balance for transfer*\n\n"
            f"Your balance: `{balance:.2f}` ETB\n\n"
            f"{get_emoji('deposit')} Use /deposit to add funds.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Reset user data for new transfer
    context.user_data['transfer_step'] = 'phone'
    
    # Create keyboard with cancel option
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_emoji('cancel')} Cancel Transfer", callback_data="cancel_transfer")]
    ])
    
    await update.message.reply_text(
        f"{get_emoji('transfer')} *Balance Transfer*\n\n"
        f"Your balance: `{balance:.2f}` ETB\n"
        f"Transfer fee: `{TRANSFER_FEE_PERCENT}`% (if applicable)\n\n"
        f"Please enter the **receiver's phone number**:\n\n"
        f"Supported formats:\n"
        f"• Ethio Telecom (Ethiopia): `0912345678` or `+251912345678`\n"
        f"• Safaricom (Kenya): `0712345678` or `+254712345678`\n\n"
        f"{get_emoji('info')} The receiver must be a registered user.",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return PHONE_NUMBER


async def transfer_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process receiver phone number entry"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    phone_input = update.message.text.strip()
    
    # Validate phone number format
    is_valid, normalized_phone, carrier = validate_phone_number(phone_input, return_carrier=True)
    
    if not is_valid:
        await update.message.reply_text(
            f"{get_emoji('error')} Invalid phone number format.\n\n"
            f"Please enter a valid phone number:\n"
            f"• Ethio Telecom: `0912345678` or `+251912345678`\n"
            f"• Safaricom: `0712345678` or `+254712345678`\n\n"
            f"Example: `0912345678`",
            parse_mode='Markdown'
        )
        return PHONE_NUMBER
    
    # Check if receiver exists and is registered
    receiver = await UserRepository.get_by_phone(normalized_phone)
    
    if not receiver:
        await update.message.reply_text(
            f"{get_emoji('error')} *Receiver not found*\n\n"
            f"The phone number `{normalized_phone}` is not registered in our system.\n\n"
            f"{get_emoji('info')} Ask your friend to register using /register first.\n\n"
            f"Please enter a different phone number or /cancel:",
            parse_mode='Markdown'
        )
        return PHONE_NUMBER
    
    if not receiver.get('registered'):
        await update.message.reply_text(
            f"{get_emoji('error')} *Receiver not fully registered*\n\n"
            f"The user with phone `{normalized_phone}` has not completed registration.\n\n"
            f"Please ask them to complete registration first.\n\n"
            f"Enter a different phone number or /cancel:",
            parse_mode='Markdown'
        )
        return PHONE_NUMBER
    
    receiver_id = receiver['telegram_id']
    
    # Prevent self-transfer
    if receiver_id == telegram_id:
        await update.message.reply_text(
            f"{get_emoji('error')} *Self-transfer not allowed*\n\n"
            f"You cannot transfer funds to yourself.\n\n"
            f"Please enter a different phone number:",
            parse_mode='Markdown'
        )
        return PHONE_NUMBER
    
    # Store receiver info
    context.user_data['receiver_phone'] = normalized_phone
    context.user_data['receiver_id'] = receiver_id
    context.user_data['receiver_name'] = receiver.get('first_name', 'User')
    context.user_data['receiver_carrier'] = carrier
    context.user_data['transfer_step'] = 'amount'
    
    # Get sender balance
    from bot.api.balance_ops import get_balance
    sender_balance = await get_balance(telegram_id)
    
    # Show amount entry
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_emoji('cancel')} Cancel", callback_data="cancel_transfer")]
    ])
    
    await update.message.reply_text(
        f"{get_emoji('user')} *Receiver Found!*\n\n"
        f"Name: `{context.user_data['receiver_name']}`\n"
        f"Phone: `{normalized_phone}`\n"
        f"Carrier: `{carrier}`\n\n"
        f"Your balance: `{sender_balance:.2f}` ETB\n"
        f"Transfer fee: `{TRANSFER_FEE_PERCENT}`%\n\n"
        f"Please enter the amount to transfer (Min: `{config.MIN_TRANSFER or 10}` ETB):",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return AMOUNT


async def transfer_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process transfer amount entry"""
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
    min_transfer = getattr(config, 'MIN_TRANSFER', 10)
    max_transfer = getattr(config, 'MAX_TRANSFER', 5000)
    
    if amount < min_transfer:
        await update.message.reply_text(
            f"{get_emoji('error')} Minimum transfer amount is `{min_transfer}` ETB.\n\n"
            f"Please enter a higher amount:",
            parse_mode='Markdown'
        )
        return AMOUNT
    
    if amount > max_transfer:
        await update.message.reply_text(
            f"{get_emoji('error')} Maximum transfer amount is `{max_transfer}` ETB.\n\n"
            f"Please enter a lower amount:",
            parse_mode='Markdown'
        )
        return AMOUNT
    
    # Check sender balance
    from bot.api.balance_ops import get_balance
    sender_balance = await get_balance(telegram_id)
    
    # Calculate fee
    fee = (amount * TRANSFER_FEE_PERCENT) / 100
    total_deduction = amount + fee
    
    if total_deduction > sender_balance:
        await update.message.reply_text(
            f"{get_emoji('error')} *Insufficient balance*\n\n"
            f"Transfer amount: `{amount:.2f}` ETB\n"
            f"Fee ({TRANSFER_FEE_PERCENT}%): `{fee:.2f}` ETB\n"
            f"Total deduction: `{total_deduction:.2f}` ETB\n"
            f"Your balance: `{sender_balance:.2f}` ETB\n"
            f"Shortfall: `{total_deduction - sender_balance:.2f}` ETB\n\n"
            f"Please enter a smaller amount:",
            parse_mode='Markdown'
        )
        return AMOUNT
    
    # Store amount and fee
    context.user_data['transfer_amount'] = amount
    context.user_data['transfer_fee'] = fee
    context.user_data['transfer_total'] = total_deduction
    
    # Show confirmation
    return await show_transfer_confirmation(update, context)


async def show_transfer_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show transfer confirmation details"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    amount = context.user_data.get('transfer_amount')
    fee = context.user_data.get('transfer_fee', 0)
    total = context.user_data.get('transfer_total', amount)
    receiver_name = context.user_data.get('receiver_name')
    receiver_phone = context.user_data.get('receiver_phone')
    receiver_carrier = context.user_data.get('receiver_carrier')
    
    # Get sender balance
    from bot.api.balance_ops import get_balance
    sender_balance = await get_balance(telegram_id)
    
    confirmation_text = (
        f"{get_emoji('warning')} *Confirm Transfer*\n\n"
        f"{get_emoji('arrow_right')} *From:* You\n"
        f"{get_emoji('arrow_left')} *To:* `{receiver_name}`\n"
        f"{get_emoji('phone')} *Phone:* `{receiver_phone}`\n"
        f"{get_emoji('signal')} *Carrier:* `{receiver_carrier}`\n\n"
        f"{get_emoji('money')} *Amount:* `{amount:.2f}` ETB\n"
    )
    
    if fee > 0:
        confirmation_text += f"{get_emoji('tax')} *Fee ({TRANSFER_FEE_PERCENT}%):* `{fee:.2f}` ETB\n"
    
    confirmation_text += (
        f"{get_emoji('money')} *Total Deduction:* `{total:.2f}` ETB\n"
        f"{get_emoji('balance')} *Your Balance After:* `{sender_balance - total:.2f}` ETB\n\n"
        f"{get_emoji('info')} *Receiver will receive:* `{amount:.2f}` ETB\n\n"
        f"Confirm this transfer?"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{get_emoji('check')} Confirm", callback_data="confirm_transfer"),
            InlineKeyboardButton(f"{get_emoji('cancel')} Cancel", callback_data="cancel_transfer")
        ]
    ])
    
    await update.message.reply_text(
        confirmation_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return CONFIRMATION


async def confirm_transfer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the transfer after confirmation"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user_obj = query.from_user
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Get transfer details
    amount = context.user_data.get('transfer_amount')
    fee = context.user_data.get('transfer_fee', 0)
    total = context.user_data.get('transfer_total', amount)
    receiver_id = context.user_data.get('receiver_id')
    receiver_phone = context.user_data.get('receiver_phone')
    receiver_name = context.user_data.get('receiver_name')
    
    if not all([amount, receiver_id]):
        await query.edit_message_text(
            f"{get_emoji('error')} Session expired. Please start over with /transfer.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    from bot.api.balance_ops import get_balance, deduct_balance, add_balance
    
    # Double-check balance
    sender_balance = await get_balance(telegram_id)
    
    if total > sender_balance:
        await query.edit_message_text(
            f"{get_emoji('error')} *Transfer Failed - Insufficient Balance*\n\n"
            f"Your balance has changed. Current balance: `{sender_balance:.2f}` ETB\n"
            f"Required: `{total:.2f}` ETB\n\n"
            f"Please start a new transfer with /transfer.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Generate transfer ID
    import uuid
    transfer_id = str(uuid.uuid4())[:8]
    
    try:
        # Deduct from sender
        await deduct_balance(
            telegram_id=telegram_id,
            amount=total,
            reason=f"transfer_out_{transfer_id}",
            metadata={
                'transfer_id': transfer_id,
                'receiver_id': receiver_id,
                'receiver_phone': receiver_phone,
                'amount': amount,
                'fee': fee
            }
        )
        
        # Add to receiver (only the amount, not the fee)
        await add_balance(
            telegram_id=receiver_id,
            amount=amount,
            reason=f"transfer_in_{transfer_id}",
            metadata={
                'transfer_id': transfer_id,
                'sender_id': telegram_id,
                'sender_phone': user_obj.username or str(telegram_id),
                'amount': amount
            }
        )
        
        # Record transfer in database
        await TransferRepository.create({
            'transfer_id': transfer_id,
            'sender_id': telegram_id,
            'receiver_id': receiver_id,
            'receiver_phone': receiver_phone,
            'amount': amount,
            'fee': fee,
            'total': total,
            'status': 'completed'
        })
        
        # Audit log
        await AuditRepository.log(
            user_id=telegram_id,
            action="transfer_sent",
            entity_type="transfer",
            entity_id=transfer_id,
            new_value={'amount': amount, 'receiver_id': receiver_id, 'fee': fee}
        )
        
        await AuditRepository.log(
            user_id=receiver_id,
            action="transfer_received",
            entity_type="transfer",
            entity_id=transfer_id,
            new_value={'amount': amount, 'sender_id': telegram_id}
        )
        
        # Get updated balances
        new_sender_balance = await get_balance(telegram_id)
        new_receiver_balance = await get_balance(receiver_id)
        
        # Notify receiver
        try:
            await context.bot.send_message(
                chat_id=receiver_id,
                text=(
                    f"{get_emoji('gift')} *Money Received!*\n\n"
                    f"You have received `{amount:.2f}` ETB from "
                    f"`{user_obj.first_name}` (@{user_obj.username or 'User'})\n\n"
                    f"{get_emoji('balance')} Your new balance: `{new_receiver_balance:.2f}` ETB\n\n"
                    f"{get_emoji('game')} Use /play to start playing!"
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Could not notify receiver {receiver_id}: {e}")
        
        # Confirm to sender
        fee_text = f"\n{get_emoji('tax')} Fee: `{fee:.2f}` ETB" if fee > 0 else ""
        
        await query.edit_message_text(
            f"{get_emoji('success')} *Transfer Successful!*\n\n"
            f"Transfer ID: `{transfer_id}`\n"
            f"Amount sent: `{amount:.2f}` ETB{fee_text}\n"
            f"Total deducted: `{total:.2f}` ETB\n"
            f"Receiver: `{receiver_name}`\n"
            f"Phone: `{receiver_phone}`\n\n"
            f"{get_emoji('balance')} Your new balance: `{new_sender_balance:.2f}` ETB\n\n"
            f"The receiver has been notified.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        
        logger.info(f"Transfer {transfer_id}: {amount} ETB from {telegram_id} to {receiver_id}")
        
    except Exception as e:
        logger.error(f"Transfer failed: {e}", exc_info=True)
        await query.edit_message_text(
            f"{get_emoji('error')} *Transfer Failed*\n\n"
            f"An error occurred while processing your transfer.\n"
            f"Please try again later or contact support.\n\n"
            f"Error: {str(e)[:100]}",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
    
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_transfer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel transfer process"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    await query.edit_message_text(
        f"{get_emoji('warning')} Transfer cancelled.\n\n"
        f"Use /transfer to start a new transfer.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel transfer via text command"""
    telegram_id = update.effective_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    await update.message.reply_text(
        f"{get_emoji('warning')} Transfer cancelled.\n\n"
        f"Use /transfer to start a new transfer.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    context.user_data.clear()
    return ConversationHandler.END


# Export all
__all__ = [
    'transfer',
    'transfer_phone_number',
    'transfer_amount',
    'confirm_transfer_callback',
    'cancel_transfer_callback',
    'cancel_transfer',
    'PHONE_NUMBER',
    'AMOUNT',
    'CONFIRMATION',
]