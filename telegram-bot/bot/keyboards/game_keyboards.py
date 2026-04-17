# telegram-bot/bot/keyboards/game_keyboards.py
# Estif Bingo 24/7 - Game Keyboards
# Creates inline keyboards for game-related interactions

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.texts.emojis import get_emoji


def game_control_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create game control keyboard for the game menu.
    
    Args:
        lang: Language code ('en' or 'am')
    
    Returns:
        InlineKeyboardMarkup: Game control keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('game')} Play Now",
                callback_data="play_game"
            ),
            InlineKeyboardButton(
                f"{get_emoji('info')} Game Rules",
                callback_data="game_rules"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('leaderboard')} Leaderboard",
                callback_data="leaderboard"
            ),
            InlineKeyboardButton(
                f"{get_emoji('history')} My History",
                callback_data="game_history"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('sound')} Sound Settings",
                callback_data="sound_settings"
            ),
            InlineKeyboardButton(
                f"{get_emoji('back')} Back to Menu",
                callback_data="back_to_menu"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def cartela_action_keyboard(cartela_id: int, is_selected: bool = False, lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create keyboard for individual cartela actions.
    
    Args:
        cartela_id: Cartela ID
        is_selected: Whether the cartela is already selected
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Cartela action keyboard
    """
    if is_selected:
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{get_emoji('cancel')} Unselect Cartela #{cartela_id}",
                    callback_data=f"unselect_cartela_{cartela_id}"
                )
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{get_emoji('cartela')} Select Cartela #{cartela_id}",
                    callback_data=f"select_cartela_{cartela_id}"
                )
            ]
        ]
    
    return InlineKeyboardMarkup(keyboard)


def selection_confirmation_keyboard(cartela_ids: list, lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create keyboard for confirming cartela selection.
    
    Args:
        cartela_ids: List of selected cartela IDs
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Confirmation keyboard
    """
    cartela_text = ", ".join(f"#{cid}" for cid in cartela_ids)
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('check')} Confirm Selection",
                callback_data=f"confirm_selection_{','.join(map(str, cartela_ids))}"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('cancel')} Cancel",
                callback_data="cancel_selection"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def number_caller_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create keyboard for number caller controls (admin only).
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Number caller keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('play')} Draw Next Number",
                callback_data="draw_next_number"
            ),
            InlineKeyboardButton(
                f"{get_emoji('reset')} Reset Numbers",
                callback_data="reset_numbers"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('stats')} Number Statistics",
                callback_data="number_stats"
            ),
            InlineKeyboardButton(
                f"{get_emoji('back')} Back",
                callback_data="back_to_game"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def winner_announcement_keyboard(round_id: int, lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create keyboard for winner announcement.
    
    Args:
        round_id: Round ID
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Winner announcement keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('trophy')} View Round Details",
                callback_data=f"round_details_{round_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('game')} Play Again",
                callback_data="play_game"
            ),
            InlineKeyboardButton(
                f"{get_emoji('leaderboard')} Leaderboard",
                callback_data="leaderboard"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def sound_pack_keyboard(current_pack: str = 'pack1', lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create keyboard for sound pack selection.
    
    Args:
        current_pack: Currently selected sound pack
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Sound pack keyboard
    """
    sound_packs = [
        ('pack1', 'Classic Bingo'),
        ('pack2', 'Modern Beat'),
        ('pack3', 'Arcade Fun'),
        ('pack4', 'Casino Style')
    ]
    
    keyboard = []
    for pack_id, pack_name in sound_packs:
        is_current = pack_id == current_pack
        emoji = get_emoji('check') if is_current else get_emoji('sound')
        button_text = f"{emoji} {pack_name}"
        if is_current:
            button_text += " ✓"
        
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"set_sound_pack_{pack_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('back')} Back",
            callback_data="back_to_game"
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


def leaderboard_type_keyboard(current_type: str = 'balance', lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create keyboard for leaderboard type selection.
    
    Args:
        current_type: Currently selected leaderboard type
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Leaderboard type keyboard
    """
    types = [
        ('balance', '💰 Balance'),
        ('wins', '🏆 Total Wins'),
        ('games', '🎮 Games Played')
    ]
    
    keyboard = []
    for type_id, type_name in types:
        is_current = type_id == current_type
        button_text = type_name
        if is_current:
            button_text = f"✅ {button_text}"
        
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"leaderboard_type_{type_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('refresh')} Refresh",
            callback_data="refresh_leaderboard"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('back')} Back",
            callback_data="back_to_game"
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


def game_history_keyboard(page: int = 1, total_pages: int = 1, lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create keyboard for game history pagination.
    
    Args:
        page: Current page number
        total_pages: Total number of pages
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Game history keyboard
    """
    keyboard = []
    
    # Pagination buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Previous", callback_data=f"history_page_{page - 1}")
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton("Next ▶️", callback_data=f"history_page_{page + 1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('refresh')} Refresh",
            callback_data="refresh_history"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('back')} Back",
            callback_data="back_to_game"
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


def game_control_admin_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create admin game control keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Admin game control keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('play')} Force Start Round",
                callback_data="admin_force_start"
            ),
            InlineKeyboardButton(
                f"{get_emoji('stop')} Force Stop Round",
                callback_data="admin_force_stop"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('settings')} Set Win Percentage",
                callback_data="admin_set_win_percent"
            ),
            InlineKeyboardButton(
                f"{get_emoji('sound')} Set Sound Pack",
                callback_data="admin_set_sound_pack"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('stats')} Game Stats",
                callback_data="admin_game_stats"
            ),
            InlineKeyboardButton(
                f"{get_emoji('reset')} Reset Game",
                callback_data="admin_reset_game"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('back')} Back",
                callback_data="back_to_game"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def win_percentage_keyboard(current_percent: int = 80, lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create keyboard for win percentage selection (admin only).
    
    Args:
        current_percent: Current win percentage
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Win percentage keyboard
    """
    percentages = [75, 78, 79, 80]
    
    keyboard = []
    row = []
    for percent in percentages:
        is_current = percent == current_percent
        button_text = f"{percent}%"
        if is_current:
            button_text = f"✅ {button_text}"
        
        row.append(
            InlineKeyboardButton(
                button_text,
                callback_data=f"admin_set_win_percent_{percent}"
            )
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('back')} Back",
            callback_data="admin_back_to_game"
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


def insufficient_balance_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create keyboard for insufficient balance situation.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Insufficient balance keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('deposit')} Deposit Now",
                callback_data="quick_deposit"
            ),
            InlineKeyboardButton(
                f"{get_emoji('eye')} Watch Only",
                callback_data="watch_only"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('back')} Back to Menu",
                callback_data="back_to_menu"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def game_in_progress_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create keyboard for when game is in progress.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Game in progress keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('eye')} Watch Game",
                callback_data="watch_game"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('deposit')} Deposit",
                callback_data="quick_deposit"
            ),
            InlineKeyboardButton(
                f"{get_emoji('back')} Back",
                callback_data="back_to_menu"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


# ==================== EXPORTS ====================

__all__ = [
    'game_control_keyboard',
    'cartela_action_keyboard',
    'selection_confirmation_keyboard',
    'number_caller_keyboard',
    'winner_announcement_keyboard',
    'sound_pack_keyboard',
    'leaderboard_type_keyboard',
    'game_history_keyboard',
    'game_control_admin_keyboard',
    'win_percentage_keyboard',
    'insufficient_balance_keyboard',
    'game_in_progress_keyboard',
]