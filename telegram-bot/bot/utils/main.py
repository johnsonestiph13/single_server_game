# telegram-bot/bot/utils/main.py
# Estif Bingo 24/7 - Main Utility Functions
# Common utility functions used across the bot

import re
import random
import string
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from functools import wraps

# ==================== STRING UTILITIES ====================

def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate text to a maximum length with suffix.
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add when truncated
    
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.
    
    Args:
        text: Input text
    
    Returns:
        str: URL-friendly slug
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces with hyphens
    text = re.sub(r'\s+', '-', text)
    # Remove special characters
    text = re.sub(r'[^\w\-]', '', text)
    # Remove multiple hyphens
    text = re.sub(r'-+', '-', text)
    # Strip hyphens from ends
    return text.strip('-')


def mask_string(text: str, visible_chars: int = 4, mask_char: str = '*') -> str:
    """
    Mask a string showing only last N characters.
    
    Args:
        text: Input text
        visible_chars: Number of visible characters at the end
        mask_char: Character used for masking
    
    Returns:
        str: Masked string
    """
    if not text:
        return ''
    if len(text) <= visible_chars:
        return text
    masked_length = len(text) - visible_chars
    return mask_char * masked_length + text[-visible_chars:]


def mask_phone(phone: str) -> str:
    """
    Mask phone number for privacy.
    
    Args:
        phone: Phone number
    
    Returns:
        str: Masked phone number
    """
    if not phone:
        return ''
    # Show last 4 digits only
    return mask_string(phone, visible_chars=4)


def mask_email(email: str) -> str:
    """
    Mask email address for privacy.
    
    Args:
        email: Email address
    
    Returns:
        str: Masked email
    """
    if not email or '@' not in email:
        return mask_string(email, 4)
    
    local, domain = email.split('@', 1)
    masked_local = mask_string(local, 2)
    return f"{masked_local}@{domain}"


# ==================== VALIDATION UTILITIES ====================

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
    Normalize phone number to standard format.
    
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


def validate_amount(amount: float, min_amount: float = 0, max_amount: float = float('inf')) -> Tuple[bool, str]:
    """
    Validate transaction amount.
    
    Args:
        amount: Amount to validate
        min_amount: Minimum allowed amount
        max_amount: Maximum allowed amount
    
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
    
    return True, ""


def validate_account_number(account_number: str, bank: str = None) -> Tuple[bool, str]:
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
    
    # Basic length check
    if len(account_number) < 5 or len(account_number) > 20:
        return False, "Account number must be between 5 and 20 characters"
    
    # Check for valid characters (digits and letters)
    if not re.match(r'^[A-Za-z0-9]+$', account_number):
        return False, "Account number can only contain letters and numbers"
    
    return True, ""


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


# ==================== TOKEN GENERATION ====================

def generate_otp(length: int = 6) -> str:
    """
    Generate numeric OTP.
    
    Args:
        length: OTP length
    
    Returns:
        str: OTP code
    """
    return ''.join(random.choices(string.digits, k=length))


def generate_token(length: int = 32) -> str:
    """
    Generate secure random token.
    
    Args:
        length: Token length in bytes (resulting hex length = length * 2)
    
    Returns:
        str: Hexadecimal token
    """
    return secrets.token_hex(length)


def generate_reference_id(prefix: str = 'REF') -> str:
    """
    Generate unique reference ID.
    
    Args:
        prefix: Reference prefix
    
    Returns:
        str: Reference ID
    """
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    random_part = secrets.token_hex(4).upper()
    return f"{prefix}_{timestamp}_{random_part}"


def hash_token(token: str, salt: Optional[str] = None) -> str:
    """
    Hash a token for secure storage.
    
    Args:
        token: Token to hash
        salt: Optional salt
    
    Returns:
        str: Hashed token
    """
    if salt:
        to_hash = f"{salt}{token}"
    else:
        to_hash = token
    
    return hashlib.sha256(to_hash.encode()).hexdigest()


# ==================== DATE/TIME UTILITIES ====================

def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format datetime for display.
    
    Args:
        dt: Datetime object
        format_str: Format string
    
    Returns:
        str: Formatted datetime string
    """
    if not dt:
        return ''
    return dt.strftime(format_str)


def format_date(dt: datetime, format_str: str = '%Y-%m-%d') -> str:
    """
    Format date for display.
    
    Args:
        dt: Datetime object
        format_str: Format string
    
    Returns:
        str: Formatted date string
    """
    if not dt:
        return ''
    return dt.strftime(format_str)


def format_time_remaining(seconds: int) -> str:
    """
    Format time remaining in human-readable format.
    
    Args:
        seconds: Seconds remaining
    
    Returns:
        str: Formatted time string
    """
    if seconds <= 0:
        return "Expired"
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string.
    
    Args:
        dt: Datetime object
    
    Returns:
        str: Time ago string
    """
    if not dt:
        return ''
    
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"


# ==================== NUMBER UTILITIES ====================

def format_currency(amount: float, currency: str = 'ETB') -> str:
    """
    Format amount as currency.
    
    Args:
        amount: Amount to format
        currency: Currency symbol
    
    Returns:
        str: Formatted currency string
    """
    return f"{amount:,.2f} {currency}"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """
    Format value as percentage.
    
    Args:
        value: Percentage value
        decimal_places: Number of decimal places
    
    Returns:
        str: Formatted percentage string
    """
    return f"{value:.{decimal_places}f}%"


def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """
    Safely divide two numbers, handling division by zero.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if denominator is zero
    
    Returns:
        float: Division result
    """
    if denominator == 0:
        return default
    return numerator / denominator


# ==================== DICTIONARY UTILITIES ====================

def safe_get(data: Dict, key: str, default: Any = None) -> Any:
    """
    Safely get value from dictionary with dot notation support.
    
    Args:
        data: Dictionary
        key: Key with dot notation (e.g., 'user.profile.name')
        default: Default value if not found
    
    Returns:
        Any: Value or default
    """
    keys = key.split('.')
    current = data
    
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
            if current is None:
                return default
        else:
            return default
    
    return current


def merge_dicts(dict1: Dict, dict2: Dict, deep: bool = False) -> Dict:
    """
    Merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
        deep: Whether to deep merge nested dictionaries
    
    Returns:
        dict: Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if deep and key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value, deep)
        else:
            result[key] = value
    
    return result


# ==================== DECORATORS ====================

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry decorator for functions that may fail temporarily.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            current_delay = delay
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_error
        
        return wrapper
    return decorator


def timing_decorator(func):
    """
    Timing decorator to measure function execution time.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = datetime.utcnow()
        result = await func(*args, **kwargs)
        end = datetime.utcnow()
        duration = (end - start).total_seconds()
        print(f"{func.__name__} took {duration:.3f}s")
        return result
    return wrapper


# ==================== EXPORTS ====================

__all__ = [
    # String utilities
    'truncate_text',
    'slugify',
    'mask_string',
    'mask_phone',
    'mask_email',
    
    # Validation utilities
    'is_valid_ethiopian_phone',
    'is_valid_kenyan_phone',
    'is_valid_phone',
    'normalize_phone',
    'get_phone_carrier',
    'validate_amount',
    'validate_account_number',
    'validate_transaction_id',
    
    # Token generation
    'generate_otp',
    'generate_token',
    'generate_reference_id',
    'hash_token',
    
    # Date/time utilities
    'format_datetime',
    'format_date',
    'format_time_remaining',
    'time_ago',
    
    # Number utilities
    'format_currency',
    'format_percentage',
    'safe_divide',
    
    # Dictionary utilities
    'safe_get',
    'merge_dicts',
    
    # Decorators
    'retry',
    'timing_decorator',
]