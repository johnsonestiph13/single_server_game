# telegram-bot/bot/texts/emojis.py
# Estif Bingo 24/7 - Emoji Mappings
# Centralized emoji management for consistent use across the bot

import random
from typing import Dict, Optional

# ==================== EMOJI DICTIONARIES ====================

# Basic emojis
BASIC_EMOJIS = {
    'check': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'question': '❓',
    'star': '⭐',
    'heart': '❤️',
    'fire': '🔥',
    'new': '🆕',
    'soon': '🔜',
    'new_year': '🎆',
}

# Game emojis
GAME_EMOJIS = {
    'game': '🎮',
    'bingo': '🎯',
    'cartela': '🎴',
    'numbers': '🔢',
    'draw': '🎲',
    'win': '🏆',
    'trophy': '🏆',
    'medal': '🏅',
    'leaderboard': '📊',
    'timer': '⏱️',
    'clock': '⏰',
    'stopwatch': '⏱️',
    'play': '▶️',
    'pause': '⏸️',
    'stop': '⏹️',
    'reset': '🔄',
    'refresh': '🔄',
    'next': '⏩',
    'previous': '⏪',
    'fast_forward': '⏩',
    'rewind': '⏪',
}

# Financial emojis
FINANCIAL_EMOJIS = {
    'money': '💰',
    'money_bag': '💰',
    'deposit': '💳',
    'withdraw': '💸',
    'cashout': '💸',
    'transfer': '💸',
    'balance': '💵',
    'wallet': '👛',
    'bank': '🏦',
    'credit_card': '💳',
    'payment': '💳',
    'receipt': '🧾',
    'tax': '📊',
    'chart': '📈',
    'graph': '📊',
}

# User emojis
USER_EMOJIS = {
    'user': '👤',
    'users': '👥',
    'admin': '👑',
    'moderator': '🛡️',
    'verified': '✅',
    'unverified': '❌',
    'phone': '📱',
    'email': '📧',
    'location': '📍',
    'id': '🆔',
    'username': '@',
    'name': '📝',
    'birthday': '🎂',
    'age': '📅',
    'gender': '⚥',
}

# Action emojis
ACTION_EMOJIS = {
    'click': '🖱️',
    'tap': '👆',
    'swipe': '👉',
    'drag': '✋',
    'select': '✅',
    'unselect': '❌',
    'confirm': '✔️',
    'cancel': '✖️',
    'submit': '📤',
    'send': '📤',
    'receive': '📥',
    'download': '⬇️',
    'upload': '⬆️',
    'save': '💾',
    'delete': '🗑️',
    'edit': '✏️',
    'copy': '📋',
    'paste': '📋',
    'cut': '✂️',
    'search': '🔍',
    'filter': '🔎',
    'sort': '🔃',
    'share': '📤',
    'link': '🔗',
    'url': '🌐',
}

# Status emojis
STATUS_EMOJIS = {
    'success': '✅',
    'failure': '❌',
    'pending': '⏳',
    'processing': '⚙️',
    'completed': '✔️',
    'cancelled': '🚫',
    'expired': '⌛',
    'active': '🟢',
    'inactive': '🔴',
    'online': '🟢',
    'offline': '🔴',
    'busy': '🟡',
    'away': '🟠',
    'locked': '🔒',
    'unlocked': '🔓',
    'secure': '🔒',
    'warning_status': '⚠️',
    'error_status': '💥',
}

# Communication emojis
COMMUNICATION_EMOJIS = {
    'chat': '💬',
    'message': '💬',
    'sms': '📱',
    'call': '📞',
    'video_call': '📹',
    'notification': '🔔',
    'bell': '🔔',
    'alert': '🚨',
    'announcement': '📢',
    'broadcast': '📡',
    'news': '📰',
    'support': '🎧',
    'help': '🆘',
    'faq': '❓',
    'feedback': '💬',
    'complaint': '🗣️',
    'suggestion': '💡',
}

# Time emojis
TIME_EMOJIS = {
    'calendar': '📅',
    'date': '📅',
    'time': '⏰',
    'hour': '🕐',
    'minute': '⏱️',
    'second': '⏲️',
    'morning': '🌅',
    'afternoon': '🌞',
    'evening': '🌆',
    'night': '🌙',
    'midnight': '🕛',
    'today': '📅',
    'tomorrow': '📅',
    'yesterday': '📅',
}

# Nature emojis
NATURE_EMOJIS = {
    'sun': '☀️',
    'moon': '🌙',
    'star_nature': '⭐',
    'cloud': '☁️',
    'rain': '🌧️',
    'snow': '❄️',
    'thunder': '⚡',
    'lightning': '⚡',
    'flower': '🌸',
    'tree': '🌳',
    'leaf': '🍃',
    'fruit': '🍎',
    'vegetable': '🥕',
    'animal': '🐕',
    'bird': '🐦',
    'fish': '🐟',
}

# Food emojis
FOOD_EMOJIS = {
    'pizza': '🍕',
    'burger': '🍔',
    'fries': '🍟',
    'hotdog': '🌭',
    'taco': '🌮',
    'burrito': '🌯',
    'sushi': '🍣',
    'rice': '🍚',
    'noodles': '🍜',
    'soup': '🥣',
    'salad': '🥗',
    'cake': '🍰',
    'ice_cream': '🍦',
    'coffee': '☕',
    'tea': '🍵',
    'water': '💧',
    'beer': '🍺',
    'wine': '🍷',
}

# Travel emojis
TRAVEL_EMOJIS = {
    'car': '🚗',
    'bus': '🚌',
    'train': '🚆',
    'plane': '✈️',
    'boat': '⛵',
    'ship': '🚢',
    'bike': '🚲',
    'motorcycle': '🏍️',
    'taxi': '🚕',
    'ambulance': '🚑',
    'fire_truck': '🚒',
    'police': '🚓',
    'airport': '🛫',
    'hotel': '🏨',
    'beach': '🏖️',
    'mountain': '⛰️',
    'forest': '🌲',
    'city': '🏙️',
    'village': '🏘️',
}

# Flag emojis
FLAG_EMOJIS = {
    'ethiopia': '🇪🇹',
    'kenya': '🇰🇪',
    'usa': '🇺🇸',
    'uk': '🇬🇧',
    'canada': '🇨🇦',
    'australia': '🇦🇺',
    'germany': '🇩🇪',
    'france': '🇫🇷',
    'italy': '🇮🇹',
    'spain': '🇪🇸',
    'japan': '🇯🇵',
    'china': '🇨🇳',
    'india': '🇮🇳',
    'brazil': '🇧🇷',
    'russia': '🇷🇺',
    'south_africa': '🇿🇦',
    'nigeria': '🇳🇬',
    'egypt': '🇪🇬',
}

# Number emojis (0-9)
NUMBER_EMOJIS = {
    0: '0️⃣',
    1: '1️⃣',
    2: '2️⃣',
    3: '3️⃣',
    4: '4️⃣',
    5: '5️⃣',
    6: '6️⃣',
    7: '7️⃣',
    8: '8️⃣',
    9: '9️⃣',
}

# Letter emojis (A-Z)
LETTER_EMOJIS = {
    'a': '🇦',
    'b': '🇧',
    'c': '🇨',
    'd': '🇩',
    'e': '🇪',
    'f': '🇫',
    'g': '🇬',
    'h': '🇭',
    'i': '🇮',
    'j': '🇯',
    'k': '🇰',
    'l': '🇱',
    'm': '🇲',
    'n': '🇳',
    'o': '🇴',
    'p': '🇵',
    'q': '🇶',
    'r': '🇷',
    's': '🇸',
    't': '🇹',
    'u': '🇺',
    'v': '🇻',
    'w': '🇼',
    'x': '🇽',
    'y': '🇾',
    'z': '🇿',
}

# Medal emojis by rank
MEDAL_EMOJIS = {
    1: '🥇',
    2: '🥈',
    3: '🥉',
    4: '🏅',
    5: '🎖️',
}

# ==================== COMBINED EMOJI MAP ====================

ALL_EMOJIS = {
    **BASIC_EMOJIS,
    **GAME_EMOJIS,
    **FINANCIAL_EMOJIS,
    **USER_EMOJIS,
    **ACTION_EMOJIS,
    **STATUS_EMOJIS,
    **COMMUNICATION_EMOJIS,
    **TIME_EMOJIS,
    **NATURE_EMOJIS,
    **FOOD_EMOJIS,
    **TRAVEL_EMOJIS,
    **FLAG_EMOJIS,
}

# Alias for backward compatibility
    EMOJIS = ALL_EMOJIS
# ==================== EMOJI FUNCTIONS ====================

def get_emoji(key: str, default: str = '📌') -> str:
    """
    Get emoji by key.
    
    Args:
        key: Emoji key (e.g., 'game', 'money', 'success')
        default: Default emoji if key not found
    
    Returns:
        str: Emoji character
    """
    return ALL_EMOJIS.get(key, default)


def get_number_emoji(number: int) -> str:
    """
    Get emoji for a number (0-9).
    
    Args:
        number: Number (0-9)
    
    Returns:
        str: Number emoji
    """
    return NUMBER_EMOJIS.get(number, f"{number}️⃣" if 0 <= number <= 9 else "🔢")


def get_letter_emoji(letter: str) -> str:
    """
    Get emoji for a letter (A-Z).
    
    Args:
        letter: Letter (A-Z, case insensitive)
    
    Returns:
        str: Letter emoji
    """
    letter_lower = letter.lower()
    return LETTER_EMOJIS.get(letter_lower, "🔤")


def get_medal_emoji(rank: int) -> str:
    """
    Get medal emoji by rank.
    
    Args:
        rank: Rank position (1 = gold, 2 = silver, 3 = bronze, etc.)
    
    Returns:
        str: Medal emoji
    """
    return MEDAL_EMOJIS.get(rank, MEDAL_EMOJIS.get(4, '🏅'))


def get_random_emoji(category: Optional[str] = None) -> str:
    """
    Get a random emoji, optionally from a specific category.
    
    Args:
        category: Optional category (basic, game, financial, user, action, status, communication)
    
    Returns:
        str: Random emoji
    """
    if category == 'basic':
        return random.choice(list(BASIC_EMOJIS.values()))
    elif category == 'game':
        return random.choice(list(GAME_EMOJIS.values()))
    elif category == 'financial':
        return random.choice(list(FINANCIAL_EMOJIS.values()))
    elif category == 'user':
        return random.choice(list(USER_EMOJIS.values()))
    elif category == 'action':
        return random.choice(list(ACTION_EMOJIS.values()))
    elif category == 'status':
        return random.choice(list(STATUS_EMOJIS.values()))
    elif category == 'communication':
        return random.choice(list(COMMUNICATION_EMOJIS.values()))
    else:
        return random.choice(list(ALL_EMOJIS.values()))


def get_win_emoji(amount: float) -> str:
    """
    Get appropriate win emoji based on amount.
    
    Args:
        amount: Win amount
    
    Returns:
        str: Win emoji
    """
    if amount >= 1000:
        return "💎"
    elif amount >= 500:
        return "🏆"
    elif amount >= 100:
        return "🎉"
    elif amount >= 50:
        return "🎊"
    else:
        return "🎁"


def get_bet_emoji(amount: float) -> str:
    """
    Get appropriate bet emoji based on amount.
    
    Args:
        amount: Bet amount
    
    Returns:
        str: Bet emoji
    """
    if amount >= 100:
        return "💎"
    elif amount >= 50:
        return "💰"
    elif amount >= 20:
        return "💵"
    else:
        return "🎴"


def get_timer_emoji(seconds_remaining: int) -> str:
    """
    Get appropriate timer emoji based on time remaining.
    
    Args:
        seconds_remaining: Seconds remaining on timer
    
    Returns:
        str: Timer emoji
    """
    if seconds_remaining <= 0:
        return "⏰"
    elif seconds_remaining <= 10:
        return "⚠️"
    elif seconds_remaining <= 30:
        return "⏱️"
    else:
        return "⏳"


def format_with_emoji(text: str, emoji_key: str) -> str:
    """
    Format text with emoji prefix.
    
    Args:
        text: Text to format
        emoji_key: Emoji key to use as prefix
    
    Returns:
        str: Formatted text with emoji
    """
    emoji = get_emoji(emoji_key)
    return f"{emoji} {text}"


def format_success(text: str) -> str:
    """Format success message with check emoji."""
    return format_with_emoji(text, 'success')


def format_error(text: str) -> str:
    """Format error message with error emoji."""
    return format_with_emoji(text, 'error')


def format_warning(text: str) -> str:
    """Format warning message with warning emoji."""
    return format_with_emoji(text, 'warning')


def format_info(text: str) -> str:
    """Format info message with info emoji."""
    return format_with_emoji(text, 'info')


# ==================== EMOJI SEQUENCES ====================

def get_loading_animation() -> list:
    """Get loading animation emoji sequence."""
    return ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]


def get_progress_bar(percentage: int, width: int = 10) -> str:
    """
    Create a progress bar with emojis.
    
    Args:
        percentage: Completion percentage (0-100)
        width: Width of the progress bar in characters
    
    Returns:
        str: Progress bar string
    """
    filled = int(width * percentage / 100)
    empty = width - filled
    
    return "█" * filled + "░" * empty


def get_star_rating(rating: float, max_rating: int = 5) -> str:
    """
    Create a star rating display.
    
    Args:
        rating: Rating value
        max_rating: Maximum rating
    
    Returns:
        str: Star rating string
    """
    full_stars = int(rating)
    half_star = 1 if rating - full_stars >= 0.5 else 0
    empty_stars = max_rating - full_stars - half_star
    
    return "⭐" * full_stars + "✨" * half_star + "☆" * empty_stars


# ==================== EMOJI CONSTANTS FOR EASY ACCESS ====================

# Common emoji constants (for convenience)
CHECK = get_emoji('check')
ERROR = get_emoji('error')
WARNING = get_emoji('warning')
INFO = get_emoji('info')
STAR = get_emoji('star')
HEART = get_emoji('heart')
FIRE = get_emoji('fire')

# Game emojis
GAME = get_emoji('game')
BINGO = get_emoji('bingo')
CARTELA = get_emoji('cartela')
NUMBERS = get_emoji('numbers')
DRAW = get_emoji('draw')
WIN = get_emoji('win')
TROPHY = get_emoji('trophy')
LEADERBOARD = get_emoji('leaderboard')
TIMER = get_emoji('timer')

# Financial emojis
MONEY = get_emoji('money')
DEPOSIT = get_emoji('deposit')
WITHDRAW = get_emoji('withdraw')
TRANSFER = get_emoji('transfer')
BALANCE = get_emoji('balance')
BANK = get_emoji('bank')
RECEIPT = get_emoji('receipt')

# User emojis
USER = get_emoji('user')
USERS = get_emoji('users')
ADMIN = get_emoji('admin')
PHONE = get_emoji('phone')
EMAIL = get_emoji('email')
ID = get_emoji('id')

# Action emojis
CLICK = get_emoji('click')
SELECT = get_emoji('select')
CONFIRM = get_emoji('confirm')
CANCEL = get_emoji('cancel')
SEND = get_emoji('send')
COPY = get_emoji('copy')
SEARCH = get_emoji('search')
SHARE = get_emoji('share')
LINK = get_emoji('link')

# Status emojis
SUCCESS = get_emoji('success')
FAILURE = get_emoji('failure')
PENDING = get_emoji('pending')
ACTIVE = get_emoji('active')
INACTIVE = get_emoji('inactive')
LOCKED = get_emoji('locked')

# Communication emojis
CHAT = get_emoji('chat')
NOTIFICATION = get_emoji('notification')
ANNOUNCEMENT = get_emoji('announcement')
SUPPORT = get_emoji('support')
HELP = get_emoji('help')

# Flag emojis
ETHIOPIA = get_emoji('ethiopia')
KENYA = get_emoji('kenya')
USA = get_emoji('usa')
UK = get_emoji('uk')


# ==================== EXPORTS ====================

__all__ = [
    # Dictionaries
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
    'EMOJIS',
    'ALL_EMOJIS',
    
    # Functions
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
    
    # Constants
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
]