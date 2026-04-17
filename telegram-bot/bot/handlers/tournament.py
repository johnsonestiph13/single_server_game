# telegram-bot/bot/handlers/tournament.py
# Estif Bingo 24/7 - Tournament Handler (Optional Feature)
# This module is DISABLED by default. Set ENABLE_TOURNAMENT=true in .env to activate.
# Tournaments allow players to compete in special events with prize pools.

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.tournament_repo import TournamentRepository
from bot.db.repository.audit_repo import AuditRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import menu
from bot.config import config
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

# Tournament conversation states
TOURNAMENT_SELECT = 1
TOURNAMENT_REGISTER = 2
TOURNAMENT_BET = 3

# Tournament settings (loaded from database or defaults)
TOURNAMENT_ENABLED = getattr(config, 'ENABLE_TOURNAMENT', False)

# Tournament types
TOURNAMENT_TYPES = {
    'daily': {'name': 'Daily Tournament', 'duration_hours': 24, 'entry_fee': 50, 'prize_pool': 5000},
    'weekly': {'name': 'Weekly Tournament', 'duration_hours': 168, 'entry_fee': 200, 'prize_pool': 25000},
    'monthly': {'name': 'Monthly Tournament', 'duration_hours': 720, 'entry_fee': 500, 'prize_pool': 100000},
    'special': {'name': 'Special Event', 'duration_hours': 48, 'entry_fee': 100, 'prize_pool': 10000}
}

logger = logging.getLogger(__name__)


async def tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tournament information and available tournaments"""
    if not TOURNAMENT_ENABLED:
        await update.message.reply_text(
            f"{get_emoji('warning')} *Tournaments Coming Soon!*\n\n"
            f"Tournament feature is currently in development.\n"
            f"Please check back later for competitive events!\n\n"
            f"{get_emoji('game')} In the meantime, use /play to enjoy regular bingo games.",
            reply_markup=menu('en'),
            parse_mode='Markdown'
        )
        return
    
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
    
    # Get active tournaments
    active_tournaments = await TournamentRepository.get_active_tournaments()
    
    # Get user's current tournament participation
    user_tournaments = await TournamentRepository.get_user_tournaments(telegram_id)
    
    if not active_tournaments:
        await update.message.reply_text(
            f"{get_emoji('info')} *No Active Tournaments*\n\n"
            f"There are no tournaments running at the moment.\n"
            f"Check back soon for upcoming events!\n\n"
            f"{get_emoji('calendar')} *Upcoming:*\n"
            f"• Daily Tournament - Every day at 00:00 UTC\n"
            f"• Weekly Tournament - Every Monday\n"
            f"• Monthly Tournament - First day of each month",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Build tournament list
    tournament_text = f"{get_emoji('trophy')} *TOURNAMENTS* {get_emoji('trophy')}\n\n"
    
    for tourney in active_tournaments:
        status = "✅ Active" if tourney['status'] == 'active' else "⏳ Upcoming"
        time_left = calculate_time_left(tourney['end_time'])
        
        tournament_text += (
            f"*{tourney['name']}*\n"
            f"└ Status: {status}\n"
            f"└ Entry Fee: `{tourney['entry_fee']}` ETB\n"
            f"└ Prize Pool: `{tourney['prize_pool']}` ETB\n"
            f"└ Time Left: `{time_left}`\n"
            f"└ Players: `{tourney['player_count']}`\n\n"
        )
    
    # Create keyboard with tournament options
    keyboard = []
    
    for tourney in active_tournaments:
        # Check if user is already registered
        is_registered = any(t['tournament_id'] == tourney['id'] for t in user_tournaments)
        
        if is_registered:
            keyboard.append([InlineKeyboardButton(
                f"{get_emoji('game')} {tourney['name']} - Registered",
                callback_data=f"tourney_play_{tourney['id']}"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                f"{get_emoji('register')} Register for {tourney['name']}",
                callback_data=f"tourney_register_{tourney['id']}"
            )])
    
    keyboard.append([InlineKeyboardButton(
        f"{get_emoji('leaderboard')} Leaderboard",
        callback_data="tourney_leaderboard"
    )])
    keyboard.append([InlineKeyboardButton(
        f"{get_emoji('back')} Back to Menu",
        callback_data="back_to_menu"
    )])
    
    await update.message.reply_text(
        tournament_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def tournament_register_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tournament registration"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    tournament_id = int(query.data.split("_")[2])
    
    # Get tournament details
    tournament = await TournamentRepository.get_tournament(tournament_id)
    
    if not tournament:
        await query.edit_message_text(
            f"{get_emoji('error')} Tournament not found.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Check if tournament is still active
    if tournament['status'] != 'active':
        await query.edit_message_text(
            f"{get_emoji('warning')} Tournament registration is closed.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Check if already registered
    is_registered = await TournamentRepository.is_user_registered(telegram_id, tournament_id)
    
    if is_registered:
        await query.edit_message_text(
            f"{get_emoji('warning')} You are already registered for this tournament!",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Check balance
    from bot.api.balance_ops import get_balance
    balance = await get_balance(telegram_id)
    
    if balance < tournament['entry_fee']:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_emoji('deposit')} Deposit Now", callback_data="quick_deposit")],
            [InlineKeyboardButton(f"{get_emoji('back')} Back", callback_data="back_to_tournament")]
        ])
        
        await query.edit_message_text(
            f"{get_emoji('error')} *Insufficient Balance*\n\n"
            f"Tournament entry fee: `{tournament['entry_fee']}` ETB\n"
            f"Your balance: `{balance:.2f}` ETB\n\n"
            f"Deposit funds to join the tournament!",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    # Ask for confirmation
    context.user_data['register_tournament_id'] = tournament_id
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{get_emoji('check')} Confirm", callback_data="tourney_confirm_register"),
            InlineKeyboardButton(f"{get_emoji('cancel')} Cancel", callback_data="cancel_tournament_register")
        ]
    ])
    
    await query.edit_message_text(
        f"{get_emoji('warning')} *Confirm Tournament Registration*\n\n"
        f"Tournament: `{tournament['name']}`\n"
        f"Entry Fee: `{tournament['entry_fee']}` ETB\n"
        f"Prize Pool: `{tournament['prize_pool']}` ETB\n\n"
        f"Once registered, you can play bingo games that count toward tournament scores.\n\n"
        f"Proceed with registration?",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def tournament_confirm_register_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm tournament registration and deduct fee"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    tournament_id = context.user_data.get('register_tournament_id')
    
    if not tournament_id:
        await query.edit_message_text(
            f"{get_emoji('error')} Registration session expired. Please try again.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    tournament = await TournamentRepository.get_tournament(tournament_id)
    
    if not tournament:
        await query.edit_message_text(
            f"{get_emoji('error')} Tournament not found.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Check balance again
    from bot.api.balance_ops import get_balance, deduct_balance
    balance = await get_balance(telegram_id)
    
    if balance < tournament['entry_fee']:
        await query.edit_message_text(
            f"{get_emoji('error')} Insufficient balance. Registration cancelled.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        context.user_data.pop('register_tournament_id', None)
        return
    
    # Deduct entry fee
    await deduct_balance(
        telegram_id=telegram_id,
        amount=tournament['entry_fee'],
        reason=f"tournament_entry_{tournament_id}",
        metadata={'tournament_id': tournament_id, 'tournament_name': tournament['name']}
    )
    
    # Register user for tournament
    await TournamentRepository.register_user(
        telegram_id=telegram_id,
        tournament_id=tournament_id,
        entry_fee=tournament['entry_fee']
    )
    
    # Update tournament player count
    await TournamentRepository.increment_player_count(tournament_id)
    
    # Audit log
    await AuditRepository.log(
        user_id=telegram_id,
        action="tournament_registered",
        entity_type="tournament",
        entity_id=str(tournament_id),
        new_value={'tournament_name': tournament['name'], 'entry_fee': tournament['entry_fee']}
    )
    
    await query.edit_message_text(
        f"{get_emoji('success')} *Successfully Registered!*\n\n"
        f"You have joined `{tournament['name']}`\n"
        f"Entry Fee: `{tournament['entry_fee']}` ETB\n\n"
        f"{get_emoji('game')} How to earn points:\n"
        f"• Play bingo games using /play\n"
        f"• Each win earns you points\n"
        f"• Higher wins = more points\n"
        f"• Top players win prizes!\n\n"
        f"{get_emoji('leaderboard')} Use /tournament to check leaderboard.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )
    
    context.user_data.pop('register_tournament_id', None)
    logger.info(f"User {telegram_id} registered for tournament {tournament_id}")


async def tournament_play_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start playing in tournament mode"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    tournament_id = int(query.data.split("_")[2])
    
    # Check if user is registered
    is_registered = await TournamentRepository.is_user_registered(telegram_id, tournament_id)
    
    if not is_registered:
        await query.edit_message_text(
            f"{get_emoji('error')} You are not registered for this tournament.\n\n"
            f"Use /tournament to register first.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Store tournament mode in context
    context.user_data['tournament_mode'] = True
    context.user_data['current_tournament_id'] = tournament_id
    
    # Launch regular game with tournament tracking
    from bot.handlers.game import play
    await play(update, context)


async def tournament_leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tournament leaderboard"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Get active tournaments
    active_tournaments = await TournamentRepository.get_active_tournaments()
    
    if not active_tournaments:
        await query.edit_message_text(
            f"{get_emoji('info')} No active tournaments.",
            reply_markup=menu(lang),
            parse_mode='Markdown'
        )
        return
    
    # Build leaderboard for each tournament
    leaderboard_text = f"{get_emoji('leaderboard')} *TOURNAMENT LEADERBOARDS* {get_emoji('leaderboard')}\n\n"
    
    for tourney in active_tournaments:
        leaderboard = await TournamentRepository.get_leaderboard(tourney['id'], limit=10)
        
        leaderboard_text += f"*{tourney['name']}*\n"
        
        if leaderboard:
            for idx, player in enumerate(leaderboard, 1):
                medal = get_medal_emoji(idx)
                leaderboard_text += f"{medal} `{idx}.` {player['first_name']} - `{player['points']}` pts\n"
        else:
            leaderboard_text += f"└ No players yet. Be the first!\n"
        
        leaderboard_text += "\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_emoji('refresh')} Refresh", callback_data="tourney_leaderboard")],
        [InlineKeyboardButton(f"{get_emoji('back')} Back", callback_data="back_to_tournament")]
    ])
    
    await query.edit_message_text(
        leaderboard_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def cancel_tournament_register_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel tournament registration"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    context.user_data.pop('register_tournament_id', None)
    
    await query.edit_message_text(
        f"{get_emoji('warning')} Tournament registration cancelled.",
        reply_markup=menu(lang),
        parse_mode='Markdown'
    )


async def back_to_tournament_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to tournament menu"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    await tournament(update, context)


def calculate_time_left(end_time: datetime) -> str:
    """Calculate time left until tournament ends"""
    now = datetime.utcnow()
    diff = end_time - now
    
    if diff.total_seconds() <= 0:
        return "Ended"
    
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    
    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def get_medal_emoji(rank: int) -> str:
    """Get medal emoji based on rank"""
    if rank == 1:
        return "🥇"
    elif rank == 2:
        return "🥈"
    elif rank == 3:
        return "🥉"
    else:
        return "•"


# Admin commands for tournament management
async def admin_create_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new tournament (admin only)"""
    telegram_id = update.effective_user.id
    
    if str(telegram_id) != str(config.ADMIN_CHAT_ID):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if len(args) < 4:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/create_tournament <type> <name> <entry_fee> <prize_pool>`\n\n"
            f"Tournament types: `daily`, `weekly`, `monthly`, `special`\n\n"
            f"Example: `/create_tournament weekly \"Champions Week\" 200 25000`",
            parse_mode='Markdown'
        )
        return
    
    tourney_type = args[0].lower()
    name = ' '.join(args[1:-2])
    entry_fee = int(args[-2])
    prize_pool = int(args[-1])
    
    if tourney_type not in TOURNAMENT_TYPES:
        await update.message.reply_text(f"{get_emoji('error')} Invalid tournament type.")
        return
    
    # Calculate start and end times
    now = datetime.utcnow()
    duration_hours = TOURNAMENT_TYPES[tourney_type]['duration_hours']
    end_time = now + timedelta(hours=duration_hours)
    
    # Create tournament
    tournament_id = await TournamentRepository.create_tournament(
        name=name,
        tourney_type=tourney_type,
        entry_fee=entry_fee,
        prize_pool=prize_pool,
        start_time=now,
        end_time=end_time
    )
    
    await update.message.reply_text(
        f"{get_emoji('success')} *Tournament Created!*\n\n"
        f"Name: `{name}`\n"
        f"Type: `{tourney_type}`\n"
        f"Entry Fee: `{entry_fee}` ETB\n"
        f"Prize Pool: `{prize_pool}` ETB\n"
        f"Ends: `{end_time.strftime('%Y-%m-%d %H:%M UTC')}`\n\n"
        f"Tournament ID: `{tournament_id}`",
        parse_mode='Markdown'
    )


async def admin_end_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End a tournament and distribute prizes (admin only)"""
    telegram_id = update.effective_user.id
    
    if str(telegram_id) != str(config.ADMIN_CHAT_ID):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/end_tournament <tournament_id>`",
            parse_mode='Markdown'
        )
        return
    
    tournament_id = int(args[0])
    
    # Get tournament
    tournament = await TournamentRepository.get_tournament(tournament_id)
    
    if not tournament:
        await update.message.reply_text(f"{get_emoji('error')} Tournament not found.")
        return
    
    # Get leaderboard
    leaderboard = await TournamentRepository.get_leaderboard(tournament_id, limit=10)
    
    if not leaderboard:
        await update.message.reply_text(f"{get_emoji('warning')} No participants in this tournament.")
        return
    
    # Distribute prizes (example distribution)
    prize_distribution = calculate_prize_distribution(tournament['prize_pool'], len(leaderboard))
    
    from bot.api.balance_ops import add_balance
    
    for idx, player in enumerate(leaderboard, 1):
        if idx <= len(prize_distribution):
            prize = prize_distribution[idx - 1]
            
            await add_balance(
                telegram_id=player['telegram_id'],
                amount=prize,
                reason=f"tournament_prize_{tournament_id}",
                metadata={'tournament_id': tournament_id, 'rank': idx}
            )
            
            # Notify winner
            await context.bot.send_message(
                chat_id=player['telegram_id'],
                text=(
                    f"{get_emoji('trophy')} *TOURNAMENT PRIZE!* {get_emoji('trophy')}\n\n"
                    f"You finished #{idx} in `{tournament['name']}`\n"
                    f"Prize: `{prize}` ETB\n\n"
                    f"Congratulations! 🎉"
                ),
                parse_mode='Markdown'
            )
    
    # Update tournament status
    await TournamentRepository.end_tournament(tournament_id)
    
    await update.message.reply_text(
        f"{get_emoji('success')} *Tournament Ended*\n\n"
        f"Name: `{tournament['name']}`\n"
        f"Prize pool: `{tournament['prize_pool']}` ETB\n"
        f"Winners: `{len(prize_distribution)}`\n\n"
        f"Prizes have been distributed!",
        parse_mode='Markdown'
    )


def calculate_prize_distribution(prize_pool: int, player_count: int) -> List[int]:
    """Calculate prize distribution based on tournament settings"""
    # Example distribution: 40%, 20%, 10%, 5%, 5%, 5%, 5%, 5%, 3%, 2%
    percentages = [40, 20, 10, 5, 5, 5, 5, 5, 3, 2]
    
    prizes = []
    for idx, percent in enumerate(percentages):
        if idx < player_count:
            prize = int(prize_pool * percent / 100)
            if prize > 0:
                prizes.append(prize)
    
    # If fewer players, redistribute remaining
    if len(prizes) < player_count and len(prizes) > 0:
        remaining = prize_pool - sum(prizes)
        if remaining > 0 and len(prizes) > 0:
            prizes[0] += remaining
    
    return prizes


# Export all
__all__ = [
    'tournament',
    'tournament_register_callback',
    'tournament_confirm_register_callback',
    'tournament_play_callback',
    'tournament_leaderboard_callback',
    'cancel_tournament_register_callback',
    'back_to_tournament_callback',
    'admin_create_tournament',
    'admin_end_tournament',
    'TOURNAMENT_ENABLED',
]