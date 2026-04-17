# telegram-bot/bot/utils/__init__.py
# Estif Bingo 24/7 - Utilities Package
# Exports all utility functions and classes

import logging

# Setup package logger
logger = logging.getLogger(__name__)

# ==================== LOGGER ====================

from bot.utils.logger import (
    get_logger,
    setup_logger,
    temp_log_level,
    RequestLogger,
    DatabaseLogger,
    GameLogger,
    FinancialLogger,
    SecurityLogger,
    request_logger,
    database_logger,
    game_logger,
    financial_logger,
    security_logger,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_FORMAT,
    LOGS_DIR,
    BOT_LOG_FILE,
    ERROR_LOG_FILE,
    ACCESS_LOG_FILE,
    GAME_LOG_FILE,
    API_LOG_FILE,
)

# ==================== SECURITY ====================

from bot.utils.security import (
    # JWT functions
    generate_jwt,
    generate_refresh_token,
    verify_jwt,
    refresh_jwt,
    generate_jwt_for_game,
    generate_ws_token,
    verify_ws_token,
    # Password functions
    hash_password,
    verify_password,
    # OTP functions
    generate_otp,
    hash_otp,
    verify_otp,
    # API key functions
    generate_api_key,
    hash_api_key,
    verify_api_key,
    # Idempotency
    generate_idempotency_key,
    # Rate limiting
    rate_limit,
    clear_rate_limit_cache,
    # Input sanitization
    sanitize_input,
    sanitize_phone,
    sanitize_amount,
    # Signature verification
    generate_signature,
    verify_signature,
    # Token generation
    generate_secure_token,
    generate_short_code,
    # Simple encryption
    simple_encrypt,
    simple_decrypt,
)

# ==================== CRYPTO ====================

from bot.utils.crypto import (
    # Fernet encryption
    encrypt_data,
    decrypt_data,
    # Phone encryption
    encrypt_phone,
    decrypt_phone,
    hash_phone,
    mask_phone,
    normalize_phone_for_display,
    # Bank details encryption
    encrypt_bank_details,
    decrypt_bank_details,
    mask_account_number,
    # Password hashing
    hash_password as crypto_hash_password,
    verify_password as crypto_verify_password,
    # Token generation
    generate_secure_token as crypto_generate_secure_token,
    generate_reference_id,
    generate_idempotency_key as crypto_generate_idempotency_key,
    # Hashing utilities
    sha256_hash,
    md5_hash,
    hmac_sign,
    verify_hmac,
    # Key derivation
    derive_key,
    # Validation
    is_valid_encrypted_data,
    # Secure comparison
    secure_compare,
    # Encrypted storage class
    EncryptedStorage,
    encrypted_storage,
)

# ==================== VALIDATORS ====================

from bot.utils.validators import (
    # Phone validation
    is_valid_ethiopian_phone,
    is_valid_kenyan_phone,
    is_valid_phone,
    normalize_phone,
    get_phone_carrier,
    validate_phone_with_carrier,
    # Amount validation
    validate_amount,
    validate_deposit_amount,
    validate_withdrawal_amount,
    validate_transfer_amount,
    # Bank validation
    validate_account_number,
    validate_account_holder,
    # Transaction validation
    validate_transaction_id,
    # Email validation
    is_valid_email,
    normalize_email,
    # Username validation
    is_valid_username,
    # Date validation
    is_valid_date,
    is_valid_datetime,
    # Cartela validation
    is_valid_cartela_id,
    validate_cartela_selection,
    # Referral validation
    is_valid_referral_code,
    # URL validation
    is_valid_url,
    # Password validation
    is_strong_password,
    # Sanitization
    sanitize_string,
    sanitize_numeric,
    sanitize_boolean,
)

# ==================== OTP ====================

from bot.utils.otp import (
    # Generation
    generate_otp as otp_generate_otp,
    generate_alphanumeric_otp,
    generate_otp_hash,
    verify_otp_hash,
    # Storage
    store_otp,
    get_stored_otp,
    verify_stored_otp,
    delete_stored_otp,
    clear_expired_otps,
    # Attempt tracking
    record_otp_attempt,
    get_otp_attempts,
    reset_otp_attempts,
    is_otp_locked,
    # Rate limiting
    check_otp_rate_limit,
    record_otp_request,
    # Complete workflow
    create_otp,
    validate_otp,
    request_new_otp,
    # TOTP
    TOTP,
    # Utility
    format_otp_message,
    cleanup_otp_storage,
    # Constants
    OTP_LENGTH,
    OTP_EXPIRY_SECONDS,
    MAX_OTP_ATTEMPTS,
    OTP_RATE_LIMIT_SECONDS,
    MAX_OTP_PER_HOUR,
)

# ==================== METRICS ====================

from bot.utils.metrics import (
    # Classes
    MetricsCollector,
    PerformanceMonitor,
    HealthChecker,
    BusinessMetrics,
    MetricType,
    MetricUnit,
    # Singleton instances
    metrics_collector,
    performance_monitor,
    health_checker,
    business_metrics,
    # Decorators
    track_time,
    track_request,
)

# ==================== CARTELA GENERATOR ====================

from bot.utils.cartela_generator import (
    TOTAL_CARTELAS,
    GRID_SIZE,
    COLUMN_RANGES,
    get_random_numbers,
    generate_single_cartela,
    generate_all_cartelas,
    validate_cartela_grid,
    validate_cartelas_file,
    cartela_to_csv_row,
    cartelas_to_csv,
    cartela_to_dict,
    save_cartelas_to_json,
    load_cartelas_from_json,
    regenerate_cartelas,
    display_cartela_grid,
    display_sample_cartelas,
    get_number_distribution,
    print_statistics,
)

# ==================== MAIN UTILITIES ====================

from bot.utils.main import (
    # String utilities
    truncate_text,
    slugify,
    mask_string,
    mask_phone as main_mask_phone,
    mask_email,
    # Validation utilities
    is_valid_ethiopian_phone as main_is_valid_ethiopian_phone,
    is_valid_kenyan_phone as main_is_valid_kenyan_phone,
    is_valid_phone as main_is_valid_phone,
    normalize_phone as main_normalize_phone,
    get_phone_carrier as main_get_phone_carrier,
    validate_amount as main_validate_amount,
    validate_account_number as main_validate_account_number,
    validate_transaction_id as main_validate_transaction_id,
    # Token generation
    generate_otp as main_generate_otp,
    generate_token,
    generate_reference_id as main_generate_reference_id,
    hash_token,
    # Date/time utilities
    format_datetime,
    format_date,
    format_time_remaining,
    time_ago,
    # Number utilities
    format_currency,
    format_percentage,
    safe_divide,
    # Dictionary utilities
    safe_get,
    merge_dicts,
    # Decorators
    retry,
    timing_decorator,
)

# ==================== CONVENIENCE RE-EXPORTS ====================

# Commonly used functions (aliases for convenience)
generate_secure_token = crypto_generate_secure_token
generate_idempotency_key = crypto_generate_idempotency_key
hash_password = crypto_hash_password
verify_password = crypto_verify_password

# ==================== PACKAGE EXPORTS ====================

__all__ = [
    # Logger
    'get_logger',
    'setup_logger',
    'temp_log_level',
    'RequestLogger',
    'DatabaseLogger',
    'GameLogger',
    'FinancialLogger',
    'SecurityLogger',
    'request_logger',
    'database_logger',
    'game_logger',
    'financial_logger',
    'security_logger',
    'DEFAULT_LOG_LEVEL',
    'DEFAULT_LOG_FORMAT',
    'LOGS_DIR',
    'BOT_LOG_FILE',
    'ERROR_LOG_FILE',
    'ACCESS_LOG_FILE',
    'GAME_LOG_FILE',
    'API_LOG_FILE',
    
    # Security
    'generate_jwt',
    'generate_refresh_token',
    'verify_jwt',
    'refresh_jwt',
    'generate_jwt_for_game',
    'generate_ws_token',
    'verify_ws_token',
    'hash_password',
    'verify_password',
    'generate_otp',
    'hash_otp',
    'verify_otp',
    'generate_api_key',
    'hash_api_key',
    'verify_api_key',
    'generate_idempotency_key',
    'rate_limit',
    'clear_rate_limit_cache',
    'sanitize_input',
    'sanitize_phone',
    'sanitize_amount',
    'generate_signature',
    'verify_signature',
    'generate_secure_token',
    'generate_short_code',
    'simple_encrypt',
    'simple_decrypt',
    
    # Crypto
    'encrypt_data',
    'decrypt_data',
    'encrypt_phone',
    'decrypt_phone',
    'hash_phone',
    'mask_phone',
    'normalize_phone_for_display',
    'encrypt_bank_details',
    'decrypt_bank_details',
    'mask_account_number',
    'sha256_hash',
    'md5_hash',
    'hmac_sign',
    'verify_hmac',
    'derive_key',
    'is_valid_encrypted_data',
    'secure_compare',
    'EncryptedStorage',
    'encrypted_storage',
    
    # Validators
    'is_valid_ethiopian_phone',
    'is_valid_kenyan_phone',
    'is_valid_phone',
    'normalize_phone',
    'get_phone_carrier',
    'validate_phone_with_carrier',
    'validate_amount',
    'validate_deposit_amount',
    'validate_withdrawal_amount',
    'validate_transfer_amount',
    'validate_account_number',
    'validate_account_holder',
    'validate_transaction_id',
    'is_valid_email',
    'normalize_email',
    'is_valid_username',
    'is_valid_date',
    'is_valid_datetime',
    'is_valid_cartela_id',
    'validate_cartela_selection',
    'is_valid_referral_code',
    'is_valid_url',
    'is_strong_password',
    'sanitize_string',
    'sanitize_numeric',
    'sanitize_boolean',
    
    # OTP
    'otp_generate_otp',
    'generate_alphanumeric_otp',
    'generate_otp_hash',
    'verify_otp_hash',
    'store_otp',
    'get_stored_otp',
    'verify_stored_otp',
    'delete_stored_otp',
    'clear_expired_otps',
    'record_otp_attempt',
    'get_otp_attempts',
    'reset_otp_attempts',
    'is_otp_locked',
    'check_otp_rate_limit',
    'record_otp_request',
    'create_otp',
    'validate_otp',
    'request_new_otp',
    'TOTP',
    'format_otp_message',
    'cleanup_otp_storage',
    'OTP_LENGTH',
    'OTP_EXPIRY_SECONDS',
    'MAX_OTP_ATTEMPTS',
    'OTP_RATE_LIMIT_SECONDS',
    'MAX_OTP_PER_HOUR',
    
    # Metrics
    'MetricsCollector',
    'PerformanceMonitor',
    'HealthChecker',
    'BusinessMetrics',
    'MetricType',
    'MetricUnit',
    'metrics_collector',
    'performance_monitor',
    'health_checker',
    'business_metrics',
    'track_time',
    'track_request',
    
    # Cartela Generator
    'TOTAL_CARTELAS',
    'GRID_SIZE',
    'COLUMN_RANGES',
    'get_random_numbers',
    'generate_single_cartela',
    'generate_all_cartelas',
    'validate_cartela_grid',
    'validate_cartelas_file',
    'cartela_to_csv_row',
    'cartelas_to_csv',
    'cartela_to_dict',
    'save_cartelas_to_json',
    'load_cartelas_from_json',
    'regenerate_cartelas',
    'display_cartela_grid',
    'display_sample_cartelas',
    'get_number_distribution',
    'print_statistics',
    
    # Main Utilities
    'truncate_text',
    'slugify',
    'mask_string',
    'main_mask_phone',
    'mask_email',
    'generate_token',
    'main_generate_reference_id',
    'hash_token',
    'format_datetime',
    'format_date',
    'format_time_remaining',
    'time_ago',
    'format_currency',
    'format_percentage',
    'safe_divide',
    'safe_get',
    'merge_dicts',
    'retry',
    'timing_decorator',
]

logger.info("Utils package initialized")