# telegram-bot/bot/handlers/admin_commands.py
# Estif Bingo 24/7 - Admin Commands Handler
# Commands: /admin, /set_win_percent, /force_start, /force_stop, /set_sound_pack,
#           /search_player, /stats, /approve_deposit, /reject_deposit,
#           /approve_withdrawal, /reject_withdrawal, /broadcast, /maintenance
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.withdrawal_repo import WithdrawalRepository
from bot.db.repository.deposit_repo import DepositRepository
from bot.db.repository.game_repo import GameRepository
from bot.db.repository.audit_repo import AuditRepository
from bot.db.repository.transaction_repo import TransactionRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import menu, admin_menu
from bot.config import config
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

# Conversation states for broadcast
BROADCAST_MESSAGE = 1
BROADCAST_CONFIRM = 2

logger = logging.getLogger(__name__)


def is_admin(telegram_id: int) -> bool:
    """Check if user is admin"""
    return str(telegram_id) == str(config.ADMIN_CHAT_ID)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel with all available commands"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text(
            f"{get_emoji('error')} *Unauthorized*\n\n"
            f"You don't have permission to use admin commands.",
            parse_mode='Markdown'
        )
        return
    
    # Get system stats
    total_users = await UserRepository.count_registered()
    active_users = await UserRepository.count_active(last_hours=24)
    pending_withdrawals = await WithdrawalRepository.count_pending()
    pending_deposits = await DepositRepository.count_pending()
    current_round = await GameRepository.get_current_round()
    current_win_percent = await GameRepository.get_win_percentage()
    
    admin_text = (
        f"{get_emoji('admin')} *ADMIN PANEL* {get_emoji('admin')}\n\n"
        f"*System Statistics:*\n"
        f"• Total Users: `{total_users}`\n"
        f"• Active (24h): `{active_users}`\n"
        f"• Pending Withdrawals: `{pending_withdrawals}`\n"
        f"• Pending Deposits: `{pending_deposits}`\n"
        f"• Current Round: `{current_round or 'None'}`\n"
        f"• Win Percentage: `{current_win_percent}%`\n\n"
        f"*Available Commands:*\n"
        f"`/set_win_percent <75-80>` - Set winning percentage\n"
        f"`/force_start` - Force start new round\n"
        f"`/force_stop` - Force stop current round\n"
        f"`/set_sound_pack <pack1-4>` - Set default sound pack\n"
        f"`/search_player <phone/username>` - Search player\n"
        f"`/stats` - Detailed statistics\n"
        f"`/approve_deposit <id>` - Approve deposit\n"
        f"`/reject_deposit <id>` - Reject deposit\n"
        f"`/approve_withdrawal <id>` - Approve withdrawal\n"
        f"`/reject_withdrawal <id>` - Reject withdrawal\n"
        f"`/broadcast` - Send message to all users\n"
        f"`/maintenance <on/off>` - Toggle maintenance mode\n"
        f"`/reset_game` - Reset game state"
    )
    
    keyboard = admin_menu('en')
    
    await update.message.reply_text(
        admin_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def set_win_percent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set winning percentage (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/set_win_percent <percentage>`\n\n"
            f"Allowed values: `75`, `78`, `79`, `80`",
            parse_mode='Markdown'
        )
        return
    
    try:
        percent = int(args[0])
    except ValueError:
        await update.message.reply_text(
            f"{get_emoji('error')} Please enter a valid number.",
            parse_mode='Markdown'
        )
        return
    
    allowed_percentages = [75, 78, 79, 80]
    if percent not in allowed_percentages:
        await update.message.reply_text(
            f"{get_emoji('error')} Invalid percentage.\n\n"
            f"Allowed values: `{', '.join(map(str, allowed_percentages))}`",
            parse_mode='Markdown'
        )
        return
    
    # Update in database
    await GameRepository.set_win_percentage(percent)
    
    # Audit log
    await AuditRepository.log(
        user_id=telegram_id,
        action="set_win_percentage",
        entity_type="system",
        entity_id="settings",
        new_value={'win_percentage': percent}
    )
    
    await update.message.reply_text(
        f"{get_emoji('success')} *Win percentage updated!*\n\n"
        f"New winning percentage: `{percent}%`\n"
        f"House edge: `{100 - percent}%`",
        parse_mode='Markdown'
    )
    
    logger.info(f"Admin {telegram_id} set win percentage to {percent}%")


async def force_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force start a new game round (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    # Get game engine instance
    from bot.game_engine.bingo_room import bingo_room
    
    success = await bingo_room.force_start()
    
    if success:
        await update.message.reply_text(
            f"{get_emoji('success')} *Game force started!*\n\n"
            f"A new round has been initiated.\n"
            f"Selection phase: `{config.SELECTION_TIME}` seconds",
            parse_mode='Markdown'
        )
        
        # Audit log
        await AuditRepository.log(
            user_id=telegram_id,
            action="force_start_game",
            entity_type="game",
            entity_id="current_round",
            new_value={'forced_by': telegram_id}
        )
    else:
        await update.message.reply_text(
            f"{get_emoji('error')} *Failed to start game*\n\n"
            f"Please check game engine status.",
            parse_mode='Markdown'
        )


async def force_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force stop current game round (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    # Get game engine instance
    from bot.game_engine.bingo_room import bingo_room
    
    success = await bingo_room.force_stop()
    
    if success:
        await update.message.reply_text(
            f"{get_emoji('warning')} *Game force stopped!*\n\n"
            f"Current round has been terminated.\n"
            f"Use `/force_start` to begin a new round.",
            parse_mode='Markdown'
        )
        
        # Audit log
        await AuditRepository.log(
            user_id=telegram_id,
            action="force_stop_game",
            entity_type="game",
            entity_id="current_round",
            new_value={'forced_by': telegram_id}
        )
    else:
        await update.message.reply_text(
            f"{get_emoji('error')} *Failed to stop game*\n\n"
            f"No active round found.",
            parse_mode='Markdown'
        )


async def set_sound_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set default sound pack for all players (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/set_sound_pack <pack1|pack2|pack3|pack4>`\n\n"
            f"Available sound packs: `pack1`, `pack2`, `pack3`, `pack4`",
            parse_mode='Markdown'
        )
        return
    
    sound_pack = args[0].lower()
    valid_packs = ['pack1', 'pack2', 'pack3', 'pack4']
    
    if sound_pack not in valid_packs:
        await update.message.reply_text(
            f"{get_emoji('error')} Invalid sound pack.\n\n"
            f"Available: `{', '.join(valid_packs)}`",
            parse_mode='Markdown'
        )
        return
    
    # Update default sound pack in settings
    await GameRepository.set_default_sound_pack(sound_pack)
    
    # Optionally update all existing users (commented by default)
    # await UserRepository.update_all_sound_pack(sound_pack)
    
    await update.message.reply_text(
        f"{get_emoji('success')} *Default sound pack updated!*\n\n"
        f"New default: `{sound_pack}`\n"
        f"Existing players keep their preference unless force-updated.",
        parse_mode='Markdown'
    )
    
    logger.info(f"Admin {telegram_id} set default sound pack to {sound_pack}")


async def search_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search player by phone number or username (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/search_player <phone|username>`\n\n"
            f"Examples:\n"
            f"• `/search_player 0912345678`\n"
            f"• `/search_player @username`",
            parse_mode='Markdown'
        )
        return
    
    search_query = ' '.join(args)
    
    # Search by phone or username
    user = None
    
    # Check if it's a phone number (starts with 0 or +251)
    if search_query[0].isdigit() or search_query.startswith('+'):
        user = await UserRepository.get_by_phone(search_query)
    else:
        # Remove @ if present
        username = search_query.lstrip('@')
        user = await UserRepository.get_by_username(username)
    
    if not user:
        await update.message.reply_text(
            f"{get_emoji('error')} Player not found for: `{search_query}`",
            parse_mode='Markdown'
        )
        return
    
    # Get user statistics
    from bot.api.balance_ops import get_balance
    balance = await get_balance(user['telegram_id'])
    
    stats = await TransactionRepository.get_stats(user['telegram_id'])
    games_played = await GameRepository.get_user_games_count(user['telegram_id'])
    
    user_text = (
        f"{get_emoji('user')} *PLAYER DETAILS* {get_emoji('user')}\n\n"
        f"*ID:* `{user['telegram_id']}`\n"
        f"*Name:* {user.get('first_name', 'N/A')} {user.get('last_name', '')}\n"
        f"*Username:* @{user.get('username', 'N/A')}\n"
        f"*Phone:* `{user.get('phone_last4', '****')}`\n"
        f"*Registered:* {user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'}\n"
        f"*Last Seen:* {user.get('last_seen', 'N/A')[:10] if user.get('last_seen') else 'N/A'}\n\n"
        f"*Balance:* `{balance:.2f}` ETB\n"
        f"*Total Deposited:* `{stats.get('total_deposit', 0):.2f}` ETB\n"
        f"*Total Withdrawn:* `{stats.get('total_withdrawal', 0):.2f}` ETB\n"
        f"*Total Won:* `{stats.get('total_won', 0):.2f}` ETB\n"
        f"*Games Played:* `{games_played}`\n\n"
        f"*Welcome Bonus Claimed:* {'✅' if user.get('welcome_bonus_claimed') else '❌'}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{get_emoji('money')} Adjust Balance", callback_data=f"admin_adjust_balance_{user['telegram_id']}"),
            InlineKeyboardButton(f"{get_emoji('history')} Full History", callback_data=f"admin_user_history_{user['telegram_id']}")
        ]
    ])
    
    await update.message.reply_text(
        user_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed system statistics (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    # Get various stats
    total_users = await UserRepository.count_registered()
    active_users = await UserRepository.count_active(last_hours=24)
    new_users_today = await UserRepository.count_new_since(datetime.now().replace(hour=0, minute=0, second=0))
    
    # Game stats
    total_rounds = await GameRepository.count_rounds()
    total_cartelas_sold = await GameRepository.total_cartelas_sold()
    total_bets = total_cartelas_sold * config.CARTELA_PRICE
    
    # Financial stats
    total_deposits = await TransactionRepository.sum_by_type('deposit')
    total_withdrawals = await TransactionRepository.sum_by_type('withdrawal')
    total_wins = await TransactionRepository.sum_by_type('win')
    pending_withdrawals = await WithdrawalRepository.sum_pending()
    
    # Current game state
    from bot.game_engine.bingo_room import bingo_room
    current_state = bingo_room.get_state()
    
    stats_text = (
        f"{get_emoji('chart')} *SYSTEM STATISTICS* {get_emoji('chart')}\n\n"
        f"*👥 Users:*\n"
        f"• Total Registered: `{total_users}`\n"
        f"• Active (24h): `{active_users}`\n"
        f"• New Today: `{new_users_today}`\n\n"
        f"*🎮 Game:*\n"
        f"• Total Rounds: `{total_rounds}`\n"
        f"• Cartelas Sold: `{total_cartelas_sold}`\n"
        f"• Total Bets: `{total_bets:.2f}` ETB\n"
        f"• Total Wins Paid: `{total_wins:.2f}` ETB\n"
        f"• House Edge: `{total_bets - total_wins:.2f}` ETB\n\n"
        f"*💰 Finance:*\n"
        f"• Total Deposits: `{total_deposits:.2f}` ETB\n"
        f"• Total Withdrawals: `{total_withdrawals:.2f}` ETB\n"
        f"• Pending Withdrawals: `{pending_withdrawals:.2f}` ETB\n\n"
        f"*🔄 Current Game:*\n"
        f"• Status: `{current_state.get('status', 'idle')}`\n"
        f"• Players in Game: `{current_state.get('player_count', 0)}`\n"
        f"• Cartelas Selected: `{current_state.get('selected_count', 0)}`"
    )
    
    await update.message.reply_text(
        stats_text,
        parse_mode='Markdown'
    )


async def approve_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a pending deposit (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/approve_deposit <deposit_id>`",
            parse_mode='Markdown'
        )
        return
    
    try:
        deposit_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            f"{get_emoji('error')} Invalid deposit ID.",
            parse_mode='Markdown'
        )
        return
    
    # Get deposit request
    deposit = await DepositRepository.get_by_id(deposit_id)
    if not deposit:
        await update.message.reply_text(
            f"{get_emoji('error')} Deposit #{deposit_id} not found.",
            parse_mode='Markdown'
        )
        return
    
    if deposit['status'] != 'pending':
        await update.message.reply_text(
            f"{get_emoji('warning')} Deposit #{deposit_id} is already {deposit['status']}.",
            parse_mode='Markdown'
        )
        return
    
    # Update status
    await DepositRepository.update_status(deposit_id, 'approved', admin_id=telegram_id)
    
    # Add balance to user
    from bot.api.balance_ops import add_balance
    await add_balance(
        telegram_id=deposit['telegram_id'],
        amount=deposit['amount'],
        reason="deposit",
        metadata={'deposit_id': deposit_id, 'admin_id': telegram_id}
    )
    
    # Notify user
    await context.bot.send_message(
        chat_id=deposit['telegram_id'],
        text=(
            f"{get_emoji('success')} *DEPOSIT APPROVED!*\n\n"
            f"Your deposit of `{deposit['amount']:.2f}` ETB has been approved.\n"
            f"Request ID: `#{deposit_id}`\n\n"
            f"Thank you for playing!"
        ),
        parse_mode='Markdown'
    )
    
    await update.message.reply_text(
        f"{get_emoji('success')} Deposit #{deposit_id} approved.\n"
        f"Amount: `{deposit['amount']:.2f}` ETB added to user balance.",
        parse_mode='Markdown'
    )
    
    logger.info(f"Admin {telegram_id} approved deposit #{deposit_id}")


async def reject_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a pending deposit (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/reject_deposit <deposit_id>`",
            parse_mode='Markdown'
        )
        return
    
    try:
        deposit_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            f"{get_emoji('error')} Invalid deposit ID.",
            parse_mode='Markdown'
        )
        return
    
    # Get deposit request
    deposit = await DepositRepository.get_by_id(deposit_id)
    if not deposit:
        await update.message.reply_text(
            f"{get_emoji('error')} Deposit #{deposit_id} not found.",
            parse_mode='Markdown'
        )
        return
    
    if deposit['status'] != 'pending':
        await update.message.reply_text(
            f"{get_emoji('warning')} Deposit #{deposit_id} is already {deposit['status']}.",
            parse_mode='Markdown'
        )
        return
    
    # Update status
    await DepositRepository.update_status(deposit_id, 'rejected', admin_id=telegram_id)
    
    # Notify user
    await context.bot.send_message(
        chat_id=deposit['telegram_id'],
        text=(
            f"{get_emoji('error')} *DEPOSIT REJECTED*\n\n"
            f"Your deposit request #{deposit_id} has been rejected.\n"
            f"Please contact support for more information.\n\n"
            f"Support: {config.SUPPORT_CHANNEL_LINK}"
        ),
        parse_mode='Markdown'
    )
    
    await update.message.reply_text(
        f"{get_emoji('error')} Deposit #{deposit_id} rejected.",
        parse_mode='Markdown'
    )
    
    logger.info(f"Admin {telegram_id} rejected deposit #{deposit_id}")


async def approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a pending withdrawal (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/approve_withdrawal <withdrawal_id>`",
            parse_mode='Markdown'
        )
        return
    
    try:
        withdrawal_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            f"{get_emoji('error')} Invalid withdrawal ID.",
            parse_mode='Markdown'
        )
        return
    
    # Get withdrawal request
    withdrawal = await WithdrawalRepository.get_by_id(withdrawal_id)
    if not withdrawal:
        await update.message.reply_text(
            f"{get_emoji('error')} Withdrawal #{withdrawal_id} not found.",
            parse_mode='Markdown'
        )
        return
    
    if withdrawal['status'] != 'pending':
        await update.message.reply_text(
            f"{get_emoji('warning')} Withdrawal #{withdrawal_id} is already {withdrawal['status']}.",
            parse_mode='Markdown'
        )
        return
    
    # Update status (amount already deducted when request was created)
    await WithdrawalRepository.update_status(withdrawal_id, 'approved', admin_id=telegram_id)
    
    # Notify user
    await context.bot.send_message(
        chat_id=withdrawal['telegram_id'],
        text=(
            f"{get_emoji('success')} *WITHDRAWAL APPROVED!*\n\n"
            f"Your withdrawal of `{withdrawal['amount']:.2f}` ETB has been approved.\n"
            f"Request ID: `#{withdrawal_id}`\n\n"
            f"Funds will be sent to your account within 24-48 hours."
        ),
        parse_mode='Markdown'
    )
    
    await update.message.reply_text(
        f"{get_emoji('success')} Withdrawal #{withdrawal_id} approved.",
        parse_mode='Markdown'
    )
    
    logger.info(f"Admin {telegram_id} approved withdrawal #{withdrawal_id}")


async def reject_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a pending withdrawal and refund balance (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/reject_withdrawal <withdrawal_id>`",
            parse_mode='Markdown'
        )
        return
    
    try:
        withdrawal_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            f"{get_emoji('error')} Invalid withdrawal ID.",
            parse_mode='Markdown'
        )
        return
    
    # Get withdrawal request
    withdrawal = await WithdrawalRepository.get_by_id(withdrawal_id)
    if not withdrawal:
        await update.message.reply_text(
            f"{get_emoji('error')} Withdrawal #{withdrawal_id} not found.",
            parse_mode='Markdown'
        )
        return
    
    if withdrawal['status'] != 'pending':
        await update.message.reply_text(
            f"{get_emoji('warning')} Withdrawal #{withdrawal_id} is already {withdrawal['status']}.",
            parse_mode='Markdown'
        )
        return
    
    # Update status
    await WithdrawalRepository.update_status(withdrawal_id, 'rejected', admin_id=telegram_id)
    
    # Refund balance to user
    from bot.api.balance_ops import add_balance
    await add_balance(
        telegram_id=withdrawal['telegram_id'],
        amount=withdrawal['amount'],
        reason="withdrawal_rejected",
        metadata={'withdrawal_id': withdrawal_id, 'admin_id': telegram_id}
    )
    
    # Notify user
    await context.bot.send_message(
        chat_id=withdrawal['telegram_id'],
        text=(
            f"{get_emoji('error')} *WITHDRAWAL REJECTED*\n\n"
            f"Your withdrawal request #{withdrawal_id} has been rejected.\n"
            f"Amount of `{withdrawal['amount']:.2f}` ETB has been returned to your balance.\n\n"
            f"Please contact support for more information."
        ),
        parse_mode='Markdown'
    )
    
    await update.message.reply_text(
        f"{get_emoji('error')} Withdrawal #{withdrawal_id} rejected. User balance refunded.",
        parse_mode='Markdown'
    )
    
    logger.info(f"Admin {telegram_id} rejected withdrawal #{withdrawal_id}")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast process (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"{get_emoji('broadcast')} *Broadcast Message*\n\n"
        f"Please send me the message you want to broadcast to all users.\n\n"
        f"Format: You can use Markdown formatting.\n"
        f"Type /cancel to abort.",
        parse_mode='Markdown'
    )
    return BROADCAST_MESSAGE


async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive broadcast message and ask for confirmation"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return ConversationHandler.END
    
    message_text = update.message.text
    
    # Store message
    context.user_data['broadcast_message'] = message_text
    
    # Get user count
    total_users = await UserRepository.count_registered()
    
    # Show confirmation
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{get_emoji('check')} Send", callback_data="broadcast_confirm"),
            InlineKeyboardButton(f"{get_emoji('cancel')} Cancel", callback_data="broadcast_cancel")
        ]
    ])
    
    await update.message.reply_text(
        f"{get_emoji('warning')} *Confirm Broadcast*\n\n"
        f"Message preview:\n"
        f"```\n{message_text[:500]}\n```\n\n"
        f"Will be sent to: `{total_users}` users\n\n"
        f"Proceed?",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return BROADCAST_CONFIRM


async def broadcast_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute broadcast to all users"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    
    if not is_admin(telegram_id):
        await query.edit_message_text("Unauthorized.")
        return ConversationHandler.END
    
    message_text = context.user_data.get('broadcast_message')
    
    if not message_text:
        await query.edit_message_text("No message to broadcast.")
        return ConversationHandler.END
    
    # Get all users
    users = await UserRepository.get_all_registered()
    
    success_count = 0
    fail_count = 0
    
    await query.edit_message_text(
        f"{get_emoji('broadcast')} *Sending Broadcast...*\n\n"
        f"Total users: `{len(users)}`\n"
        f"Starting...",
        parse_mode='Markdown'
    )
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['telegram_id'],
                text=message_text,
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            fail_count += 1
            logger.warning(f"Broadcast failed to {user['telegram_id']}: {e}")
        
        # Small delay to avoid rate limiting
        if success_count % 10 == 0:
            await asyncio.sleep(0.5)
    
    # Audit log
    await AuditRepository.log(
        user_id=telegram_id,
        action="broadcast",
        entity_type="system",
        entity_id="broadcast",
        new_value={'success': success_count, 'failed': fail_count}
    )
    
    await query.edit_message_text(
        f"{get_emoji('success')} *Broadcast Completed*\n\n"
        f"✅ Sent: `{success_count}`\n"
        f"❌ Failed: `{fail_count}`",
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return ConversationHandler.END


async def broadcast_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel broadcast"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"{get_emoji('warning')} Broadcast cancelled.",
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return ConversationHandler.END


async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle maintenance mode (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if not args or args[0].lower() not in ['on', 'off']:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/maintenance <on|off>`\n\n"
            f"• `on` - Enable maintenance mode (prevents new games)\n"
            f"• `off` - Disable maintenance mode",
            parse_mode='Markdown'
        )
        return
    
    mode = args[0].lower() == 'on'
    
    await GameRepository.set_maintenance_mode(mode)
    
    # Audit log
    await AuditRepository.log(
        user_id=telegram_id,
        action="maintenance_mode",
        entity_type="system",
        entity_id="settings",
        new_value={'maintenance_mode': mode}
    )
    
    status_text = "enabled" if mode else "disabled"
    
    await update.message.reply_text(
        f"{get_emoji('warning')} *Maintenance mode {status_text}*\n\n"
        f"New games are {'blocked' if mode else 'allowed'}.\n"
        f"Existing games continue normally.",
        parse_mode='Markdown'
    )


async def reset_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset game state (admin only)"""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("Unauthorized.")
        return
    
    # Get game engine
    from bot.game_engine.bingo_room import bingo_room
    
    await bingo_room.reset_game()
    
    # Audit log
    await AuditRepository.log(
        user_id=telegram_id,
        action="reset_game",
        entity_type="game",
        entity_id="system",
        new_value={'reset_by': telegram_id}
    )
    
    await update.message.reply_text(
        f"{get_emoji('success')} *Game state reset!*\n\n"
        f"All game data has been cleared.\n"
        f"Use `/force_start` to begin a new round.",
        parse_mode='Markdown'
    )


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel broadcast conversation"""
    telegram_id = update.effective_user.id
    
    await update.message.reply_text(
        f"{get_emoji('warning')} Broadcast cancelled.",
        parse_mode='Markdown'
    )
    context.user_data.clear()
    return ConversationHandler.END


# Export all
__all__ = [
    'admin_command',
    'set_win_percent',
    'force_start',
    'force_stop',
    'set_sound_pack',
    'search_player',
    'stats_command',
    'approve_deposit',
    'reject_deposit',
    'approve_withdrawal',
    'reject_withdrawal',
    'broadcast_command',
    'broadcast_message',
    'broadcast_confirm_callback',
    'broadcast_cancel_callback',
    'maintenance_command',
    'reset_game_command',
    'cancel_broadcast',
    'BROADCAST_MESSAGE',
    'BROADCAST_CONFIRM',
]