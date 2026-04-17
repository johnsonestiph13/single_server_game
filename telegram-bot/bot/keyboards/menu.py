# telegram-bot/bot/keyboards/menu.py
# Estif Bingo 24/7 - Main Menu Keyboards
# Creates inline and reply keyboards for bot navigation

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from bot.texts.emojis import get_emoji


# ==================== MAIN MENU KEYBOARDS ====================

def main_menu_keyboard(lang: str = 'en', is_admin: bool = False) -> InlineKeyboardMarkup:
    """
    Create main menu inline keyboard.
    
    Args:
        lang: Language code ('en' or 'am')
        is_admin: Whether to show admin buttons
    
    Returns:
        InlineKeyboardMarkup: Main menu keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('game')} Play Bingo",
                callback_data="play_game"
            ),
            InlineKeyboardButton(
                f"{get_emoji('game')} Mini Bingo",
                callback_data="play_mini_bingo"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('money')} Balance",
                callback_data="check_balance"
            ),
            InlineKeyboardButton(
                f"{get_emoji('deposit')} Deposit",
                callback_data="deposit_menu"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('cashout')} Cashout",
                callback_data="cashout_menu"
            ),
            InlineKeyboardButton(
                f"{get_emoji('transfer')} Transfer",
                callback_data="transfer_menu"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('invite')} Invite Friends",
                callback_data="invite_menu"
            ),
            InlineKeyboardButton(
                f"{get_emoji('support')} Contact",
                callback_data="contact_menu"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('bonus')} Bonuses",
                callback_data="bonus_menu"
            ),
            InlineKeyboardButton(
                f"{get_emoji('settings')} Settings",
                callback_data="settings_menu"
            )
        ]
    ]
    
    # Add admin button if user is admin
    if is_admin:
        keyboard.append([
            InlineKeyboardButton(
                f"{get_emoji('admin')} Admin Panel",
                callback_data="admin_panel"
            )
        ])
    
    return InlineKeyboardMarkup(keyboard)


def reply_menu_keyboard(lang: str = 'en') -> ReplyKeyboardMarkup:
    """
    Create reply keyboard for quick commands.
    
    Args:
        lang: Language code
    
    Returns:
        ReplyKeyboardMarkup: Reply keyboard
    """
    keyboard = [
        [
            KeyboardButton(f"{get_emoji('game')} /play"),
            KeyboardButton(f"{get_emoji('game')} /mini_bingo")
        ],
        [
            KeyboardButton(f"{get_emoji('money')} /balance"),
            KeyboardButton(f"{get_emoji('deposit')} /deposit")
        ],
        [
            KeyboardButton(f"{get_emoji('cashout')} /cashout"),
            KeyboardButton(f"{get_emoji('transfer')} /transfer")
        ],
        [
            KeyboardButton(f"{get_emoji('invite')} /invite"),
            KeyboardButton(f"{get_emoji('support')} /contact")
        ],
        [
            KeyboardButton(f"{get_emoji('bonus')} /bonus"),
            KeyboardButton(f"{get_emoji('help')} /help")
        ]
    ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


# ==================== DEPOSIT KEYBOARDS ====================

def deposit_methods_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create deposit methods selection keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Deposit methods keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('bank')} CBE (Commercial Bank)",
                callback_data="deposit_cbe"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('bank')} Abyssinia Bank",
                callback_data="deposit_abyssinia"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('phone')} Telebirr",
                callback_data="deposit_telebirr"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('phone')} M-Pesa",
                callback_data="deposit_mpesa"
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


def deposit_amount_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create deposit amount suggestion keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Deposit amount keyboard
    """
    amounts = [50, 100, 200, 500, 1000]
    
    keyboard = []
    row = []
    for amount in amounts:
        row.append(
            InlineKeyboardButton(
                f"{amount} ETB",
                callback_data=f"deposit_amount_{amount}"
            )
        )
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('cancel')} Cancel",
            callback_data="cancel_deposit"
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== CASHOUT KEYBOARDS ====================

def cashout_methods_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create cashout methods selection keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Cashout methods keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('bank')} CBE (Commercial Bank)",
                callback_data="cashout_cbe"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('bank')} Abyssinia Bank",
                callback_data="cashout_abyssinia"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('phone')} Telebirr",
                callback_data="cashout_telebirr"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('phone')} M-Pesa",
                callback_data="cashout_mpesa"
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


def cashout_amount_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create cashout amount suggestion keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Cashout amount keyboard
    """
    amounts = [100, 200, 500, 1000, 5000]
    
    keyboard = []
    row = []
    for amount in amounts:
        row.append(
            InlineKeyboardButton(
                f"{amount} ETB",
                callback_data=f"cashout_amount_{amount}"
            )
        )
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('cancel')} Cancel",
            callback_data="cancel_cashout"
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== TRANSFER KEYBOARDS ====================

def transfer_amount_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create transfer amount suggestion keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Transfer amount keyboard
    """
    amounts = [10, 20, 50, 100, 200, 500]
    
    keyboard = []
    row = []
    for amount in amounts:
        row.append(
            InlineKeyboardButton(
                f"{amount} ETB",
                callback_data=f"transfer_amount_{amount}"
            )
        )
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('cancel')} Cancel",
            callback_data="cancel_transfer"
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== SETTINGS KEYBOARDS ====================

def settings_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create settings menu keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Settings keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('language')} Language",
                callback_data="settings_language"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('sound')} Sound Pack",
                callback_data="settings_sound"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('bell')} Notifications",
                callback_data="settings_notifications"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('info')} About",
                callback_data="settings_about"
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


def language_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create language selection keyboard.
    
    Args:
        lang: Current language code
    
    Returns:
        InlineKeyboardMarkup: Language keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                "🇬🇧 English" + (" ✓" if lang == 'en' else ""),
                callback_data="set_lang_en"
            )
        ],
        [
            InlineKeyboardButton(
                "🇪🇹 አማርኛ" + (" ✓" if lang == 'am' else ""),
                callback_data="set_lang_am"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('back')} Back",
                callback_data="back_to_settings"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


# ==================== BONUS KEYBOARDS ====================

def bonus_keyboard(lang: str = 'en', has_welcome: bool = True, has_daily: bool = False) -> InlineKeyboardMarkup:
    """
    Create bonus menu keyboard.
    
    Args:
        lang: Language code
        has_welcome: Whether welcome bonus is available
        has_daily: Whether daily bonus is available
    
    Returns:
        InlineKeyboardMarkup: Bonus keyboard
    """
    keyboard = []
    
    if has_welcome:
        keyboard.append([
            InlineKeyboardButton(
                f"{get_emoji('gift')} Claim Welcome Bonus",
                callback_data="claim_welcome_bonus"
            )
        ])
    
    if has_daily:
        keyboard.append([
            InlineKeyboardButton(
                f"{get_emoji('calendar')} Claim Daily Bonus",
                callback_data="claim_daily_bonus"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('info')} Bonus Info",
            callback_data="bonus_info"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('back')} Back to Menu",
            callback_data="back_to_menu"
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== ADMIN KEYBOARDS ====================

def admin_panel_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create admin panel keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Admin panel keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('stats')} Statistics",
                callback_data="admin_stats"
            ),
            InlineKeyboardButton(
                f"{get_emoji('users')} Users",
                callback_data="admin_users"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('deposit')} Deposits",
                callback_data="admin_deposits"
            ),
            InlineKeyboardButton(
                f"{get_emoji('cashout')} Withdrawals",
                callback_data="admin_withdrawals"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('game')} Game Control",
                callback_data="admin_game_control"
            ),
            InlineKeyboardButton(
                f"{get_emoji('settings')} System Settings",
                callback_data="admin_system_settings"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('broadcast')} Broadcast",
                callback_data="admin_broadcast"
            ),
            InlineKeyboardButton(
                f"{get_emoji('report')} Reports",
                callback_data="admin_reports"
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


def admin_users_keyboard(page: int = 1, total_pages: int = 1) -> InlineKeyboardMarkup:
    """
    Create admin users management keyboard.
    
    Args:
        page: Current page number
        total_pages: Total number of pages
    
    Returns:
        InlineKeyboardMarkup: Admin users keyboard
    """
    keyboard = []
    
    # Pagination buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton("◀️ Previous", callback_data=f"admin_users_page_{page - 1}")
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton("Next ▶️", callback_data=f"admin_users_page_{page + 1}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('search')} Search User",
            callback_data="admin_search_user"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('back')} Back to Admin Panel",
            callback_data="admin_panel"
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


def admin_deposit_keyboard(deposit_id: int) -> InlineKeyboardMarkup:
    """
    Create admin deposit action keyboard.
    
    Args:
        deposit_id: Deposit request ID
    
    Returns:
        InlineKeyboardMarkup: Admin deposit keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('check')} Approve",
                callback_data=f"admin_approve_deposit_{deposit_id}"
            ),
            InlineKeyboardButton(
                f"{get_emoji('cancel')} Reject",
                callback_data=f"admin_reject_deposit_{deposit_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('back')} Back",
                callback_data="admin_deposits"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def admin_withdrawal_keyboard(withdrawal_id: int) -> InlineKeyboardMarkup:
    """
    Create admin withdrawal action keyboard.
    
    Args:
        withdrawal_id: Withdrawal request ID
    
    Returns:
        InlineKeyboardMarkup: Admin withdrawal keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('check')} Approve",
                callback_data=f"admin_approve_withdrawal_{withdrawal_id}"
            ),
            InlineKeyboardButton(
                f"{get_emoji('cancel')} Reject",
                callback_data=f"admin_reject_withdrawal_{withdrawal_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"{get_emoji('back')} Back",
                callback_data="admin_withdrawals"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


# ==================== CONFIRMATION KEYBOARDS ====================

def confirmation_keyboard(action: str, data: str = "") -> InlineKeyboardMarkup:
    """
    Create generic confirmation keyboard.
    
    Args:
        action: Action identifier for callback
        data: Additional data to include in callback
    
    Returns:
        InlineKeyboardMarkup: Confirmation keyboard
    """
    confirm_callback = f"confirm_{action}_{data}" if data else f"confirm_{action}"
    cancel_callback = f"cancel_{action}"
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('check')} Confirm",
                callback_data=confirm_callback
            ),
            InlineKeyboardButton(
                f"{get_emoji('cancel')} Cancel",
                callback_data=cancel_callback
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def pagination_keyboard(prefix: str, page: int, total_pages: int, **kwargs) -> InlineKeyboardMarkup:
    """
    Create generic pagination keyboard.
    
    Args:
        prefix: Callback data prefix
        page: Current page number
        total_pages: Total number of pages
        **kwargs: Additional data to include in callback
    
    Returns:
        InlineKeyboardMarkup: Pagination keyboard
    """
    keyboard = []
    
    # Build base callback
    base_callback = prefix
    if kwargs:
        base_callback += "_" + "_".join(f"{k}_{v}" for k, v in kwargs.items())
    
    # Pagination buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "◀️ Previous",
                callback_data=f"{base_callback}_page_{page - 1}"
            )
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(
                "Next ▶️",
                callback_data=f"{base_callback}_page_{page + 1}"
            )
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton(
            f"{get_emoji('back')} Back",
            callback_data=f"{base_callback}_back"
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


# ==================== SIMPLE KEYBOARDS ====================

def back_to_menu_keyboard(lang: str = 'en') -> InlineKeyboardMarkup:
    """
    Create simple back to menu keyboard.
    
    Args:
        lang: Language code
    
    Returns:
        InlineKeyboardMarkup: Back to menu keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('back')} Back to Menu",
                callback_data="back_to_menu"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


def cancel_keyboard(action: str = "") -> InlineKeyboardMarkup:
    """
    Create cancel action keyboard.
    
    Args:
        action: Action identifier for cancel callback
    
    Returns:
        InlineKeyboardMarkup: Cancel keyboard
    """
    cancel_callback = f"cancel_{action}" if action else "cancel"
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{get_emoji('cancel')} Cancel",
                callback_data=cancel_callback
            )
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)


# ==================== EXPORTS ====================

__all__ = [
    # Main menus
    'main_menu_keyboard',
    'reply_menu_keyboard',
    
    # Deposit menus
    'deposit_methods_keyboard',
    'deposit_amount_keyboard',
    
    # Cashout menus
    'cashout_methods_keyboard',
    'cashout_amount_keyboard',
    
    # Transfer menus
    'transfer_amount_keyboard',
    
    # Settings menus
    'settings_keyboard',
    'language_keyboard',
    
    # Bonus menus
    'bonus_keyboard',
    
    # Admin menus
    'admin_panel_keyboard',
    'admin_users_keyboard',
    'admin_deposit_keyboard',
    'admin_withdrawal_keyboard',
    
    # Utility keyboards
    'confirmation_keyboard',
    'pagination_keyboard',
    'back_to_menu_keyboard',
    'cancel_keyboard',
]
# ==================== ALIAS FOR BACKWARD COMPATIBILITY ====================
menu = main_menu_keyboard  # ← ADD THIS ONE LINE