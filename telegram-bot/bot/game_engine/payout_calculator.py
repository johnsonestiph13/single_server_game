# telegram-bot/bot/game_engine/payout_calculator.py
# Estif Bingo 24/7 - Payout Calculator
# Calculates and distributes payouts to winners based on win percentage and prize pool

import logging
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP

from bot.config import config
from bot.db.repository import GameRepository, TransactionRepository, AuditRepository
from bot.api.balance_ops import add_balance
from bot.utils.logger import logger


class PayoutCalculator:
    """
    Calculates and distributes payouts for bingo game winners.
    Handles prize pool calculation, split among multiple winners, and balance updates.
    """
    
    def __init__(self):
        """Initialize the payout calculator"""
        self.cartela_price = config.CARTELA_PRICE
        self.default_win_percentage = config.DEFAULT_WIN_PERCENTAGE
        logger.info("PayoutCalculator initialized")
    
    # ==================== PRIZE POOL CALCULATION ====================
    
    def calculate_prize_pool(
        self,
        total_cartelas_selected: int,
        win_percentage: Optional[int] = None
    ) -> Tuple[float, float]:
        """
        Calculate the total prize pool based on selected cartelas and win percentage.
        
        Args:
            total_cartelas_selected: int - Total number of cartelas selected in the round
            win_percentage: int - Win percentage (default: from config)
        
        Returns:
            tuple: (total_bets, prize_pool)
        """
        if win_percentage is None:
            win_percentage = self.default_win_percentage
        
        total_bets = total_cartelas_selected * self.cartela_price
        prize_pool = total_bets * win_percentage / 100
        
        # Round to 2 decimal places
        prize_pool = float(Decimal(str(prize_pool)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        
        logger.debug(f"Prize pool calculation: {total_cartelas_selected} cartelas × {self.cartela_price} = {total_bets} total bets, {win_percentage}% win rate = {prize_pool} prize pool")
        
        return total_bets, prize_pool
    
    def calculate_house_edge(self, total_bets: float, prize_pool: float) -> float:
        """
        Calculate the house edge (commission) for the round.
        
        Args:
            total_bets: float - Total amount bet
            prize_pool: float - Total prize pool paid out
        
        Returns:
            float: House edge amount
        """
        house_edge = total_bets - prize_pool
        return max(0, house_edge)
    
    # ==================== WINNER PAYOUT CALCULATION ====================
    
    def calculate_winner_payouts(
        self,
        winners: List[Dict],
        total_cartelas_selected: int,
        win_percentage: Optional[int] = None
    ) -> List[Dict]:
        """
        Calculate payout amounts for each winner.
        
        Args:
            winners: list - List of winner dictionaries with user_id and cartela_id
            total_cartelas_selected: int - Total cartelas selected in the round
            win_percentage: int - Win percentage for the round
        
        Returns:
            list: Winners with calculated payout amounts
        """
        if not winners:
            return []
        
        # Calculate prize pool
        total_bets, prize_pool = self.calculate_prize_pool(total_cartelas_selected, win_percentage)
        
        # Split prize pool among winners
        payout_per_winner = prize_pool / len(winners)
        
        # Round to 2 decimal places
        payout_per_winner = float(Decimal(str(payout_per_winner)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        
        # Distribute to winners
        result = []
        for winner in winners:
            winner_copy = winner.copy()
            winner_copy['payout_amount'] = payout_per_winner
            winner_copy['total_bets'] = total_bets
            winner_copy['prize_pool'] = prize_pool
            winner_copy['total_winners'] = len(winners)
            result.append(winner_copy)
        
        logger.info(f"Calculated payouts: {len(winners)} winners, {prize_pool} prize pool, {payout_per_winner} per winner")
        
        return result
    
    def calculate_payout_for_single_winner(
        self,
        total_cartelas_selected: int,
        win_percentage: Optional[int] = None
    ) -> float:
        """
        Calculate payout for a single winner.
        
        Args:
            total_cartelas_selected: int - Total cartelas selected
            win_percentage: int - Win percentage
        
        Returns:
            float: Payout amount for the single winner
        """
        _, prize_pool = self.calculate_prize_pool(total_cartelas_selected, win_percentage)
        return prize_pool
    
    def calculate_payout_for_multiple_winners(
        self,
        total_cartelas_selected: int,
        num_winners: int,
        win_percentage: Optional[int] = None
    ) -> float:
        """
        Calculate payout per winner when there are multiple winners.
        
        Args:
            total_cartelas_selected: int - Total cartelas selected
            num_winners: int - Number of winners
            win_percentage: int - Win percentage
        
        Returns:
            float: Payout amount per winner
        """
        _, prize_pool = self.calculate_prize_pool(total_cartelas_selected, win_percentage)
        return prize_pool / num_winners if num_winners > 0 else 0
    
    # ==================== PAYOUT DISTRIBUTION ====================
    
    async def distribute_payouts(
        self,
        winners: List[Dict],
        round_id: int,
        round_number: int,
        win_percentage: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Distribute payouts to winners and update database.
        
        Args:
            winners: list - List of winner dictionaries
            round_id: int - Current round ID
            round_number: int - Current round number
            win_percentage: int - Win percentage for the round
        
        Returns:
            dict: Distribution results
        """
        if not winners:
            return {
                'success': False,
                'message': 'No winners to distribute',
                'total_paid': 0,
                'winners_count': 0
            }
        
        # Get total cartelas selected
        from bot.game_engine.cartela_manager import cartela_manager
        total_cartelas = cartela_manager.get_selected_count()
        
        # Calculate payouts
        payouts = self.calculate_winner_payouts(winners, total_cartelas, win_percentage)
        
        total_paid = 0
        distributed_winners = []
        
        for payout_info in payouts:
            user_id = payout_info['user_id']
            payout_amount = payout_info['payout_amount']
            
            # Add balance to winner
            success = await add_balance(
                telegram_id=user_id,
                amount=payout_amount,
                reason="game_win",
                metadata={
                    'round_id': round_id,
                    'round_number': round_number,
                    'cartela_id': payout_info.get('cartela_id'),
                    'pattern': payout_info.get('pattern'),
                    'total_winners': len(winners)
                },
                reference_id=f"round_{round_id}"
            )
            
            if success:
                total_paid += payout_amount
                distributed_winners.append({
                    'user_id': user_id,
                    'amount': payout_amount,
                    'cartela_id': payout_info.get('cartela_id'),
                    'pattern': payout_info.get('pattern')
                })
                
                logger.info(f"Paid {payout_amount} ETB to user {user_id} for round {round_number}")
            else:
                logger.error(f"Failed to pay {payout_amount} ETB to user {user_id} for round {round_number}")
        
        # Update round with winners
        await GameRepository.end_round(round_id, distributed_winners, total_paid)
        
        # Audit log for payouts
        await AuditRepository.log(
            user_id=0,  # System action
            action="payout_distributed",
            entity_type="round",
            entity_id=str(round_id),
            new_value={
                'round_number': round_number,
                'total_paid': total_paid,
                'winners_count': len(distributed_winners),
                'total_cartelas': total_cartelas
            }
        )
        
        return {
            'success': True,
            'message': f'Distributed {total_paid} ETB to {len(distributed_winners)} winners',
            'total_paid': total_paid,
            'winners_count': len(distributed_winners),
            'winners': distributed_winners
        }
    
    # ==================== WIN VERIFICATION ====================
    
    def verify_payout_amount(
        self,
        total_cartelas_selected: int,
        num_winners: int,
        actual_payout: float,
        win_percentage: Optional[int] = None
    ) -> bool:
        """
        Verify that a payout amount is correct.
        
        Args:
            total_cartelas_selected: int - Total cartelas selected
            num_winners: int - Number of winners
            actual_payout: float - Actual payout amount per winner
            win_percentage: int - Win percentage
        
        Returns:
            bool: True if payout is correct within tolerance
        """
        expected_payout = self.calculate_payout_for_multiple_winners(
            total_cartelas_selected, num_winners, win_percentage
        )
        
        # Allow 0.01 tolerance for rounding
        tolerance = 0.01
        return abs(actual_payout - expected_payout) <= tolerance
    
    # ==================== REPORTING ====================
    
    def generate_payout_report(
        self,
        round_id: int,
        round_number: int,
        total_cartelas_selected: int,
        winners: List[Dict],
        win_percentage: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a detailed payout report for a round.
        
        Args:
            round_id: int - Round ID
            round_number: int - Round number
            total_cartelas_selected: int - Total cartelas selected
            winners: list - List of winners
            win_percentage: int - Win percentage
        
        Returns:
            dict: Payout report
        """
        total_bets, prize_pool = self.calculate_prize_pool(total_cartelas_selected, win_percentage)
        house_edge = self.calculate_house_edge(total_bets, prize_pool)
        
        report = {
            'round_id': round_id,
            'round_number': round_number,
            'statistics': {
                'total_cartelas_selected': total_cartelas_selected,
                'cartela_price': self.cartela_price,
                'total_bets': total_bets,
                'win_percentage': win_percentage or self.default_win_percentage,
                'prize_pool': prize_pool,
                'house_edge': house_edge,
                'house_edge_percentage': (house_edge / total_bets * 100) if total_bets > 0 else 0
            },
            'winners': [],
            'summary': {
                'total_winners': len(winners),
                'payout_per_winner': prize_pool / len(winners) if winners else 0
            }
        }
        
        for winner in winners:
            report['winners'].append({
                'user_id': winner.get('user_id'),
                'cartela_id': winner.get('cartela_id'),
                'pattern': winner.get('pattern'),
                'payout_amount': prize_pool / len(winners) if winners else 0
            })
        
        return report
    
    # ==================== BULK PAYOUT OPERATIONS ====================
    
    async def distribute_bulk_payouts(
        self,
        payouts: List[Dict],
        reason: str = "bulk_payout"
    ) -> Dict[str, Any]:
        """
        Distribute payouts to multiple users in bulk.
        
        Args:
            payouts: list - List of dicts with 'user_id' and 'amount'
            reason: str - Reason for payout
        
        Returns:
            dict: Bulk distribution results
        """
        results = {
            'success': [],
            'failed': [],
            'total_paid': 0,
            'total_users': len(payouts)
        }
        
        for payout in payouts:
            user_id = payout.get('user_id')
            amount = payout.get('amount')
            metadata = payout.get('metadata', {})
            
            if not user_id or not amount:
                results['failed'].append({
                    'user_id': user_id,
                    'amount': amount,
                    'reason': 'Invalid user_id or amount'
                })
                continue
            
            success = await add_balance(
                telegram_id=user_id,
                amount=amount,
                reason=reason,
                metadata=metadata
            )
            
            if success:
                results['success'].append({
                    'user_id': user_id,
                    'amount': amount
                })
                results['total_paid'] += amount
            else:
                results['failed'].append({
                    'user_id': user_id,
                    'amount': amount,
                    'reason': 'Balance update failed'
                })
        
        logger.info(f"Bulk payout completed: {len(results['success'])} successful, {len(results['failed'])} failed, total paid: {results['total_paid']}")
        
        return results
    
    # ==================== REFUND OPERATIONS ====================
    
    async def refund_cartela_purchases(
        self,
        user_id: int,
        cartela_ids: List[int],
        round_id: int,
        reason: str = "cartela_refund"
    ) -> bool:
        """
        Refund cartela purchases to a user (e.g., when game is cancelled).
        
        Args:
            user_id: int - User's Telegram ID
            cartela_ids: list - List of cartela IDs to refund
            round_id: int - Round ID
            reason: str - Refund reason
        
        Returns:
            bool: True if successful
        """
        refund_amount = len(cartela_ids) * self.cartela_price
        
        if refund_amount <= 0:
            return False
        
        success = await add_balance(
            telegram_id=user_id,
            amount=refund_amount,
            reason=reason,
            metadata={
                'cartela_ids': cartela_ids,
                'round_id': round_id,
                'refund_type': 'cartela_refund'
            }
        )
        
        if success:
            logger.info(f"Refunded {refund_amount} ETB to user {user_id} for cartelas {cartela_ids} in round {round_id}")
        
        return success
    
    async def refund_all_players(
        self,
        round_id: int,
        reason: str = "game_cancelled"
    ) -> Dict[str, Any]:
        """
        Refund all players in a round (when game is cancelled).
        
        Args:
            round_id: int - Round ID
            reason: str - Refund reason
        
        Returns:
            dict: Refund results
        """
        from bot.game_engine.cartela_manager import cartela_manager
        
        # Get all selected cartelas grouped by user
        selected_cartelas = cartela_manager.get_all_selected_cartelas()
        user_cartelas: Dict[int, List[int]] = {}
        
        for cartela_id, user_id in selected_cartelas.items():
            if user_id not in user_cartelas:
                user_cartelas[user_id] = []
            user_cartelas[user_id].append(cartela_id)
        
        # Refund each user
        results = {
            'success': [],
            'failed': [],
            'total_refunded': 0
        }
        
        for user_id, cartela_ids in user_cartelas.items():
            success = await self.refund_cartela_purchases(user_id, cartela_ids, round_id, reason)
            
            if success:
                refund_amount = len(cartela_ids) * self.cartela_price
                results['success'].append({
                    'user_id': user_id,
                    'cartelas': cartela_ids,
                    'refund_amount': refund_amount
                })
                results['total_refunded'] += refund_amount
            else:
                results['failed'].append({
                    'user_id': user_id,
                    'cartelas': cartela_ids,
                    'reason': 'Refund failed'
                })
        
        logger.info(f"Refunded all players in round {round_id}: {len(results['success'])} successful, {results['total_refunded']} ETB total")
        
        return results
    
    # ==================== UTILITY METHODS ====================
    
    def get_payout_summary(self, winners: List[Dict]) -> Dict:
        """
        Get a summary of payouts for display.
        
        Args:
            winners: list - List of winner dictionaries
        
        Returns:
            dict: Payout summary
        """
        if not winners:
            return {
                'has_winners': False,
                'total_winners': 0,
                'total_payout': 0,
                'winners_list': []
            }
        
        total_payout = sum(w.get('payout_amount', 0) for w in winners)
        
        return {
            'has_winners': True,
            'total_winners': len(winners),
            'total_payout': total_payout,
            'winners_list': [
                {
                    'user_id': w.get('user_id'),
                    'cartela_id': w.get('cartela_id'),
                    'pattern': w.get('pattern'),
                    'amount': w.get('payout_amount', 0)
                }
                for w in winners
            ]
        }
    
    def format_payout_message(self, winners: List[Dict]) -> str:
        """
        Format a payout message for display to players.
        
        Args:
            winners: list - List of winner dictionaries
        
        Returns:
            str: Formatted payout message
        """
        if not winners:
            return "No winners this round."
        
        if len(winners) == 1:
            winner = winners[0]
            return f"🎉 BINGO! Winner won {winner.get('payout_amount', 0):.2f} ETB!"
        else:
            payout_per_winner = winners[0].get('payout_amount', 0) if winners else 0
            return f"🎉 BINGO! {len(winners)} winners! Each won {payout_per_winner:.2f} ETB!"


# ==================== FACTORY FUNCTION ====================

def create_payout_calculator() -> PayoutCalculator:
    """
    Factory function to create a PayoutCalculator instance.
    
    Returns:
        PayoutCalculator: PayoutCalculator instance
    """
    return PayoutCalculator()


# ==================== EXPORTS ====================

__all__ = [
    'PayoutCalculator',
    'create_payout_calculator',
]