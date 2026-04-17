# telegram-bot/bot/texts/game_texts.py
# Estif Bingo 24/7 - Game Text Templates
# Contains all game-related text messages and templates

from typing import Dict, Any, Optional, List
from bot.texts.emojis import get_emoji

# ==================== GAME STATUS MESSAGES ====================

GAME_STATUS_MESSAGES: Dict[str, str] = {
    'selection_start': f"{get_emoji('game')} *ROUND STARTED!*\n\n"
                       f"Selection phase has begun!\n"
                       f"You have {get_emoji('timer')} seconds to select your cartelas.\n\n"
                       f"🎯 Choose up to 4 cartelas.\n"
                       f"💰 Each cartela costs 10 ETB.\n\n"
                       f"Good luck! 🍀",
    
    'selection_end': f"{get_emoji('timer')} *SELECTION PHASE ENDED*\n\n"
                     f"Cartela selection is now closed.\n"
                     f"🎲 Number drawing will begin shortly!\n\n"
                     f"Total cartelas selected: 0\n"
                     f"Players in round: 0",
    
    'drawing_start': f"{get_emoji('draw')} *NUMBER DRAWING STARTED*\n\n"
                     f"Numbers are now being called!\n"
                     f"Watch your cartelas carefully.\n\n"
                     f"🎯 First player to complete a line wins!\n"
                     f"💰 Win rate: 80%",
    
    'drawing_number': f"{get_emoji('numbers')} *NUMBER CALLED:* `0`\n\n"
                      f"📊 Called: 0/75\n"
                      f"🎯 Mark your cartelas!",
    
    'game_end': f"{get_emoji('win')} *ROUND ENDED*\n\n"
                f"🎉 Congratulations to the winners!\n"
                f"💰 Prize pool: 0 ETB\n"
                f"👥 Winners: 0\n\n"
                f"Next round starts in 6 seconds!",
}


# ==================== WINNER MESSAGES ====================

WINNER_MESSAGES: Dict[str, str] = {
    'single_winner': f"{get_emoji('trophy')} *🎉 BINGO! 🎉*\n\n"
                     f"🎊 *WINNER!*\n"
                     f"💰 Amount: 0 ETB\n"
                     f"🎯 Pattern: Horizontal Line\n"
                     f"🃏 Cartela: #0\n\n"
                     f"Congratulations! 🎉",
    
    'multiple_winners': f"{get_emoji('trophy')} *🎉 BINGO! 🎉*\n\n"
                        f"🎊 *2 WINNERS!*\n"
                        f"💰 Each wins: 0 ETB\n"
                        f"💎 Total prize pool: 0 ETB\n\n"
                        f"Congratulations to all winners! 🎉",
    
    'you_won': f"{get_emoji('trophy')} *🎉 YOU WON! 🎉*\n\n"
               f"💰 Amount: 0 ETB\n"
               f"🎯 Pattern: Horizontal Line\n"
               f"🃏 Cartela: #0\n"
               f"📊 Total winners: 1\n\n"
               f"Your balance has been updated! 💵",
    
    'no_winner': f"{get_emoji('warning')} *NO WINNER THIS ROUND*\n\n"
                 f"😢 No one completed a line this round.\n"
                 f"💰 Prize pool will be added to next round!\n\n"
                 f"Better luck next time! 🍀",
}


# ==================== CARTELA MESSAGES ====================

CARTELA_MESSAGES: Dict[str, str] = {
    'select_prompt': f"{get_emoji('cartela')} *SELECT YOUR CARTELAS*\n\n"
                     f"Choose up to 4 cartelas from the grid below.\n"
                     f"💰 Each cartela costs 10 ETB.\n\n"
                     f"🟢 Green = Your selection\n"
                     f"🔴 Red = Taken by another player\n"
                     f"⚪ Grey = Available\n\n"
                     f"Click on a cartela to select/deselect.",
    
    'selection_success': f"{get_emoji('success')} *CARTELAS SELECTED!*\n\n"
                         f"✅ Selected 0 cartela(s)\n"
                         f"💰 Total cost: 0 ETB\n"
                         f"💵 New balance: 0 ETB\n\n"
                         f"🎯 Waiting for number drawing...",
    
    'selection_failed': f"{get_emoji('error')} *SELECTION FAILED*\n\n"
                        f"❌ An error occurred\n\n"
                        f"Please try again or contact support.",
    
    'selection_cancelled': f"{get_emoji('warning')} *SELECTION CANCELLED*\n\n"
                           f"Your cartela selection has been cancelled.\n"
                           f"💰 Refunded: 0 ETB\n\n"
                           f"Use /play to start a new game.",
    
    'max_selection_reached': f"{get_emoji('warning')} *MAX CARTELAS REACHED*\n\n"
                             f"You have already selected the maximum of 4 cartelas.\n"
                             f"Unselect some to choose different ones.",
    
    'insufficient_balance_cartela': f"{get_emoji('error')} *INSUFFICIENT BALANCE*\n\n"
                                    f"💵 Your balance: `0` ETB\n"
                                    f"💰 Required for cartela(s): `10` ETB\n\n"
                                    f"Please deposit funds to continue.",
    
    'cartela_taken': f"{get_emoji('error')} *CARTELA ALREADY TAKEN*\n\n"
                     f"🃏 Cartela #0 has already been selected by another player.\n\n"
                     f"Please choose a different cartela.",
    
    'invalid_cartela': f"{get_emoji('error')} *INVALID CARTELA*\n\n"
                       f"🃏 Cartela #0 does not exist.\n\n"
                       f"Please select a valid cartela.",
}


# ==================== NUMBER CALLING MESSAGES ====================

NUMBER_MESSAGES: Dict[str, str] = {
    'number_called': f"{get_emoji('draw')} *NUMBER:* `0`\n"
                     f"📊 *Called:* 0/75",
    
    'number_with_column': f"{get_emoji('draw')} *B0* - `0`\n"
                          f"📊 Called: 0/75",
    
    'your_number_marked': f"{get_emoji('check')} Number `0` marked on your cartela #0!",
    
    'no_numbers_left': f"{get_emoji('warning')} *NO NUMBERS LEFT*\n\n"
                       f"All 75 numbers have been called.\n"
                       f"No winner this round.\n\n"
                       f"Starting new round...",
    
    'numbers_remaining': f"{get_emoji('numbers')} *NUMBERS REMAINING:* `75`\n"
                         f"📊 Called: 0/75",
}


# ==================== WIN PATTERN MESSAGES ====================

WIN_PATTERN_MESSAGES: Dict[str, str] = {
    'horizontal': f"{get_emoji('win')} *HORIZONTAL LINE!*\n"
                  f"🎯 Row 1 completed!",
    
    'vertical': f"{get_emoji('win')} *VERTICAL LINE!*\n"
                f"🎯 Column 1 completed!",
    
    'diagonal_main': f"{get_emoji('win')} *MAIN DIAGONAL!*\n"
                     f"🎯 Top-left to bottom-right completed!",
    
    'diagonal_anti': f"{get_emoji('win')} *ANTI DIAGONAL!*\n"
                     f"🎯 Top-right to bottom-left completed!",
    
    'full_house': f"{get_emoji('trophy')} *FULL HOUSE!*\n"
                  f"🎯 All numbers marked! Incredible!",
}


# ==================== LEADERBOARD MESSAGES ====================

LEADERBOARD_MESSAGES: Dict[str, str] = {
    'title': f"{get_emoji('leaderboard')} *LEADERBOARD* {get_emoji('leaderboard')}\n\n",
    
    'balance': f"{get_emoji('money')} *TOP BY BALANCE*\n\n",
    'wins': f"{get_emoji('trophy')} *TOP BY WINS*\n\n",
    'games': f"{get_emoji('game')} *TOP BY GAMES PLAYED*\n\n",
    
    'entry': f"🥇 `1.` User - `1000`\n",
    
    'your_rank': f"\n{get_emoji('user')} *Your Rank:* `1`\n"
                 f"{get_emoji('money')} *Your Balance:* `1000` ETB\n"
                 f"{get_emoji('trophy')} *Your Wins:* `10`\n"
                 f"{get_emoji('game')} *Games Played:* `50`",
    
    'empty': f"{get_emoji('info')} No players found.\n",
}


# ==================== GAME HISTORY MESSAGES ====================

HISTORY_MESSAGES: Dict[str, str] = {
    'title': f"{get_emoji('history')} *GAME HISTORY* {get_emoji('history')}\n\n",
    
    'round_entry': f"🎯 *Round #1*\n"
                   f"📅 Date: 2024-01-01\n"
                   f"🃏 Cartelas: 2\n"
                   f"💰 Spent: 20 ETB\n"
                   f"🏆 WON: 40 ETB\n\n",
    
    'no_history': f"{get_emoji('info')} No game history found.\n\n"
                  f"Play some games to see your history!",
    
    'stats': f"\n📊 *STATISTICS*\n"
             f"🎮 Total Games: 0\n"
             f"🏆 Total Wins: 0\n"
             f"💰 Total Won: 0 ETB\n"
             f"💸 Total Spent: 0 ETB\n"
             f"📈 Net Profit: 0 ETB",
}


# ==================== SOUND SETTINGS MESSAGES ====================

SOUND_MESSAGES: Dict[str, str] = {
    'pack_changed': f"{get_emoji('success')} *SOUND PACK CHANGED*\n\n"
                    f"🎵 New sound pack: `Pack 1`\n"
                    f"🔊 Sound enabled: Yes\n\n"
                    f"Changes will apply immediately.",
    
    'sound_toggled': f"{get_emoji('success')} *SOUND ENABLED*\n\n"
                     f"🔊 Sound is now enabled.",
    
    'packs_available': f"{get_emoji('sound')} *AVAILABLE SOUND PACKS*\n\n"
                       f"🎵 *Pack 1* - Classic Bingo\n"
                       f"🎧 *Pack 2* - Modern Beat\n"
                       f"🎮 *Pack 3* - Arcade Fun\n"
                       f"🎰 *Pack 4* - Casino Style\n\n"
                       f"Use `/set_sound_pack <pack_name>` to change.",
}


# ==================== GAME HELP MESSAGES ====================

GAME_HELP_MESSAGES: Dict[str, str] = {
    'how_to_play': f"{get_emoji('info')} *HOW TO PLAY BINGO*\n\n"
                   f"1️⃣ *Selection Phase (50s)*\n"
                   f"   • Choose 1-4 cartelas\n"
                   f"   • Each cartela costs 10 ETB\n"
                   f"   • Green = Your selection\n"
                   f"   • Red = Taken by others\n"
                   f"   • Grey = Available\n\n"
                   f"2️⃣ *Drawing Phase*\n"
                   f"   • Numbers 1-75 are called randomly\n"
                   f"   • Numbers are marked automatically\n"
                   f"   • First to complete a line wins!\n\n"
                   f"3️⃣ *Winning Patterns*\n"
                   f"   • Horizontal line (any row)\n"
                   f"   • Vertical line (any column)\n"
                   f"   • Diagonal line (both directions)\n\n"
                   f"4️⃣ *Prizes*\n"
                   f"   • Prize pool = Cartelas × 10 ETB\n"
                   f"   • Win amount = Prize pool × 80%\n"
                   f"   • Split among multiple winners\n\n"
                   f"Good luck and have fun! 🍀",
    
    'game_rules': f"{get_emoji('rules')} *GAME RULES*\n\n"
                  f"📋 *Cartela Rules*\n"
                  f"• Each cartela has 25 cells (5x5 grid)\n"
                  f"• Center cell is a FREE space\n"
                  f"• Numbers are arranged by column:\n"
                  f"  - B: 1-15\n"
                  f"  - I: 16-30\n"
                  f"  - N: 31-45 (center is FREE)\n"
                  f"  - G: 46-60\n"
                  f"  - O: 61-75\n\n"
                  f"🎯 *Winning Conditions*\n"
                  f"• Complete any horizontal line\n"
                  f"• Complete any vertical line\n"
                  f"• Complete either diagonal\n\n"
                  f"💰 *Payout Structure*\n"
                  f"• 80% of total bets goes to winners\n"
                  f"• Prize split equally among winners\n"
                  f"• Winnings credited instantly\n\n"
                  f"⚡ *Real-time Features*\n"
                  f"• All players see same numbers\n"
                  f"• Instant winner detection\n"
                  f"• Automatic balance updates",
    
    'tips': f"{get_emoji('tips')} *PRO TIPS*\n\n"
            f"💡 *Strategy Tips*\n"
            f"• Select multiple cartelas for better chances\n"
            f"• Watch for patterns in called numbers\n"
            f"• Balance your cartela selection\n\n"
            f"🎯 *Game Tips*\n"
            f"• Use sound for better experience\n"
            f"• Check leaderboard for competition\n"
            f"• Review your game history\n\n"
            f"💰 *Financial Tips*\n"
            f"• Set a budget for each session\n"
            f"• Withdraw winnings regularly\n"
            f"• Take breaks between games",
}


# ==================== HELPER FUNCTIONS ====================

def get_medal_emoji(rank: int) -> str:
    """Get medal emoji based on rank."""
    if rank == 1:
        return "🥇"
    elif rank == 2:
        return "🥈"
    elif rank == 3:
        return "🥉"
    else:
        return "🎖️"


def format_leaderboard_entry(rank: int, name: str, value: str) -> str:
    """Format a leaderboard entry."""
    medal = get_medal_emoji(rank)
    return f"{medal} `{rank}.` {name} - `{value}`\n"


def format_game_status_message(status: str, **kwargs) -> str:
    """Format a game status message with variables."""
    template = GAME_STATUS_MESSAGES.get(status, "")
    return template


def format_winner_message(winner_type: str, **kwargs) -> str:
    """Format a winner message with variables."""
    template = WINNER_MESSAGES.get(winner_type, "")
    return template


def format_cartela_message(message_type: str, **kwargs) -> str:
    """Format a cartela message with variables."""
    template = CARTELA_MESSAGES.get(message_type, "")
    return template


def format_number_message(number: int, called_count: int, column: Optional[str] = None) -> str:
    """Format a number called message."""
    if column:
        return f"{get_emoji('draw')} *{column}{number}* - `{number}`\n📊 Called: {called_count}/75"
    return f"{get_emoji('draw')} *NUMBER:* `{number}`\n📊 *Called:* {called_count}/75"


def format_win_pattern(pattern: str, row: Optional[int] = None, col: Optional[int] = None) -> str:
    """Format a win pattern message."""
    if pattern == 'horizontal':
        return f"{get_emoji('win')} *HORIZONTAL LINE!*\n🎯 Row {row + 1 if row else 1} completed!"
    elif pattern == 'vertical':
        return f"{get_emoji('win')} *VERTICAL LINE!*\n🎯 Column {col + 1 if col else 1} completed!"
    elif pattern == 'diagonal_main':
        return f"{get_emoji('win')} *MAIN DIAGONAL!*\n🎯 Top-left to bottom-right completed!"
    elif pattern == 'diagonal_anti':
        return f"{get_emoji('win')} *ANTI DIAGONAL!*\n🎯 Top-right to bottom-left completed!"
    else:
        return WIN_PATTERN_MESSAGES.get(pattern, "")


# ==================== EXPORTS ====================

__all__ = [
    'GAME_STATUS_MESSAGES',
    'WINNER_MESSAGES',
    'CARTELA_MESSAGES',
    'NUMBER_MESSAGES',
    'WIN_PATTERN_MESSAGES',
    'LEADERBOARD_MESSAGES',
    'HISTORY_MESSAGES',
    'SOUND_MESSAGES',
    'GAME_HELP_MESSAGES',
    'get_medal_emoji',
    'format_leaderboard_entry',
    'format_game_status_message',
    'format_winner_message',
    'format_cartela_message',
    'format_number_message',
    'format_win_pattern',
]