# telegram-bot/bot/handlers/mini_bingo.py
# Estif Bingo 24/7 - Mini Bingo Game Handler (Legacy Single-Player Fallback)
# This is a simple single-player bingo game for users who want to practice
# or when the main real-time game is unavailable.

import logging
import random
import json
from datetime import datetime
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes

from bot.db.repository.user_repo import UserRepository
from bot.db.repository.audit_repo import AuditRepository
from bot.texts.locales import TEXTS
from bot.keyboards.menu import menu
from bot.config import config
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

# Game settings
MINI_BINGO_PRICE = 5  # ETB per cartela
MINI_BINGO_WIN_PERCENTAGE = 80  # 80% win rate
MINI_BINGO_NUMBERS_RANGE = 75
MINI_BINGO_GRID_SIZE = 5

logger = logging.getLogger(__name__)


async def mini_bingo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send mini bingo game link for single-player practice game.
    This is a fallback option when the main real-time game is unavailable.
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
        return
    
    # Check balance
    from bot.api.balance_ops import get_balance
    balance = await get_balance(telegram_id)
    
    if balance < MINI_BINGO_PRICE:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_emoji('deposit')} Deposit Now", callback_data="quick_deposit")],
            [InlineKeyboardButton(f"{get_emoji('game')} Play Advanced Bingo", callback_data="play_advanced")]
        ])
        
        await update.message.reply_text(
            f"{get_emoji('warning')} *Mini Bingo - Insufficient Balance*\n\n"
            f"Mini Bingo requires `{MINI_BINGO_PRICE}` ETB per game.\n"
            f"Your balance: `{balance:.2f}` ETB\n\n"
            f"{get_emoji('info')} *Mini Bingo Features:*\n"
            f"• Single-player practice game\n"
            f"• `{MINI_BINGO_WIN_PERCENTAGE}%` win chance\n"
            f"• Instant results\n"
            f"• Great for learning the rules\n\n"
            f"Deposit funds to play or try the advanced game!",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        return
    
    # Get user's sound pack preference
    sound_pack = user.get('sound_pack', config.DEFAULT_SOUND_PACK)
    
    # Generate game URL with parameters
    jwt_token = await generate_mini_bingo_token(telegram_id)
    game_url = f"{config.BASE_URL}/mini_bingo.html?token={jwt_token}&sound={sound_pack}"
    
    # Create WebApp button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{get_emoji('game')} PLAY MINI BINGO {get_emoji('game')}",
            web_app=WebAppInfo(url=game_url)
        )],
        [InlineKeyboardButton(
            f"{get_emoji('trophy')} Play Advanced Bingo",
            callback_data="play_advanced"
        )],
        [InlineKeyboardButton(
            f"{get_emoji('info')} How to Play",
            callback_data="mini_bingo_rules"
        )],
        [InlineKeyboardButton(
            f"{get_emoji('back')} Back to Menu",
            callback_data="back_to_menu"
        )]
    ])
    
    await update.message.reply_text(
        f"{get_emoji('game')} *MINI BINGO - Practice Mode* {get_emoji('game')}\n\n"
        f"{get_emoji('money')} Your balance: `{balance:.2f}` ETB\n"
        f"{get_emoji('cartela')} Game cost: `{MINI_BINGO_PRICE}` ETB\n"
        f"{get_emoji('trophy')} Win rate: `{MINI_BINGO_WIN_PERCENTAGE}%`\n\n"
        f"*🎮 Game Features:*\n"
        f"• Single-player practice game\n"
        f"• Random 5x5 bingo cartela\n"
        f"• Numbers called until you get BINGO!\n"
        f"• Instant win/loss result\n"
        f"• Great for learning the rules\n\n"
        f"*💰 How it works:*\n"
        f"1️⃣ Click PLAY MINI BINGO\n"
        f"2️⃣ Game automatically deducts `{MINI_BINGO_PRICE}` ETB\n"
        f"3️⃣ Numbers are called randomly\n"
        f"4️⃣ Complete a line to win!\n"
        f"5️⃣ Win amount: `{MINI_BINGO_PRICE * MINI_BINGO_WIN_PERCENTAGE // 100}` ETB\n\n"
        f"{get_emoji('info')} *Note:* This is a single-player practice game.\n"
        f"For real-time multiplayer, use the Advanced Bingo game!",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    logger.info(f"Mini bingo launched for user {telegram_id}")


async def play_mini_bingo_game(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    """
    Start a mini bingo game session (called from web app or directly).
    Deducts balance, generates cartela, and returns game state.
    """
    telegram_id = update.effective_user.id if update.effective_user else query.from_user.id
    
    # Check balance
    from bot.api.balance_ops import get_balance, deduct_balance
    balance = await get_balance(telegram_id)
    
    if balance < MINI_BINGO_PRICE:
        return {
            'success': False,
            'error': 'insufficient_balance',
            'message': f'Insufficient balance. Need {MINI_BINGO_PRICE} ETB to play.'
        }
    
    # Deduct game cost
    await deduct_balance(
        telegram_id=telegram_id,
        amount=MINI_BINGO_PRICE,
        reason="mini_bingo_game",
        metadata={'game_type': 'mini_bingo'}
    )
    
    # Generate random cartela (5x5 grid)
    cartela = generate_random_cartela()
    
    # Generate random number sequence (1-75 shuffled)
    numbers_sequence = list(range(1, MINI_BINGO_NUMBERS_RANGE + 1))
    random.shuffle(numbers_sequence)
    
    # Determine if player wins (based on win percentage)
    will_win = random.randint(1, 100) <= MINI_BINGO_WIN_PERCENTAGE
    
    # Store game session in context
    game_session = {
        'telegram_id': telegram_id,
        'cartela': cartela,
        'numbers_called': [],
        'numbers_sequence': numbers_sequence,
        'will_win': will_win,
        'started_at': datetime.utcnow().isoformat()
    }
    
    context.user_data['mini_bingo_session'] = game_session
    
    return {
        'success': True,
        'cartela': cartela,
        'numbers_sequence': numbers_sequence[:20],  # Send first 20 numbers
        'game_cost': MINI_BINGO_PRICE,
        'win_amount': MINI_BINGO_PRICE * MINI_BINGO_WIN_PERCENTAGE // 100 if will_win else 0
    }


async def check_mini_bingo_win(update: Update, context: ContextTypes.DEFAULT_TYPE, called_numbers: List[int]) -> Dict:
    """
    Check if the player has won based on called numbers.
    Returns win status and winning pattern.
    """
    telegram_id = update.effective_user.id
    game_session = context.user_data.get('mini_bingo_session')
    
    if not game_session:
        return {'win': False, 'error': 'No active game session'}
    
    cartela = game_session.get('cartela')
    will_win = game_session.get('will_win', False)
    
    # Check if player should win based on preset win chance
    if will_win:
        # Find a winning line
        winning_pattern = find_winning_line(cartela, called_numbers)
        if winning_pattern:
            # Award win amount
            win_amount = MINI_BINGO_PRICE * MINI_BINGO_WIN_PERCENTAGE // 100
            
            from bot.api.balance_ops import add_balance
            await add_balance(
                telegram_id=telegram_id,
                amount=win_amount,
                reason="mini_bingo_win",
                metadata={'pattern': winning_pattern}
            )
            
            # Audit log
            await AuditRepository.log(
                user_id=telegram_id,
                action="mini_bingo_win",
                entity_type="game",
                entity_id=str(telegram_id),
                new_value={'win_amount': win_amount, 'pattern': winning_pattern}
            )
            
            # Clear session
            context.user_data.pop('mini_bingo_session', None)
            
            return {
                'win': True,
                'win_amount': win_amount,
                'pattern': winning_pattern,
                'message': f'🎉 BINGO! You won {win_amount} ETB!'
            }
    
    # No win yet
    return {'win': False, 'message': 'Keep playing!'}


async def end_mini_bingo_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    End mini bingo game session (called when game is closed or completed).
    """
    telegram_id = update.effective_user.id
    game_session = context.user_data.pop('mini_bingo_session', None)
    
    if game_session:
        logger.info(f"Mini bingo game ended for user {telegram_id}")
        
        await AuditRepository.log(
            user_id=telegram_id,
            action="mini_bingo_ended",
            entity_type="game",
            entity_id=str(telegram_id),
            metadata={'duration': game_session.get('started_at')}
        )
    
    return {'success': True, 'message': 'Game session ended'}


def generate_random_cartela() -> List[List[int]]:
    """Generate a random 5x5 bingo cartela following BINGO column rules"""
    cartela = []
    
    # Column ranges: B(1-15), I(16-30), N(31-45), G(46-60), O(61-75)
    column_ranges = [
        (1, 15),    # B
        (16, 30),   # I
        (31, 45),   # N
        (46, 60),   # G
        (61, 75)    # O
    ]
    
    for col in range(MINI_BINGO_GRID_SIZE):
        col_numbers = []
        min_val, max_val = column_ranges[col]
        
        for row in range(MINI_BINGO_GRID_SIZE):
            if row == 2 and col == 2:
                # Free space (center)
                col_numbers.append(0)
            else:
                # Generate unique number for this column
                available = list(range(min_val, max_val + 1))
                # Remove already used numbers in this column
                for used in col_numbers:
                    if used in available:
                        available.remove(used)
                num = random.choice(available)
                col_numbers.append(num)
        
        cartela.append(col_numbers)
    
    return cartela


def find_winning_line(cartela: List[List[int]], called_numbers: List[int]) -> Optional[str]:
    """
    Check if there's a winning line on the cartela.
    Returns the pattern name if win, None otherwise.
    """
    called_set = set(called_numbers)
    
    # Check rows (horizontal)
    for row in range(MINI_BINGO_GRID_SIZE):
        row_complete = True
        for col in range(MINI_BINGO_GRID_SIZE):
            value = cartela[col][row]
            if value != 0 and value not in called_set:
                row_complete = False
                break
        if row_complete:
            return f"horizontal_row_{row + 1}"
    
    # Check columns (vertical)
    for col in range(MINI_BINGO_GRID_SIZE):
        col_complete = True
        for row in range(MINI_BINGO_GRID_SIZE):
            value = cartela[col][row]
            if value != 0 and value not in called_set:
                col_complete = False
                break
        if col_complete:
            return f"vertical_col_{col + 1}"
    
    # Check main diagonal (top-left to bottom-right)
    diag_complete = True
    for i in range(MINI_BINGO_GRID_SIZE):
        value = cartela[i][i]
        if value != 0 and value not in called_set:
            diag_complete = False
            break
    if diag_complete:
        return "diagonal_main"
    
    # Check anti-diagonal (top-right to bottom-left)
    anti_diag_complete = True
    for i in range(MINI_BINGO_GRID_SIZE):
        value = cartela[i][MINI_BINGO_GRID_SIZE - 1 - i]
        if value != 0 and value not in called_set:
            anti_diag_complete = False
            break
    if anti_diag_complete:
        return "diagonal_anti"
    
    return None


async def mini_bingo_rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mini bingo game rules"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    rules_text = (
        f"{get_emoji('info')} *MINI BINGO RULES* {get_emoji('info')}\n\n"
        
        f"*🎯 What is Mini Bingo?*\n"
        f"Mini Bingo is a single-player practice game that simulates the real bingo experience.\n\n"
        
        f"*📋 How to Play:*\n"
        f"1️⃣ Click PLAY MINI BINGO\n"
        f"2️⃣ Game deducts `{MINI_BINGO_PRICE}` ETB from your balance\n"
        f"3️⃣ A random 5x5 cartela is generated\n"
        f"4️⃣ Numbers are called one by one\n"
        f"5️⃣ Marked numbers turn green automatically\n"
        f"6️⃣ Complete a line (horizontal, vertical, or diagonal) to win!\n\n"
        
        f"*💰 Winning:*\n"
        f"• Win rate: `{MINI_BINGO_WIN_PERCENTAGE}%`\n"
        f"• Win amount: `{MINI_BINGO_PRICE * MINI_BINGO_WIN_PERCENTAGE // 100}` ETB\n"
        f"• Winnings credited instantly to your balance\n\n"
        
        f"*🎮 Differences from Advanced Bingo:*\n"
        f"• Single-player only (no competition)\n"
        f"• No cartela selection (random cartela)\n"
        f"• Fixed win percentage\n"
        f"• Shorter game duration\n\n"
        
        f"{get_emoji('game')} *Ready to play?* Use /mini_bingo to start!\n"
        f"{get_emoji('trophy')} Or try the Advanced Bingo with /play for real-time multiplayer!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{get_emoji('game')} Play Mini Bingo", callback_data="play_mini_bingo")],
        [InlineKeyboardButton(f"{get_emoji('trophy')} Play Advanced", callback_data="play_advanced")],
        [InlineKeyboardButton(f"{get_emoji('back')} Back", callback_data="back_to_mini_bingo")]
    ])
    
    await query.edit_message_text(
        rules_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def play_mini_bingo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle play mini bingo button click"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    # Call mini_bingo function
    await mini_bingo(update, context)


async def back_to_mini_bingo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to mini bingo menu"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    user = await UserRepository.get_by_telegram_id(telegram_id)
    lang = user.get('lang', 'en') if user else 'en'
    
    await mini_bingo(update, context)


async def generate_mini_bingo_token(telegram_id: int) -> str:
    """Generate a simple token for mini bingo game (no JWT needed for simple game)"""
    import hashlib
    import time
    
    timestamp = int(time.time())
    data = f"{telegram_id}:{timestamp}:mini_bingo"
    token = hashlib.md5(data.encode()).hexdigest()[:16]
    
    return token


# Admin command to adjust mini bingo settings
async def set_mini_bingo_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set mini bingo game settings (admin only)"""
    telegram_id = update.effective_user.id
    
    if str(telegram_id) != str(config.ADMIN_CHAT_ID):
        await update.message.reply_text("Unauthorized.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            f"{get_emoji('error')} *Usage:* `/set_mini_bingo <price|win_percent> <value>`\n\n"
            f"Examples:\n"
            f"• `/set_mini_bingo price 10` - Set game price to 10 ETB\n"
            f"• `/set_mini_bingo win_percent 75` - Set win percentage to 75%",
            parse_mode='Markdown'
        )
        return
    
    setting = args[0].lower()
    try:
        value = int(args[1])
    except ValueError:
        await update.message.reply_text(f"{get_emoji('error')} Invalid value.")
        return
    
    global MINI_BINGO_PRICE, MINI_BINGO_WIN_PERCENTAGE
    
    if setting == 'price':
        MINI_BINGO_PRICE = value
        await update.message.reply_text(
            f"{get_emoji('success')} Mini bingo price set to `{MINI_BINGO_PRICE}` ETB.",
            parse_mode='Markdown'
        )
    elif setting == 'win_percent':
        if value < 1 or value > 100:
            await update.message.reply_text(f"{get_emoji('error')} Win percentage must be between 1 and 100.")
            return
        MINI_BINGO_WIN_PERCENTAGE = value
        await update.message.reply_text(
            f"{get_emoji('success')} Mini bingo win percentage set to `{MINI_BINGO_WIN_PERCENTAGE}%`.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"{get_emoji('error')} Unknown setting. Use `price` or `win_percent`.")


# Export all
__all__ = [
    'mini_bingo',
    'play_mini_bingo_game',
    'check_mini_bingo_win',
    'end_mini_bingo_game',
    'mini_bingo_rules_callback',
    'play_mini_bingo_callback',
    'back_to_mini_bingo_callback',
    'set_mini_bingo_settings',
    'MINI_BINGO_PRICE',
    'MINI_BINGO_WIN_PERCENTAGE',
]