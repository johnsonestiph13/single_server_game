# telegram-bot/bot/utils/crypto.py
# Estif Bingo 24/7 - Cryptographic Utilities
# Handles encryption, decryption, hashing, and secure data management

import hashlib
import base64
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Tuple, Dict, Any

from bot.config import config
from bot.utils.logger import logger

# ==================== CONSTANTS ====================

# Encryption key (should be set in environment variables)
ENCRYPTION_KEY = config.JWT_SECRET[:32].encode() if config.JWT_SECRET else Fernet.generate_key()
FERNET_CIPHER = Fernet(ENCRYPTION_KEY if len(ENCRYPTION_KEY) == 44 else Fernet.generate_key())


# ==================== FERNET ENCRYPTION (Symmetric) ====================

def encrypt_data(data: str) -> str:
    """
    Encrypt a string using Fernet symmetric encryption.
    
    Args:
        data: String to encrypt
    
    Returns:
        str: Base64 encoded encrypted string
    """
    if not data:
        return ""
    
    try:
        encrypted = FERNET_CIPHER.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return ""


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt a string using Fernet symmetric encryption.
    
    Args:
        encrypted_data: Base64 encoded encrypted string
    
    Returns:
        str: Decrypted string
    """
    if not encrypted_data:
        return ""
    
    try:
        decoded = base64.urlsafe_b64decode(encrypted_data)
        decrypted = FERNET_CIPHER.decrypt(decoded)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return ""


# ==================== PHONE NUMBER ENCRYPTION ====================

def encrypt_phone(phone: str) -> str:
    """
    Encrypt a phone number for secure storage.
    
    Args:
        phone: Phone number string
    
    Returns:
        str: Encrypted phone number
    """
    return encrypt_data(phone)


def decrypt_phone(encrypted_phone: str) -> str:
    """
    Decrypt a phone number.
    
    Args:
        encrypted_phone: Encrypted phone number
    
    Returns:
        str: Decrypted phone number
    """
    return decrypt_data(encrypted_phone)


def hash_phone(phone: str) -> str:
    """
    Create a hash of a phone number for lookup (without revealing the number).
    
    Args:
        phone: Phone number string
    
    Returns:
        str: SHA-256 hash of the phone number
    """
    salt = config.JWT_SECRET[:16].encode()
    return hashlib.pbkdf2_hmac('sha256', phone.encode(), salt, 100000).hex()


def mask_phone(phone: str, visible_chars: int = 4) -> str:
    """
    Create a masked version of a phone number for display.
    
    Args:
        phone: Phone number string
        visible_chars: Number of characters to show at the end
    
    Returns:
        str: Masked phone number (e.g., ****5678)
    """
    if not phone:
        return ""
    
    phone = normalize_phone_for_display(phone)
    if len(phone) <= visible_chars:
        return phone
    
    return "*" * (len(phone) - visible_chars) + phone[-visible_chars:]


def normalize_phone_for_display(phone: str) -> str:
    """
    Normalize phone number for display purposes.
    
    Args:
        phone: Phone number string
    
    Returns:
        str: Normalized phone number
    """
    # Remove any non-digit characters
    return ''.join(filter(str.isdigit, phone))


# ==================== BANK DETAILS ENCRYPTION ====================

def encrypt_bank_details(bank_details: Dict[str, Any]) -> str:
    """
    Encrypt bank details for secure storage.
    
    Args:
        bank_details: Dictionary containing bank account information
    
    Returns:
        str: Encrypted bank details as JSON string
    """
    import json
    
    if not bank_details:
        return ""
    
    try:
        json_str = json.dumps(bank_details)
        return encrypt_data(json_str)
    except Exception as e:
        logger.error(f"Bank details encryption error: {e}")
        return ""


def decrypt_bank_details(encrypted_details: str) -> Dict[str, Any]:
    """
    Decrypt bank details.
    
    Args:
        encrypted_details: Encrypted bank details string
    
    Returns:
        dict: Decrypted bank details
    """
    import json
    
    if not encrypted_details:
        return {}
    
    try:
        decrypted = decrypt_data(encrypted_details)
        return json.loads(decrypted) if decrypted else {}
    except Exception as e:
        logger.error(f"Bank details decryption error: {e}")
        return {}


def mask_account_number(account_number: str, visible_chars: int = 4) -> str:
    """
    Mask account number for display.
    
    Args:
        account_number: Account number
        visible_chars: Number of characters to show at the end
    
    Returns:
        str: Masked account number
    """
    if not account_number:
        return ""
    
    if len(account_number) <= visible_chars:
        return account_number
    
    return "*" * (len(account_number) - visible_chars) + account_number[-visible_chars:]


# ==================== PASSWORD HASHING ====================

def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2.
    
    Args:
        password: Plain text password
    
    Returns:
        str: Hashed password with salt
    """
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{base64.b64encode(key).decode()}"


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password
        password_hash: Stored password hash (format: salt:hash)
    
    Returns:
        bool: True if password matches
    """
    try:
        salt, stored_key = password_hash.split(':')
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return base64.b64encode(key).decode() == stored_key
    except Exception:
        return False


# ==================== TOKEN GENERATION ====================

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Token length in bytes
    
    Returns:
        str: Hexadecimal token
    """
    return secrets.token_hex(length)


def generate_reference_id(prefix: str = "REF") -> str:
    """
    Generate a unique reference ID.
    
    Args:
        prefix: Reference prefix
    
    Returns:
        str: Reference ID
    """
    from datetime import datetime
    
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    random_part = secrets.token_hex(4).upper()
    return f"{prefix}_{timestamp}_{random_part}"


def generate_idempotency_key() -> str:
    """
    Generate a unique idempotency key.
    
    Returns:
        str: Idempotency key
    """
    return generate_reference_id("IK")


# ==================== HASHING UTILITIES ====================

def sha256_hash(data: str) -> str:
    """
    Create SHA-256 hash of a string.
    
    Args:
        data: Input string
    
    Returns:
        str: SHA-256 hash
    """
    return hashlib.sha256(data.encode()).hexdigest()


def md5_hash(data: str) -> str:
    """
    Create MD5 hash of a string (for non-security purposes only).
    
    Args:
        data: Input string
    
    Returns:
        str: MD5 hash
    """
    return hashlib.md5(data.encode()).hexdigest()


def hmac_sign(data: str, secret: Optional[str] = None) -> str:
    """
    Create HMAC signature for data.
    
    Args:
        data: Input data
        secret: Secret key (uses JWT_SECRET if not provided)
    
    Returns:
        str: HMAC signature
    """
    import hmac
    
    if secret is None:
        secret = config.JWT_SECRET
    
    return hmac.new(
        secret.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_hmac(data: str, signature: str, secret: Optional[str] = None) -> bool:
    """
    Verify HMAC signature.
    
    Args:
        data: Original data
        signature: Signature to verify
        secret: Secret key
    
    Returns:
        bool: True if signature is valid
    """
    import hmac
    
    if secret is None:
        secret = config.JWT_SECRET
    
    expected = hmac.new(
        secret.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


# ==================== KEY DERIVATION ====================

def derive_key(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Derive a cryptographic key from a password using PBKDF2.
    
    Args:
        password: Password string
        salt: Optional salt (generated if not provided)
    
    Returns:
        tuple: (key, salt)
    """
    if salt is None:
        salt = secrets.token_bytes(16)
    
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100000,
)
    key = kdf.derive(password.encode())
    
    return key, salt


# ==================== DATA VALIDATION ====================

def is_valid_encrypted_data(encrypted_data: str) -> bool:
    """
    Check if a string appears to be valid encrypted data.
    
    Args:
        encrypted_data: Encrypted data string
    
    Returns:
        bool: True if appears valid
    """
    if not encrypted_data:
        return False
    
    try:
        base64.urlsafe_b64decode(encrypted_data)
        return True
    except Exception:
        return False


# ==================== SECURE COMPARISON ====================

def secure_compare(a: str, b: str) -> bool:
    """
    Securely compare two strings to prevent timing attacks.
    
    Args:
        a: First string
        b: Second string
    
    Returns:
        bool: True if strings are equal
    """
    return hmac.compare_digest(a, b)


# ==================== ENCRYPTED STORAGE CLASS ====================

class EncryptedStorage:
    """
    A secure storage class for encrypting and storing sensitive data.
    """
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize encrypted storage.
        
        Args:
            encryption_key: Optional custom encryption key
        """
        self.cipher = Fernet(encryption_key) if encryption_key else FERNET_CIPHER
    
    def encrypt(self, data: str) -> str:
        """Encrypt data."""
        if not data:
            return ""
        encrypted = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        if not encrypted_data:
            return ""
        decoded = base64.urlsafe_b64decode(encrypted_data)
        return self.cipher.decrypt(decoded).decode()
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt a dictionary as JSON."""
        import json
        return self.encrypt(json.dumps(data))
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt a dictionary from JSON."""
        import json
        decrypted = self.decrypt(encrypted_data)
        return json.loads(decrypted) if decrypted else {}
    
    def encrypt_batch(self, items: Dict[str, str]) -> Dict[str, str]:
        """Encrypt multiple items."""
        return {key: self.encrypt(value) for key, value in items.items()}
    
    def decrypt_batch(self, items: Dict[str, str]) -> Dict[str, str]:
        """Decrypt multiple items."""
        return {key: self.decrypt(value) for key, value in items.items()}


# ==================== SINGLETON INSTANCES ====================

# Create global encrypted storage instance
encrypted_storage = EncryptedStorage()


# ==================== EXPORTS ====================

__all__ = [
    # Fernet encryption
    'encrypt_data',
    'decrypt_data',
    
    # Phone encryption
    'encrypt_phone',
    'decrypt_phone',
    'hash_phone',
    'mask_phone',
    'normalize_phone_for_display',
    
    # Bank details encryption
    'encrypt_bank_details',
    'decrypt_bank_details',
    'mask_account_number',
    
    # Password hashing
    'hash_password',
    'verify_password',
    
    # Token generation
    'generate_secure_token',
    'generate_reference_id',
    'generate_idempotency_key',
    
    # Hashing utilities
    'sha256_hash',
    'md5_hash',
    'hmac_sign',
    'verify_hmac',
    
    # Key derivation
    'derive_key',
    
    # Validation
    'is_valid_encrypted_data',
    
    # Secure comparison
    'secure_compare',
    
    # Encrypted storage class
    'EncryptedStorage',
    'encrypted_storage',
]