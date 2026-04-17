# telegram-bot/bot/api/admin_api.py
# Estif Bingo 24/7 - Admin API Endpoints
# Handles admin operations: system settings, user management, reports, game controls

import logging
import csv
import json
from io import StringIO
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, Response
from bot.api.auth import token_required
from bot.db.repository import (
    UserRepository, TransactionRepository, GameRepository, 
    DepositRepository, WithdrawalRepository, AdminRepository,
    BonusRepository, TournamentRepository, CartelaRepository
)
from bot.api.balance_ops import get_balance, add_balance, deduct_balance, admin_adjust_balance
from bot.config import config
from bot.utils.logger import logger

# Create blueprint
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')


# ==================== AUTHENTICATION & ACCESS CONTROL ====================

def require_admin(f):
    """Decorator to require admin access"""
    @token_required
    async def decorated(*args, **kwargs):
        current_user = kwargs.get('current_user')
        if not current_user or not current_user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        return await f(*args, **kwargs)
    return decorated


# ==================== SYSTEM STATISTICS ====================

@admin_api_bp.route('/statistics', methods=['GET'])
@require_admin
async def get_system_statistics(current_user):
    """
    Get comprehensive system statistics
    
    Query params:
        period: str - 'day', 'week', 'month', 'all' (default: 'day')
    
    Returns:
        JSON: System statistics
    """
    try:
        period = request.args.get('period', 'day')
        
        # Calculate date range
        now = datetime.utcnow()
        if period == 'day':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        else:
            start_date = None
        
        # User statistics
        total_users = await UserRepository.count_registered()
        active_users = await UserRepository.count_active(last_hours=24)
        new_users = await UserRepository.count_new_since(start_date) if start_date else total_users
        
        # Game statistics
        total_rounds = await GameRepository.count_rounds()
        completed_rounds = await GameRepository.count_rounds(status='ended')
        total_cartelas = await GameRepository.total_cartelas_sold()
        total_bets = total_cartelas * config.CARTELA_PRICE
        
        # Financial statistics
        total_deposits = await TransactionRepository.sum_by_type('deposit')
        total_withdrawals = await TransactionRepository.sum_by_type('withdrawal')
        total_wins = await TransactionRepository.sum_by_type('win')
        
        # Pending requests
        pending_deposits = await DepositRepository.count_pending()
        pending_deposits_amount = await DepositRepository.sum_pending()
        pending_withdrawals = await WithdrawalRepository.count_pending()
        pending_withdrawals_amount = await WithdrawalRepository.sum_pending()
        
        # Current game state
        from bot.game_engine.bingo_room import bingo_room
        game_state = bingo_room.get_state() if bingo_room else {}
        
        return jsonify({
            'success': True,
            'data': {
                'period': period,
                'users': {
                    'total': total_users,
                    'active_24h': active_users,
                    'new': new_users
                },
                'games': {
                    'total_rounds': total_rounds,
                    'completed_rounds': completed_rounds,
                    'total_cartelas_sold': total_cartelas,
                    'total_bets': total_bets,
                    'current_round': game_state.get('round_id'),
                    'game_status': game_state.get('status', 'idle'),
                    'active_players': game_state.get('player_count', 0)
                },
                'financial': {
                    'total_deposits': total_deposits,
                    'total_withdrawals': total_withdrawals,
                    'total_wins': total_wins,
                    'net_revenue': total_deposits - total_withdrawals,
                    'house_edge': total_bets - total_wins
                },
                'pending': {
                    'deposits_count': pending_deposits,
                    'deposits_amount': pending_deposits_amount,
                    'withdrawals_count': pending_withdrawals,
                    'withdrawals_amount': pending_withdrawals_amount
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting system statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== USER MANAGEMENT ====================

@admin_api_bp.route('/users', methods=['GET'])
@require_admin
async def get_users(current_user):
    """
    Get list of users with pagination and search
    
    Query params:
        page: int - Page number (default: 1)
        limit: int - Items per page (default: 20)
        search: str - Search term (optional)
        sort_by: str - Sort field (default: 'created_at')
        sort_order: str - 'asc' or 'desc' (default: 'desc')
    
    Returns:
        JSON: User list
    """
    try:
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit
        search = request.args.get('search', '')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        if search:
            users = await UserRepository.search_users(search, limit=limit, offset=offset)
            total = len(users)
        else:
            users = await UserRepository.get_all_registered(limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order)
            total = await UserRepository.count_registered()
        
        # Add balance to each user
        for user in users:
            user['balance'] = await get_balance(user['telegram_id'])
        
        return jsonify({
            'success': True,
            'data': {
                'users': users,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/users/<int:user_id>', methods=['GET'])
@require_admin
async def get_user_details(current_user, user_id):
    """
    Get detailed user information
    
    Args:
        user_id: int - User's Telegram ID
    
    Returns:
        JSON: User details
    """
    try:
        user = await UserRepository.get_by_telegram_id(user_id)
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Get additional data
        balance = await get_balance(user_id)
        stats = await TransactionRepository.get_stats(user_id)
        games_played = await GameRepository.get_user_games_count(user_id)
        deposits = await DepositRepository.get_by_telegram_id(user_id, limit=10)
        withdrawals = await WithdrawalRepository.get_by_telegram_id(user_id, limit=10)
        
        return jsonify({
            'success': True,
            'data': {
                'user': {
                    **user,
                    'balance': balance
                },
                'statistics': stats,
                'games_played': games_played,
                'recent_deposits': deposits,
                'recent_withdrawals': withdrawals
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/users/<int:user_id>/balance', methods=['PUT'])
@require_admin
async def adjust_user_balance(current_user, user_id):
    """
    Adjust user balance (admin only)
    
    Request body:
        {
            "amount": 100,
            "reason": "compensation",
            "operation": "add"  # 'add' or 'deduct'
        }
    
    Returns:
        JSON: Updated balance
    """
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        reason = data.get('reason', 'admin_adjustment')
        operation = data.get('operation', 'add')
        
        if amount <= 0:
            return jsonify({'success': False, 'error': 'Amount must be positive'}), 400
        
        if operation == 'add':
            success = await add_balance(
                telegram_id=user_id,
                amount=amount,
                reason=f"admin_{reason}",
                metadata={'admin_id': current_user['telegram_id'], 'operation': operation}
            )
        elif operation == 'deduct':
            success = await deduct_balance(
                telegram_id=user_id,
                amount=amount,
                reason=f"admin_{reason}",
                metadata={'admin_id': current_user['telegram_id'], 'operation': operation},
                allow_negative=False
            )
        else:
            return jsonify({'success': False, 'error': 'Invalid operation'}), 400
        
        if not success:
            return jsonify({'success': False, 'error': 'Failed to adjust balance'}), 500
        
        new_balance = await get_balance(user_id)
        
        # Log admin action
        await AdminRepository.log_admin_action(
            admin_id=current_user['telegram_id'],
            action='adjust_balance',
            target_type='user',
            target_id=str(user_id),
            details={'amount': amount, 'operation': operation, 'reason': reason}
        )
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'new_balance': new_balance,
                'adjustment': amount,
                'operation': operation
            }
        })
        
    except Exception as e:
        logger.error(f"Error adjusting user balance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@require_admin
async def toggle_admin(current_user, user_id):
    """
    Toggle admin status for a user
    
    Request body:
        {
            "is_admin": true
        }
    
    Returns:
        JSON: Updated admin status
    """
    try:
        data = request.get_json()
        is_admin = data.get('is_admin', False)
        
        user = await UserRepository.get_by_telegram_id(user_id)
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        success = await UserRepository.set_admin(user_id, is_admin)
        
        if not success:
            return jsonify({'success': False, 'error': 'Failed to update admin status'}), 500
        
        # Log admin action
        await AdminRepository.log_admin_action(
            admin_id=current_user['telegram_id'],
            action='toggle_admin',
            target_type='user',
            target_id=str(user_id),
            details={'is_admin': is_admin}
        )
        
        return jsonify({
            'success': True,
            'data': {
                'user_id': user_id,
                'is_admin': is_admin
            }
        })
        
    except Exception as e:
        logger.error(f"Error toggling admin status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@require_admin
async def deactivate_user(current_user, user_id):
    """
    Deactivate a user account
    
    Returns:
        JSON: Deactivation status
    """
    try:
        user = await UserRepository.get_by_telegram_id(user_id)
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        success = await UserRepository.deactivate_user(user_id)
        
        if not success:
            return jsonify({'success': False, 'error': 'Failed to deactivate user'}), 500
        
        # Log admin action
        await AdminRepository.log_admin_action(
            admin_id=current_user['telegram_id'],
            action='deactivate_user',
            target_type='user',
            target_id=str(user_id),
            details={'username': user.get('username')}
        )
        
        return jsonify({
            'success': True,
            'message': f'User {user_id} has been deactivated'
        })
        
    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== DEPOSIT MANAGEMENT ====================

@admin_api_bp.route('/deposits', methods=['GET'])
@require_admin
async def get_deposits(current_user):
    """
    Get deposit requests with filters
    
    Query params:
        status: str - 'pending', 'approved', 'rejected'
        page: int - Page number
        limit: int - Items per page
    
    Returns:
        JSON: Deposit list
    """
    try:
        status = request.args.get('status', 'pending')
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit
        
        if status == 'pending':
            deposits = await DepositRepository.get_pending(limit=limit)
            total = await DepositRepository.count_pending()
        else:
            deposits = await DepositRepository.get_all(limit=limit, offset=offset, status=status)
            total = len(deposits)
        
        return jsonify({
            'success': True,
            'data': {
                'deposits': deposits,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting deposits: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/deposits/<int:deposit_id>/approve', methods=['POST'])
@require_admin
async def approve_deposit(current_user, deposit_id):
    """
    Approve a deposit request
    
    Returns:
        JSON: Approval status
    """
    try:
        deposit = await DepositRepository.get_by_id(deposit_id)
        
        if not deposit:
            return jsonify({'success': False, 'error': 'Deposit not found'}), 404
        
        if deposit['status'] != 'pending':
            return jsonify({'success': False, 'error': f'Deposit already {deposit["status"]}'}), 400
        
        # Update deposit status
        await DepositRepository.update_status(deposit_id, 'approved', admin_id=current_user['telegram_id'])
        
        # Add balance to user
        await add_balance(
            telegram_id=deposit['telegram_id'],
            amount=float(deposit['amount']),
            reason="deposit",
            metadata={'deposit_id': deposit_id, 'admin_id': current_user['telegram_id']},
            reference_id=f"deposit_{deposit_id}"
        )
        
        # Log admin action
        await AdminRepository.log_admin_action(
            admin_id=current_user['telegram_id'],
            action='approve_deposit',
            target_type='deposit',
            target_id=str(deposit_id),
            details={'amount': deposit['amount'], 'user_id': deposit['telegram_id']}
        )
        
        return jsonify({
            'success': True,
            'message': f'Deposit #{deposit_id} approved',
            'data': {
                'deposit_id': deposit_id,
                'amount': deposit['amount'],
                'user_id': deposit['telegram_id']
            }
        })
        
    except Exception as e:
        logger.error(f"Error approving deposit: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/deposits/<int:deposit_id>/reject', methods=['POST'])
@require_admin
async def reject_deposit(current_user, deposit_id):
    """
    Reject a deposit request
    
    Request body:
        {
            "reason": "Invalid screenshot"
        }
    
    Returns:
        JSON: Rejection status
    """
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        deposit = await DepositRepository.get_by_id(deposit_id)
        
        if not deposit:
            return jsonify({'success': False, 'error': 'Deposit not found'}), 404
        
        if deposit['status'] != 'pending':
            return jsonify({'success': False, 'error': f'Deposit already {deposit["status"]}'}), 400
        
        # Update deposit status
        await DepositRepository.update_status(deposit_id, 'rejected', admin_id=current_user['telegram_id'], notes=reason)
        
        # Log admin action
        await AdminRepository.log_admin_action(
            admin_id=current_user['telegram_id'],
            action='reject_deposit',
            target_type='deposit',
            target_id=str(deposit_id),
            details={'amount': deposit['amount'], 'user_id': deposit['telegram_id'], 'reason': reason}
        )
        
        return jsonify({
            'success': True,
            'message': f'Deposit #{deposit_id} rejected'
        })
        
    except Exception as e:
        logger.error(f"Error rejecting deposit: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== WITHDRAWAL MANAGEMENT ====================

@admin_api_bp.route('/withdrawals', methods=['GET'])
@require_admin
async def get_withdrawals(current_user):
    """
    Get withdrawal requests with filters
    
    Query params:
        status: str - 'pending', 'approved', 'rejected'
        page: int - Page number
        limit: int - Items per page
    
    Returns:
        JSON: Withdrawal list
    """
    try:
        status = request.args.get('status', 'pending')
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = (page - 1) * limit
        
        if status == 'pending':
            withdrawals = await WithdrawalRepository.get_pending(limit=limit)
            total = await WithdrawalRepository.count_pending()
        else:
            withdrawals = await WithdrawalRepository.get_all(limit=limit, offset=offset, status=status)
            total = len(withdrawals)
        
        return jsonify({
            'success': True,
            'data': {
                'withdrawals': withdrawals,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting withdrawals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/withdrawals/<int:withdrawal_id>/approve', methods=['POST'])
@require_admin
async def approve_withdrawal(current_user, withdrawal_id):
    """
    Approve a withdrawal request
    
    Returns:
        JSON: Approval status
    """
    try:
        withdrawal = await WithdrawalRepository.get_by_id(withdrawal_id)
        
        if not withdrawal:
            return jsonify({'success': False, 'error': 'Withdrawal not found'}), 404
        
        if withdrawal['status'] != 'pending':
            return jsonify({'success': False, 'error': f'Withdrawal already {withdrawal["status"]}'}), 400
        
        # Update withdrawal status
        await WithdrawalRepository.update_status(withdrawal_id, 'approved', admin_id=current_user['telegram_id'])
        
        # Log admin action
        await AdminRepository.log_admin_action(
            admin_id=current_user['telegram_id'],
            action='approve_withdrawal',
            target_type='withdrawal',
            target_id=str(withdrawal_id),
            details={'amount': withdrawal['amount'], 'user_id': withdrawal['telegram_id']}
        )
        
        return jsonify({
            'success': True,
            'message': f'Withdrawal #{withdrawal_id} approved'
        })
        
    except Exception as e:
        logger.error(f"Error approving withdrawal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/withdrawals/<int:withdrawal_id>/reject', methods=['POST'])
@require_admin
async def reject_withdrawal(current_user, withdrawal_id):
    """
    Reject a withdrawal request and refund balance
    
    Request body:
        {
            "reason": "Invalid bank details"
        }
    
    Returns:
        JSON: Rejection status
    """
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        withdrawal = await WithdrawalRepository.get_by_id(withdrawal_id)
        
        if not withdrawal:
            return jsonify({'success': False, 'error': 'Withdrawal not found'}), 404
        
        if withdrawal['status'] != 'pending':
            return jsonify({'success': False, 'error': f'Withdrawal already {withdrawal["status"]}'}), 400
        
        # Update withdrawal status
        await WithdrawalRepository.update_status(withdrawal_id, 'rejected', admin_id=current_user['telegram_id'], notes=reason)
        
        # Refund balance to user
        await add_balance(
            telegram_id=withdrawal['telegram_id'],
            amount=float(withdrawal['amount']),
            reason="withdrawal_rejected",
            metadata={'withdrawal_id': withdrawal_id, 'admin_id': current_user['telegram_id'], 'reason': reason}
        )
        
        # Log admin action
        await AdminRepository.log_admin_action(
            admin_id=current_user['telegram_id'],
            action='reject_withdrawal',
            target_type='withdrawal',
            target_id=str(withdrawal_id),
            details={'amount': withdrawal['amount'], 'user_id': withdrawal['telegram_id'], 'reason': reason}
        )
        
        return jsonify({
            'success': True,
            'message': f'Withdrawal #{withdrawal_id} rejected, balance refunded'
        })
        
    except Exception as e:
        logger.error(f"Error rejecting withdrawal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== GAME CONTROLS ====================

@admin_api_bp.route('/game/force-start', methods=['POST'])
@require_admin
async def force_start_game(current_user):
    """
    Force start a new game round
    
    Returns:
        JSON: Start status
    """
    try:
        from bot.game_engine.bingo_room import bingo_room
        
        success = await bingo_room.force_start()
        
        if success:
            await AdminRepository.log_admin_action(
                admin_id=current_user['telegram_id'],
                action='force_start_game',
                target_type='game',
                details={'round_id': bingo_room.current_round_id}
            )
            
            return jsonify({
                'success': True,
                'message': 'Game force started',
                'data': {'round_id': bingo_room.current_round_id}
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to start game'}), 500
            
    except Exception as e:
        logger.error(f"Error force starting game: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/game/force-stop', methods=['POST'])
@require_admin
async def force_stop_game(current_user):
    """
    Force stop current game round
    
    Returns:
        JSON: Stop status
    """
    try:
        from bot.game_engine.bingo_room import bingo_room
        
        success = await bingo_room.force_stop()
        
        if success:
            await AdminRepository.log_admin_action(
                admin_id=current_user['telegram_id'],
                action='force_stop_game',
                target_type='game'
            )
            
            return jsonify({
                'success': True,
                'message': 'Game force stopped'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to stop game'}), 500
            
    except Exception as e:
        logger.error(f"Error force stopping game: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/game/settings', methods=['GET'])
@require_admin
async def get_game_settings(current_user):
    """
    Get current game settings
    
    Returns:
        JSON: Game settings
    """
    try:
        win_percentage = await GameRepository.get_win_percentage()
        maintenance_mode = await GameRepository.get_maintenance_mode()
        default_sound_pack = await GameRepository.get_default_sound_pack()
        
        return jsonify({
            'success': True,
            'data': {
                'win_percentage': win_percentage,
                'available_percentages': [75, 78, 79, 80],
                'maintenance_mode': maintenance_mode,
                'default_sound_pack': default_sound_pack,
                'cartela_price': config.CARTELA_PRICE,
                'max_cartelas': config.MAX_CARTELAS,
                'selection_time': config.SELECTION_TIME,
                'draw_interval': config.DRAW_INTERVAL
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting game settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_api_bp.route('/game/settings', methods=['PUT'])
@require_admin
async def update_game_settings(current_user):
    """
    Update game settings
    
    Request body:
        {
            "win_percentage": 78,
            "maintenance_mode": false,
            "default_sound_pack": "pack2"
        }
    
    Returns:
        JSON: Updated settings
    """
    try:
        data = request.get_json()
        updates = []
        
        if 'win_percentage' in data:
            percentage = data['win_percentage']
            if percentage in [75, 78, 79, 80]:
                await GameRepository.set_win_percentage(percentage)
                updates.append(f"win_percentage={percentage}")
        
        if 'maintenance_mode' in data:
            await GameRepository.set_maintenance_mode(data['maintenance_mode'])
            updates.append(f"maintenance_mode={data['maintenance_mode']}")
        
        if 'default_sound_pack' in data:
            sound_pack = data['default_sound_pack']
            if sound_pack in ['pack1', 'pack2', 'pack3', 'pack4']:
                await GameRepository.set_default_sound_pack(sound_pack)
                updates.append(f"default_sound_pack={sound_pack}")
        
        # Log admin action
        await AdminRepository.log_admin_action(
            admin_id=current_user['telegram_id'],
            action='update_game_settings',
            target_type='system',
            details=data
        )
        
        return jsonify({
            'success': True,
            'message': f'Updated: {", ".join(updates)}'
        })
        
    except Exception as e:
        logger.error(f"Error updating game settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== REPORTING ====================

@admin_api_bp.route('/reports/commission', methods=['GET'])
@require_admin
async def get_commission_report(current_user):
    """
    Get commission report
    
    Query params:
        start_date: str - YYYY-MM-DD
        end_date: str - YYYY-MM-DD
        format: str - 'json' or 'csv' (default: 'json')
    
    Returns:
        JSON or CSV: Commission report
    """
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        format_type = request.args.get('format', 'json')
        
        if not start_date_str or not end_date_str:
            return jsonify({'success': False, 'error': 'Missing start_date or end_date'}), 400
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
        
        # Get rounds in date range
        query = """
            SELECT 
                id, round_number, total_cartelas, start_time, win_percentage,
                total_cartelas * $3 as total_bets
            FROM game_rounds
            WHERE start_time >= $1 AND start_time < $2 AND status = 'ended'
            ORDER BY start_time ASC
        """
        
        from bot.db.database import fetch_all
        rounds = await fetch_all(query, start_date, end_date, config.CARTELA_PRICE)
        
        report_data = []
        total_bets = 0
        total_commission = 0
        
        for round_data in rounds:
            round_bets = round_data['total_bets']
            win_percentage = round_data.get('win_percentage', 80)
            commission = round_bets * (100 - win_percentage) / 100
            
            total_bets += round_bets
            total_commission += commission
            
            report_data.append({
                'date': round_data['start_time'].strftime('%Y-%m-%d'),
                'round_id': round_data['id'],
                'round_number': round_data['round_number'],
                'cartelas_sold': round_data['total_cartelas'],
                'total_bets': round_bets,
                'win_percentage': win_percentage,
                'commission': commission
            })
        
        summary = {
            'total_bets': total_bets,
            'total_commission': total_commission,
            'average_commission_rate': (total_commission / total_bets * 100) if total_bets > 0 else 0
        }
        
        if format_type == 'csv':
            # Generate CSV
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['Date', 'Round ID', 'Round Number', 'Cartelas Sold', 'Total Bets (ETB)', 'Win %', 'Commission (ETB)'])
            
            for row in report_data:
                writer.writerow([
                    row['date'], row['round_id'], row['round_number'],
                    row['cartelas_sold'], f"{row['total_bets']:.2f}",
                    f"{row['win_percentage']}%", f"{row['commission']:.2f}"
                ])
            
            writer.writerow([])
            writer.writerow(['SUMMARY', '', '', '', '', '', ''])
            writer.writerow(['Total Bets', f"{summary['total_bets']:.2f} ETB"])
            writer.writerow(['Total Commission', f"{summary['total_commission']:.2f} ETB"])
            writer.writerow(['Avg Commission Rate', f"{summary['average_commission_rate']:.2f}%"])
            
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=commission_report_{start_date_str}_to_{end_date_str}.csv'}
            )
        
        return jsonify({
            'success': True,
            'data': {
                'period': {'start_date': start_date_str, 'end_date': end_date_str},
                'summary': summary,
                'details': report_data
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating commission report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== SYSTEM HEALTH ====================

@admin_api_bp.route('/health', methods=['GET'])
@require_admin
async def system_health(current_user):
    """
    Get system health status
    
    Returns:
        JSON: Health status
    """
    try:
        from bot.db.database import db
        from bot.game_engine.bingo_room import bingo_room
        from bot.game_engine.events import connected_clients  # Import from events.py
        
        # Database health
        db_health = await db.health_check()
        
        # Game engine health
        game_health = {
            'status': bingo_room.status if bingo_room else 'unknown',
            'round_id': bingo_room.current_round_id if bingo_room else None,
            'player_count': bingo_room.get_player_count() if hasattr(bingo_room, 'get_player_count') else 0
        }
        
        # Active WebSocket clients (from events.py)
        active_sessions = len(connected_clients) if connected_clients else 0
        
        return jsonify({
            'success': True,
            'data': {
                'database': db_health,
                'game_engine': game_health,
                'active_sessions': active_sessions,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== EXPORTS ====================

__all__ = [
    'admin_api_bp',
]