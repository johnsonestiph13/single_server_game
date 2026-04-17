# telegram-bot/bot/game_engine/events.py
# Estif Bingo 24/7 - SocketIO Events Handler
# Handles real-time WebSocket events from the game client

import asyncio

from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask import request
from typing import List, Dict, Any, Optional
from bot.game_engine.bingo_room import bingo_room, GamePhase
from bot.game_engine.cartela_manager import cartela_manager
from bot.api.auth import verify_ws_token
from bot.db.repository import UserRepository
from bot.config import config
from bot.utils.logger import logger


# Store connected clients with their user IDs
connected_clients: Dict[str, int] = {}  # session_id -> user_id
client_rooms: Dict[str, str] = {}       # session_id -> room_name


# ==================== CONNECTION HANDLERS ====================

def register_socket_events(socketio: SocketIO, game_room=None):
    """
    Register all SocketIO event handlers.
    
    Args:
        socketio: SocketIO instance
        game_room: BingoRoom instance (uses global if not provided)
    """
    actual_game_room = game_room or bingo_room
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        session_id = request.sid
        logger.info(f"Client connected: {session_id}")
        
        # Send initial connection acknowledgment
        emit('connected', {
            'status': 'connected',
            'game_status': actual_game_room.status.value,
            'server_time': asyncio.get_event_loop().time()
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        session_id = request.sid
        user_id = connected_clients.get(session_id)
        
        if user_id:
            logger.info(f"Client disconnected: {session_id} (user: {user_id})")
            # Remove from tracking
            connected_clients.pop(session_id, None)
            client_rooms.pop(session_id, None)
        else:
            logger.info(f"Client disconnected: {session_id} (unauthenticated)")
    
    @socketio.on('authenticate')
    def handle_authenticate(data: Dict):
        """
        Authenticate client with JWT token.
        
        Expected data:
            {
                "token": "jwt_token_here"
            }
        """
        session_id = request.sid
        token = data.get('token')
        
        if not token:
            emit('auth_error', {'error': 'Missing token'})
            disconnect()
            return
        
        # Verify token
        payload = verify_ws_token(token)
        
        if not payload:
            emit('auth_error', {'error': 'Invalid or expired token'})
            disconnect()
            return
        
        user_id = payload.get('user_id')
        
        if not user_id:
            emit('auth_error', {'error': 'Invalid token payload'})
            disconnect()
            return
        
        # Store client mapping
        connected_clients[session_id] = user_id
        
        # Join appropriate room
        if actual_game_room.current_round_id:
            room_name = f"game_room_{actual_game_room.current_round_id}"
            join_room(room_name, sid=session_id)
            client_rooms[session_id] = room_name
        else:
            join_room('lobby', sid=session_id)
            client_rooms[session_id] = 'lobby'
        
        # Get user info
        user = asyncio.run_coroutine_threadsafe(
            UserRepository.get_by_telegram_id(user_id),
            asyncio.get_event_loop()
        ).result()
        
        # Send authentication success
        emit('authenticated', {
            'success': True,
            'user_id': user_id,
            'username': user.get('username') if user else None,
            'balance': float(user.get('balance', 0)) if user else 0,
            'game_status': actual_game_room.status.value,
            'round_id': actual_game_room.current_round_id,
            'round_number': actual_game_room.round_number,
            'timer': actual_game_room.remaining if actual_game_room.status == GamePhase.SELECTION else 0,
            'called_numbers': actual_game_room.called_numbers,
            'selected_count': cartela_manager.get_selected_count(),
            'user_selected_count': cartela_manager.get_user_selected_count(user_id),
            'max_cartelas': config.MAX_CARTELAS,
            'cartela_price': config.CARTELA_PRICE
        })
        
        logger.info(f"Client authenticated: {session_id} -> user {user_id}")
    
    # ==================== GAME ACTION HANDLERS ====================
    
    @socketio.on('select_cartelas')
    def handle_select_cartelas(data: Dict):
        """
        Handle cartela selection from client.
        
        Expected data:
            {
                "cartela_ids": [1, 2, 3, 4]
            }
        """
        session_id = request.sid
        user_id = connected_clients.get(session_id)
        
        if not user_id:
            emit('error', {'error': 'Not authenticated'})
            return
        
        cartela_ids = data.get('cartela_ids', [])
        
        if not cartela_ids:
            emit('select_error', {'error': 'No cartelas selected'})
            return
        
        # Run async operation
        result = asyncio.run_coroutine_threadsafe(
            actual_game_room.handle_select_cartelas(user_id, cartela_ids),
            asyncio.get_event_loop()
        ).result()
        
        if result.get('success'):
            emit('select_success', {
                'selected': result.get('selected', []),
                'failed': result.get('failed', []),
                'total_selected': result.get('total_selected', 0),
                'total_cost': result.get('total_cost', 0),
                'new_balance': result.get('new_balance', 0),
                'user_selected_count': result.get('user_selected_count', 0),
                'global_selected_count': result.get('global_selected_count', 0)
            })
        else:
            emit('select_error', {
                'error': result.get('error'),
                'code': result.get('code'),
                'balance': result.get('balance'),
                'required': result.get('required')
            })
    
    @socketio.on('unselect_cartelas')
    def handle_unselect_cartelas(data: Dict):
        """
        Handle cartela unselection from client.
        
        Expected data:
            {
                "cartela_ids": [1, 2]
            }
        """
        session_id = request.sid
        user_id = connected_clients.get(session_id)
        
        if not user_id:
            emit('error', {'error': 'Not authenticated'})
            return
        
        cartela_ids = data.get('cartela_ids', [])
        
        if not cartela_ids:
            emit('unselect_error', {'error': 'No cartelas specified'})
            return
        
        # Run async operation
        result = asyncio.run_coroutine_threadsafe(
            actual_game_room.handle_unselect_cartelas(user_id, cartela_ids),
            asyncio.get_event_loop()
        ).result()
        
        if result.get('success'):
            emit('unselect_success', {
                'unselected': result.get('unselected', []),
                'failed': result.get('failed', []),
                'new_balance': result.get('new_balance', 0),
                'user_selected_count': result.get('user_selected_count', 0)
            })
        else:
            emit('unselect_error', {
                'error': result.get('error'),
                'code': result.get('code')
            })
    
    # ==================== INFO REQUEST HANDLERS ====================
    
    @socketio.on('get_game_state')
    def handle_get_game_state():
        """Send current game state to client"""
        session_id = request.sid
        user_id = connected_clients.get(session_id)
        
        state = actual_game_room.get_state()
        
        if user_id:
            state['user_selected_count'] = cartela_manager.get_user_selected_count(user_id)
            state['user_cartelas'] = list(cartela_manager.get_user_cartelas(user_id))
        
        emit('game_state', state)
    
    @socketio.on('get_cartelas')
    def handle_get_cartelas(data: Dict):
        """
        Get cartelas with pagination.
        
        Expected data:
            {
                "page": 1,
                "limit": 100,
                "include_status": true
            }
        """
        session_id = request.sid
        user_id = connected_clients.get(session_id)
        
        page = data.get('page', 1)
        limit = min(data.get('limit', 100), 200)
        include_status = data.get('include_status', True)
        
        start = (page - 1) * limit
        
        if include_status:
            cartelas = cartela_manager.get_cartelas_batch(start, limit, include_taken_status=True)
            
            # Add 'is_mine' flag for authenticated users
            if user_id:
                for cartela in cartelas:
                    cartela['is_mine'] = cartela_manager.is_cartela_mine(user_id, cartela['id'])
        else:
            cartelas = cartela_manager.get_cartelas_batch(start, limit, include_taken_status=False)
        
        total = cartela_manager.get_total_cartelas()
        
        emit('cartelas_response', {
            'cartelas': cartelas,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            },
            'user_selected_count': cartela_manager.get_user_selected_count(user_id) if user_id else 0,
            'global_selected_count': cartela_manager.get_selected_count(),
            'max_cartelas': config.MAX_CARTELAS
        })
    
    @socketio.on('get_cartela_detail')
    def handle_get_cartela_detail(data: Dict):
        """
        Get detailed information for a specific cartela.
        
        Expected data:
            {
                "cartela_id": 123
            }
        """
        session_id = request.sid
        user_id = connected_clients.get(session_id)
        
        cartela_id = data.get('cartela_id')
        
        if not cartela_id:
            emit('error', {'error': 'Missing cartela_id'})
            return
        
        cartela = cartela_manager.get_cartela_with_status(cartela_id, user_id)
        
        if cartela:
            emit('cartela_detail', cartela)
        else:
            emit('error', {'error': 'Cartela not found'})
    
    @socketio.on('get_leaderboard')
    def handle_get_leaderboard(data: Dict):
        """
        Get leaderboard data.
        
        Expected data:
            {
                "type": "balance",  # balance, wins, games
                "limit": 10
            }
        """
        leaderboard_type = data.get('type', 'balance')
        limit = min(data.get('limit', 10), 50)
        
        # Run async operation
        if leaderboard_type == 'balance':
            leaderboard = asyncio.run_coroutine_threadsafe(
                UserRepository.get_top_users_by_balance(limit),
                asyncio.get_event_loop()
            ).result()
        elif leaderboard_type == 'wins':
            leaderboard = asyncio.run_coroutine_threadsafe(
                UserRepository.get_top_users_by_wins(limit),
                asyncio.get_event_loop()
            ).result()
        elif leaderboard_type == 'games':
            leaderboard = asyncio.run_coroutine_threadsafe(
                UserRepository.get_top_users_by_games(limit),
                asyncio.get_event_loop()
            ).result()
        else:
            emit('error', {'error': 'Invalid leaderboard type'})
            return
        
        # Format leaderboard
        formatted = []
        for idx, user in enumerate(leaderboard, 1):
            formatted.append({
                'rank': idx,
                'user_id': user['telegram_id'],
                'name': user.get('first_name') or user.get('username', 'Unknown'),
                'value': float(user.get(leaderboard_type, 0)) if leaderboard_type == 'balance' else user.get(f'total_{leaderboard_type}', 0)
            })
        
        emit('leaderboard_response', {
            'type': leaderboard_type,
            'leaderboard': formatted,
            'limit': limit
        })
    
    @socketio.on('ping')
    def handle_ping():
        """Handle ping for connection health check"""
        emit('pong', {'timestamp': asyncio.get_event_loop().time()})
    
    # ==================== ADMIN EVENT HANDLERS ====================
    
    @socketio.on('admin_force_start')
    def handle_admin_force_start(data: Dict):
        """
        Admin: Force start a new round.
        """
        session_id = request.sid
        user_id = connected_clients.get(session_id)
        
        if not user_id:
            emit('error', {'error': 'Not authenticated'})
            return
        
        # Check if user is admin
        user = asyncio.run_coroutine_threadsafe(
            UserRepository.get_by_telegram_id(user_id),
            asyncio.get_event_loop()
        ).result()
        
        if not user or not user.get('is_admin'):
            emit('error', {'error': 'Admin access required'})
            return
        
        # Run async operation
        result = asyncio.run_coroutine_threadsafe(
            actual_game_room.force_start(),
            asyncio.get_event_loop()
        ).result()
        
        if result:
            emit('admin_action_response', {'success': True, 'action': 'force_start'})
            # Broadcast to all clients
            emit('game_state', actual_game_room.get_state(), broadcast=True)
        else:
            emit('admin_action_response', {'success': False, 'action': 'force_start', 'error': 'Failed to start game'})
    
    @socketio.on('admin_force_stop')
    def handle_admin_force_stop(data: Dict):
        """
        Admin: Force stop current round.
        """
        session_id = request.sid
        user_id = connected_clients.get(session_id)
        
        if not user_id:
            emit('error', {'error': 'Not authenticated'})
            return
        
        # Check if user is admin
        user = asyncio.run_coroutine_threadsafe(
            UserRepository.get_by_telegram_id(user_id),
            asyncio.get_event_loop()
        ).result()
        
        if not user or not user.get('is_admin'):
            emit('error', {'error': 'Admin access required'})
            return
        
        # Run async operation
        result = asyncio.run_coroutine_threadsafe(
            actual_game_room.force_stop(),
            asyncio.get_event_loop()
        ).result()
        
        if result:
            emit('admin_action_response', {'success': True, 'action': 'force_stop'})
            # Broadcast to all clients
            emit('game_state', actual_game_room.get_state(), broadcast=True)
        else:
            emit('admin_action_response', {'success': False, 'action': 'force_stop', 'error': 'Failed to stop game'})


# ==================== BROADCAST FUNCTIONS ====================

async def broadcast_cartela_update(cartela_ids: List[int], user_id: int, action: str = 'select'):
    """
    Broadcast cartela selection update to all clients.
    
    Args:
        cartela_ids: list - List of cartela IDs
        user_id: int - User who made the selection
        action: str - 'select' or 'unselect'
    """
    if not bingo_room.socketio:
        return
    
    data = {
        'action': action,
        'cartela_ids': cartela_ids,
        'user_id': user_id,
        'taken_by': {cid: user_id for cid in cartela_ids}
    }
    
    await bingo_room.socketio.emit('cartela_update', data, room=f"game_room_{bingo_room.current_round_id}")


async def broadcast_winner_announcement(winners: List[Dict], prize_pool: float):
    """
    Broadcast winner announcement to all clients.
    
    Args:
        winners: list - List of winner dictionaries
        prize_pool: float - Total prize pool
    """
    if not bingo_room.socketio:
        return
    
    data = {
        'winners': winners,
        'prize_pool': prize_pool,
        'next_round_delay': bingo_room.next_round_delay // 1000
    }
    
    await bingo_room.socketio.emit('game_ended', data, room=f"game_room_{bingo_room.current_round_id}")


# ==================== EXPORTS ====================

__all__ = [
    'register_socket_events',
    'broadcast_cartela_update',
    'broadcast_winner_announcement',
    'connected_clients',
]