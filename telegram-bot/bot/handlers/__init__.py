# telegram-bot/bot/handlers/__init__.py
# Estif Bingo 24/7 - Handlers Package
# Exports all handler functions and conversation states

# ==================== CORE HANDLERS ====================
from bot.handlers.start import (
    start,
    language_callback,
    help_command,
    about_command,
)

from bot.handlers.register import (
    register,
    handle_contact,
    register_phone,
    register_cancel,
    play,
    PHONE as REGISTER_PHONE,
)

from bot.handlers.deposit import (
    deposit,
    deposit_callback,
    deposit_amount,
    deposit_screenshot,
    deposit_cancel,
    AMOUNT as DEPOSIT_AMOUNT,
    SCREENSHOT as DEPOSIT_SCREENSHOT,
)

from bot.handlers.cashout import (
    cashout,
    withdrawal_amount,
    withdrawal_method_callback,
    withdrawal_details,
    confirm_withdrawal_callback,
    cancel_withdrawal,
    approve_withdrawal_callback,
    reject_withdrawal_callback,
    AMOUNT as CASHOUT_AMOUNT,
    METHOD as CASHOUT_METHOD,
    ACCOUNT_DETAILS as CASHOUT_ACCOUNT_DETAILS,
    CONFIRMATION as CASHOUT_CONFIRMATION,
)

from bot.handlers.transfer import (
    transfer,
    transfer_phone_number,
    transfer_amount,
    confirm_transfer_callback,
    cancel_transfer_callback,
    cancel_transfer,
    PHONE_NUMBER as TRANSFER_PHONE_NUMBER,
    AMOUNT as TRANSFER_AMOUNT,
    CONFIRMATION as TRANSFER_CONFIRMATION,
)

from bot.handlers.balance import (
    balance,
    balance_callback,
    history_page_callback,
    back_to_balance_callback,
)

from bot.handlers.bonus import (
    bonus,
    claim_welcome_bonus_callback,
    claim_daily_bonus_callback,
    check_bonus_eligibility,
    bonus_info_command,
    grant_bonus,
    no_bonus_callback,
)

# ==================== GAME HANDLERS ====================
from bot.handlers.game import (
    play as play_game,
    game_rules_callback,
    back_to_game_callback,
    quick_deposit_callback,
    game_status,
)

from bot.handlers.mini_bingo import (
    mini_bingo,
    play_mini_bingo_game,
    check_mini_bingo_win,
    end_mini_bingo_game,
    mini_bingo_rules_callback,
    play_mini_bingo_callback,
    back_to_mini_bingo_callback,
    set_mini_bingo_settings,
    MINI_BINGO_PRICE,
    MINI_BINGO_WIN_PERCENTAGE,
)

from bot.handlers.bingo_otp import (
    bingo_otp,
    verify_otp,
    cancel_otp,
    copy_otp_callback,
    resend_otp,
    verify_otp_api,
    WAITING_FOR_OTP,
)

# ==================== TOURNAMENT HANDLERS (Optional) ====================
from bot.handlers.tournament import (
    tournament,
    tournament_register_callback,
    tournament_confirm_register_callback,
    tournament_play_callback,
    tournament_leaderboard_callback,
    cancel_tournament_register_callback,
    back_to_tournament_callback,
    admin_create_tournament,
    admin_end_tournament,
    TOURNAMENT_ENABLED,
)

# ==================== SOCIAL HANDLERS ====================
from bot.handlers.invite import (
    invite,
    copy_invite_link_callback,
    back_to_invite_callback,
)

from bot.handlers.contact import (
    contact_center,
    contact_admin_callback,
    handle_contact_message,
    cancel_contact_callback,
    back_to_menu_callback,
    admin_reply_to_user,
)

# ==================== ADMIN HANDLERS ====================
from bot.handlers.admin_commands import (
    admin_command,
    set_win_percent,
    force_start,
    force_stop,
    set_sound_pack,
    search_player,
    stats_command,
    approve_deposit,
    reject_deposit,
    approve_withdrawal,
    reject_withdrawal,
    broadcast_command,
    broadcast_message,
    broadcast_confirm_callback,
    broadcast_cancel_callback,
    maintenance_command,
    reset_game_command,
    cancel_broadcast,
    BROADCAST_MESSAGE,
    BROADCAST_CONFIRM,
)

# ==================== CONVENIENCE RE-EXPORTS ====================
# Common conversation states grouped by feature
CONVERSATION_STATES = {
    'REGISTER': REGISTER_PHONE,
    'DEPOSIT': (DEPOSIT_AMOUNT, DEPOSIT_SCREENSHOT),
    'CASHOUT': (CASHOUT_AMOUNT, CASHOUT_METHOD, CASHOUT_ACCOUNT_DETAILS, CASHOUT_CONFIRMATION),
    'TRANSFER': (TRANSFER_PHONE_NUMBER, TRANSFER_AMOUNT, TRANSFER_CONFIRMATION),
    'BINGO_OTP': WAITING_FOR_OTP,
    'BROADCAST': (BROADCAST_MESSAGE, BROADCAST_CONFIRM),
}

# List of all conversation handler functions for easy registration
CONVERSATION_HANDLERS = [
    # Deposit conversation
    (deposit, deposit_callback, deposit_amount, deposit_screenshot, deposit_cancel),
    
    # Cashout conversation
    (cashout, withdrawal_amount, withdrawal_method_callback, withdrawal_details, 
     withdrawal_details, withdrawal_details, confirm_withdrawal_callback, cancel_withdrawal),
    
    # Transfer conversation
    (transfer, transfer_phone_number, transfer_amount, confirm_transfer_callback, cancel_transfer),
    
    # Register conversation
    (register, handle_contact, register_phone, register_cancel),
    
    # Bingo OTP conversation
    (bingo_otp, verify_otp, cancel_otp),
    
    # Broadcast conversation
    (broadcast_command, broadcast_message, cancel_broadcast),
]

# List of all callback query handlers
CALLBACK_HANDLERS = [
    # Language and menu
    language_callback,
    back_to_menu_callback,
    
    # Deposit
    deposit_callback,
    
    # Cashout
    withdrawal_method_callback,
    confirm_withdrawal_callback,
    approve_withdrawal_callback,
    reject_withdrawal_callback,
    
    # Transfer
    confirm_transfer_callback,
    cancel_transfer_callback,
    
    # Balance
    balance_callback,
    history_page_callback,
    back_to_balance_callback,
    
    # Bonus
    claim_welcome_bonus_callback,
    claim_daily_bonus_callback,
    no_bonus_callback,
    
    # Game
    game_rules_callback,
    back_to_game_callback,
    quick_deposit_callback,
    
    # Mini Bingo
    mini_bingo_rules_callback,
    play_mini_bingo_callback,
    back_to_mini_bingo_callback,
    
    # Bingo OTP
    cancel_otp,
    copy_otp_callback,
    
    # Tournament
    tournament_register_callback,
    tournament_confirm_register_callback,
    tournament_play_callback,
    tournament_leaderboard_callback,
    cancel_tournament_register_callback,
    back_to_tournament_callback,
    
    # Invite
    copy_invite_link_callback,
    back_to_invite_callback,
    
    # Contact
    contact_admin_callback,
    cancel_contact_callback,
    
    # Admin
    broadcast_confirm_callback,
    broadcast_cancel_callback,
]

# List of all command handlers
COMMAND_HANDLERS = [
    # Core commands
    ('start', start),
    ('help', help_command),
    ('about', about_command),
    
    # Registration
    ('register', register),
    
    # Financial
    ('balance', balance),
    ('deposit', deposit),
    ('cashout', cashout),
    ('transfer', transfer),
    ('bonus', bonus),
    ('bonus_info', bonus_info_command),
    
    # Game
    ('play', play_game),
    ('mini_bingo', mini_bingo),
    ('bingo', bingo_otp),
    ('verify', verify_otp),
    ('game_status', game_status),
    
    # Social
    ('invite', invite),
    ('contact', contact_center),
    
    # Tournament (if enabled)
    ('tournament', tournament),
    
    # Admin commands
    ('admin', admin_command),
    ('set_win_percent', set_win_percent),
    ('force_start', force_start),
    ('force_stop', force_stop),
    ('set_sound_pack', set_sound_pack),
    ('search_player', search_player),
    ('stats', stats_command),
    ('approve_deposit', approve_deposit),
    ('reject_deposit', reject_deposit),
    ('approve_withdrawal', approve_withdrawal),
    ('reject_withdrawal', reject_withdrawal),
    ('broadcast', broadcast_command),
    ('maintenance', maintenance_command),
    ('reset_game', reset_game_command),
    ('grant_bonus', grant_bonus),
    ('set_mini_bingo', set_mini_bingo_settings),
    
    # Tournament admin commands (if enabled)
    ('create_tournament', admin_create_tournament),
    ('end_tournament', admin_end_tournament),
]

# List of message handlers (non-command text messages)
MESSAGE_HANDLERS = [
    # Contact messages (forward to admin)
    handle_contact_message,
    
    # Manual phone entry during registration
    register_phone,
    
    # Deposit amount and screenshot
    deposit_amount,
    deposit_screenshot,
    
    # Cashout details
    withdrawal_amount,
    withdrawal_details,
    withdrawal_details,  # For account number
    withdrawal_details,  # For account holder
    withdrawal_details,  # For phone number
    
    # Transfer amount
    transfer_amount,
    transfer_phone_number,
    
    # Broadcast message
    broadcast_message,
    
    # Bingo OTP verification
    verify_otp,
]

# Export all handler functions
__all__ = [
    # Core
    'start',
    'language_callback',
    'help_command',
    'about_command',
    
    # Registration
    'register',
    'handle_contact',
    'register_phone',
    'register_cancel',
    'play',
    'REGISTER_PHONE',
    
    # Deposit
    'deposit',
    'deposit_callback',
    'deposit_amount',
    'deposit_screenshot',
    'deposit_cancel',
    'DEPOSIT_AMOUNT',
    'DEPOSIT_SCREENSHOT',
    
    # Cashout
    'cashout',
    'withdrawal_amount',
    'withdrawal_method_callback',
    'withdrawal_details',
    'confirm_withdrawal_callback',
    'cancel_withdrawal',
    'approve_withdrawal_callback',
    'reject_withdrawal_callback',
    'CASHOUT_AMOUNT',
    'CASHOUT_METHOD',
    'CASHOUT_ACCOUNT_DETAILS',
    'CASHOUT_CONFIRMATION',
    
    # Transfer
    'transfer',
    'transfer_phone_number',
    'transfer_amount',
    'confirm_transfer_callback',
    'cancel_transfer_callback',
    'cancel_transfer',
    'TRANSFER_PHONE_NUMBER',
    'TRANSFER_AMOUNT',
    'TRANSFER_CONFIRMATION',
    
    # Balance
    'balance',
    'balance_callback',
    'history_page_callback',
    'back_to_balance_callback',
    
    # Bonus
    'bonus',
    'claim_welcome_bonus_callback',
    'claim_daily_bonus_callback',
    'check_bonus_eligibility',
    'bonus_info_command',
    'grant_bonus',
    'no_bonus_callback',
    
    # Game
    'play_game',
    'game_rules_callback',
    'back_to_game_callback',
    'quick_deposit_callback',
    'game_status',
    
    # Mini Bingo
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
    
    # Bingo OTP
    'bingo_otp',
    'verify_otp',
    'cancel_otp',
    'copy_otp_callback',
    'resend_otp',
    'verify_otp_api',
    'WAITING_FOR_OTP',
    
    # Tournament
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
    
    # Social
    'invite',
    'copy_invite_link_callback',
    'back_to_invite_callback',
    'contact_center',
    'contact_admin_callback',
    'handle_contact_message',
    'cancel_contact_callback',
    'back_to_menu_callback',
    'admin_reply_to_user',
    
    # Admin
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
    
    # Convenience exports
    'CONVERSATION_STATES',
    'CONVERSATION_HANDLERS',
    'CALLBACK_HANDLERS',
    'COMMAND_HANDLERS',
    'MESSAGE_HANDLERS',
]