# telegram-bot/bot/api/balance_ops.py
# Estif Bingo 24/7 - Balance Operations Module
# Handles all balance-related operations with atomic transactions and audit logging

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from bot.db.database import db, execute, fetch_one, fetch_val
from bot.db.repository import UserRepository, TransactionRepository, AuditRepository
from bot.utils.logger import logger

# ==================== CORE BALANCE OPERATIONS ====================

async def get_balance(telegram_id: int) -> float:
    """
    Get user's current balance
    
    Args:
        telegram_id: int - User's Telegram ID
    
    Returns:
        float: Current balance
    """
    try:
        balance = await UserRepository.get_balance(telegram_id)
        logger.debug(f"Balance for user {telegram_id}: {balance}")
        return balance
    except Exception as e:
        logger.error(f"Error getting balance for user {telegram_id}: {e}")
        return 0.0


async def add_balance(
    telegram_id: int,
    amount: float,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None,
    reference_id: Optional[str] = None
) -> bool:
    """
    Add balance to a user's account (credit)
    
    Args:
        telegram_id: int - User's Telegram ID
        amount: float - Amount to add (must be positive)
        reason: str - Reason for adding balance (e.g., 'deposit', 'win', 'bonus')
        metadata: dict - Additional metadata
        reference_id: str - Reference ID (e.g., deposit_id, round_id)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if amount <= 0:
        logger.warning(f"Invalid add amount for user {telegram_id}: {amount}")
        return False
    
    # Start transaction
    async with db.transaction():
        # Get current balance
        current_balance = await get_balance(telegram_id)
        new_balance = current_balance + amount
        
        # Update balance in database
        result = await UserRepository.update_balance(telegram_id, new_balance, operation='set')
        
        if result is None:
            logger.error(f"Failed to update balance for user {telegram_id}")
            return False
        
        # Create transaction record
        await TransactionRepository.create({
            'user_id': telegram_id,
            'type': reason,
            'amount': amount,
            'balance_after': new_balance,
            'reference_id': reference_id,
            'metadata': {
                'operation': 'add',
                'previous_balance': current_balance,
                'new_balance': new_balance,
                **(metadata or {})
            }
        })
        
        # Audit log
        await AuditRepository.log(
            user_id=telegram_id,
            action=f"balance_add_{reason}",
            entity_type="balance",
            entity_id=str(telegram_id),
            old_value={'balance': current_balance},
            new_value={'balance': new_balance, 'amount': amount},
            metadata={'reason': reason, **metadata} if metadata else {'reason': reason}
        )
        
        logger.info(f"Added {amount} to user {telegram_id} balance. Reason: {reason}. New balance: {new_balance}")
        return True


async def deduct_balance(
    telegram_id: int,
    amount: float,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None,
    reference_id: Optional[str] = None,
    allow_negative: bool = False
) -> bool:
    """
    Deduct balance from a user's account (debit)
    
    Args:
        telegram_id: int - User's Telegram ID
        amount: float - Amount to deduct (must be positive)
        reason: str - Reason for deducting balance (e.g., 'cartela_purchase', 'withdrawal')
        metadata: dict - Additional metadata
        reference_id: str - Reference ID (e.g., withdrawal_id, round_id)
        allow_negative: bool - Allow balance to go negative (default: False)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if amount <= 0:
        logger.warning(f"Invalid deduct amount for user {telegram_id}: {amount}")
        return False
    
    # Start transaction
    async with db.transaction():
        # Get current balance
        current_balance = await get_balance(telegram_id)
        
        # Check if sufficient balance
        if current_balance < amount and not allow_negative:
            logger.warning(f"Insufficient balance for user {telegram_id}. Balance: {current_balance}, Required: {amount}")
            return False
        
        new_balance = current_balance - amount
        
        # Update balance in database
        result = await UserRepository.update_balance(telegram_id, new_balance, operation='set')
        
        if result is None:
            logger.error(f"Failed to update balance for user {telegram_id}")
            return False
        
        # Create transaction record (negative amount)
        await TransactionRepository.create({
            'user_id': telegram_id,
            'type': reason,
            'amount': -amount,
            'balance_after': new_balance,
            'reference_id': reference_id,
            'metadata': {
                'operation': 'deduct',
                'previous_balance': current_balance,
                'new_balance': new_balance,
                'allow_negative': allow_negative,
                **(metadata or {})
            }
        })
        
        # Audit log
        await AuditRepository.log(
            user_id=telegram_id,
            action=f"balance_deduct_{reason}",
            entity_type="balance",
            entity_id=str(telegram_id),
            old_value={'balance': current_balance},
            new_value={'balance': new_balance, 'amount': amount},
            metadata={'reason': reason, **metadata} if metadata else {'reason': reason}
        )
        
        logger.info(f"Deducted {amount} from user {telegram_id} balance. Reason: {reason}. New balance: {new_balance}")
        return True


async def set_balance(
    telegram_id: int,
    amount: float,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None,
    reference_id: Optional[str] = None,
    admin_id: Optional[int] = None
) -> bool:
    """
    Set balance to a specific amount (admin only operation)
    
    Args:
        telegram_id: int - User's Telegram ID
        amount: float - New balance amount
        reason: str - Reason for setting balance
        metadata: dict - Additional metadata
        reference_id: str - Reference ID
        admin_id: int - Admin who performed this action
    
    Returns:
        bool: True if successful, False otherwise
    """
    if amount < 0:
        logger.warning(f"Cannot set negative balance for user {telegram_id}: {amount}")
        return False
    
    # Start transaction
    async with db.transaction():
        # Get current balance
        current_balance = await get_balance(telegram_id)
        
        # Update balance in database
        result = await UserRepository.update_balance(telegram_id, amount, operation='set')
        
        if result is None:
            logger.error(f"Failed to set balance for user {telegram_id}")
            return False
        
        # Create transaction record
        await TransactionRepository.create({
            'user_id': telegram_id,
            'type': 'admin_adjustment',
            'amount': amount - current_balance,
            'balance_after': amount,
            'reference_id': reference_id,
            'metadata': {
                'operation': 'set',
                'previous_balance': current_balance,
                'new_balance': amount,
                'reason': reason,
                'admin_id': admin_id,
                **(metadata or {})
            }
        })
        
        # Audit log
        await AuditRepository.log(
            user_id=telegram_id,
            action="balance_set",
            entity_type="balance",
            entity_id=str(telegram_id),
            old_value={'balance': current_balance, 'admin_id': admin_id},
            new_value={'balance': amount, 'reason': reason},
            metadata={'admin_id': admin_id, 'reason': reason}
        )
        
        logger.info(f"Balance set for user {telegram_id} from {current_balance} to {amount} by admin {admin_id}")
        return True


# ==================== BULK BALANCE OPERATIONS ====================

async def add_balance_bulk(
    operations: list,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Add balance to multiple users in a single transaction
    
    Args:
        operations: list - List of dicts with 'telegram_id' and 'amount'
        reason: str - Reason for adding balance
        metadata: dict - Additional metadata
    
    Returns:
        dict: Results with success and failure counts
    """
    results = {
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    async with db.transaction():
        for op in operations:
            try:
                telegram_id = op.get('telegram_id')
                amount = op.get('amount')
                
                if not telegram_id or amount <= 0:
                    results['failed'] += 1
                    results['errors'].append(f"Invalid operation: {op}")
                    continue
                
                success = await add_balance(
                    telegram_id=telegram_id,
                    amount=amount,
                    reason=reason,
                    metadata=metadata,
                    reference_id=op.get('reference_id')
                )
                
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed for user {telegram_id}")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error for {op}: {e}")
    
    logger.info(f"Bulk add balance completed: {results['success']} success, {results['failed']} failed")
    return results


async def deduct_balance_bulk(
    operations: list,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None,
    allow_negative: bool = False
) -> Dict[str, Any]:
    """
    Deduct balance from multiple users in a single transaction
    
    Args:
        operations: list - List of dicts with 'telegram_id' and 'amount'
        reason: str - Reason for deducting balance
        metadata: dict - Additional metadata
        allow_negative: bool - Allow balance to go negative
    
    Returns:
        dict: Results with success and failure counts
    """
    results = {
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    async with db.transaction():
        for op in operations:
            try:
                telegram_id = op.get('telegram_id')
                amount = op.get('amount')
                
                if not telegram_id or amount <= 0:
                    results['failed'] += 1
                    results['errors'].append(f"Invalid operation: {op}")
                    continue
                
                success = await deduct_balance(
                    telegram_id=telegram_id,
                    amount=amount,
                    reason=reason,
                    metadata=metadata,
                    reference_id=op.get('reference_id'),
                    allow_negative=allow_negative
                )
                
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed for user {telegram_id} (insufficient balance?)")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Error for {op}: {e}")
    
    logger.info(f"Bulk deduct balance completed: {results['success']} success, {results['failed']} failed")
    return results


# ==================== BALANCE VALIDATION ====================

async def check_sufficient_balance(telegram_id: int, required_amount: float) -> bool:
    """
    Check if user has sufficient balance
    
    Args:
        telegram_id: int - User's Telegram ID
        required_amount: float - Amount required
    
    Returns:
        bool: True if sufficient, False otherwise
    """
    balance = await get_balance(telegram_id)
    return balance >= required_amount


async def validate_and_deduct(
    telegram_id: int,
    amount: float,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None,
    reference_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate balance and deduct in one atomic operation
    
    Args:
        telegram_id: int - User's Telegram ID
        amount: float - Amount to deduct
        reason: str - Reason for deduction
        metadata: dict - Additional metadata
        reference_id: str - Reference ID
    
    Returns:
        dict: Result with success status and details
    """
    # Check balance first (fast check without transaction)
    if not await check_sufficient_balance(telegram_id, amount):
        current_balance = await get_balance(telegram_id)
        return {
            'success': False,
            'error': 'insufficient_balance',
            'current_balance': current_balance,
            'required': amount,
            'shortfall': amount - current_balance
        }
    
    # Perform deduction in transaction
    success = await deduct_balance(
        telegram_id=telegram_id,
        amount=amount,
        reason=reason,
        metadata=metadata,
        reference_id=reference_id
    )
    
    if success:
        new_balance = await get_balance(telegram_id)
        return {
            'success': True,
            'new_balance': new_balance,
            'deducted': amount
        }
    else:
        return {
            'success': False,
            'error': 'deduction_failed'
        }


# ==================== BALANCE HISTORY ====================

async def get_balance_history(
    telegram_id: int,
    limit: int = 50,
    offset: int = 0,
    transaction_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Get user's balance history with pagination
    
    Args:
        telegram_id: int - User's Telegram ID
        limit: int - Number of records
        offset: int - Pagination offset
        transaction_type: str - Filter by transaction type
        start_date: datetime - Start date filter
        end_date: datetime - End date filter
    
    Returns:
        dict: Balance history with pagination info
    """
    transactions = await TransactionRepository.get_by_user(
        user_id=telegram_id,
        limit=limit,
        offset=offset,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date
    )
    
    total = await TransactionRepository.get_transaction_count(telegram_id)
    
    return {
        'transactions': transactions,
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': total,
            'has_more': offset + limit < total
        }
    }


async def get_balance_summary(telegram_id: int) -> Dict[str, Any]:
    """
    Get comprehensive balance summary for a user
    
    Args:
        telegram_id: int - User's Telegram ID
    
    Returns:
        dict: Balance summary
    """
    current_balance = await get_balance(telegram_id)
    stats = await TransactionRepository.get_stats(telegram_id)
    
    return {
        'current_balance': current_balance,
        'statistics': stats,
        'net_position': stats.get('win_total', 0) - stats.get('cartela_total', 0)
    }


# ==================== ADMIN BALANCE OPERATIONS ====================

async def admin_adjust_balance(
    admin_id: int,
    telegram_id: int,
    amount: float,
    reason: str,
    is_adjustment: bool = True
) -> Dict[str, Any]:
    """
    Admin adjustment of user balance (add or deduct)
    
    Args:
        admin_id: int - Admin's Telegram ID
        telegram_id: int - User's Telegram ID
        amount: float - Amount (positive for add, negative for deduct)
        reason: str - Reason for adjustment
        is_adjustment: bool - Whether this is an adjustment (vs regular operation)
    
    Returns:
        dict: Result of operation
    """
    if amount > 0:
        success = await add_balance(
            telegram_id=telegram_id,
            amount=amount,
            reason=f"admin_adjustment_{reason}",
            metadata={
                'admin_id': admin_id,
                'is_adjustment': is_adjustment,
                'original_reason': reason
            }
        )
        operation = 'added'
    elif amount < 0:
        success = await deduct_balance(
            telegram_id=telegram_id,
            amount=abs(amount),
            reason=f"admin_adjustment_{reason}",
            metadata={
                'admin_id': admin_id,
                'is_adjustment': is_adjustment,
                'original_reason': reason
            },
            allow_negative=False
        )
        operation = 'deducted'
    else:
        return {
            'success': False,
            'error': 'Amount cannot be zero'
        }
    
    if success:
        new_balance = await get_balance(telegram_id)
        return {
            'success': True,
            'operation': operation,
            'amount': abs(amount),
            'new_balance': new_balance,
            'message': f"Successfully {operation} {abs(amount)} to user balance"
        }
    else:
        return {
            'success': False,
            'error': f"Failed to {operation} balance"
        }


# ==================== UTILITY FUNCTIONS ====================

async def transfer_balance(
    from_user_id: int,
    to_user_id: int,
    amount: float,
    fee: float = 0,
    reason: str = "transfer"
) -> Dict[str, Any]:
    """
    Transfer balance between two users
    
    Args:
        from_user_id: int - Sender's Telegram ID
        to_user_id: int - Receiver's Telegram ID
        amount: float - Amount to transfer (before fee)
        fee: float - Fee amount (deducted from sender)
        reason: str - Transfer reason
    
    Returns:
        dict: Transfer result
    """
    total_deduction = amount + fee
    
    # Start transaction
    async with db.transaction():
        # Check sender balance
        if not await check_sufficient_balance(from_user_id, total_deduction):
            current_balance = await get_balance(from_user_id)
            return {
                'success': False,
                'error': 'insufficient_balance',
                'current_balance': current_balance,
                'required': total_deduction
            }
        
        # Deduct from sender
        deduct_success = await deduct_balance(
            telegram_id=from_user_id,
            amount=total_deduction,
            reason=f"transfer_sent_{reason}",
            metadata={
                'to_user_id': to_user_id,
                'amount': amount,
                'fee': fee
            }
        )
        
        if not deduct_success:
            return {'success': False, 'error': 'Failed to deduct from sender'}
        
        # Add to receiver
        add_success = await add_balance(
            telegram_id=to_user_id,
            amount=amount,
            reason=f"transfer_received_{reason}",
            metadata={
                'from_user_id': from_user_id,
                'amount': amount
            }
        )
        
        if not add_success:
            # Rollback: refund sender
            await add_balance(
                telegram_id=from_user_id,
                amount=total_deduction,
                reason="transfer_rollback",
                metadata={'original_transfer': reason}
            )
            return {'success': False, 'error': 'Failed to add to receiver, transaction rolled back'}
        
        return {
            'success': True,
            'amount': amount,
            'fee': fee,
            'total_deducted': total_deduction,
            'receiver_received': amount
        }


# ==================== EXPORTS ====================

__all__ = [
    # Core operations
    'get_balance',
    'add_balance',
    'deduct_balance',
    'set_balance',
    
    # Bulk operations
    'add_balance_bulk',
    'deduct_balance_bulk',
    
    # Validation
    'check_sufficient_balance',
    'validate_and_deduct',
    
    # History
    'get_balance_history',
    'get_balance_summary',
    
    # Admin operations
    'admin_adjust_balance',
    
    # Utility
    'transfer_balance',
]