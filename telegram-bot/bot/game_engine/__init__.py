# telegram-bot/bot/game_engine/__init__.py
# Estif Bingo 24/7 - Game Engine Package
# Initializes the real-time multiplayer bingo game engine

import logging
from typing import Optional

from bot.game_engine.bingo_room import BingoRoom, GamePhase, bingo_room
from bot.game_engine.cartela_manager import CartelaManager, cartela_manager
from bot.game_engine.number_caller import NumberCaller, WeightedNumberCaller, create_number_caller
from bot.game_engine.winner_detector import WinnerDetector, FastWinnerDetector, WinPattern, create_winner_detector
from bot.game_engine.payout_calculator import PayoutCalculator, create_payout_calculator
from bot.game_engine.events import (
    register_socket_events,
    broadcast_cartela_update,
    broadcast_winner_announcement,
    connected_clients,
)

from bot.utils.logger import logger

# ==================== PACKAGE INFORMATION ====================

__version__ = "1.0.0"
__author__ = "Estif Bingo Team"
__description__ = "Real-time multiplayer bingo game engine for Telegram Bot"


# ==================== INITIALIZATION FUNCTION ====================

async def init_game_engine(socketio=None) -> dict:
    """
    Initialize the game engine components.
    
    Args:
        socketio: Flask-SocketIO instance (optional)
    
    Returns:
        dict: Initialization results
    """
    results = {
        'bingo_room_initialized': False,
        'cartela_manager_initialized': False,
        'events_registered': False,
        'errors': []
    }
    
    try:
        # Initialize cartela manager (loads cartelas)
        if cartela_manager.get_total_cartelas() > 0:
            results['cartela_manager_initialized'] = True
            logger.info(f"Cartela manager initialized with {cartela_manager.get_total_cartelas()} cartelas")
        else:
            results['errors'].append("Cartela manager has no cartelas loaded")
        
        # Initialize bingo room with socketio
        if socketio:
            bingo_room.init(socketio)
            results['bingo_room_initialized'] = True
            logger.info("Bingo room initialized with SocketIO")
        
        # Start game loop
        if socketio:
            import asyncio
            asyncio.create_task(bingo_room.start())
            logger.info("Game loop started")
        
    except Exception as e:
        results['errors'].append(f"Game engine initialization failed: {e}")
        logger.error(f"Game engine initialization failed: {e}")
    
    return results


async def shutdown_game_engine():
    """
    Shutdown the game engine gracefully.
    """
    try:
        # Force stop any ongoing game
        if bingo_room.status != GamePhase.IDLE:
            await bingo_room.force_stop()
        
        logger.info("Game engine shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down game engine: {e}")


def get_game_engine_status() -> dict:
    """
    Get the current status of the game engine.
    
    Returns:
        dict: Game engine status
    """
    return {
        'bingo_room': {
            'status': bingo_room.status.value,
            'round_id': bingo_room.current_round_id,
            'round_number': bingo_room.round_number,
            'players_count': bingo_room.get_player_count(),
            'selected_count': cartela_manager.get_selected_count(),
            'called_numbers_count': len(bingo_room.called_numbers)
        },
        'cartela_manager': {
            'total_cartelas': cartela_manager.get_total_cartelas(),
            'selected_count': cartela_manager.get_selected_count(),
            'available_count': cartela_manager.get_available_count(),
            'unique_players': len(cartela_manager.selected_by)
        },
        'connected_clients': len(connected_clients)
    }


# ==================== CONVENIENCE RE-EXPORTS ====================

# Re-export commonly used classes and functions
__all__ = [
    # Core classes
    'BingoRoom',
    'GamePhase',
    'CartelaManager',
    'NumberCaller',
    'WeightedNumberCaller',
    'WinnerDetector',
    'FastWinnerDetector',
    'WinPattern',
    'PayoutCalculator',
    
    # Singleton instances
    'bingo_room',
    'cartela_manager',
    
    # Factory functions
    'create_number_caller',
    'create_winner_detector',
    'create_payout_calculator',
    
    # Event functions
    'register_socket_events',
    'broadcast_cartela_update',
    'broadcast_winner_announcement',
    'connected_clients',
    
    # Initialization functions
    'init_game_engine',
    'shutdown_game_engine',
    'get_game_engine_status',
    
    # Version info
    '__version__',
    '__author__',
    '__description__',
]


# ==================== LOGGER ====================

logger.info(f"Game engine package v{__version__} initialized")