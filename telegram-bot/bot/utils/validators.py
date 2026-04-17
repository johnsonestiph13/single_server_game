# telegram-bot/bot/utils/validators.py
# Estif Bingo 24/7 - Input Validators
# Provides validation functions for user inputs

import re
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime

from bot.config import config


# ==================== PHONE NUMBER VALIDATION ====================

def is_valid_ethiopian_phone(phone: str) -> bool:
    """
    Validate Ethiopian phone number.
    
    Args:
        phone: Phone number string
    
    Returns:
        bool: True if valid
    """
    # Remove any non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # Ethiopian phone patterns
    patterns = [
        r'^09\d{8}$',      # 09XXXXXXXX
        r'^07\d{8}$',      # 07XXXXXXXX
        r'^2519\d{8}$',    # 2519XXXXXXXX
        r'^2517\d{8}$',    # 2517XXXXXXXX
    ]
    
    return any(re.match(pattern, phone) for pattern in patterns)


def is_valid_kenyan_phone(phone: str) -> bool:
    """
    Validate Kenyan phone number (Safaricom).
    
    Args:
        phone: Phone number string
    
    Returns:
        bool: True if valid
    """
    # Remove any non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # Kenyan phone patterns
    patterns = [
        r'^07\d{8}$',      # 07XXXXXXXX
        r'^2547\d{8}$',    # 2547XXXXXXXX
        r'^01\d{8}$',      # 01XXXXXXXX (Safaricom)
    ]
    
    return any(re.match(pattern, phone) for pattern in patterns)


def is_valid_phone(phone: str) -> bool:
    """
    Validate phone number (supports Ethiopian and Kenyan).
    
    Args:
        phone: Phone number string
    
    Returns:
        bool: True if valid
    """
    return is_valid_ethiopian_phone(phone) or is_valid_kenyan_phone(phone)


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to standard format (09XXXXXXXX).
    
    Args:
        phone: Phone number string
    
    Returns:
        str: Normalized phone number
    """
    # Remove any non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # Convert to 09XXXXXXXX format for Ethiopian
    if phone.startswith('251'):
        phone = '0' + phone[3:]
    elif phone.startswith('254'):
        phone = '0' + phone[3:]
    
    return phone


def get_phone_carrier(phone: str) -> str:
    """
    Detect phone carrier based on prefix.
    
    Args:
        phone: Phone number string
    
    Returns:
        str: Carrier name
    """
    phone = normalize_phone(phone)
    
    # Ethiopian carriers
    if phone.startswith('09'):
        if phone.startswith('091') or phone.startswith('092'):
            return 'Ethio Telecom'
        elif phone.startswith('093') or phone.startswith('094'):
            return 'Safaricom Ethiopia'
        elif phone.startswith('096'):
            return 'MTN Ethiopia'
        elif phone.startswith('097'):
            return 'Ethio Telecom'
    
    # Kenyan Safaricom
    if phone.startswith('07') or phone.startswith('01'):
        return 'Safaricom Kenya'
    
    return 'Unknown'


def validate_phone_with_carrier(phone: str) -> Tuple[bool, str, str]:
    """
    Validate phone number and return carrier info.
    
    Args:
        phone: Phone number string
    
    Returns:
        tuple: (is_valid, normalized_phone, carrier)
    """
    if not is_valid_phone(phone):
        return False, "", ""
    
    normalized = normalize_phone(phone)
    carrier = get_phone_carrier(normalized)
    
    return True, normalized, carrier


# ==================== AMOUNT VALIDATION ====================

def validate_amount(
    amount: float,
    min_amount: float = 0,
    max_amount: float = float('inf'),
    balance: Optional[float] = None
) -> Tuple[bool, str]:
    """
    Validate transaction amount.
    
    Args:
        amount: Amount to validate
        min_amount: Minimum allowed amount
        max_amount: Maximum allowed amount
        balance: User's current balance (for withdrawal checks)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if amount <= 0:
        return False, "Amount must be positive"
    
    if amount < min_amount:
        return False, f"Minimum amount is {min_amount} ETB"
    
    if amount > max_amount:
        return False, f"Maximum amount is {max_amount} ETB"
    
    # Check for too many decimal places
    if amount != round(amount, 2):
        return False, "Amount cannot have more than 2 decimal places"
    
    # Check balance if provided (for withdrawals)
    if balance is not None and amount > balance:
        return False, f"Insufficient balance. You have {balance:.2f} ETB"
    
    return True, ""


def validate_deposit_amount(amount: float) -> Tuple[bool, str]:
    """
    Validate deposit amount.
    
    Args:
        amount: Deposit amount
    
    Returns:
        tuple: (is_valid, error_message)
    """
    min_deposit = getattr(config, 'MIN_DEPOSIT', 10)
    max_deposit = getattr(config, 'MAX_DEPOSIT', 10000)
    
    return validate_amount(amount, min_deposit, max_deposit)


def validate_withdrawal_amount(amount: float, balance: float) -> Tuple[bool, str]:
    """
    Validate withdrawal amount.
    
    Args:
        amount: Withdrawal amount
        balance: User's current balance
    
    Returns:
        tuple: (is_valid, error_message)
    """
    min_withdrawal = getattr(config, 'MIN_WITHDRAWAL', 50)
    max_withdrawal = getattr(config, 'MAX_WITHDRAWAL', 10000)
    
    return validate_amount(amount, min_withdrawal, max_withdrawal, balance)


def validate_transfer_amount(amount: float, balance: float) -> Tuple[bool, str]:
    """
    Validate transfer amount.
    
    Args:
        amount: Transfer amount
        balance: User's current balance
    
    Returns:
        tuple: (is_valid, error_message)
    """
    min_transfer = getattr(config, 'MIN_TRANSFER', 10)
    max_transfer = getattr(config, 'MAX_TRANSFER', 5000)
    
    # Add fee to total if applicable
    fee_percent = getattr(config, 'TRANSFER_FEE_PERCENT', 0)
    total = amount + (amount * fee_percent / 100)
    
    if total > balance:
        fee_amount = amount * fee_percent / 100
        return False, f"Insufficient balance. Amount: {amount} ETB, Fee: {fee_amount:.2f} ETB, Total: {total:.2f} ETB"
    
    return validate_amount(amount, min_transfer, max_transfer)


# ==================== BANK ACCOUNT VALIDATION ====================

def validate_account_number(account_number: str, bank: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate bank account number.
    
    Args:
        account_number: Account number string
        bank: Bank name (optional)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not account_number:
        return False, "Account number is required"
    
    # Remove spaces
    account_number = account_number.replace(' ', '')
    
    # Length check
    if len(account_number) < 5 or len(account_number) > 20:
        return False, "Account number must be between 5 and 20 characters"
    
    # Check for valid characters
    if not re.match(r'^[A-Za-z0-9\-]+$', account_number):
        return False, "Account number can only contain letters, numbers, and hyphens"
    
    return True, ""


def validate_account_holder(name: str) -> Tuple[bool, str]:
    """
    Validate account holder name.
    
    Args:
        name: Account holder name
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not name:
        return False, "Account holder name is required"
    
    name = name.strip()
    
    if len(name) < 3:
        return False, "Name must be at least 3 characters"
    
    if len(name) > 100:
        return False, "Name cannot exceed 100 characters"
    
    # Check for valid characters (letters, spaces, dots, hyphens)
    if not re.match(r'^[A-Za-z\s\.\-]+$', name):
        return False, "Name can only contain letters, spaces, dots, and hyphens"
    
    return True, ""


# ==================== TRANSACTION ID VALIDATION ====================

def validate_transaction_id(transaction_id: str) -> bool:
    """
    Validate transaction ID format.
    
    Args:
        transaction_id: Transaction ID string
    
    Returns:
        bool: True if valid
    """
    if not transaction_id:
        return False
    
    # Remove spaces
    transaction_id = transaction_id.strip()
    
    # Length check
    if len(transaction_id) < 5 or len(transaction_id) > 50:
        return False
    
    # Check for valid characters
    if not re.match(r'^[A-Za-z0-9\-_]+$', transaction_id):
        return False
    
    return True


# ==================== EMAIL VALIDATION ====================

def is_valid_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address string
    
    Returns:
        bool: True if valid
    """
    if not email:
        return False
    
    # Basic email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def normalize_email(email: str) -> str:
    """
    Normalize email address (lowercase, trim).
    
    Args:
        email: Email address string
    
    Returns:
        str: Normalized email
    """
    if not email:
        return ""
    
    return email.lower().strip()


# ==================== USERNAME VALIDATION ====================

def is_valid_username(username: str) -> bool:
    """
    Validate Telegram username format.
    
    Args:
        username: Username string
    
    Returns:
        bool: True if valid
    """
    if not username:
        return True  # Username is optional
    
    # Remove @ if present
    if username.startswith('@'):
        username = username[1:]
    
    # Telegram username rules: 5-32 characters, letters, numbers, underscore
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$'
    return re.match(pattern, username) is not None


# ==================== DATE VALIDATION ====================

def is_valid_date(date_string: str, format_str: str = '%Y-%m-%d') -> bool:
    """
    Validate date string format.
    
    Args:
        date_string: Date string
        format_str: Expected format
    
    Returns:
        bool: True if valid
    """
    try:
        datetime.strptime(date_string, format_str)
        return True
    except ValueError:
        return False


def is_valid_datetime(datetime_string: str, format_str: str = '%Y-%m-%d %H:%M:%S') -> bool:
    """
    Validate datetime string format.
    
    Args:
        datetime_string: Datetime string
        format_str: Expected format
    
    Returns:
        bool: True if valid
    """
    try:
        datetime.strptime(datetime_string, format_str)
        return True
    except ValueError:
        return False


# ==================== CARTELA VALIDATION ====================

def is_valid_cartela_id(cartela_id: int, total_cartelas: int = 1000) -> bool:
    """
    Validate cartela ID.
    
    Args:
        cartela_id: Cartela ID
        total_cartelas: Total number of cartelas
    
    Returns:
        bool: True if valid
    """
    return 1 <= cartela_id <= total_cartelas


def validate_cartela_selection(cartela_ids: List[int], max_cartelas: int = 4) -> Tuple[bool, str]:
    """
    Validate cartela selection.
    
    Args:
        cartela_ids: List of selected cartela IDs
        max_cartelas: Maximum allowed cartelas
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not cartela_ids:
        return False, "No cartelas selected"
    
    if len(cartela_ids) > max_cartelas:
        return False, f"Maximum {max_cartelas} cartelas allowed"
    
    # Check for duplicates
    if len(cartela_ids) != len(set(cartela_ids)):
        return False, "Duplicate cartelas selected"
    
    # Check each ID is valid
    for cartela_id in cartela_ids:
        if not is_valid_cartela_id(cartela_id):
            return False, f"Invalid cartela ID: {cartela_id}"
    
    return True, ""


# ==================== REFERRAL CODE VALIDATION ====================

def is_valid_referral_code(code: str) -> bool:
    """
    Validate referral code format.
    
    Args:
        code: Referral code
    
    Returns:
        bool: True if valid
    """
    if not code:
        return False
    
    # Referral code format: 8-16 characters, alphanumeric
    pattern = r'^[A-Za-z0-9]{8,16}$'
    return re.match(pattern, code) is not None


# ==================== URL VALIDATION ====================

def is_valid_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL string
    
    Returns:
        bool: True if valid
    """
    if not url:
        return False
    
    pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*/?'
    return re.match(pattern, url) is not None


# ==================== PASSWORD VALIDATION ====================

def is_strong_password(password: str) -> Tuple[bool, str]:
    """
    Check if password meets strength requirements.
    
    Args:
        password: Password string
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if len(password) > 100:
        return False, "Password cannot exceed 100 characters"
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    return True, ""


# ==================== INPUT SANITIZATION ====================

def sanitize_string(text: str, max_length: int = 1000) -> str:
    """
    Sanitize string input.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
    
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Trim whitespace
    text = text.strip()
    
    # Truncate
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove dangerous characters
    text = re.sub(r'[<>]', '', text)
    
    return text


def sanitize_numeric(value: Any, default: float = 0) -> float:
    """
    Sanitize numeric input.
    
    Args:
        value: Input value
        default: Default value if conversion fails
    
    Returns:
        float: Sanitized numeric value
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def sanitize_boolean(value: Any) -> bool:
    """
    Sanitize boolean input.
    
    Args:
        value: Input value
    
    Returns:
        bool: Boolean value
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 'on']
    
    return bool(value)


# ==================== EXPORTS ====================

__all__ = [
    # Phone validation
    'is_valid_ethiopian_phone',
    'is_valid_kenyan_phone',
    'is_valid_phone',
    'normalize_phone',
    'get_phone_carrier',
    'validate_phone_with_carrier',
    
    # Amount validation
    'validate_amount',
    'validate_deposit_amount',
    'validate_withdrawal_amount',
    'validate_transfer_amount',
    
    # Bank validation
    'validate_account_number',
    'validate_account_holder',
    
    # Transaction validation
    'validate_transaction_id',
    
    # Email validation
    'is_valid_email',
    'normalize_email',
    
    # Username validation
    'is_valid_username',
    
    # Date validation
    'is_valid_date',
    'is_valid_datetime',
    
    # Cartela validation
    'is_valid_cartela_id',
    'validate_cartela_selection',
    
    # Referral validation
    'is_valid_referral_code',
    
    # URL validation
    'is_valid_url',
    
    # Password validation
    'is_strong_password',
    
    # Sanitization
    'sanitize_string',
    'sanitize_numeric',
    'sanitize_boolean',
]
# ==================== ALIASES FOR BACKWARD COMPATIBILITY ====================
validate_phone_number = is_valid_phone