# telegram-bot/bot/api/commission.py
# Estif Bingo 24/7 - Commission Management API
# Handles win percentage settings, commission calculations, and reporting

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from flask import Blueprint, request, jsonify
from bot.db.repository import GameRepository, AdminRepository, TransactionRepository, AuditRepository
from bot.api.auth import token_required
from bot.config import config
from bot.utils.logger import logger

# Create blueprint
commission_bp = Blueprint('commission', __name__, url_prefix='/api/commission')

# Default win percentages
DEFAULT_WIN_PERCENTAGES = [75, 78, 79, 80]
DEFAULT_WIN_PERCENTAGE = 80

logger = logging.getLogger(__name__)


# ==================== WIN PERCENTAGE MANAGEMENT ====================

@commission_bp.route('/percentage', methods=['GET'])
async def get_win_percentage():
    """
    Get current win percentage
    
    Returns:
        JSON: Current win percentage
    """
    try:
        percentage = await GameRepository.get_win_percentage()
        
        return jsonify({
            'success': True,
            'data': {
                'win_percentage': percentage,
                'house_edge': 100 - percentage,
                'available_percentages': DEFAULT_WIN_PERCENTAGES
            }
        })
    except Exception as e:
        logger.error(f"Error getting win percentage: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@commission_bp.route('/percentage', methods=['POST'])
@token_required
async def set_win_percentage(current_user):
    """
    Set win percentage (admin only)
    
    Request body:
        {
            "percentage": 78
        }
    
    Returns:
        JSON: Updated win percentage
    """
    try:
        # Check admin permission
        if not current_user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.get_json()
        percentage = data.get('percentage')
        
        if percentage is None:
            return jsonify({'success': False, 'error': 'Missing percentage'}), 400
        
        if percentage not in DEFAULT_WIN_PERCENTAGES:
            return jsonify({
                'success': False, 
                'error': f'Invalid percentage. Allowed values: {DEFAULT_WIN_PERCENTAGES}'
            }), 400
        
        # Update win percentage
        success = await GameRepository.set_win_percentage(percentage)
        
        if success:
            # Log admin action
            await AdminRepository.log_admin_action(
                admin_id=current_user['telegram_id'],
                action='set_win_percentage',
                target_type='system',
                details={'old_percentage': await GameRepository.get_win_percentage(), 'new_percentage': percentage}
            )
            
            return jsonify({
                'success': True,
                'data': {
                    'win_percentage': percentage,
                    'house_edge': 100 - percentage
                },
                'message': f'Win percentage updated to {percentage}%'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to update win percentage'}), 500
            
    except Exception as e:
        logger.error(f"Error setting win percentage: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== COMMISSION CALCULATION ====================

async def calculate_commission(total_bets: float, win_percentage: int) -> float:
    """
    Calculate admin commission from total bets
    
    Args:
        total_bets: float - Total amount bet
        win_percentage: int - Win percentage (players get this %)
    
    Returns:
        float: Commission amount (house edge)
    """
    house_edge_percentage = 100 - win_percentage
    commission = total_bets * house_edge_percentage / 100
    return commission


async def calculate_round_commission(round_id: int) -> Dict[str, Any]:
    """
    Calculate commission for a specific round
    
    Args:
        round_id: int - Round ID
    
    Returns:
        dict: Commission details
    """
    # Get round total bets
    total_bets = await GameRepository.get_round_total_bets(round_id)
    
    # Get round win percentage (from when round was played)
    round_data = await GameRepository.get_round(round_id)
    win_percentage = round_data.get('win_percentage', DEFAULT_WIN_PERCENTAGE) if round_data else DEFAULT_WIN_PERCENTAGE
    
    # Calculate commission
    commission = await calculate_commission(total_bets, win_percentage)
    
    return {
        'round_id': round_id,
        'total_bets': total_bets,
        'win_percentage': win_percentage,
        'house_edge_percentage': 100 - win_percentage,
        'commission': commission,
        'players_payout': total_bets - commission
    }


@commission_bp.route('/calculate', methods=['POST'])
@token_required
async def calculate_commission_api(current_user):
    """
    Calculate commission for a specific amount or round
    
    Request body:
        {
            "total_bets": 1000,
            "win_percentage": 80
        }
        OR
        {
            "round_id": 123
        }
    
    Returns:
        JSON: Commission calculation
    """
    try:
        data = request.get_json()
        
        if 'round_id' in data:
            # Calculate for specific round
            result = await calculate_round_commission(data['round_id'])
        elif 'total_bets' in data:
            # Calculate for custom amount
            total_bets = float(data['total_bets'])
            win_percentage = data.get('win_percentage', await GameRepository.get_win_percentage())
            
            commission = await calculate_commission(total_bets, win_percentage)
            
            result = {
                'total_bets': total_bets,
                'win_percentage': win_percentage,
                'house_edge_percentage': 100 - win_percentage,
                'commission': commission,
                'players_payout': total_bets - commission
            }
        else:
            return jsonify({'success': False, 'error': 'Missing total_bets or round_id'}), 400
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logger.error(f"Error calculating commission: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== COMMISSION REPORTS ====================

@commission_bp.route('/report/daily', methods=['GET'])
@token_required
async def get_daily_commission_report(current_user):
    """
    Get daily commission report
    
    Query params:
        date: str - Date in YYYY-MM-DD format (optional, defaults to today)
    
    Returns:
        JSON: Daily commission report
    """
    try:
        # Check admin permission
        if not current_user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        date_str = request.args.get('date')
        
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        next_date = date + timedelta(days=1)
        
        # Get rounds for the date
        query = """
            SELECT id, total_cartelas, prize_pool, total_bets, win_percentage, start_time
            FROM game_rounds
            WHERE start_time >= $1 AND start_time < $2 AND status = 'ended'
        """
        
        from bot.db.database import fetch_all
        rounds = await fetch_all(query, date, next_date)
        
        total_bets = 0
        total_commission = 0
        total_payout = 0
        
        round_details = []
        for round_data in rounds:
            round_bets = round_data.get('total_bets', 0) or (round_data['total_cartelas'] * config.CARTELA_PRICE)
            win_percentage = round_data.get('win_percentage', DEFAULT_WIN_PERCENTAGE)
            commission = await calculate_commission(round_bets, win_percentage)
            
            total_bets += round_bets
            total_commission += commission
            total_payout += round_bets - commission
            
            round_details.append({
                'round_id': round_data['id'],
                'cartelas_sold': round_data['total_cartelas'],
                'total_bets': round_bets,
                'win_percentage': win_percentage,
                'commission': commission,
                'payout': round_bets - commission,
                'time': round_data['start_time'].isoformat() if round_data['start_time'] else None
            })
        
        # Get additional stats
        total_deposits = await TransactionRepository.sum_by_type('deposit')
        total_withdrawals = await TransactionRepository.sum_by_type('withdrawal')
        net_revenue = total_commission - total_withdrawals
        
        return jsonify({
            'success': True,
            'data': {
                'date': date.strftime('%Y-%m-%d'),
                'summary': {
                    'total_bets': total_bets,
                    'total_commission': total_commission,
                    'total_payout': total_payout,
                    'total_deposits': total_deposits,
                    'total_withdrawals': total_withdrawals,
                    'net_revenue': net_revenue,
                    'rounds_count': len(round_details)
                },
                'rounds': round_details
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting daily commission report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@commission_bp.route('/report/weekly', methods=['GET'])
@token_required
async def get_weekly_commission_report(current_user):
    """
    Get weekly commission report (last 7 days)
    
    Returns:
        JSON: Weekly commission report
    """
    try:
        if not current_user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        reports = []
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            
            # Get rounds for this date
            next_date = date + timedelta(days=1)
            
            query = """
                SELECT COALESCE(SUM(total_cartelas * $1), 0) as total_bets
                FROM game_rounds
                WHERE start_time >= $2 AND start_time < $3 AND status = 'ended'
            """
            
            from bot.db.database import fetch_val
            total_bets = await fetch_val(query, config.CARTELA_PRICE, date, next_date)
            total_bets = total_bets or 0
            
            win_percentage = await GameRepository.get_win_percentage()
            commission = await calculate_commission(total_bets, win_percentage)
            
            reports.append({
                'date': date.strftime('%Y-%m-%d'),
                'total_bets': total_bets,
                'commission': commission,
                'win_percentage': win_percentage
            })
        
        # Calculate totals
        total_bets = sum(r['total_bets'] for r in reports)
        total_commission = sum(r['commission'] for r in reports)
        
        return jsonify({
            'success': True,
            'data': {
                'period': {
                    'start_date': (today - timedelta(days=6)).strftime('%Y-%m-%d'),
                    'end_date': today.strftime('%Y-%m-%d'),
                    'days': 7
                },
                'summary': {
                    'total_bets': total_bets,
                    'total_commission': total_commission,
                    'average_daily_bets': total_bets / 7,
                    'average_daily_commission': total_commission / 7,
                    'house_edge_percentage': 100 - win_percentage
                },
                'daily_breakdown': reports
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting weekly commission report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@commission_bp.route('/report/monthly', methods=['GET'])
@token_required
async def get_monthly_commission_report(current_user):
    """
    Get monthly commission report
    
    Query params:
        year: int - Year (default: current year)
        month: int - Month (1-12, default: current month)
    
    Returns:
        JSON: Monthly commission report
    """
    try:
        if not current_user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        now = datetime.utcnow()
        year = int(request.args.get('year', now.year))
        month = int(request.args.get('month', now.month))
        
        # Get first day of month
        start_date = datetime(year, month, 1, 0, 0, 0)
        
        # Get last day of month
        if month == 12:
            end_date = datetime(year + 1, 1, 1, 0, 0, 0)
        else:
            end_date = datetime(year, month + 1, 1, 0, 0, 0)
        
        # Get rounds for the month
        query = """
            SELECT 
                DATE(start_time) as date,
                COALESCE(SUM(total_cartelas * $1), 0) as total_bets
            FROM game_rounds
            WHERE start_time >= $2 AND start_time < $3 AND status = 'ended'
            GROUP BY DATE(start_time)
            ORDER BY date ASC
        """
        
        from bot.db.database import fetch_all
        results = await fetch_all(query, config.CARTELA_PRICE, start_date, end_date)
        
        win_percentage = await GameRepository.get_win_percentage()
        
        daily_reports = []
        total_bets = 0
        total_commission = 0
        
        for row in results:
            daily_bets = row['total_bets'] or 0
            daily_commission = await calculate_commission(daily_bets, win_percentage)
            
            total_bets += daily_bets
            total_commission += daily_commission
            
            daily_reports.append({
                'date': row['date'].strftime('%Y-%m-%d') if row['date'] else None,
                'total_bets': daily_bets,
                'commission': daily_commission
            })
        
        return jsonify({
            'success': True,
            'data': {
                'year': year,
                'month': month,
                'month_name': start_date.strftime('%B'),
                'summary': {
                    'total_bets': total_bets,
                    'total_commission': total_commission,
                    'win_percentage': win_percentage,
                    'house_edge_percentage': 100 - win_percentage,
                    'days_with_activity': len(daily_reports)
                },
                'daily_breakdown': daily_reports
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting monthly commission report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@commission_bp.route('/report/custom', methods=['POST'])
@token_required
async def get_custom_commission_report(current_user):
    """
    Get custom date range commission report
    
    Request body:
        {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }
    
    Returns:
        JSON: Custom commission report
    """
    try:
        if not current_user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.get_json()
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return jsonify({'success': False, 'error': 'Missing start_date or end_date'}), 400
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
        
        # Get rounds in date range
        query = """
            SELECT 
                id,
                total_cartelas,
                start_time,
                win_percentage
            FROM game_rounds
            WHERE start_time >= $1 AND start_time < $2 AND status = 'ended'
            ORDER BY start_time ASC
        """
        
        from bot.db.database import fetch_all
        rounds = await fetch_all(query, start_date, end_date)
        
        total_bets = 0
        total_commission = 0
        total_payout = 0
        
        round_details = []
        for round_data in rounds:
            round_bets = round_data['total_cartelas'] * config.CARTELA_PRICE
            win_percentage = round_data.get('win_percentage', DEFAULT_WIN_PERCENTAGE)
            commission = await calculate_commission(round_bets, win_percentage)
            
            total_bets += round_bets
            total_commission += commission
            total_payout += round_bets - commission
            
            round_details.append({
                'round_id': round_data['id'],
                'cartelas_sold': round_data['total_cartelas'],
                'total_bets': round_bets,
                'win_percentage': win_percentage,
                'commission': commission,
                'payout': round_bets - commission,
                'date': round_data['start_time'].strftime('%Y-%m-%d') if round_data['start_time'] else None
            })
        
        # Get financial stats for period
        total_deposits = await TransactionRepository.sum_by_type('deposit')
        total_withdrawals = await TransactionRepository.sum_by_type('withdrawal')
        
        return jsonify({
            'success': True,
            'data': {
                'period': {
                    'start_date': start_date_str,
                    'end_date': end_date_str,
                    'days': (end_date - start_date).days
                },
                'summary': {
                    'total_bets': total_bets,
                    'total_commission': total_commission,
                    'total_payout': total_payout,
                    'total_deposits': total_deposits,
                    'total_withdrawals': total_withdrawals,
                    'net_revenue': total_commission - total_withdrawals,
                    'rounds_count': len(round_details)
                },
                'rounds': round_details
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting custom commission report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== COMMISSION EXPORT ====================

@commission_bp.route('/export', methods=['POST'])
@token_required
async def export_commission_report(current_user):
    """
    Export commission report as CSV
    
    Request body:
        {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "format": "csv"
        }
    
    Returns:
        CSV: Commission report
    """
    try:
        if not current_user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.get_json()
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        format_type = data.get('format', 'csv')
        
        if not start_date_str or not end_date_str:
            return jsonify({'success': False, 'error': 'Missing start_date or end_date'}), 400
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
        
        # Get rounds in date range
        query = """
            SELECT 
                id as round_id,
                round_number,
                total_cartelas as cartelas_sold,
                total_cartelas * $3 as total_bets,
                start_time,
                end_time,
                win_percentage,
                prize_pool
            FROM game_rounds
            WHERE start_time >= $1 AND start_time < $2 AND status = 'ended'
            ORDER BY start_time ASC
        """
        
        from bot.db.database import fetch_all
        rounds = await fetch_all(query, start_date, end_date, config.CARTELA_PRICE)
        
        # Build CSV
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Round ID', 'Round Number', 'Date', 'Cartelas Sold', 'Total Bets (ETB)',
            'Win Percentage', 'House Edge %', 'Commission (ETB)', 'Payout (ETB)'
        ])
        
        total_bets = 0
        total_commission = 0
        
        for round_data in rounds:
            round_bets = round_data['total_bets']
            win_percentage = round_data.get('win_percentage', DEFAULT_WIN_PERCENTAGE)
            commission = await calculate_commission(round_bets, win_percentage)
            
            total_bets += round_bets
            total_commission += commission
            
            writer.writerow([
                round_data['round_id'],
                round_data['round_number'],
                round_data['start_time'].strftime('%Y-%m-%d %H:%M') if round_data['start_time'] else '',
                round_data['cartelas_sold'],
                f"{round_bets:.2f}",
                f"{win_percentage}%",
                f"{100 - win_percentage}%",
                f"{commission:.2f}",
                f"{round_bets - commission:.2f}"
            ])
        
        # Write summary
        writer.writerow([])
        writer.writerow(['SUMMARY', '', '', '', '', '', '', '', ''])
        writer.writerow(['Total Rounds', len(rounds)])
        writer.writerow(['Total Bets', f"{total_bets:.2f} ETB"])
        writer.writerow(['Total Commission', f"{total_commission:.2f} ETB"])
        writer.writerow(['Average Commission per Round', f"{total_commission / len(rounds):.2f} ETB" if rounds else "0"])
        
        # Return CSV
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=commission_report_{start_date_str}_to_{end_date_str}.csv'
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting commission report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== COMMISSION STATISTICS ====================

@commission_bp.route('/statistics', methods=['GET'])
@token_required
async def get_commission_statistics(current_user):
    """
    Get overall commission statistics
    
    Returns:
        JSON: Commission statistics
    """
    try:
        if not current_user.get('is_admin'):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        # Get all rounds
        query = """
            SELECT 
                COUNT(*) as total_rounds,
                COALESCE(SUM(total_cartelas), 0) as total_cartelas,
                COALESCE(AVG(win_percentage), $1) as avg_win_percentage
            FROM game_rounds
            WHERE status = 'ended'
        """
        
        from bot.db.database import fetch_one
        result = await fetch_one(query, DEFAULT_WIN_PERCENTAGE)
        
        total_cartelas = result['total_cartelas'] if result else 0
        total_bets = total_cartelas * config.CARTELA_PRICE
        avg_win_percentage = result['avg_win_percentage'] if result else DEFAULT_WIN_PERCENTAGE
        
        total_commission = await calculate_commission(total_bets, avg_win_percentage)
        
        # Get total deposits and withdrawals
        total_deposits = await TransactionRepository.sum_by_type('deposit')
        total_withdrawals = await TransactionRepository.sum_by_type('withdrawal')
        
        return jsonify({
            'success': True,
            'data': {
                'overall': {
                    'total_rounds': result['total_rounds'] if result else 0,
                    'total_cartelas_sold': total_cartelas,
                    'total_bets': total_bets,
                    'total_commission': total_commission,
                    'avg_win_percentage': avg_win_percentage,
                    'avg_house_edge': 100 - avg_win_percentage
                },
                'financial': {
                    'total_deposits': total_deposits,
                    'total_withdrawals': total_withdrawals,
                    'net_revenue': total_commission - total_withdrawals
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting commission statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== EXPORTS ====================

__all__ = [
    'commission_bp',
    'calculate_commission',
    'calculate_round_commission',
]