# telegram-bot/bot/api/webhooks.py
# Estif Bingo 24/7 - Payment Webhook Handler
# Handles incoming webhooks from payment providers (Telebirr, CBE, M-Pesa, etc.)

import hashlib
import hmac
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from bot.db.repository import DepositRepository, UserRepository, TransactionRepository, AuditRepository
from bot.api.balance_ops import add_balance
from bot.config import config
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

# Create blueprint
webhook_bp = Blueprint('webhooks', __name__, url_prefix='/api/webhooks')


# ==================== WEBHOOK VERIFICATION ====================

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify webhook signature using HMAC-SHA256
    
    Args:
        payload: bytes - Raw request body
        signature: str - Signature from header
        secret: str - Webhook secret
    
    Returns:
        bool: True if signature is valid
    """
    if not signature or not secret:
        return False
    
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


# ==================== TELEBIRR WEBHOOK ====================

@webhook_bp.route('/telebirr', methods=['POST'])
async def telebirr_webhook():
    """
    Telebirr payment webhook handler
    
    Expected payload format:
    {
        "transaction_id": "TX123456",
        "amount": 100.00,
        "phone_number": "0912345678",
        "status": "success",
        "reference": "DEP_123456",
        "signature": "xxx"
    }
    """
    try:
        # Get raw payload for signature verification
        raw_payload = request.get_data()
        
        # Parse JSON
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Invalid payload'}), 400
        
        logger.info(f"Received Telebirr webhook: {data}")
        
        # Verify signature
        signature = request.headers.get('X-Signature', '')
        if not verify_signature(raw_payload, signature, config.TELEBIRR_WEBHOOK_SECRET):
            logger.warning("Invalid Telebirr webhook signature")
            return jsonify({'success': False, 'error': 'Invalid signature'}), 401
        
        # Extract data
        transaction_id = data.get('transaction_id')
        amount = float(data.get('amount', 0))
        phone_number = data.get('phone_number')
        status = data.get('status')
        reference = data.get('reference')
        
        if status != 'success':
            logger.info(f"Telebirr payment not successful: {status}")
            return jsonify({'success': True, 'message': 'Payment not successful'}), 200
        
        # Find deposit by reference
        deposit = await DepositRepository.get_by_transaction_id(reference)
        
        if not deposit:
            logger.warning(f"Deposit not found for reference: {reference}")
            return jsonify({'success': False, 'error': 'Deposit not found'}), 404
        
        if deposit['status'] != 'pending':
            logger.info(f"Deposit {deposit['id']} already processed: {deposit['status']}")
            return jsonify({'success': True, 'message': 'Already processed'}), 200
        
        # Verify amount matches
        if abs(float(deposit['amount']) - amount) > 0.01:
            logger.warning(f"Amount mismatch for deposit {deposit['id']}: expected {deposit['amount']}, got {amount}")
            return jsonify({'success': False, 'error': 'Amount mismatch'}), 400
        
        # Update deposit status
        await DepositRepository.update_status(deposit['id'], 'approved')
        
        # Add balance to user
        await add_balance(
            telegram_id=deposit['telegram_id'],
            amount=amount,
            reason="deposit",
            metadata={
                'provider': 'telebirr',
                'transaction_id': transaction_id,
                'phone_number': phone_number,
                'webhook_received': True
            },
            reference_id=f"telebirr_{transaction_id}"
        )
        
        # Notify user via bot (will be handled by background task)
        # Store notification in queue or send directly if bot instance available
        
        logger.info(f"Telebirr deposit {deposit['id']} approved: {amount} ETB for user {deposit['telegram_id']}")
        
        return jsonify({'success': True, 'message': 'Deposit processed'}), 200
        
    except Exception as e:
        logger.error(f"Error processing Telebirr webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== CBE WEBHOOK ====================

@webhook_bp.route('/cbe', methods=['POST'])
async def cbe_webhook():
    """
    Commercial Bank of Ethiopia (CBE) payment webhook handler
    
    Expected payload format:
    {
        "transaction_ref": "REF123456",
        "amount": 100.00,
        "account_number": "1000123456789",
        "status": "COMPLETED",
        "reference": "DEP_123456",
        "signature": "xxx"
    }
    """
    try:
        raw_payload = request.get_data()
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Invalid payload'}), 400
        
        logger.info(f"Received CBE webhook: {data}")
        
        # Verify signature
        signature = request.headers.get('X-Signature', '')
        if not verify_signature(raw_payload, signature, config.CBE_WEBHOOK_SECRET):
            logger.warning("Invalid CBE webhook signature")
            return jsonify({'success': False, 'error': 'Invalid signature'}), 401
        
        # Extract data
        transaction_ref = data.get('transaction_ref')
        amount = float(data.get('amount', 0))
        account_number = data.get('account_number')
        status = data.get('status')
        reference = data.get('reference')
        
        if status != 'COMPLETED':
            logger.info(f"CBE payment not completed: {status}")
            return jsonify({'success': True, 'message': 'Payment not completed'}), 200
        
        # Find deposit by reference
        deposit = await DepositRepository.get_by_transaction_id(reference)
        
        if not deposit:
            logger.warning(f"Deposit not found for reference: {reference}")
            return jsonify({'success': False, 'error': 'Deposit not found'}), 404
        
        if deposit['status'] != 'pending':
            return jsonify({'success': True, 'message': 'Already processed'}), 200
        
        # Verify amount
        if abs(float(deposit['amount']) - amount) > 0.01:
            logger.warning(f"Amount mismatch for deposit {deposit['id']}")
            return jsonify({'success': False, 'error': 'Amount mismatch'}), 400
        
        # Update deposit status
        await DepositRepository.update_status(deposit['id'], 'approved')
        
        # Add balance
        await add_balance(
            telegram_id=deposit['telegram_id'],
            amount=amount,
            reason="deposit",
            metadata={
                'provider': 'cbe',
                'transaction_ref': transaction_ref,
                'account_number': account_number
            },
            reference_id=f"cbe_{transaction_ref}"
        )
        
        logger.info(f"CBE deposit {deposit['id']} approved: {amount} ETB for user {deposit['telegram_id']}")
        
        return jsonify({'success': True, 'message': 'Deposit processed'}), 200
        
    except Exception as e:
        logger.error(f"Error processing CBE webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== ABYSSINIA WEBHOOK ====================

@webhook_bp.route('/abyssinia', methods=['POST'])
async def abyssinia_webhook():
    """
    Abyssinia Bank payment webhook handler
    """
    try:
        raw_payload = request.get_data()
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Invalid payload'}), 400
        
        logger.info(f"Received Abyssinia webhook: {data}")
        
        signature = request.headers.get('X-Signature', '')
        if not verify_signature(raw_payload, signature, config.ABYSSINIA_WEBHOOK_SECRET):
            logger.warning("Invalid Abyssinia webhook signature")
            return jsonify({'success': False, 'error': 'Invalid signature'}), 401
        
        transaction_id = data.get('transactionId')
        amount = float(data.get('amount', 0))
        status = data.get('status')
        reference = data.get('reference')
        
        if status != 'SUCCESS':
            return jsonify({'success': True, 'message': 'Payment not successful'}), 200
        
        deposit = await DepositRepository.get_by_transaction_id(reference)
        
        if not deposit or deposit['status'] != 'pending':
            return jsonify({'success': True, 'message': 'Already processed'}), 200
        
        await DepositRepository.update_status(deposit['id'], 'approved')
        
        await add_balance(
            telegram_id=deposit['telegram_id'],
            amount=amount,
            reason="deposit",
            metadata={'provider': 'abyssinia', 'transaction_id': transaction_id},
            reference_id=f"abyssinia_{transaction_id}"
        )
        
        logger.info(f"Abyssinia deposit {deposit['id']} approved")
        
        return jsonify({'success': True, 'message': 'Deposit processed'}), 200
        
    except Exception as e:
        logger.error(f"Error processing Abyssinia webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== M-PESA WEBHOOK ====================

@webhook_bp.route('/mpesa', methods=['POST'])
async def mpesa_webhook():
    """
    M-Pesa payment webhook handler
    """
    try:
        raw_payload = request.get_data()
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Invalid payload'}), 400
        
        logger.info(f"Received M-Pesa webhook: {data}")
        
        signature = request.headers.get('X-Signature', '')
        if not verify_signature(raw_payload, signature, config.MPESA_WEBHOOK_SECRET):
            logger.warning("Invalid M-Pesa webhook signature")
            return jsonify({'success': False, 'error': 'Invalid signature'}), 401
        
        # M-Pesa specific fields
        transaction_id = data.get('TransactionID')
        amount = float(data.get('Amount', 0))
        phone_number = data.get('PhoneNumber')
        result_code = data.get('ResultCode')
        reference = data.get('Reference')
        
        if result_code != '0':
            logger.info(f"M-Pesa payment failed: {result_code}")
            return jsonify({'success': True, 'message': 'Payment failed'}), 200
        
        deposit = await DepositRepository.get_by_transaction_id(reference)
        
        if not deposit or deposit['status'] != 'pending':
            return jsonify({'success': True, 'message': 'Already processed'}), 200
        
        await DepositRepository.update_status(deposit['id'], 'approved')
        
        await add_balance(
            telegram_id=deposit['telegram_id'],
            amount=amount,
            reason="deposit",
            metadata={
                'provider': 'mpesa',
                'transaction_id': transaction_id,
                'phone_number': phone_number
            },
            reference_id=f"mpesa_{transaction_id}"
        )
        
        logger.info(f"M-Pesa deposit {deposit['id']} approved")
        
        return jsonify({'success': True, 'message': 'Deposit processed'}), 200
        
    except Exception as e:
        logger.error(f"Error processing M-Pesa webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== GENERIC WEBHOOK HANDLER ====================

@webhook_bp.route('/generic', methods=['POST'])
async def generic_webhook():
    """
    Generic webhook handler for custom payment providers
    
    Expected payload:
    {
        "provider": "custom_provider",
        "transaction_id": "xxx",
        "amount": 100.00,
        "status": "completed",
        "reference": "DEP_xxx",
        "signature": "xxx"
    }
    """
    try:
        raw_payload = request.get_data()
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Invalid payload'}), 400
        
        provider = data.get('provider')
        transaction_id = data.get('transaction_id')
        amount = float(data.get('amount', 0))
        status = data.get('status')
        reference = data.get('reference')
        
        # Verify signature (using provider-specific secret)
        secret_key = config.WEBHOOK_SECRETS.get(provider)
        if secret_key:
            signature = request.headers.get('X-Signature', '')
            if not verify_signature(raw_payload, signature, secret_key):
                logger.warning(f"Invalid signature for provider {provider}")
                return jsonify({'success': False, 'error': 'Invalid signature'}), 401
        
        if status not in ['completed', 'success', 'COMPLETED', 'SUCCESS']:
            return jsonify({'success': True, 'message': 'Payment not completed'}), 200
        
        deposit = await DepositRepository.get_by_transaction_id(reference)
        
        if not deposit or deposit['status'] != 'pending':
            return jsonify({'success': True, 'message': 'Already processed'}), 200
        
        await DepositRepository.update_status(deposit['id'], 'approved')
        
        await add_balance(
            telegram_id=deposit['telegram_id'],
            amount=amount,
            reason="deposit",
            metadata={'provider': provider, 'transaction_id': transaction_id},
            reference_id=f"{provider}_{transaction_id}"
        )
        
        logger.info(f"Generic webhook: deposit {deposit['id']} approved via {provider}")
        
        return jsonify({'success': True, 'message': 'Deposit processed'}), 200
        
    except Exception as e:
        logger.error(f"Error processing generic webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== WEBHOOK HEALTH CHECK ====================

@webhook_bp.route('/health', methods=['GET'])
async def webhook_health():
    """
    Health check endpoint for webhooks
    """
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'providers': ['telebirr', 'cbe', 'abyssinia', 'mpesa', 'generic']
    }), 200


# ==================== TEST WEBHOOK ENDPOINTS ====================

@webhook_bp.route('/test/telebirr', methods=['POST'])
async def test_telebirr_webhook():
    """
    Test endpoint for Telebirr webhook (development only)
    """
    if config.NODE_ENV == 'production':
        return jsonify({'success': False, 'error': 'Not available in production'}), 403
    
    data = request.get_json()
    logger.info(f"Test Telebirr webhook received: {data}")
    
    # Process as regular webhook
    return await telebirr_webhook()


@webhook_bp.route('/test/cbe', methods=['POST'])
async def test_cbe_webhook():
    """
    Test endpoint for CBE webhook (development only)
    """
    if config.NODE_ENV == 'production':
        return jsonify({'success': False, 'error': 'Not available in production'}), 403
    
    return await cbe_webhook()


# ==================== EXPORTS ====================

__all__ = [
    'webhook_bp',
    'verify_signature',
]