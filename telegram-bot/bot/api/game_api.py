# telegram-bot/bot/api/game_api.py
# Estif Bingo 24/7 - Game API Endpoints
# REST API endpoints for the advanced bingo web application

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from bot.db.repository import (
    UserRepository,
    GameRepository,
    CartelaRepository,
    TransactionRepository,
    AuditRepository,
    active_game_cartelas,
)
from bot.api.auth import token_required, get_current_user_from_request as get_current_user
from bot.config import config
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji

# Create blueprint
game_api_bp = Blueprint('game_api', __name__, url_prefix='/api/game')


# ==================== GAME STATE ENDPOINTS ====================

@game_api_bp.route('/state', methods=['GET'])
@token_required
async def get_game_state(current_user):
    """
    Get current game state (timer, phase, called numbers, etc.)
    
    Returns:
        JSON: Current game state
    """
    try:
        from bot.game_engine.bingo_room import bingo_room
        
        state = bingo_room.get_state()
        
        return jsonify({
            'success': True,
            'data': {
                'status': state.get('status', 'idle'),
                'phase': state.get('phase', 'waiting'),
                'timer': state.get('timer', 0),
                'called_numbers': state.get('called_numbers', []),
                'last_number': state.get('last_number'),
                'total_cartelas_selected': state.get('selected_count', 0),
                'players_count': state.get('player_count', 0),
                'round_id': state.get('round_id'),
                'win_percentage': await GameRepository.get_win_percentage()
            }
        })
    except Exception as e:
        logger.error(f"Error getting game state: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@game_api_bp.route('/cartelas', methods=['GET'])
@token_required
async def get_cartelas(current_user):
    """
    Get all cartelas with availability status
    
    Query params:
        page: int - Page number (default: 1)
        limit: int - Items per page (default: 100)
    
    Returns:
        JSON: List of cartelas with status
    """
    try:
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 100)), 200)
        offset = (page - 1) * limit
        
        # Get cartelas
        cartelas = await CartelaRepository.get_all(limit=limit, offset=offset, only_active=True)
        
        # Get current selections
        selected_cartelas = active_game_cartelas.get_all_selected_cartelas()
        
        # Get user's selections
        user_id = current_user['telegram_id']
        user_cartelas = active_game_cartelas.get_user_cartelas(user_id)
        
        # Build response
        cartela_list = []
        for cartela in cartelas:
            cartela_id = cartela['id']
            cartela_list.append({
                'id': cartela_id,
                'grid': cartela['grid'],
                'is_taken': cartela_id in selected_cartelas,
                'taken_by': selected_cartelas.get(cartela_id),
                'is_mine': cartela_id in user_cartelas,
                'can_select': (
                    cartela_id not in selected_cartelas and
                    len(user_cartelas) < config.MAX_CARTELAS
                )
            })
        
        total_cartelas = await CartelaRepository.get_count()
        
        return jsonify({
            'success': True,
            'data': {
                'cartelas': cartela_list,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total_cartelas,
                    'pages': (total_cartelas + limit - 1) // limit
                },
                'user_selected_count': len(user_cartelas),
                'max_cartelas': config.MAX_CARTELAS,
                'cartela_price': config.CARTELA_PRICE
            }
        })
    except Exception as e:
        logger.error(f"Error getting cartelas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@game_api_bp.route('/cartelas/available', methods=['GET'])
@token_required
async def get_available_cartelas(current_user):
    """
    Get only available (not taken) cartelas for quick selection
    
    Returns:
        JSON: List of available cartela IDs
    """
    try:
        available_ids = active_game_cartelas.get_available_cartelas(total_cartelas=1000)
        
        return jsonify({
            'success': True,
            'data': {
                'available_ids': available_ids,
                'count': len(available_ids)
            }
        })
    except Exception as e:
        logger.error(f"Error getting available cartelas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== CARTELA SELECTION ENDPOINTS ====================

@game_api_bp.route('/select', methods=['POST'])
@token_required
async def select_cartelas(current_user):
    """
    Select cartelas for the current round
    
    Request body:
        {
            "cartela_ids": [1, 2, 3, 4]
        }
    
    Returns:
        JSON: Selection result
    """
    try:
        data = request.get_json()
        cartela_ids = data.get('cartela_ids', [])
        
        if not cartela_ids:
            return jsonify({'success': False, 'error': 'No cartelas selected'}), 400
        
        if len(cartela_ids) > config.MAX_CARTELAS:
            return jsonify({
                'success': False, 
                'error': f'Maximum {config.MAX_CARTELAS} cartelas allowed'
            }), 400
        
        user_id = current_user['telegram_id']
        
        # Check if game is in selection phase
        from bot.game_engine.bingo_room import bingo_room
        if bingo_room.status != 'selection':
            return jsonify({'success': False, 'error': 'Game is not in selection phase'}), 400
        
        # Check if timer still running
        if bingo_room.remaining <= 0:
            return jsonify({'success': False, 'error': 'Selection time has ended'}), 400
        
        # Check user balance
        from bot.api.balance_ops import get_balance
        balance = await get_balance(user_id)
        total_cost = len(cartela_ids) * config.CARTELA_PRICE
        
        if balance < total_cost:
            return jsonify({
                'success': False, 
                'error': 'insufficient_balance',
                'balance': balance,
                'required': total_cost
            }), 400
        
        # Validate each cartela
        selected = []
        failed = []
        
        for cartela_id in cartela_ids:
            # Check if cartela exists and is active
            is_valid = await CartelaRepository.is_valid_cartela(cartela_id)
            if not is_valid:
                failed.append({'cartela_id': cartela_id, 'reason': 'Invalid cartela'})
                continue
            
            # Check if cartela is available
            if not active_game_cartelas.is_cartela_available(cartela_id):
                failed.append({'cartela_id': cartela_id, 'reason': 'Already taken'})
                continue
            
            # Check if user already selected this cartela
            if active_game_cartelas.is_cartela_mine(user_id, cartela_id):
                failed.append({'cartela_id': cartela_id, 'reason': 'Already selected'})
                continue
            
            selected.append(cartela_id)
        
        if not selected:
            return jsonify({'success': False, 'error': 'No valid cartelas selected', 'failed': failed}), 400
        
        # Deduct balance
        from bot.api.balance_ops import deduct_balance
        total_deduction = len(selected) * config.CARTELA_PRICE
        
        await deduct_balance(
            telegram_id=user_id,
            amount=total_deduction,
            reason="cartela_purchase",
            metadata={
                'cartela_ids': selected,
                'round_id': bingo_room.current_round_id,
                'count': len(selected)
            }
        )
        
        # Mark cartelas as taken
        for cartela_id in selected:
            active_game_cartelas.take_cartela(cartela_id, user_id)
            active_game_cartelas.select_cartela(user_id, cartela_id)
            
            # Record selection in database
            await GameRepository.create_selection({
                'round_id': bingo_room.current_round_id,
                'user_id': user_id,
                'cartela_id': cartela_id,
                'amount': config.CARTELA_PRICE
            })
        
        # Broadcast selection update to all players
        from bot.game_engine.events import broadcast_cartela_update
        await broadcast_cartela_update(cartela_ids=selected, user_id=user_id)
        
        # Get updated balance
        new_balance = await get_balance(user_id)
        
        return jsonify({
            'success': True,
            'data': {
                'selected': selected,
                'failed': failed,
                'total_selected': len(selected),
                'total_cost': total_deduction,
                'new_balance': new_balance,
                'user_selected_count': active_game_cartelas.get_user_selected_count(user_id),
                'global_selected_count': active_game_cartelas.get_selected_count()
            }
        })
        
    except Exception as e:
        logger.error(f"Error selecting cartelas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@game_api_bp.route('/unselect', methods=['POST'])
@token_required
async def unselect_cartelas(current_user):
    """
    Unselect cartelas (remove from selection)
    
    Request body:
        {
            "cartela_ids": [1, 2]
        }
    
    Returns:
        JSON: Unselection result
    """
    try:
        data = request.get_json()
        cartela_ids = data.get('cartela_ids', [])
        
        if not cartela_ids:
            return jsonify({'success': False, 'error': 'No cartelas specified'}), 400
        
        user_id = current_user['telegram_id']
        
        # Check if game is in selection phase
        from bot.game_engine.bingo_room import bingo_room
        if bingo_room.status != 'selection':
            return jsonify({'success': False, 'error': 'Cannot unselect after selection phase'}), 400
        
        # Unselect each cartela
        unselected = []
        failed = []
        
        for cartela_id in cartela_ids:
            if active_game_cartelas.is_cartela_mine(user_id, cartela_id):
                active_game_cartelas.unselect_cartela(user_id, cartela_id)
                unselected.append(cartela_id)
                
                # Refund balance
                from bot.api.balance_ops import add_balance
                await add_balance(
                    telegram_id=user_id,
                    amount=config.CARTELA_PRICE,
                    reason="cartela_unselected",
                    metadata={'cartela_id': cartela_id}
                )
            else:
                failed.append({'cartela_id': cartela_id, 'reason': 'Not your cartela'})
        
        # Broadcast update
        if unselected:
            from bot.game_engine.events import broadcast_cartela_update
            await broadcast_cartela_update(cartela_ids=unselected, user_id=user_id, action='unselect')
        
        # Get updated balance
        from bot.api.balance_ops import get_balance
        new_balance = await get_balance(user_id)
        
        return jsonify({
            'success': True,
            'data': {
                'unselected': unselected,
                'failed': failed,
                'new_balance': new_balance,
                'user_selected_count': active_game_cartelas.get_user_selected_count(user_id)
            }
        })
        
    except Exception as e:
        logger.error(f"Error unselecting cartelas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== USER INFO ENDPOINTS ====================

@game_api_bp.route('/user/balance', methods=['GET'])
@token_required
async def get_user_balance(current_user):
    """
    Get current user's balance
    
    Returns:
        JSON: User balance
    """
    try:
        user_id = current_user['telegram_id']
        from bot.api.balance_ops import get_balance
        
        balance = await get_balance(user_id)
        
        return jsonify({
            'success': True,
            'data': {
                'balance': balance,
                'cartela_price': config.CARTELA_PRICE,
                'min_balance_for_play': config.MIN_BALANCE_FOR_PLAY
            }
        })
    except Exception as e:
        logger.error(f"Error getting user balance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@game_api_bp.route('/user/selections', methods=['GET'])
@token_required
async def get_user_selections(current_user):
    """
    Get user's selected cartelas for current round
    
    Returns:
        JSON: User's selected cartelas with grids
    """
    try:
        user_id = current_user['telegram_id']
        
        # Get selected cartela IDs
        selected_ids = list(active_game_cartelas.get_user_cartelas(user_id))
        
        # Get cartela grids
        cartelas = []
        for cartela_id in selected_ids:
            cartela = await CartelaRepository.get_by_id(cartela_id)
            if cartela:
                cartelas.append({
                    'id': cartela_id,
                    'grid': cartela['grid']
                })
        
        return jsonify({
            'success': True,
            'data': {
                'cartelas': cartelas,
                'count': len(cartelas),
                'max_allowed': config.MAX_CARTELAS
            }
        })
    except Exception as e:
        logger.error(f"Error getting user selections: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== GAME HISTORY ENDPOINTS ====================

@game_api_bp.route('/history', methods=['GET'])
@token_required
async def get_game_history(current_user):
    """
    Get user's game history
    
    Query params:
        limit: int - Number of records (default: 20)
        offset: int - Pagination offset (default: 0)
    
    Returns:
        JSON: Game history
    """
    try:
        user_id = current_user['telegram_id']
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # Get user's round selections with round info
        query = """
            SELECT 
                gr.id as round_id,
                gr.round_number,
                gr.status,
                gr.start_time,
                gr.end_time,
                gr.winners,
                gr.prize_pool,
                COUNT(rs.id) as cartelas_count,
                SUM(rs.amount) as total_spent,
                CASE 
                    WHEN gr.winners IS NOT NULL AND gr.winners::text LIKE '%$1%' THEN true
                    ELSE false
                END as did_win
            FROM round_selections rs
            JOIN game_rounds gr ON rs.round_id = gr.id
            WHERE rs.user_id = $1
            GROUP BY gr.id, gr.round_number, gr.status, gr.start_time, gr.end_time, gr.winners, gr.prize_pool
            ORDER BY gr.start_time DESC
            LIMIT $2 OFFSET $3
        """
        
        from bot.db.database import fetch_all
        results = await fetch_all(query, user_id, limit, offset)
        
        history = []
        for row in results:
            history.append({
                'round_id': row['round_id'],
                'round_number': row['round_number'],
                'status': row['status'],
                'start_time': row['start_time'].isoformat() if row['start_time'] else None,
                'end_time': row['end_time'].isoformat() if row['end_time'] else None,
                'cartelas_count': row['cartelas_count'],
                'total_spent': float(row['total_spent']) if row['total_spent'] else 0,
                'did_win': row['did_win'],
                'prize_pool': float(row['prize_pool']) if row['prize_pool'] else 0
            })
        
        return jsonify({
            'success': True,
            'data': {
                'history': history,
                'count': len(history)
            }
        })
    except Exception as e:
        logger.error(f"Error getting game history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@game_api_bp.route('/round/<int:round_id>', methods=['GET'])
@token_required
async def get_round_details(current_user, round_id):
    """
    Get detailed information about a specific round
    
    Args:
        round_id: int - Round ID
    
    Returns:
        JSON: Round details
    """
    try:
        user_id = current_user['telegram_id']
        
        # Get round info
        round_data = await GameRepository.get_round(round_id)
        if not round_data:
            return jsonify({'success': False, 'error': 'Round not found'}), 404
        
        # Get user's selections for this round
        selections = await GameRepository.get_user_selections(round_id, user_id)
        
        # Get winners
        winners = round_data.get('winners', [])
        user_won = any(w.get('user_id') == user_id for w in winners) if winners else False
        
        return jsonify({
            'success': True,
            'data': {
                'round': {
                    'id': round_data['id'],
                    'round_number': round_data['round_number'],
                    'status': round_data['status'],
                    'start_time': round_data['start_time'].isoformat() if round_data['start_time'] else None,
                    'end_time': round_data['end_time'].isoformat() if round_data['end_time'] else None,
                    'total_cartelas': round_data['total_cartelas'],
                    'total_players': round_data['total_players'],
                    'prize_pool': float(round_data['prize_pool']) if round_data['prize_pool'] else 0,
                    'winners': winners,
                    'user_won': user_won
                },
                'user_selections': [
                    {
                        'cartela_id': s['cartela_id'],
                        'amount': float(s['amount']),
                        'selected_at': s['selected_at'].isoformat() if s['selected_at'] else None
                    }
                    for s in selections
                ]
            }
        })
    except Exception as e:
        logger.error(f"Error getting round details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== WINNER ENDPOINTS ====================

@game_api_bp.route('/winners/current', methods=['GET'])
@token_required
async def get_current_winners(current_user):
    """
    Get winners of the current/previous round
    
    Returns:
        JSON: Winner information
    """
    try:
        from bot.game_engine.bingo_room import bingo_room
        
        winners = bingo_room.get_current_winners()
        
        return jsonify({
            'success': True,
            'data': {
                'winners': winners,
                'has_winners': len(winners) > 0,
                'round_id': bingo_room.current_round_id
            }
        })
    except Exception as e:
        logger.error(f"Error getting current winners: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== SOUND PACK ENDPOINTS ====================

@game_api_bp.route('/sound/packs', methods=['GET'])
@token_required
async def get_sound_packs(current_user):
    """
    Get available sound packs
    
    Returns:
        JSON: List of sound packs
    """
    try:
        sound_packs = [
            {'id': 'pack1', 'name': 'Classic Bingo', 'preview_url': '/static/sounds/pack1/click.mp3'},
            {'id': 'pack2', 'name': 'Modern Beat', 'preview_url': '/static/sounds/pack2/click.mp3'},
            {'id': 'pack3', 'name': 'Arcade Fun', 'preview_url': '/static/sounds/pack3/click.mp3'},
            {'id': 'pack4', 'name': 'Casino Style', 'preview_url': '/static/sounds/pack4/click.mp3'}
        ]
        
        # Get user's current sound pack
        user_id = current_user['telegram_id']
        user = await UserRepository.get_by_telegram_id(user_id)
        current_pack = user.get('sound_pack', 'pack1') if user else 'pack1'
        
        return jsonify({
            'success': True,
            'data': {
                'packs': sound_packs,
                'current': current_pack
            }
        })
    except Exception as e:
        logger.error(f"Error getting sound packs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@game_api_bp.route('/sound/select', methods=['POST'])
@token_required
async def select_sound_pack(current_user):
    """
    Change user's sound pack preference
    
    Request body:
        {
            "sound_pack": "pack2"
        }
    
    Returns:
        JSON: Update result
    """
    try:
        data = request.get_json()
        sound_pack = data.get('sound_pack')
        
        valid_packs = ['pack1', 'pack2', 'pack3', 'pack4']
        if sound_pack not in valid_packs:
            return jsonify({'success': False, 'error': 'Invalid sound pack'}), 400
        
        user_id = current_user['telegram_id']
        
        # Update user preference
        success = await UserRepository.update_sound_pack(user_id, sound_pack)
        
        if success:
            return jsonify({
                'success': True,
                'data': {
                    'sound_pack': sound_pack,
                    'message': f'Sound pack changed to {sound_pack}'
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update sound pack'}), 500
            
    except Exception as e:
        logger.error(f"Error selecting sound pack: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== LEADERBOARD ENDPOINTS ====================

@game_api_bp.route('/leaderboard', methods=['GET'])
@token_required
async def get_leaderboard(current_user):
    """
    Get global leaderboard
    
    Query params:
        type: str - 'balance', 'wins', 'games' (default: 'balance')
        limit: int - Number of players (default: 10)
    
    Returns:
        JSON: Leaderboard data
    """
    try:
        leaderboard_type = request.args.get('type', 'balance')
        limit = min(int(request.args.get('limit', 10)), 50)
        
        if leaderboard_type == 'balance':
            leaderboard = await UserRepository.get_top_users_by_balance(limit)
        elif leaderboard_type == 'wins':
            leaderboard = await UserRepository.get_top_users_by_wins(limit)
        elif leaderboard_type == 'games':
            leaderboard = await UserRepository.get_top_users_by_games(limit)
        else:
            return jsonify({'success': False, 'error': 'Invalid leaderboard type'}), 400
        
        # Format leaderboard
        formatted = []
        for idx, user in enumerate(leaderboard, 1):
            formatted.append({
                'rank': idx,
                'user_id': user['telegram_id'],
                'name': user.get('first_name') or user.get('username', 'Unknown'),
                'value': float(user.get(leaderboard_type, 0)) if leaderboard_type == 'balance' else user.get(f'total_{leaderboard_type}', 0)
            })
        
        return jsonify({
            'success': True,
            'data': {
                'type': leaderboard_type,
                'leaderboard': formatted,
                'user_rank': await UserRepository.get_user_rank_by_balance(current_user['telegram_id'])
            }
        })
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== STATISTICS ENDPOINTS ====================

@game_api_bp.route('/statistics', methods=['GET'])
@token_required
async def get_statistics(current_user):
    """
    Get game statistics for the user
    
    Returns:
        JSON: User game statistics
    """
    try:
        user_id = current_user['telegram_id']
        
        # Get user stats
        user_stats = await UserRepository.get_user_stats(user_id)
        
        # Get transaction stats
        tx_stats = await TransactionRepository.get_stats(user_id)
        
        # Get global stats
        global_stats = await GameRepository.get_global_stats()
        
        return jsonify({
            'success': True,
            'data': {
                'user': {
                    'games_played': user_stats.get('total_games_played', 0),
                    'total_wagered': user_stats.get('total_wagered', 0),
                    'total_won': user_stats.get('total_won', 0),
                    'net_profit': user_stats.get('net_profit', 0),
                    'registered_since': user_stats.get('created_at')
                },
                'transactions': tx_stats,
                'global': global_stats
            }
        })
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== ADMIN ENDPOINTS ====================

@game_api_bp.route('/admin/game/force_start', methods=['POST'])
@token_required
async def admin_force_start(current_user):
    """
    Force start a new game round (admin only)
    """
    try:
        # Check if user is admin
        if not current_user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        from bot.game_engine.bingo_room import bingo_room
        success = await bingo_room.force_start()
        
        if success:
            return jsonify({'success': True, 'message': 'Game force started'})
        else:
            return jsonify({'success': False, 'error': 'Failed to force start game'}), 500
            
    except Exception as e:
        logger.error(f"Error force starting game: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@game_api_bp.route('/admin/game/force_stop', methods=['POST'])
@token_required
async def admin_force_stop(current_user):
    """
    Force stop current game round (admin only)
    """
    try:
        if not current_user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        from bot.game_engine.bingo_room import bingo_room
        success = await bingo_room.force_stop()
        
        if success:
            return jsonify({'success': True, 'message': 'Game force stopped'})
        else:
            return jsonify({'success': False, 'error': 'Failed to force stop game'}), 500
            
    except Exception as e:
        logger.error(f"Error force stopping game: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== WEBSOCKET AUTH ENDPOINT ====================

@game_api_bp.route('/ws_auth', methods=['POST'])
@token_required
async def websocket_auth(current_user):
    """
    Authenticate for WebSocket connection
    
    Returns:
        JSON: WebSocket authentication token
    """
    try:
        from bot.utils.security import generate_ws_token
        
        user_id = current_user['telegram_id']
        ws_token = generate_ws_token(user_id)
        
        return jsonify({
            'success': True,
            'data': {
                'token': ws_token,
                'user_id': user_id
            }
        })
    except Exception as e:
        logger.error(f"Error generating WS token: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== HEALTH CHECK ====================

@game_api_bp.route('/health', methods=['GET'])
async def health_check():
    """
    Health check endpoint for the game API
    
    Returns:
        JSON: Health status
    """
    try:
        from bot.game_engine.bingo_room import bingo_room
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'game_status': bingo_room.status if bingo_room else 'unknown',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# ==================== EXPORTS ====================

__all__ = [
    'game_api_bp',
]