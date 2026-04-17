# telegram-bot/bot/keyboards/__init__.py
# Estif Bingo 24/7 - Keyboards Package
# Exports all keyboard functions for menus and interactions

import logging
from bot.texts.emojis import get_emoji

logger = logging.getLogger(__name__)


# ==================== MAIN MENU KEYBOARDS ====================

from bot.keyboards.menu import (
    main_menu_keyboard,
    reply_menu_keyboard,
    deposit_methods_keyboard,
    deposit_amount_keyboard,
    cashout_methods_keyboard,
    cashout_amount_keyboard,
    transfer_amount_keyboard,
    settings_keyboard,
    language_keyboard,
    bonus_keyboard,
    admin_panel_keyboard,
    admin_users_keyboard,
    admin_deposit_keyboard,
    admin_withdrawal_keyboard,
    confirmation_keyboard,
    pagination_keyboard,
    back_to_menu_keyboard,
    cancel_keyboard,
)


# ==================== GAME KEYBOARDS ====================

from bot.keyboards.game_keyboards import (
    game_control_keyboard,
    cartela_action_keyboard,
    selection_confirmation_keyboard,
    number_caller_keyboard,
    winner_announcement_keyboard,
    sound_pack_keyboard,
    leaderboard_type_keyboard,
    game_history_keyboard,
    game_control_admin_keyboard,
    win_percentage_keyboard,
    insufficient_balance_keyboard,
    game_in_progress_keyboard,
)


# ==================== CONVENIENCE FUNCTIONS ====================

def get_menu_keyboard(lang: str = 'en', is_admin: bool = False):
    """
    Get the main menu keyboard based on language and admin status.
    
    Args:
        lang: Language code ('en' or 'am')
        is_admin: Whether user is admin
    
    Returns:
        InlineKeyboardMarkup: Main menu keyboard
    """
    return main_menu_keyboard(lang, is_admin)


def get_reply_keyboard(lang: str = 'en'):
    """
    Get the reply keyboard for quick commands.
    
    Args:
        lang: Language code
    
    Returns:
        ReplyKeyboardMarkup: Reply keyboard
    """
    return reply_menu_keyboard(lang)


def get_deposit_keyboard(lang: str = 'en'):
    """
    Get deposit methods keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Deposit methods keyboard
    """
    return deposit_methods_keyboard(lang)


def get_cashout_keyboard(lang: str = 'en'):
    """
    Get cashout methods keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Cashout methods keyboard
    """
    return cashout_methods_keyboard(lang)


def get_settings_keyboard(lang: str = 'en'):
    """
    Get settings menu keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Settings keyboard
    """
    return settings_keyboard(lang)


def get_bonus_keyboard(lang: str = 'en', has_welcome: bool = True, has_daily: bool = False):
    """
    Get bonus menu keyboard.
    
    Args:
        lang: Language code
        has_welcome: Whether welcome bonus is available
        has_daily: Whether daily bonus is available
    
    Returns:
        InlineKeyboardMarkup: Bonus keyboard
    """
    return bonus_keyboard(lang, has_welcome, has_daily)


def get_admin_keyboard(lang: str = 'en'):
    """
    Get admin panel keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Admin panel keyboard
    """
    return admin_panel_keyboard(lang)


def get_game_keyboard(lang: str = 'en', is_admin: bool = False):
    """
    Get game control keyboard.
    
    Args:
        lang: Language code
        is_admin: Whether user is admin
    
    Returns:
        InlineKeyboardMarkup: Game control keyboard
    """
    if is_admin:
        return game_control_admin_keyboard(lang)
    return game_control_keyboard(lang)


def get_sound_pack_keyboard(current_pack: str = 'pack1', lang: str = 'en'):
    """
    Get sound pack selection keyboard.
    
    Args:
        current_pack: Currently selected sound pack
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Sound pack keyboard
    """
    return sound_pack_keyboard(current_pack, lang)


def get_leaderboard_keyboard(current_type: str = 'balance', lang: str = 'en'):
    """
    Get leaderboard type selection keyboard.
    
    Args:
        current_type: Currently selected leaderboard type
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Leaderboard type keyboard
    """
    return leaderboard_type_keyboard(current_type, lang)


def get_insufficient_balance_keyboard(lang: str = 'en'):
    """
    Get insufficient balance keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Insufficient balance keyboard
    """
    return insufficient_balance_keyboard(lang)


def get_game_in_progress_keyboard(lang: str = 'en'):
    """
    Get game in progress keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Game in progress keyboard
    """
    return game_in_progress_keyboard(lang)


# ==================== KEYBOARD DICTIONARY ====================

# Dictionary mapping keyboard names to their functions for dynamic access
KEYBOARD_MAP = {
    # Main menus
    'main_menu': main_menu_keyboard,
    'reply_menu': reply_menu_keyboard,
    
    # Deposit menus
    'deposit_methods': deposit_methods_keyboard,
    'deposit_amount': deposit_amount_keyboard,
    
    # Cashout menus
    'cashout_methods': cashout_methods_keyboard,
    'cashout_amount': cashout_amount_keyboard,
    
    # Transfer menus
    'transfer_amount': transfer_amount_keyboard,
    
    # Settings menus
    'settings': settings_keyboard,
    'language': language_keyboard,
    
    # Bonus menus
    'bonus': bonus_keyboard,
    
    # Admin menus
    'admin_panel': admin_panel_keyboard,
    'admin_users': admin_users_keyboard,
    
    # Game menus
    'game_control': game_control_keyboard,
    'game_control_admin': game_control_admin_keyboard,
    'sound_pack': sound_pack_keyboard,
    'leaderboard_type': leaderboard_type_keyboard,
    'game_history': game_history_keyboard,
    'win_percentage': win_percentage_keyboard,
    'insufficient_balance': insufficient_balance_keyboard,
    'game_in_progress': game_in_progress_keyboard,
    
    # Utility
    'confirmation': confirmation_keyboard,
    'pagination': pagination_keyboard,
    'back_to_menu': back_to_menu_keyboard,
    'cancel': cancel_keyboard,
}


def get_keyboard(keyboard_name: str, **kwargs):
    """
    Dynamically get a keyboard by name.
    
    Args:
        keyboard_name: Name of the keyboard function
        **kwargs: Arguments to pass to the keyboard function
    
    Returns:
        Keyboard: The requested keyboard
    """
    keyboard_func = KEYBOARD_MAP.get(keyboard_name)
    
    if keyboard_func:
        return keyboard_func(**kwargs)
    else:
        logger.warning(f"Keyboard '{keyboard_name}' not found")
        return back_to_menu_keyboard()


# ==================== EXPORTS ====================

__all__ = [
    # Main menu keyboards
    'main_menu_keyboard',
    'reply_menu_keyboard',
    
    # Deposit keyboards
    'deposit_methods_keyboard',
    'deposit_amount_keyboard',
    
    # Cashout keyboards
    'cashout_methods_keyboard',
    'cashout_amount_keyboard',
    
    # Transfer keyboards
    'transfer_amount_keyboard',
    
    # Settings keyboards
    'settings_keyboard',
    'language_keyboard',
    
    # Bonus keyboards
    'bonus_keyboard',
    
    # Admin keyboards
    'admin_panel_keyboard',
    'admin_users_keyboard',
    'admin_deposit_keyboard',
    'admin_withdrawal_keyboard',
    
    # Game keyboards
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
    
    # Utility keyboards
    'confirmation_keyboard',
    'pagination_keyboard',
    'back_to_menu_keyboard',
    'cancel_keyboard',
    
    # Convenience functions
    'get_menu_keyboard',
    'get_reply_keyboard',
    'get_deposit_keyboard',
    'get_cashout_keyboard',
    'get_settings_keyboard',
    'get_bonus_keyboard',
    'get_admin_keyboard',
    'get_game_keyboard',
    'get_sound_pack_keyboard',
    'get_leaderboard_keyboard',
    'get_insufficient_balance_keyboard',
    'get_game_in_progress_keyboard',
    
    # Dynamic keyboard access
    'KEYBOARD_MAP',
    'get_keyboard',
]


# ==================== LOGGER ====================

logger.info("Keyboards package initialized")