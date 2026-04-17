# telegram-bot/bot/game_engine/bingo_room.py
# Estif Bingo 24/7 - Bingo Game Engine
# Real-time multiplayer bingo game manager with WebSocket support

import asyncio
import random
import json
from datetime import datetime
from typing import Dict, List, Set, Optional, Any, Tuple
from enum import Enum

from flask_socketio import SocketIO, emit, join_room, leave_room

from bot.game_engine.cartela_manager import cartela_manager
from bot.game_engine.number_caller import NumberCaller
from bot.game_engine.winner_detector import WinnerDetector
from bot.game_engine.payout_calculator import PayoutCalculator
from bot.db.repository import GameRepository, UserRepository, TransactionRepository
from bot.api.balance_ops import get_balance, deduct_balance, add_balance
from bot.config import config
from bot.utils.logger import logger
from bot.texts.emojis import get_emoji


class GamePhase(Enum):
    """Game phase states"""
    IDLE = "idle"
    SELECTION = "selection"
    DRAWING = "drawing"
    ENDED = "ended"


class BingoRoom:
    """
    Real-time multiplayer bingo game engine.
    Manages game state, timer, number calling, winner detection, and payouts.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the bingo room"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            
            # Game state
            self.socketio: Optional[SocketIO] = None
            self.status: GamePhase = GamePhase.IDLE
            self.current_round_id: Optional[int] = None
            self.round_number: int = 0
            
            # Timer
            self.selection_time: int = config.SELECTION_TIME
            self.remaining: int = 0
            self.timer_task: Optional[asyncio.Task] = None
            
            # Number caller
            self.number_caller: Optional[NumberCaller] = None
            self.called_numbers: List[int] = []
            self.draw_task: Optional[asyncio.Task] = None
            
            # Winner tracking
            self.winners: List[Dict] = []
            self.winner_detector = WinnerDetector()
            self.payout_calculator = PayoutCalculator()
            
            # Connected players
            self.connected_players: Dict[str, int] = {}  # session_id -> user_id
            self.player_sessions: Dict[int, str] = {}    # user_id -> session_id
            self.player_rooms: Dict[int, str] = {}       # user_id -> room_name
            
            # Game settings
            self.win_percentage: int = config.DEFAULT_WIN_PERCENTAGE
            self.draw_interval: int = config.DRAW_INTERVAL
            self.next_round_delay: int = config.NEXT_ROUND_DELAY
            
            logger.info("BingoRoom initialized")
    
    # ==================== INITIALIZATION ====================
    
    def init(self, socketio: SocketIO):
        """Initialize with SocketIO instance"""
        self.socketio = socketio
        logger.info("BingoRoom connected to SocketIO")
    
    # ==================== GAME STATE MANAGEMENT ====================
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current game state for clients
        
        Returns:
            dict: Current game state
        """
        return {
            'status': self.status.value,
            'phase': self.status.value,
            'timer': self.remaining if self.status == GamePhase.SELECTION else 0,
            'called_numbers': self.called_numbers,
            'last_number': self.called_numbers[-1] if self.called_numbers else None,
            'total_called': len(self.called_numbers),
            'selected_count': cartela_manager.get_selected_count(),
            'players_count': len(self.connected_players),
            'round_id': self.current_round_id,
            'round_number': self.round_number,
            'win_percentage': self.win_percentage
        }
    
    async def update_win_percentage(self):
        """Update win percentage from database"""
        self.win_percentage = await GameRepository.get_win_percentage()
        logger.info(f"Win percentage updated to {self.win_percentage}%")
    
    # ==================== PLAYER MANAGEMENT ====================
    
    def register_player(self, session_id: str, user_id: int) -> str:
        """
        Register a connected player
        
        Args:
            session_id: str - SocketIO session ID
            user_id: int - User's Telegram ID
        
        Returns:
            str: Room name for the player
        """
        room_name = f"game_room_{self.current_round_id}" if self.current_round_id else "lobby"
        
        self.connected_players[session_id] = user_id
        self.player_sessions[user_id] = session_id
        self.player_rooms[user_id] = room_name
        
        # Join room
        if self.socketio:
            join_room(room_name, sid=session_id)
        
        logger.info(f"Player {user_id} registered, session: {session_id}, room: {room_name}")
        
        return room_name
    
    def unregister_player(self, session_id: str):
        """Unregister a disconnected player"""
        user_id = self.connected_players.get(session_id)
        if user_id:
            # Leave room
            if self.socketio and user_id in self.player_rooms:
                leave_room(self.player_rooms[user_id], sid=session_id)
            
            del self.connected_players[session_id]
            del self.player_sessions[user_id]
            if user_id in self.player_rooms:
                del self.player_rooms[user_id]
            
            logger.info(f"Player {user_id} unregistered")
    
    def get_player_count(self) -> int:
        """Get number of connected players"""
        return len(self.connected_players)
    
    # ==================== BROADCAST METHODS ====================
    
    async def broadcast_state(self):
        """Broadcast current game state to all players"""
        if not self.socketio:
            return
        
        state = self.get_state()
        await self.socketio.emit('game_state', state, room='lobby')
        if self.current_round_id:
            await self.socketio.emit('game_state', state, room=f"game_room_{self.current_round_id}")
    
    async def broadcast_timer(self, remaining: int):
        """Broadcast timer update"""
        if not self.socketio:
            return
        
        data = {
            'remaining': remaining,
            'is_blinking': remaining <= 10
        }
        await self.socketio.emit('timer_update', data, room=f"game_room_{self.current_round_id}")
    
    async def broadcast_number_called(self, number: int, marked_cells: Dict[int, List[Dict]]):
        """
        Broadcast a called number and marked cells to all players
        
        Args:
            number: int - Called number
            marked_cells: dict - {user_id: list of marked cells}
        """
        if not self.socketio:
            return
        
        data = {
            'number': number,
            'marked_cells': marked_cells,
            'called_numbers': self.called_numbers,
            'total_called': len(self.called_numbers)
        }
        await self.socketio.emit('number_called', data, room=f"game_room_{self.current_round_id}")
    
    async def broadcast_cartela_update(self, cartela_ids: List[int], user_id: int, action: str = 'select'):
        """
        Broadcast cartela selection update
        
        Args:
            cartela_ids: list - List of cartela IDs
            user_id: int - User who made the selection
            action: str - 'select' or 'unselect'
        """
        if not self.socketio:
            return
        
        data = {
            'action': action,
            'cartela_ids': cartela_ids,
            'user_id': user_id,
            'taken_by': {cid: user_id for cid in cartela_ids}
        }
        await self.socketio.emit('cartela_update', data, room=f"game_room_{self.current_round_id}")
    
    async def broadcast_winners(self, winners: List[Dict], prize_pool: float):
        """
        Broadcast winner information
        
        Args:
            winners: list - List of winner dictionaries
            prize_pool: float - Total prize pool
        """
        if not self.socketio:
            return
        
        data = {
            'winners': winners,
            'prize_pool': prize_pool,
            'next_round_delay': self.next_round_delay // 1000
        }
        await self.socketio.emit('game_ended', data, room=f"game_room_{self.current_round_id}")
    
    # ==================== CARTELA SELECTION HANDLER ====================
    
    async def handle_select_cartelas(self, user_id: int, cartela_ids: List[int]) -> Dict[str, Any]:
        """
        Handle cartela selection from a player
        
        Args:
            user_id: int - User's Telegram ID
            cartela_ids: list - List of cartela IDs to select
        
        Returns:
            dict: Selection result
        """
        # Check if game is in selection phase
        if self.status != GamePhase.SELECTION:
            return {'success': False, 'error': 'Game is not in selection phase', 'code': 'wrong_phase'}
        
        # Check if timer still running
        if self.remaining <= 0:
            return {'success': False, 'error': 'Selection time has ended', 'code': 'time_ended'}
        
        # Check max cartelas limit
        max_cartelas = getattr(config, 'MAX_CARTELAS', 4)
        if len(cartela_ids) > max_cartelas:
            return {
                'success': False,
                'error': f'Maximum {max_cartelas} cartelas allowed',
                'code': 'max_limit'
            }
        
        # Validate selections
        validation = cartela_manager.validate_selection(user_id, cartela_ids)
        if not validation['valid']:
            return {'success': False, 'error': validation['error'], 'code': validation['code']}
        
        # Check balance
        total_cost = len(cartela_ids) * config.CARTELA_PRICE
        balance = await get_balance(user_id)
        
        if balance < total_cost:
            return {
                'success': False,
                'error': 'Insufficient balance',
                'code': 'insufficient_balance',
                'balance': balance,
                'required': total_cost
            }
        
        # Deduct balance
        deduct_success = await deduct_balance(
            telegram_id=user_id,
            amount=total_cost,
            reason="cartela_purchase",
            metadata={
                'cartela_ids': cartela_ids,
                'round_id': self.current_round_id,
                'count': len(cartela_ids)
            }
        )
        
        if not deduct_success:
            return {'success': False, 'error': 'Failed to deduct balance', 'code': 'deduct_failed'}
        
        # Select cartelas
        result = cartela_manager.bulk_select_cartelas(user_id, cartela_ids)
        
        if result['success']:
            # Record selections in database
            for cartela_id in result['success']:
                await GameRepository.create_selection({
                    'round_id': self.current_round_id,
                    'user_id': user_id,
                    'cartela_id': cartela_id,
                    'amount': config.CARTELA_PRICE
                })
            
            # Broadcast update to all players
            await self.broadcast_cartela_update(result['success'], user_id, 'select')
        
        # Get updated balance
        new_balance = await get_balance(user_id)
        
        return {
            'success': True,
            'selected': result['success'],
            'failed': result['failed'],
            'total_selected': len(result['success']),
            'total_cost': total_cost,
            'new_balance': new_balance,
            'user_selected_count': cartela_manager.get_user_selected_count(user_id),
            'global_selected_count': cartela_manager.get_selected_count()
        }
    
    async def handle_unselect_cartelas(self, user_id: int, cartela_ids: List[int]) -> Dict[str, Any]:
        """
        Handle cartela unselection from a player
        
        Args:
            user_id: int - User's Telegram ID
            cartela_ids: list - List of cartela IDs to unselect
        
        Returns:
            dict: Unselection result
        """
        # Check if game is in selection phase
        if self.status != GamePhase.SELECTION:
            return {'success': False, 'error': 'Cannot unselect after selection phase', 'code': 'wrong_phase'}
        
        unselected = []
        failed = []
        
        for cartela_id in cartela_ids:
            if cartela_manager.is_cartela_mine(user_id, cartela_id):
                cartela_manager.unselect_cartela(user_id, cartela_id)
                unselected.append(cartela_id)
                
                # Refund balance
                await add_balance(
                    telegram_id=user_id,
                    amount=config.CARTELA_PRICE,
                    reason="cartela_unselected",
                    metadata={'cartela_id': cartela_id, 'round_id': self.current_round_id}
                )
            else:
                failed.append({'cartela_id': cartela_id, 'reason': 'Not your cartela'})
        
        # Broadcast update
        if unselected:
            await self.broadcast_cartela_update(unselected, user_id, 'unselect')
        
        new_balance = await get_balance(user_id)
        
        return {
            'success': True,
            'unselected': unselected,
            'failed': failed,
            'new_balance': new_balance,
            'user_selected_count': cartela_manager.get_user_selected_count(user_id)
        }
    
    # ==================== GAME LOOP ====================
    
    async def start(self):
        """Start the game loop"""
        logger.info("Starting bingo game loop")
        asyncio.create_task(self._game_loop())
    
    async def _game_loop(self):
        """Main game loop - runs continuously"""
        while True:
            await self._selection_phase()
            await self._drawing_phase()
            await self._end_phase()
            await asyncio.sleep(1)
    
    async def _selection_phase(self):
        """Phase 1: Cartela selection (50 seconds)"""
        # Start new round
        self.status = GamePhase.SELECTION
        self.round_number += 1
        self.called_numbers = []
        self.winners = []
        
        # Create round in database
        self.current_round_id = await GameRepository.create_round({
            'round_number': self.round_number,
            'status': 'selection',
            'start_time': datetime.utcnow()
        })
        
        # Reset cartela manager
        cartela_manager.reset_round(self.current_round_id)
        
        # Update win percentage
        await self.update_win_percentage()
        
        # Broadcast initial state
        await self.broadcast_state()
        
        # Start timer
        self.remaining = self.selection_time
        await self._run_timer()
        
        # Selection phase ended
        self.status = GamePhase.DRAWING
        
        # Update round in database
        await GameRepository.update_round(self.current_round_id, {
            'status': 'drawing',
            'selection_end_time': datetime.utcnow(),
            'total_cartelas': cartela_manager.get_selected_count(),
            'total_players': len(cartela_manager.selected_by)
        })
        
        logger.info(f"Selection phase ended. Round {self.round_number}: {cartela_manager.get_selected_count()} cartelas selected by {len(cartela_manager.selected_by)} players")
    
    async def _run_timer(self):
        """Run the countdown timer"""
        while self.remaining > 0 and self.status == GamePhase.SELECTION:
            await self.broadcast_timer(self.remaining)
            await asyncio.sleep(1)
            self.remaining -= 1
        
        if self.status == GamePhase.SELECTION:
            self.remaining = 0
            await self.broadcast_timer(0)
    
    async def _drawing_phase(self):
        """Phase 2: Number drawing until winner found"""
        # Check if any cartelas were selected
        if cartela_manager.get_selected_count() == 0:
            logger.info(f"No cartelas selected in round {self.round_number}, skipping drawing phase")
            await asyncio.sleep(2)
            return
        
        # Initialize number caller
        self.number_caller = NumberCaller()
        self.number_caller.reset()
        
        # Get all selected cartelas with their owners
        selected_cartelas = cartela_manager.get_all_selected_cartelas()
        
        # Get user cartelas for winner detection
        user_cartelas = {}
        for user_id in cartela_manager.selected_by.keys():
            user_cartelas[user_id] = cartela_manager.get_user_cartelas_with_grids(user_id)
        
        # Draw numbers until winner found
        while self.status == GamePhase.DRAWING:
            # Draw next number
            number = self.number_caller.draw_next()
            
            if number is None:
                # No more numbers - no winner this round
                logger.info(f"No winner in round {self.round_number}, all numbers drawn")
                break
            
            self.called_numbers.append(number)
            
            # Mark numbers on all players' cartelas and check for winners
            winners = await self._process_number_and_check_winners(number, user_cartelas)
            
            if winners:
                # Winners found!
                await self._process_winners(winners)
                break
            
            # Broadcast the number
            await self._broadcast_number_with_marked_cells(number, user_cartelas)
            
            # Wait before next draw
            await asyncio.sleep(self.draw_interval / 1000)
    
    async def _process_number_and_check_winners(self, number: int, user_cartelas: Dict[int, List[Dict]]) -> List[Dict]:
        """
        Process a called number and check for winners
        
        Args:
            number: int - Called number
            user_cartelas: dict - User cartelas mapping
        
        Returns:
            list: List of winners found
        """
        winners = []
        
        for user_id, cartelas in user_cartelas.items():
            for cartela in cartelas:
                grid = cartela['grid']
                cartela_id = cartela['id']
                
                # Check if number is in this cartela
                if self._is_number_in_grid(number, grid):
                    # Check if this creates a win
                    win_pattern = self.winner_detector.check_win(grid, self.called_numbers)
                    
                    if win_pattern:
                        winners.append({
                            'user_id': user_id,
                            'cartela_id': cartela_id,
                            'grid': grid,
                            'pattern': win_pattern,
                            'numbers_until_win': len(self.called_numbers)
                        })
        
        return winners
    
    def _is_number_in_grid(self, number: int, grid: List[List[int]]) -> bool:
        """Check if a number exists in the grid"""
        for col in range(5):
            for row in range(5):
                if grid[col][row] == number:
                    return True
        return False
    
    async def _broadcast_number_with_marked_cells(self, number: int, user_cartelas: Dict[int, List[Dict]]):
        """
        Broadcast the called number with marked cell information for each player
        
        Args:
            number: int - Called number
            user_cartelas: dict - User cartelas mapping
        """
        if not self.socketio:
            return
        
        # For each player, find which of their cartelas have this number
        marked_cells_by_user = {}
        
        for user_id, cartelas in user_cartelas.items():
            marked_cells = []
            for cartela in cartelas:
                grid = cartela['grid']
                cartela_id = cartela['id']
                
                for col in range(5):
                    for row in range(5):
                        if grid[col][row] == number:
                            marked_cells.append({
                                'cartela_id': cartela_id,
                                'col': col,
                                'row': row,
                                'value': number
                            })
            
            if marked_cells:
                marked_cells_by_user[user_id] = marked_cells
        
        # Send individual updates to each player
        for user_id, marked_cells in marked_cells_by_user.items():
            session_id = self.player_sessions.get(user_id)
            if session_id:
                data = {
                    'number': number,
                    'marked_cells': marked_cells,
                    'called_numbers': self.called_numbers,
                    'total_called': len(self.called_numbers)
                }
                await self.socketio.emit('number_called', data, room=session_id)
    
    async def _process_winners(self, winners: List[Dict]):
        """
        Process winners and distribute payouts
        
        Args:
            winners: list - List of winner dictionaries
        """
        self.status = GamePhase.ENDED
        
        # Calculate prize pool
        total_cartelas = cartela_manager.get_selected_count()
        total_bets = total_cartelas * config.CARTELA_PRICE
        prize_pool = total_bets * self.win_percentage // 100
        
        # Calculate individual payouts
        win_amount = prize_pool // len(winners) if len(winners) > 0 else 0
        
        # Update winner records
        for winner in winners:
            winner['win_amount'] = win_amount
            
            # Add balance to winner
            await add_balance(
                telegram_id=winner['user_id'],
                amount=win_amount,
                reason="game_win",
                metadata={
                    'round_id': self.current_round_id,
                    'round_number': self.round_number,
                    'cartela_id': winner['cartela_id'],
                    'pattern': winner['pattern'],
                    'total_winners': len(winners)
                }
            )
            
            # Record transaction
            await TransactionRepository.create({
                'user_id': winner['user_id'],
                'type': 'win',
                'amount': win_amount,
                'reference_id': f"round_{self.current_round_id}",
                'metadata': {
                    'round_id': self.current_round_id,
                    'pattern': winner['pattern'],
                    'total_winners': len(winners)
                }
            })
            
            logger.info(f"Winner: User {winner['user_id']} won {win_amount} ETB with cartela {winner['cartela_id']}")
        
        # Update round in database
        await GameRepository.end_round(self.current_round_id, winners, prize_pool)
        
        # Broadcast winners
        await self.broadcast_winners(winners, prize_pool)
        
        logger.info(f"Round {self.round_number} ended with {len(winners)} winners. Prize pool: {prize_pool} ETB")
    
    async def _end_phase(self):
        """Phase 3: Round end with delay before next round"""
        self.status = GamePhase.ENDED
        
        # Wait before starting new round
        await asyncio.sleep(self.next_round_delay / 1000)
        
        # Reset for next round
        self.current_round_id = None
    
    # ==================== ADMIN CONTROLS ====================
    
    async def force_start(self) -> bool:
        """Force start a new round (admin)"""
        if self.status == GamePhase.SELECTION:
            # Cancel current timer
            self.remaining = 0
            await self.broadcast_timer(0)
            
            # Force end selection phase
            self.status = GamePhase.DRAWING
            asyncio.create_task(self._drawing_phase())
            return True
        elif self.status == GamePhase.IDLE or self.status == GamePhase.ENDED:
            # Start new round immediately
            asyncio.create_task(self._selection_phase())
            return True
        
        return False
    
    async def force_stop(self) -> bool:
        """Force stop current round (admin)"""
        if self.status in [GamePhase.SELECTION, GamePhase.DRAWING]:
            self.status = GamePhase.ENDED
            
            # Cancel tasks
            if self.timer_task:
                self.timer_task.cancel()
            if self.draw_task:
                self.draw_task.cancel()
            
            # Update round in database
            if self.current_round_id:
                await GameRepository.update_round(self.current_round_id, {
                    'status': 'ended',
                    'end_time': datetime.utcnow()
                })
            
            await self.broadcast_state()
            logger.info(f"Round {self.round_number} force stopped by admin")
            return True
        
        return False
    
    async def reset_game(self):
        """Reset entire game state (admin)"""
        self.status = GamePhase.IDLE
        self.current_round_id = None
        self.called_numbers = []
        self.winners = []
        cartela_manager.reset_round(None)
        logger.info("Game state reset by admin")
    
    # ================= = UTILITY METHODS ====================
    
    def get_current_winners(self) -> List[Dict]:
        """Get current round winners"""
        return self.winners


# ==================== SINGLETON INSTANCE ====================

bingo_room = BingoRoom()


# ==================== EXPORTS ====================

__all__ = [
    'BingoRoom',
    'GamePhase',
    'bingo_room',
]