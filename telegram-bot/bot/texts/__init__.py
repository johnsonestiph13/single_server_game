# telegram-bot/bot/texts/__init__.py
# Estif Bingo 24/7 - Texts Package
# Exports all text-related modules for localization and emojis

import logging
from typing import Dict, Optional

# Setup package logger
logger = logging.getLogger(__name__)

# ==================== EMOJIS ====================

from bot.texts.emojis import (
    # Dictionaries
    EMOJIS,  # ← MAKE SURE THIS IS IMPORTED
    ALL_EMOJIS,
    BASIC_EMOJIS,
    GAME_EMOJIS,
    FINANCIAL_EMOJIS,
    USER_EMOJIS,
    ACTION_EMOJIS,
    STATUS_EMOJIS,
    COMMUNICATION_EMOJIS,
    TIME_EMOJIS,
    NATURE_EMOJIS,
    FOOD_EMOJIS,
    TRAVEL_EMOJIS,
    FLAG_EMOJIS,
    NUMBER_EMOJIS,
    LETTER_EMOJIS,
    MEDAL_EMOJIS,
    ALL_EMOJIS,
    
    # Functions
    get_emoji,
    get_number_emoji,
    get_letter_emoji,
    get_medal_emoji,
    get_random_emoji,
    get_win_emoji,
    get_bet_emoji,
    get_timer_emoji,
    format_with_emoji,
    format_success,
    format_error,
    format_warning,
    format_info,
    get_loading_animation,
    get_progress_bar,
    get_star_rating,
    
    # Constants
    CHECK,
    ERROR,
    WARNING,
    INFO,
    STAR,
    HEART,
    FIRE,
    GAME,
    BINGO,
    CARTELA,
    NUMBERS,
    DRAW,
    WIN,
    TROPHY,
    LEADERBOARD,
    TIMER,
    MONEY,
    DEPOSIT,
    WITHDRAW,
    TRANSFER,
    BALANCE,
    BANK,
    RECEIPT,
    USER,
    USERS,
    ADMIN,
    PHONE,
    EMAIL,
    ID,
    CLICK,
    SELECT,
    CONFIRM,
    CANCEL,
    SEND,
    COPY,
    SEARCH,
    SHARE,
    LINK,
    SUCCESS,
    FAILURE,
    PENDING,
    ACTIVE,
    INACTIVE,
    LOCKED,
    CHAT,
    NOTIFICATION,
    ANNOUNCEMENT,
    SUPPORT,
    HELP,
    ETHIOPIA,
    KENYA,
    USA,
    UK,
)

# ==================== GAME TEXTS ====================

from bot.texts.game_texts import (
    # Message dictionaries
    GAME_STATUS_MESSAGES,
    WINNER_MESSAGES,
    CARTELA_MESSAGES,
    NUMBER_MESSAGES,
    WIN_PATTERN_MESSAGES,
    LEADERBOARD_MESSAGES,
    HISTORY_MESSAGES,
    SOUND_MESSAGES,
    GAME_HELP_MESSAGES,
    
    # Helper functions
    get_medal_emoji as game_get_medal_emoji,
    format_leaderboard_entry,
    format_game_status_message,
    format_winner_message,
    format_cartela_message,
    format_number_message,
    format_win_pattern,
)

# ==================== LOCALES ====================

from bot.texts.locales import (
    ENGLISH_TEXTS,
    AMHARIC_TEXTS,
    TEXTS,
    get_text,
    get_language_name,
)

# ==================== CONVENIENCE FUNCTIONS ====================

def get_localized_text(key: str, lang: str = 'en', **kwargs) -> str:
    """
    Get localized text (alias for get_text).
    
    Args:
        key: Text key
        lang: Language code ('en' or 'am')
        **kwargs: Format parameters
    
    Returns:
        str: Localized and formatted text
    """
    return get_text(key, lang, **kwargs)


def get_welcome_message(lang: str = 'en', **kwargs) -> str:
    """Get welcome message."""
    return get_text('welcome', lang, **kwargs)


def get_error_message(error_type: str, lang: str = 'en', **kwargs) -> str:
    """Get error message by type."""
    error_key = f'error_{error_type}'
    return get_text(error_key, lang, **kwargs)


def get_success_message(success_type: str, lang: str = 'en', **kwargs) -> str:
    """Get success message by type."""
    success_key = f'success_{success_type}'
    return get_text(success_key, lang, **kwargs)


def get_button_text(button_name: str, lang: str = 'en') -> str:
    """Get button text."""
    button_key = f'btn_{button_name}'
    return get_text(button_key, lang)


# ==================== DEFAULT TEXTS ====================

# Default text for when a key is not found
DEFAULT_TEXT = {
    'en': "Text not found",
    'am': "ጽሁፍ አልተገኘም",
}

# Available languages
AVAILABLE_LANGUAGES = {
    'en': {
        'name': 'English',
        'flag': '🇬🇧',
        'code': 'en'
    },
    'am': {
        'name': 'አማርኛ',
        'flag': '🇪🇹',
        'code': 'am'
    }
}


def get_available_languages() -> Dict[str, Dict]:
    """Get available languages with their details."""
    return AVAILABLE_LANGUAGES


def is_language_supported(lang: str) -> bool:
    """Check if a language is supported."""
    return lang in AVAILABLE_LANGUAGES


# ==================== PACKAGE EXPORTS ====================

__all__ = [
    # Emojis
    'EMOJIS',  # ← MAKE SURE THIS IS IMPORTED
    'BASIC_EMOJIS',
    'GAME_EMOJIS',
    'FINANCIAL_EMOJIS',
    'USER_EMOJIS',
    'ACTION_EMOJIS',
    'STATUS_EMOJIS',
    'COMMUNICATION_EMOJIS',
    'TIME_EMOJIS',
    'NATURE_EMOJIS',
    'FOOD_EMOJIS',
    'TRAVEL_EMOJIS',
    'FLAG_EMOJIS',
    'NUMBER_EMOJIS',
    'LETTER_EMOJIS',
    'MEDAL_EMOJIS',
    'ALL_EMOJIS',
    'get_emoji',
    'get_number_emoji',
    'get_letter_emoji',
    'get_medal_emoji',
    'get_random_emoji',
    'get_win_emoji',
    'get_bet_emoji',
    'get_timer_emoji',
    'format_with_emoji',
    'format_success',
    'format_error',
    'format_warning',
    'format_info',
    'get_loading_animation',
    'get_progress_bar',
    'get_star_rating',
    'CHECK',
    'ERROR',
    'WARNING',
    'INFO',
    'STAR',
    'HEART',
    'FIRE',
    'GAME',
    'BINGO',
    'CARTELA',
    'NUMBERS',
    'DRAW',
    'WIN',
    'TROPHY',
    'LEADERBOARD',
    'TIMER',
    'MONEY',
    'DEPOSIT',
    'WITHDRAW',
    'TRANSFER',
    'BALANCE',
    'BANK',
    'RECEIPT',
    'USER',
    'USERS',
    'ADMIN',
    'PHONE',
    'EMAIL',
    'ID',
    'CLICK',
    'SELECT',
    'CONFIRM',
    'CANCEL',
    'SEND',
    'COPY',
    'SEARCH',
    'SHARE',
    'LINK',
    'SUCCESS',
    'FAILURE',
    'PENDING',
    'ACTIVE',
    'INACTIVE',
    'LOCKED',
    'CHAT',
    'NOTIFICATION',
    'ANNOUNCEMENT',
    'SUPPORT',
    'HELP',
    'ETHIOPIA',
    'KENYA',
    'USA',
    'UK',
    
    # Game Texts
    'GAME_STATUS_MESSAGES',
    'WINNER_MESSAGES',
    'CARTELA_MESSAGES',
    'NUMBER_MESSAGES',
    'WIN_PATTERN_MESSAGES',
    'LEADERBOARD_MESSAGES',
    'HISTORY_MESSAGES',
    'SOUND_MESSAGES',
    'GAME_HELP_MESSAGES',
    'game_get_medal_emoji',
    'format_leaderboard_entry',
    'format_game_status_message',
    'format_winner_message',
    'format_cartela_message',
    'format_number_message',
    'format_win_pattern',
    
    # Locales
    'ENGLISH_TEXTS',
    'AMHARIC_TEXTS',
    'TEXTS',
    'get_text',
    'get_language_name',
    
    # Convenience Functions
    'get_localized_text',
    'get_welcome_message',
    'get_error_message',
    'get_success_message',
    'get_button_text',
    
    # Defaults
    'DEFAULT_TEXT',
    'AVAILABLE_LANGUAGES',
    'get_available_languages',
    'is_language_supported',
]

logger.info("Texts package initialized")