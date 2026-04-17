# telegram-bot/bot/utils/logger.py
# Estif Bingo 24/7 - Logging Utilities
# Provides structured logging with file rotation, JSON formatting, and log levels

import logging
import logging.handlers
import sys
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from bot.config import config

# Log format constants
DEFAULT_LOG_FORMAT = config.LOG_FORMAT
DEFAULT_LOG_LEVEL = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
BOT_LOG_FILE = LOGS_DIR / "bot.log"
ERROR_LOG_FILE = LOGS_DIR / "errors.log"
ACCESS_LOG_FILE = LOGS_DIR / "access.log"
GAME_LOG_FILE = LOGS_DIR / "game.log"
API_LOG_FILE = LOGS_DIR / "api.log"


# ==================== CUSTOM LOG FORMATTERS ====================

class ColoredFormatter(logging.Formatter):
    """Custom formatter with color codes for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        log_message = super().format(record)
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        return f"{color}{log_message}{self.COLORS['RESET']}"


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, 'extra_data'):
            log_entry['extra'] = record.extra_data
        
        return json.dumps(log_entry)


# ==================== CUSTOM LOGGER CLASS ====================

class CustomLogger:
    """
    Custom logger with additional functionality for structured logging,
    file rotation, and context tracking.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(DEFAULT_LOG_LEVEL)
        self.name = name
        self._handlers = {}
        
        # Prevent adding handlers multiple times
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup log handlers (console and file)"""
        
        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(DEFAULT_LOG_LEVEL)
        console_formatter = ColoredFormatter(DEFAULT_LOG_FORMAT)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        self._handlers['console'] = console_handler
        
        # File handler for all logs
        if config.LOG_TO_FILE:
            file_handler = logging.handlers.RotatingFileHandler(
                BOT_LOG_FILE,
                maxBytes=10_485_760,  # 10MB
                backupCount=10
            )
            file_handler.setLevel(DEFAULT_LOG_LEVEL)
            file_formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            self._handlers['file'] = file_handler
            
            # Error file handler (only errors and above)
            error_handler = logging.handlers.RotatingFileHandler(
                ERROR_LOG_FILE,
                maxBytes=10_485_760,
                backupCount=10
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            self.logger.addHandler(error_handler)
            self._handlers['error_file'] = error_handler
    
    def _log(self, level: int, message: str, extra: Optional[Dict] = None):
        """Internal log method with extra data support"""
        if extra:
            # Add extra data to log record
            self.logger._log(level, message, (), extra={'extra_data': extra})
        else:
            self.logger.log(level, message)
    
    def debug(self, message: str, extra: Optional[Dict] = None):
        """Log debug message"""
        self._log(logging.DEBUG, message, extra)
    
    def info(self, message: str, extra: Optional[Dict] = None):
        """Log info message"""
        self._log(logging.INFO, message, extra)
    
    def warning(self, message: str, extra: Optional[Dict] = None):
        """Log warning message"""
        self._log(logging.WARNING, message, extra)
    
    def error(self, message: str, extra: Optional[Dict] = None):
        """Log error message"""
        self._log(logging.ERROR, message, extra)
    
    def critical(self, message: str, extra: Optional[Dict] = None):
        """Log critical message"""
        self._log(logging.CRITICAL, message, extra)
    
    def exception(self, message: str, extra: Optional[Dict] = None):
        """Log exception with traceback"""
        self.logger.exception(message, extra={'extra_data': extra} if extra else None)
    
    def set_level(self, level: str):
        """Set log level for all handlers"""
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(numeric_level)
        for handler in self._handlers.values():
            handler.setLevel(numeric_level)
    
    def add_file_handler(self, file_path: Path, level: str = "INFO"):
        """Add a custom file handler"""
        handler = logging.handlers.RotatingFileHandler(
            file_path,
            maxBytes=10_485_760,
            backupCount=5
        )
        handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
        self.logger.addHandler(handler)
        return handler


# ==================== LOGGER FACTORY ====================

_loggers: Dict[str, CustomLogger] = {}


def get_logger(name: str) -> CustomLogger:
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        CustomLogger: Logger instance
    """
    if name not in _loggers:
        _loggers[name] = CustomLogger(name)
    return _loggers[name]


def setup_logger(name: str = "estif_bingo") -> CustomLogger:
    """
    Setup and return the main application logger.
    
    Args:
        name: Logger name
    
    Returns:
        CustomLogger: Configured logger
    """
    logger = get_logger(name)
    
    # Log startup info
    logger.info(f"Logger initialized with level: {DEFAULT_LOG_LEVEL}")
    logger.info(f"Log to file: {config.LOG_TO_FILE}")
    
    return logger


# ==================== CONTEXT MANAGER FOR TEMPORARY LOG LEVEL ====================

class temp_log_level:
    """
    Context manager to temporarily change log level.
    
    Usage:
        with temp_log_level(logger, "DEBUG"):
            logger.debug("This will be logged")
    """
    
    def __init__(self, logger: CustomLogger, level: str):
        self.logger = logger
        self.level = level
        self.old_level = None
    
    def __enter__(self):
        self.old_level = self.logger.logger.level
        numeric_level = getattr(logging, self.level.upper(), logging.INFO)
        self.logger.logger.setLevel(numeric_level)
        for handler in self.logger._handlers.values():
            handler.setLevel(numeric_level)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.logger.setLevel(self.old_level)
        for handler in self.logger._handlers.values():
            handler.setLevel(self.old_level)


# ==================== REQUEST LOGGING MIDDLEWARE ====================

class RequestLogger:
    """
    Request logger for tracking API calls.
    """
    
    def __init__(self):
        self.logger = get_logger("api")
    
    def log_request(self, method: str, path: str, ip: str, user_agent: str, duration_ms: float, status: int):
        """
        Log an API request.
        
        Args:
            method: HTTP method
            path: Request path
            ip: Client IP address
            user_agent: User agent string
            duration_ms: Request duration in milliseconds
            status: Response status code
        """
        self.logger.info(
            f"Request: {method} {path} - {status} - {duration_ms:.2f}ms",
            extra={
                'method': method,
                'path': path,
                'ip': ip,
                'user_agent': user_agent,
                'duration_ms': duration_ms,
                'status': status
            }
        )
    
    def log_error(self, method: str, path: str, error: str, ip: str):
        """
        Log an API error.
        
        Args:
            method: HTTP method
            path: Request path
            error: Error message
            ip: Client IP address
        """
        self.logger.error(
            f"Error: {method} {path} - {error}",
            extra={
                'method': method,
                'path': path,
                'error': error,
                'ip': ip
            }
        )


# ==================== DATABASE LOGGER ====================

class DatabaseLogger:
    """
    Specialized logger for database operations.
    """
    
    def __init__(self):
        self.logger = get_logger("database")
    
    def log_query(self, query: str, params: tuple, duration_ms: float, success: bool):
        """
        Log a database query.
        
        Args:
            query: SQL query
            params: Query parameters
            duration_ms: Query duration in milliseconds
            success: Whether query was successful
        """
        # Truncate long queries for logging
        query_preview = query[:200] + "..." if len(query) > 200 else query
        
        self.logger.debug(
            f"Query: {query_preview} - {duration_ms:.2f}ms",
            extra={
                'query': query_preview,
                'params': str(params)[:200],
                'duration_ms': duration_ms,
                'success': success
            }
        )
    
    def log_error(self, query: str, error: str):
        """
        Log a database error.
        
        Args:
            query: SQL query that caused error
            error: Error message
        """
        query_preview = query[:200] + "..." if len(query) > 200 else query
        
        self.logger.error(
            f"Database error: {error}",
            extra={
                'query': query_preview,
                'error': error
            }
        )


# ==================== GAME LOGGER ====================

class GameLogger:
    """
    Specialized logger for game engine events.
    """
    
    def __init__(self):
        self.logger = get_logger("game_engine")
    
    def log_round_start(self, round_id: int, round_number: int):
        """Log round start"""
        self.logger.info(
            f"Round #{round_number} started",
            extra={'round_id': round_id, 'round_number': round_number}
        )
    
    def log_round_end(self, round_id: int, round_number: int, winners: list, prize_pool: float):
        """Log round end"""
        self.logger.info(
            f"Round #{round_number} ended with {len(winners)} winners, prize pool: {prize_pool}",
            extra={
                'round_id': round_id,
                'round_number': round_number,
                'winners': winners,
                'prize_pool': prize_pool
            }
        )
    
    def log_cartela_selection(self, user_id: int, cartela_ids: list, round_id: int):
        """Log cartela selection"""
        self.logger.info(
            f"User {user_id} selected cartelas: {cartela_ids}",
            extra={
                'user_id': user_id,
                'cartela_ids': cartela_ids,
                'round_id': round_id
            }
        )
    
    def log_number_draw(self, number: int, round_id: int, called_count: int):
        """Log number draw"""
        self.logger.debug(
            f"Number drawn: {number} ({called_count}/75)",
            extra={
                'number': number,
                'round_id': round_id,
                'called_count': called_count
            }
        )
    
    def log_win(self, user_id: int, amount: float, pattern: str, round_id: int):
        """Log win"""
        self.logger.info(
            f"User {user_id} won {amount} ETB with pattern: {pattern}",
            extra={
                'user_id': user_id,
                'amount': amount,
                'pattern': pattern,
                'round_id': round_id
            }
        )


# ==================== FINANCIAL LOGGER ====================

class FinancialLogger:
    """
    Specialized logger for financial transactions (deposits, withdrawals, transfers).
    """
    
    def __init__(self):
        self.logger = get_logger("financial")
    
    def log_deposit(self, user_id: int, amount: float, method: str, status: str, deposit_id: int):
        """Log deposit transaction"""
        self.logger.info(
            f"Deposit: User {user_id} - {amount} ETB via {method} - {status}",
            extra={
                'user_id': user_id,
                'amount': amount,
                'method': method,
                'status': status,
                'deposit_id': deposit_id,
                'type': 'deposit'
            }
        )
    
    def log_withdrawal(self, user_id: int, amount: float, method: str, status: str, withdrawal_id: int):
        """Log withdrawal transaction"""
        self.logger.info(
            f"Withdrawal: User {user_id} - {amount} ETB via {method} - {status}",
            extra={
                'user_id': user_id,
                'amount': amount,
                'method': method,
                'status': status,
                'withdrawal_id': withdrawal_id,
                'type': 'withdrawal'
            }
        )
    
    def log_transfer(self, from_user: int, to_user: int, amount: float, fee: float, transfer_id: str):
        """Log transfer transaction"""
        self.logger.info(
            f"Transfer: {from_user} -> {to_user} - {amount} ETB (fee: {fee})",
            extra={
                'from_user': from_user,
                'to_user': to_user,
                'amount': amount,
                'fee': fee,
                'transfer_id': transfer_id,
                'type': 'transfer'
            }
        )


# ==================== SECURITY LOGGER ====================

class SecurityLogger:
    """
    Specialized logger for security events (login attempts, auth failures, etc.).
    """
    
    def __init__(self):
        self.logger = get_logger("security")
    
    def log_login_attempt(self, user_id: int, success: bool, ip: str):
        """Log login attempt"""
        self.logger.info(
            f"Login attempt: User {user_id} - {'Success' if success else 'Failed'}",
            extra={
                'user_id': user_id,
                'success': success,
                'ip': ip,
                'event': 'login_attempt'
            }
        )
    
    def log_otp_request(self, user_id: int, purpose: str, ip: str):
        """Log OTP request"""
        self.logger.info(
            f"OTP requested: User {user_id} - {purpose}",
            extra={
                'user_id': user_id,
                'purpose': purpose,
                'ip': ip,
                'event': 'otp_request'
            }
        )
    
    def log_unauthorized_access(self, user_id: Optional[int], endpoint: str, ip: str):
        """Log unauthorized access attempt"""
        self.logger.warning(
            f"Unauthorized access: User {user_id} - {endpoint}",
            extra={
                'user_id': user_id,
                'endpoint': endpoint,
                'ip': ip,
                'event': 'unauthorized'
            }
        )
    
    def log_admin_action(self, admin_id: int, action: str, target: str, details: Dict):
        """Log admin action"""
        self.logger.info(
            f"Admin action: {admin_id} - {action} on {target}",
            extra={
                'admin_id': admin_id,
                'action': action,
                'target': target,
                'details': details,
                'event': 'admin_action'
            }
        )


# ==================== EXPORTS ====================

__all__ = [
    # Main logger functions
    'get_logger',
    'setup_logger',
    'temp_log_level',
    
    # Specialized loggers
    'RequestLogger',
    'DatabaseLogger',
    'GameLogger',
    'FinancialLogger',
    'SecurityLogger',
    
    # Constants
    'DEFAULT_LOG_LEVEL',
    'DEFAULT_LOG_FORMAT',
    'LOGS_DIR',
    'BOT_LOG_FILE',
    'ERROR_LOG_FILE',
    'ACCESS_LOG_FILE',
    'GAME_LOG_FILE',
    'API_LOG_FILE',
]

# Create default loggers for convenience
request_logger = RequestLogger()
database_logger = DatabaseLogger()
game_logger = GameLogger()
financial_logger = FinancialLogger()
security_logger = SecurityLogger()