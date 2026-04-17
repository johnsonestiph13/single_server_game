# telegram-bot/bot/db/models.py
# Estif Bingo 24/7 - Database Models
# Defines all database tables using SQLAlchemy ORM

from datetime import datetime
from typing import Optional, List, Dict, Any
# SQLAlchemy imports
from sqlalchemy import (  # noqa: F401
    BigInteger, String, Boolean, Integer, Float, 
    DateTime, Text, JSON, ForeignKey, Index, 
    Numeric, Table, Column
)
from sqlalchemy.ext.declarative import declarative_base  # noqa: F401
from sqlalchemy.orm import Mapped, mapped_column, relationship  # noqa: F401
from sqlalchemy.dialects.postgresql import JSONB     # noqa: F401

Base = declarative_base()


# ==================== USERS & AUTHENTICATION ====================

class User(Base):
    """User model - stores all user information"""
    __tablename__ = 'users'

    # Primary Key
    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    
    # Basic Info
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Phone (encrypted)
    phone_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    phone_last4: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    
    # Preferences
    lang: Mapped[str] = mapped_column(String(10), default='en')
    sound_pack: Mapped[str] = mapped_column(String(20), default='pack1')
    
    # Status Flags
    registered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    welcome_bonus_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Financial
    balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    
    # Statistics
    total_games_played: Mapped[int] = mapped_column(Integer, default=0)
    total_wagered: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    total_won: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="user", lazy="dynamic")
    deposits: Mapped[List["Deposit"]] = relationship(back_populates="user", lazy="dynamic")
    withdrawals: Mapped[List["Withdrawal"]] = relationship(back_populates="user", lazy="dynamic")
    sent_transfers: Mapped[List["Transfer"]] = relationship(foreign_keys="Transfer.sender_id", back_populates="sender", lazy="dynamic")
    received_transfers: Mapped[List["Transfer"]] = relationship(foreign_keys="Transfer.receiver_id", back_populates="receiver", lazy="dynamic")
    round_selections: Mapped[List["RoundSelection"]] = relationship(back_populates="user", lazy="dynamic")
    bonus_claims: Mapped[List["BonusClaim"]] = relationship(back_populates="user", lazy="dynamic")
    tournament_registrations: Mapped[List["TournamentRegistration"]] = relationship(back_populates="user", lazy="dynamic")
    admin_logs: Mapped[List["AdminLog"]] = relationship(back_populates="admin", lazy="dynamic")
    auth_codes: Mapped[List["AuthCode"]] = relationship(back_populates="user", lazy="dynamic")
    sessions: Mapped[List["UserSession"]] = relationship(back_populates="user", lazy="dynamic")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username}, balance={self.balance})>"


class AuthCode(Base):
    """Authentication codes (OTP) model"""
    __tablename__ = 'auth_codes'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    purpose: Mapped[str] = mapped_column(String(50), default='game_login')
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="auth_codes")
    
    __table_args__ = (
        Index('idx_auth_codes_telegram_id', 'telegram_id'),
        Index('idx_auth_codes_code_hash', 'code_hash'),
        Index('idx_auth_codes_expires_at', 'expires_at'),
        Index('idx_auth_codes_purpose', 'purpose'),
    )


class UserSession(Base):
    """User session model for web app authentication"""
    __tablename__ = 'user_sessions'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")
    
    __table_args__ = (
        Index('idx_user_sessions_telegram_id', 'telegram_id'),
        Index('idx_user_sessions_session_token', 'session_token'),
        Index('idx_user_sessions_expires_at', 'expires_at'),
    )


# ==================== FINANCIAL ====================

class Transaction(Base):
    """Transaction model for all financial movements"""
    __tablename__ = 'transactions'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    balance_after: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="transactions")
    
    __table_args__ = (
        Index('idx_transactions_user_id', 'user_id'),
        Index('idx_transactions_type', 'type'),
        Index('idx_transactions_created_at', 'created_at'),
        Index('idx_transactions_reference_id', 'reference_id'),
        Index('idx_transactions_user_type', 'user_id', 'type'),
    )


class Deposit(Base):
    """Deposit request model"""
    __tablename__ = 'deposits'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    account_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    photo_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="deposits")
    
    __table_args__ = (
        Index('idx_deposits_telegram_id', 'telegram_id'),
        Index('idx_deposits_status', 'status'),
        Index('idx_deposits_created_at', 'created_at'),
        Index('idx_deposits_transaction_id', 'transaction_id'),
    )


class Withdrawal(Base):
    """Withdrawal request model"""
    __tablename__ = 'withdrawals'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    method_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="withdrawals")
    
    __table_args__ = (
        Index('idx_withdrawals_telegram_id', 'telegram_id'),
        Index('idx_withdrawals_status', 'status'),
        Index('idx_withdrawals_created_at', 'created_at'),
        Index('idx_withdrawals_session_id', 'session_id'),
    )


class Transfer(Base):
    """Balance transfer between users"""
    __tablename__ = 'transfers'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transfer_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    receiver_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='completed')
    sender_balance_before: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    sender_balance_after: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    receiver_balance_before: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    receiver_balance_after: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    metadata: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sender: Mapped["User"] = relationship(foreign_keys=[sender_id], back_populates="sent_transfers")
    receiver: Mapped["User"] = relationship(foreign_keys=[receiver_id], back_populates="received_transfers")
    
    __table_args__ = (
        Index('idx_transfers_transfer_id', 'transfer_id'),
        Index('idx_transfers_sender_id', 'sender_id'),
        Index('idx_transfers_receiver_id', 'receiver_id'),
        Index('idx_transfers_created_at', 'created_at'),
        Index('idx_transfers_sender_receiver', 'sender_id', 'receiver_id'),
    )


# ==================== GAME ====================

class Cartela(Base):
    """Bingo cartela (card) model"""
    __tablename__ = 'cartelas'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    grid: Mapped[List[List[int]]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_cartelas_is_active', 'is_active'),
        Index('idx_cartelas_id_active', 'id', 'is_active'),
    )


class GameRound(Base):
    """Game round model"""
    __tablename__ = 'game_rounds'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='selection')
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    selection_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_cartelas: Mapped[int] = mapped_column(Integer, default=0)
    total_players: Mapped[int] = mapped_column(Integer, default=0)
    winners: Mapped[Optional[List[Dict]]] = mapped_column(JSONB, nullable=True)
    prize_pool: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    selections: Mapped[List["RoundSelection"]] = relationship(back_populates="round", lazy="dynamic")
    
    __table_args__ = (
        Index('idx_game_rounds_status', 'status'),
        Index('idx_game_rounds_start_time', 'start_time'),
    )


class RoundSelection(Base):
    """Player's cartela selection in a round"""
    __tablename__ = 'round_selections'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_id: Mapped[int] = mapped_column(Integer, ForeignKey('game_rounds.id'))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    cartela_id: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    selected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    round: Mapped["GameRound"] = relationship(back_populates="selections")
    user: Mapped["User"] = relationship(back_populates="round_selections")
    
    __table_args__ = (
        Index('idx_round_selections_round_id', 'round_id'),
        Index('idx_round_selections_user_id', 'user_id'),
        Index('idx_round_selections_cartela_id', 'cartela_id'),
    )


# ==================== BONUS ====================

class BonusClaim(Base):
    """Bonus claim record"""
    __tablename__ = 'bonus_claims'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    bonus_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    metadata: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='claimed')
    claimed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="bonus_claims")
    
    __table_args__ = (
        Index('idx_bonus_claims_telegram_id', 'telegram_id'),
        Index('idx_bonus_claims_type', 'bonus_type'),
        Index('idx_bonus_claims_claimed_at', 'claimed_at'),
        Index('idx_bonus_claims_telegram_type', 'telegram_id', 'bonus_type'),
    )


# ==================== TOURNAMENT ====================

class Tournament(Base):
    """Tournament model"""
    __tablename__ = 'tournaments'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    prize_pool: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_players: Mapped[int] = mapped_column(Integer, default=1000)
    min_players: Mapped[int] = mapped_column(Integer, default=2)
    player_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    prize_distributed: Mapped[bool] = mapped_column(Boolean, default=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    registrations: Mapped[List["TournamentRegistration"]] = relationship(back_populates="tournament", lazy="dynamic")
    prizes: Mapped[List["TournamentPrize"]] = relationship(back_populates="tournament", lazy="dynamic")
    
    __table_args__ = (
        Index('idx_tournaments_status', 'status'),
        Index('idx_tournaments_type', 'type'),
        Index('idx_tournaments_start_time', 'start_time'),
        Index('idx_tournaments_end_time', 'end_time'),
    )


class TournamentRegistration(Base):
    """Tournament registration model"""
    __tablename__ = 'tournament_registrations'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey('tournaments.id'))
    entry_fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default='active')
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="tournament_registrations")
    tournament: Mapped["Tournament"] = relationship(back_populates="registrations")
    
    __table_args__ = (
        Index('idx_tournament_registrations_tournament', 'tournament_id'),
        Index('idx_tournament_registrations_user', 'telegram_id'),
        Index('idx_tournament_registrations_points', 'points'),
        Index('idx_tournament_registrations_status', 'status'),
        Index('idx_tournament_registrations_unique', 'telegram_id', 'tournament_id', unique=True),
    )


class TournamentPrize(Base):
    """Tournament prize distribution model"""
    __tablename__ = 'tournament_prizes'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey('tournaments.id'))
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    prize_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tournament: Mapped["Tournament"] = relationship(back_populates="prizes")
    
    __table_args__ = (
        Index('idx_tournament_prizes_tournament', 'tournament_id'),
        Index('idx_tournament_prizes_user', 'telegram_id'),
        Index('idx_tournament_prizes_rank', 'rank'),
        Index('idx_tournament_prizes_unique', 'tournament_id', 'telegram_id', 'rank', unique=True),
    )


# ==================== ADMIN & SYSTEM ====================

class AdminLog(Base):
    """Admin action log model"""
    __tablename__ = 'admin_log'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    admin: Mapped["User"] = relationship(back_populates="admin_logs")
    
    __table_args__ = (
        Index('idx_admin_log_admin_id', 'admin_id'),
        Index('idx_admin_log_action', 'action'),
        Index('idx_admin_log_created_at', 'created_at'),
        Index('idx_admin_log_target', 'target_type', 'target_id'),
    )


class SystemSetting(Base):
    """System settings model"""
    __tablename__ = 'system_settings'
    
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BroadcastLog(Base):
    """Broadcast message log model"""
    __tablename__ = 'broadcast_log'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_broadcast_log_admin_id', 'admin_id'),
        Index('idx_broadcast_log_sent_at', 'sent_at'),
    )


class Announcement(Base):
    """System announcement model"""
    __tablename__ = 'announcements'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default='normal')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_announcements_is_active', 'is_active'),
        Index('idx_announcements_priority', 'priority'),
        Index('idx_announcements_expires_at', 'expires_at'),
    )


class AnnouncementDismissal(Base):
    """Track which users dismissed which announcements"""
    __tablename__ = 'announcement_dismissals'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(Integer, ForeignKey('announcements.id'))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.telegram_id'))
    dismissed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_announcement_dismissals_user', 'user_id'),
        Index('idx_announcement_dismissals_announcement', 'announcement_id'),
        Index('idx_announcement_dismissals_unique', 'announcement_id', 'user_id', unique=True),
    )


class RateLimit(Base):
    """Rate limiting records"""
    __tablename__ = 'rate_limits'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_rate_limits_identifier', 'identifier'),
        Index('idx_rate_limits_action', 'action'),
        Index('idx_rate_limits_created_at', 'created_at'),
        Index('idx_rate_limits_identifier_action', 'identifier', 'action'),
    )


class ApiKey(Base):
    """API key model for external access"""
    __tablename__ = 'api_keys'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    permissions: Mapped[List[str]] = mapped_column(JSONB, default=['read'])
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_api_keys_key_hash', 'key_hash'),
        Index('idx_api_keys_is_active', 'is_active'),
        Index('idx_api_keys_expires_at', 'expires_at'),
    )


class SchemaMigration(Base):
    """Track database schema migrations"""
    __tablename__ = 'schema_migrations'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    migration_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==================== EXPORTS ====================

__all__ = [
    # Users & Auth
    'User',
    'AuthCode',
    'UserSession',
    
    # Financial
    'Transaction',
    'Deposit',
    'Withdrawal',
    'Transfer',
    
    # Game
    'Cartela',
    'GameRound',
    'RoundSelection',
    
    # Bonus
    'BonusClaim',
    
    # Tournament
    'Tournament',
    'TournamentRegistration',
    'TournamentPrize',
    
    # Admin & System
    'AdminLog',
    'SystemSetting',
    'BroadcastLog',
    'Announcement',
    'AnnouncementDismissal',
    'RateLimit',
    'ApiKey',
    'SchemaMigration',
    
    # Base
    'Base',
]