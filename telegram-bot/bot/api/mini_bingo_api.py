# telegram-bot/bot/api/mini_bingo_api.py
# Estif Bingo 24/7 - Mini Bingo API Endpoints
# Handles single-player mini bingo game operations

import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from flask import Blueprint, request, jsonify, session
from bot.api.auth import token_required, optional_token_required
from bot.db.repository import UserRepository, TransactionRepository, AuditRepository
from bot.api.balance_ops import get_balance, deduct_balance, add_balance
from bot.config import config
from bot.utils.logger import logger

# Create blueprint
mini_bingo_bp = Blueprint('mini_bingo', __name__, url_prefix='/api/mini-bingo')

# Game constants
MINI_BINGO_PRICE = getattr(config, 'MINI_BINGO_PRICE', 5)
MINI_BINGO_WIN_PERCENTAGE = getattr(config, 'MINI_BINGO_WIN_PERCENTAGE', 80)
GRID_SIZE = 5
NUMBERS_RANGE = 75

# Column ranges for BINGO
COLUMN_RANGES = {
    0: (1, 15),   # B
    1: (16, 30),  # I
    2: (31, 45),  # N
    3: (46, 60),  # G
    4: (61, 75)   # O
}

# Store active game sessions (in production, use Redis)
active_games: Dict[str, Dict] = {}


# ==================== CARTELA GENERATION ====================

def generate_cartela() -> List[List[int]]:
    """
    Generate a random 5x5 bingo cartela
    
    Returns:
        list: 5x5 grid with numbers
    """
    cartela = []
    
    for col in range(GRID_SIZE):
        col_numbers = []
        min_val, max_val = COLUMN_RANGES[col]
        
        # Generate 5 unique numbers for this column
        available = list(range(min_val, max_val + 1))
        random.shuffle(available)
        
        for row in range(GRID_SIZE):
            if row == 2 and col == 2:
                # Free space (center)
                col_numbers.append(0)
            else:
                col_numbers.append(available.pop())
        
        cartela.append(col_numbers)
    
    return cartela


def check_win(cartela: List[List[int]], called_numbers: List[int]) -> Optional[Dict]:
    """
    Check if the cartela has a winning pattern
    
    Args:
        cartela: 5x5 grid
        called_numbers: List of called numbers
    
    Returns:
        dict: Winning pattern info or None
    """
    called_set = set(called_numbers)
    
    # Check rows (horizontal)
    for row in range(GRID_SIZE):
        row_complete = True
        for col in range(GRID_SIZE):
            value = cartela[col][row]
            if value != 0 and value not in called_set:
                row_complete = False
                break
        if row_complete:
            return {'type': 'horizontal', 'index': row, 'cells': [(col, row) for col in range(GRID_SIZE)]}
    
    # Check columns (vertical)
    for col in range(GRID_SIZE):
        col_complete = True
        for row in range(GRID_SIZE):
            value = cartela[col][row]
            if value != 0 and value not in called_set:
                col_complete = False
                break
        if col_complete:
            return {'type': 'vertical', 'index': col, 'cells': [(col, row) for row in range(GRID_SIZE)]}
    
    # Check main diagonal (top-left to bottom-right)
    diag_complete = True
    diag_cells = []
    for i in range(GRID_SIZE):
        value = cartela[i][i]
        diag_cells.append((i, i))
        if value != 0 and value not in called_set:
            diag_complete = False
            break
    if diag_complete:
        return {'type': 'diagonal', 'subtype': 'main', 'cells': diag_cells}
    
    # Check anti-diagonal (top-right to bottom-left)
    anti_diag_complete = True
    anti_diag_cells = []
    for i in range(GRID_SIZE):
        value = cartela[i][GRID_SIZE - 1 - i]
        anti_diag_cells.append((i, GRID_SIZE - 1 - i))
        if value != 0 and value not in called_set:
            anti_diag_complete = False
            break
    if anti_diag_complete:
        return {'type': 'diagonal', 'subtype': 'anti', 'cells': anti_diag_cells}
    
    return None


# ==================== GAME SESSION MANAGEMENT ====================

def create_game_session(user_id: int, cartela: List[List[int]]) -> str:
    """
    Create a new game session
    
    Args:
        user_id: User's Telegram ID
        cartela: 5x5 grid
    
    Returns:
        str: Session ID
    """
    session_id = str(uuid.uuid4())[:8]
    
    active_games[session_id] = {
        'user_id': user_id,
        'cartela': cartela,
        'called_numbers': [],
        'numbers_sequence': list(range(1, NUMBERS_RANGE + 1)),
        'status': 'active',
        'win_amount': 0,
        'win_pattern': None,
        'started_at': datetime.utcnow().isoformat(),
        'last_number_at': None
    }
    
    # Shuffle numbers sequence
    random.shuffle(active_games[session_id]['numbers_sequence'])
    
    return session_id


def get_game_session(session_id: str) -> Optional[Dict]:
    """Get game session by ID"""
    return active_games.get(session_id)


def update_game_session(session_id: str, updates: Dict) -> bool:
    """Update game session"""
    if session_id in active_games:
        active_games[session_id].update(updates)
        return True
    return False


def delete_game_session(session_id: str) -> bool:
    """Delete game session"""
    if session_id in active_games:
        del active_games[session_id]
        return True
    return False


def cleanup_expired_sessions():
    """Remove expired game sessions (older than 30 minutes)"""
    now = datetime.utcnow()
    expired = []
    
    for session_id, game in active_games.items():
        started = datetime.fromisoformat(game['started_at'])
        if (now - started).total_seconds() > 1800:  # 30 minutes
            expired.append(session_id)
    
    for session_id in expired:
        del active_games[session_id]
    
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired mini bingo sessions")


# ==================== API ENDPOINTS ====================

@mini_bingo_bp.route('/start', methods=['POST'])
@token_required
async def start_game(current_user):
    """
    Start a new mini bingo game
    
    Request body:
        {
            "sound_pack": "pack1"  # optional
        }
    
    Returns:
        JSON: Game session with cartela
    """
    try:
        user_id = current_user['telegram_id']
        
        # Check balance
        balance = await get_balance(user_id)
        
        if balance < MINI_BINGO_PRICE:
            return jsonify({
                'success': False,
                'error': 'insufficient_balance',
                'balance': balance,
                'required': MINI_BINGO_PRICE
            }), 400
        
        # Deduct game cost
        deduct_success = await deduct_balance(
            telegram_id=user_id,
            amount=MINI_BINGO_PRICE,
            reason="mini_bingo_game",
            metadata={'game_type': 'mini_bingo'}
        )
        
        if not deduct_success:
            return jsonify({'success': False, 'error': 'Failed to deduct balance'}), 500
        
        # Generate cartela
        cartela = generate_cartela()
        
        # Create game session
        session_id = create_game_session(user_id, cartela)
        
        # Get sound pack preference
        sound_pack = current_user.get('sound_pack', config.DEFAULT_SOUND_PACK)
        
        return jsonify({
            'success': True,
            'data': {
                'session_id': session_id,
                'cartela': cartela,
                'game_cost': MINI_BINGO_PRICE,
                'win_percentage': MINI_BINGO_WIN_PERCENTAGE,
                'sound_pack': sound_pack,
                'numbers_range': NUMBERS_RANGE
            }
        })
        
    except Exception as e:
        logger.error(f"Error starting mini bingo game: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@mini_bingo_bp.route('/draw', methods=['POST'])
@token_required
async def draw_number(current_user):
    """
    Draw the next number for a mini bingo game
    
    Request body:
        {
            "session_id": "abc123"
        }
    
    Returns:
        JSON: Drawn number and game state
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Missing session_id'}), 400
        
        game = get_game_session(session_id)
        
        if not game:
            return jsonify({'success': False, 'error': 'Game session not found'}), 404
        
        if game['user_id'] != current_user['telegram_id']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if game['status'] != 'active':
            return jsonify({
                'success': False,
                'error': 'Game already ended',
                'win_amount': game.get('win_amount', 0),
                'win_pattern': game.get('win_pattern')
            }), 400
        
        # Get next number
        numbers_sequence = game['numbers_sequence']
        called_numbers = game['called_numbers']
        
        if len(called_numbers) >= len(numbers_sequence):
            # Game over - no more numbers
            update_game_session(session_id, {'status': 'ended'})
            return jsonify({
                'success': False,
                'error': 'No more numbers',
                'game_ended': True
            }), 400
        
        # Draw next number
        next_number = numbers_sequence[len(called_numbers)]
        called_numbers.append(next_number)
        
        # Check for win
        cartela = game['cartela']
        win_info = check_win(cartela, called_numbers)
        
        game_data = {
            'called_numbers': called_numbers,
            'last_number_at': datetime.utcnow().isoformat()
        }
        
        if win_info:
            # Calculate win amount
            win_amount = MINI_BINGO_PRICE * MINI_BINGO_WIN_PERCENTAGE // 100
            
            # Add win to balance
            await add_balance(
                telegram_id=current_user['telegram_id'],
                amount=win_amount,
                reason="mini_bingo_win",
                metadata={
                    'session_id': session_id,
                    'pattern': win_info['type'],
                    'numbers_called': len(called_numbers)
                }
            )
            
            game_data['status'] = 'won'
            game_data['win_amount'] = win_amount
            game_data['win_pattern'] = win_info
            
            # Audit log
            await AuditRepository.log(
                user_id=current_user['telegram_id'],
                action="mini_bingo_win",
                entity_type="game",
                entity_id=session_id,
                new_value={'win_amount': win_amount, 'pattern': win_info['type']}
            )
            
            logger.info(f"Mini bingo win for user {current_user['telegram_id']}: {win_amount} ETB")
        
        update_game_session(session_id, game_data)
        
        return jsonify({
            'success': True,
            'data': {
                'number': next_number,
                'called_numbers': called_numbers,
                'numbers_count': len(called_numbers),
                'game_status': game_data.get('status', 'active'),
                'win_amount': game_data.get('win_amount', 0),
                'win_pattern': game_data.get('win_pattern'),
                'marked_cells': get_marked_cells(cartela, called_numbers)
            }
        })
        
    except Exception as e:
        logger.error(f"Error drawing number: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@mini_bingo_bp.route('/state', methods=['POST'])
@token_required
async def get_game_state(current_user):
    """
    Get current game state
    
    Request body:
        {
            "session_id": "abc123"
        }
    
    Returns:
        JSON: Current game state
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Missing session_id'}), 400
        
        game = get_game_session(session_id)
        
        if not game:
            return jsonify({'success': False, 'error': 'Game session not found'}), 404
        
        if game['user_id'] != current_user['telegram_id']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        cartela = game['cartela']
        called_numbers = game['called_numbers']
        
        return jsonify({
            'success': True,
            'data': {
                'session_id': session_id,
                'status': game['status'],
                'cartela': cartela,
                'called_numbers': called_numbers,
                'numbers_count': len(called_numbers),
                'marked_cells': get_marked_cells(cartela, called_numbers),
                'win_amount': game.get('win_amount', 0),
                'win_pattern': game.get('win_pattern'),
                'started_at': game['started_at']
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting game state: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@mini_bingo_bp.route('/end', methods=['POST'])
@token_required
async def end_game(current_user):
    """
    End a mini bingo game (user forfeits)
    
    Request body:
        {
            "session_id": "abc123"
        }
    
    Returns:
        JSON: Game ended confirmation
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Missing session_id'}), 400
        
        game = get_game_session(session_id)
        
        if not game:
            return jsonify({'success': False, 'error': 'Game session not found'}), 404
        
        if game['user_id'] != current_user['telegram_id']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if game['status'] != 'active':
            return jsonify({
                'success': False,
                'error': f'Game already {game["status"]}'
            }), 400
        
        # Mark game as ended
        update_game_session(session_id, {'status': 'ended'})
        
        logger.info(f"Mini bingo game ended by user {current_user['telegram_id']}")
        
        return jsonify({
            'success': True,
            'message': 'Game ended',
            'data': {
                'session_id': session_id,
                'called_numbers': game['called_numbers'],
                'numbers_count': len(game['called_numbers'])
            }
        })
        
    except Exception as e:
        logger.error(f"Error ending game: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@mini_bingo_bp.route('/history', methods=['GET'])
@token_required
async def get_game_history(current_user):
    """
    Get user's mini bingo game history
    
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
        
        # Get transactions for mini bingo
        transactions = await TransactionRepository.get_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
            transaction_type='mini_bingo_game'
        )
        
        # Get win transactions
        wins = await TransactionRepository.get_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
            transaction_type='mini_bingo_win'
        )
        
        history = []
        for tx in transactions:
            history.append({
                'type': 'game',
                'amount': abs(tx['amount']),
                'timestamp': tx['created_at'].isoformat() if tx['created_at'] else None,
                'metadata': tx.get('metadata')
            })
        
        for win in wins:
            history.append({
                'type': 'win',
                'amount': win['amount'],
                'timestamp': win['created_at'].isoformat() if win['created_at'] else None,
                'metadata': win.get('metadata')
            })
        
        # Sort by timestamp descending
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Get statistics
        stats = await TransactionRepository.get_stats(user_id)
        
        return jsonify({
            'success': True,
            'data': {
                'history': history[:limit],
                'statistics': {
                    'total_games': stats.get('mini_bingo_games', 0),
                    'total_wins': stats.get('mini_bingo_wins', 0),
                    'total_spent': stats.get('mini_bingo_spent', 0),
                    'total_won': stats.get('mini_bingo_won', 0),
                    'net_result': stats.get('mini_bingo_won', 0) - stats.get('mini_bingo_spent', 0)
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting game history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@mini_bingo_bp.route('/statistics', methods=['GET'])
@token_required
async def get_statistics(current_user):
    """
    Get mini bingo statistics for the user
    
    Returns:
        JSON: User statistics
    """
    try:
        user_id = current_user['telegram_id']
        
        # Get user's transaction stats
        stats = await TransactionRepository.get_stats(user_id)
        
        # Calculate win rate
        total_games = stats.get('mini_bingo_games', 0)
        total_wins = stats.get('mini_bingo_wins', 0)
        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_games_played': total_games,
                'total_wins': total_wins,
                'total_losses': total_games - total_wins,
                'win_rate': round(win_rate, 2),
                'total_spent': stats.get('mini_bingo_spent', 0),
                'total_won': stats.get('mini_bingo_won', 0),
                'net_profit': stats.get('mini_bingo_won', 0) - stats.get('mini_bingo_spent', 0),
                'best_streak': stats.get('mini_bingo_streak', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@mini_bingo_bp.route('/settings', methods=['GET'])
@token_required
async def get_settings(current_user):
    """
    Get mini bingo game settings
    
    Returns:
        JSON: Game settings
    """
    return jsonify({
        'success': True,
        'data': {
            'game_cost': MINI_BINGO_PRICE,
            'win_percentage': MINI_BINGO_WIN_PERCENTAGE,
            'grid_size': GRID_SIZE,
            'numbers_range': NUMBERS_RANGE,
            'win_amount': MINI_BINGO_PRICE * MINI_BINGO_WIN_PERCENTAGE // 100
        }
    })


@mini_bingo_bp.route('/cleanup', methods=['POST'])
async def cleanup_sessions():
    """
    Cleanup expired game sessions (can be called by cron job)
    """
    cleanup_expired_sessions()
    return jsonify({
        'success': True,
        'message': f'Active sessions: {len(active_games)}'
    })


# ==================== HELPER FUNCTIONS ====================

def get_marked_cells(cartela: List[List[int]], called_numbers: List[int]) -> List[Dict]:
    """
    Get marked cells on the cartela
    
    Args:
        cartela: 5x5 grid
        called_numbers: List of called numbers
    
    Returns:
        list: Marked cell coordinates
    """
    called_set = set(called_numbers)
    marked = []
    
    for col in range(GRID_SIZE):
        for row in range(GRID_SIZE):
            value = cartela[col][row]
            if value == 0 or value in called_set:
                marked.append({
                    'col': col,
                    'row': row,
                    'value': value,
                    'is_free': value == 0
                })
    
    return marked


# ==================== ADMIN ENDPOINTS ====================

@mini_bingo_bp.route('/admin/settings', methods=['PUT'])
@token_required
async def update_settings(current_user):
    """
    Update mini bingo game settings (admin only)
    
    Request body:
        {
            "game_cost": 10,
            "win_percentage": 75
        }
    
    Returns:
        JSON: Updated settings
    """
    try:
        if not current_user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.get_json()
        
        # Update global variables (in production, store in database)
        global MINI_BINGO_PRICE, MINI_BINGO_WIN_PERCENTAGE
        
        if 'game_cost' in data:
            new_cost = data['game_cost']
            if 1 <= new_cost <= 100:
                MINI_BINGO_PRICE = new_cost
        
        if 'win_percentage' in data:
            new_percentage = data['win_percentage']
            if 1 <= new_percentage <= 100:
                MINI_BINGO_WIN_PERCENTAGE = new_percentage
        
        # Audit log
        await AuditRepository.log(
            user_id=current_user['telegram_id'],
            action="mini_bingo_settings_updated",
            entity_type="settings",
            metadata=data
        )
        
        return jsonify({
            'success': True,
            'data': {
                'game_cost': MINI_BINGO_PRICE,
                'win_percentage': MINI_BINGO_WIN_PERCENTAGE
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating mini bingo settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== HEALTH CHECK ====================

@mini_bingo_bp.route('/health', methods=['GET'])
async def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'success': True,
        'status': 'healthy',
        'active_sessions': len(active_games),
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# ==================== EXPORTS ====================

__all__ = [
    'mini_bingo_bp',
    'generate_cartela',
    'check_win',
    'create_game_session',
    'get_game_session',
    'delete_game_session',
    'cleanup_expired_sessions',
]