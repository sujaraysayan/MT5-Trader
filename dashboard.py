"""
Dashboard Web Application
========================
Real-time trading dashboard using Flask.
Access at: http://localhost:5000
"""

import os
import sys
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, jsonify, request
import sqlite3

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    init_database, get_connection,
    get_recent_signals, get_trade_history, get_open_trades,
    get_equity_curve, get_performance_summary, record_equity
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mt5-gold-trader-secret-key'

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Settings file path
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')


# =====================================================================
# Settings API
# =====================================================================

@app.route('/api/settings')
def api_settings():
    """Get trading settings."""
    import json
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            return jsonify(settings)
    except:
        pass
    
    return jsonify({
        'lot_min': 0.01,
        'lot_max': 0.1,
        'tp_percent': 1.5,
        'sl_percent': 1.0
    })


@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    """Save trading settings."""
    import json
    data = request.get_json()
    
    try:
        settings = {
            'lot_min': float(data.get('lot_min', 0.01)),
            'lot_max': float(data.get('lot_max', 0.1)),
            'tp_percent': float(data.get('tp_percent', 1.5)),
            'sl_percent': float(data.get('sl_percent', 1.0))
        }
        
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# =====================================================================
# Routes
# =====================================================================

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/status')
def api_status():
    """Get system status."""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'mt5_connected': True,  # Will be updated by trading loop
    })


@app.route('/api/performance')
def api_performance():
    """Get performance summary with real MT5 data."""
    try:
        import MetaTrader5 as mt5
        from datetime import datetime
        
        mt5.initialize()
        account = mt5.account_info()
        positions = mt5.positions_get()
        
        # Get closed trades for P&L calculation
        deals = mt5.history_deals_get(datetime(2026, 1, 1), datetime(2026, 12, 31))
        
        # Group deals by position to get closed trades P&L
        closed_pnl = 0
        winning_trades = 0
        losing_trades = 0
        total_closed_trades = 0
        
        positions_data = {}
        if deals:
            for deal in deals:
                if deal.symbol != 'GOLD' or deal.volume == 0:
                    continue
                pos_id = deal.position_id
                if pos_id not in positions_data:
                    positions_data[pos_id] = {'in': None, 'out': None}
                if deal.entry == 0:
                    positions_data[pos_id]['in'] = deal
                else:
                    positions_data[pos_id]['out'] = deal
        
        # Calculate P&L from closed positions
        total_wins = 0
        total_losses = 0
        win_count = 0
        loss_count = 0
        
        for pos_id, p in positions_data.items():
            if p['in'] and p['out']:
                total_closed_trades += 1
                pnl = p['out'].profit
                closed_pnl += pnl
                if pnl > 0:
                    winning_trades += 1
                    total_wins += pnl
                    win_count += 1
                elif pnl < 0:
                    losing_trades += 1
                    total_losses += pnl
                    loss_count += 1
        
        avg_win = total_wins / win_count if win_count > 0 else 0
        avg_loss = total_losses / loss_count if loss_count > 0 else 0
        
        # Calculate open P&L
        open_pnl = 0
        if positions:
            for pos in positions:
                open_pnl += pos.profit
        
        mt5.shutdown()
        
        # Build performance object
        initial = account.balance - closed_pnl - open_pnl if account else 10000
        
        perf = {
            'initial_balance': initial,
            'current_equity': account.equity if account else 0,
            'total_pnl': closed_pnl + open_pnl,
            'total_return': ((closed_pnl + open_pnl) / initial * 100) if initial > 0 else 0,
            'open_positions_pnl': open_pnl,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'total_trades': total_closed_trades,
            'win_rate': (winning_trades / total_closed_trades * 100) if total_closed_trades > 0 else 0,
            'avg_win': avg_win,
            'avg_loss': avg_loss
        }
        
        return jsonify(perf)
        
    except Exception as e:
        print(f"Error: {e}")
        pass
    
    # Fallback
    perf = get_performance_summary()
    return jsonify(perf)


@app.route('/api/equity')
def api_equity():
    """Get equity curve data from MT5."""
    try:
        import MetaTrader5 as mt5
        from datetime import datetime
        
        mt5.initialize()
        account = mt5.account_info()
        positions = mt5.positions_get()
        
        # Get current equity and balance
        current_equity = account.equity if account else 10000
        current_balance = account.balance if account else 10000
        
        # Get closed trades for building equity curve
        deals = mt5.history_deals_get(datetime(2026, 1, 1), datetime(2026, 12, 31))
        
        # Group deals by position
        positions_data = {}
        if deals:
            for deal in deals:
                if deal.symbol != 'GOLD' or deal.volume == 0:
                    continue
                pos_id = deal.position_id
                if pos_id not in positions_data:
                    positions_data[pos_id] = {'in': None, 'out': None}
                if deal.entry == 0:
                    positions_data[pos_id]['in'] = deal
                else:
                    positions_data[pos_id]['out'] = deal
        
        # Build list of closed trades with timestamps (in time order)
        closed_trades = []
        for pos_id, p in positions_data.items():
            if p['in'] and p['out']:
                exit_time = datetime.fromtimestamp(p['out'].time)
                pnl = p['out'].profit
                closed_trades.append({
                    'time': exit_time,
                    'pnl': pnl,
                    'time_str': exit_time.strftime('%Y-%m-%d %H:%M')
                })
        
        # Sort by time ascending
        closed_trades = sorted(closed_trades, key=lambda x: x['time'])
        
        # Calculate equity at each point (working BACKWARDS from current)
        # Current equity = initial + all closed P&Ls
        # So initial = current equity - sum of all closed P&Ls
        
        total_closed_pnl = sum(t['pnl'] for t in closed_trades)
        initial_equity = current_equity - total_closed_pnl
        
        # Build equity curve starting from initial, adding P&Ls
        equity_points = []
        
        # Add initial point
        equity_points.append({
            'time': '2026-03-31 00:00',
            'equity': initial_equity
        })
        
        # Add each trade in time order, accumulating equity
        running_equity = initial_equity
        for trade in closed_trades:
            running_equity += trade['pnl']  # Add P&L (positive or negative)
            equity_points.append({
                'time': trade['time_str'],
                'equity': running_equity
            })
        
        # Add current point
        equity_points.append({
            'time': 'Now',
            'equity': current_equity
        })
        
        mt5.shutdown()
        
        return jsonify({
            'data': equity_points,
            'count': len(equity_points)
        })
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Fallback to database
    days = request.args.get('days', 30, type=int)
    equity = get_equity_curve(days)
    return jsonify({
        'data': equity,
        'count': len(equity)
    })


@app.route('/api/signals')
def api_signals():
    """Get recent signals."""
    limit = request.args.get('limit', 20, type=int)
    signals = get_recent_signals(limit)
    return jsonify({
        'data': signals,
        'count': len(signals)
    })


@app.route('/api/trades')
def api_trades():
    """Get trade history from MT5 - paired IN/OUT deals."""
    limit = request.args.get('limit', 50, type=int)
    
    try:
        import MetaTrader5 as mt5
        from datetime import datetime, timedelta
        
        mt5.initialize()
        
        # Get deals using a wide date range to capture all
        # Use fixed dates to avoid timezone issues
        from_date = datetime(2026, 1, 1)
        to_date = datetime(2026, 12, 31)
        
        deals = mt5.history_deals_get(from_date, to_date)
        
        if deals:
            # Group deals by position_id
            positions = {}  # position_id -> {'in': deal, 'out': deal}
            
            for deal in deals:
                # Skip non-GOLD or zero volume
                if deal.symbol != 'GOLD' or deal.volume == 0:
                    continue
                
                pos_id = deal.position_id
                if pos_id not in positions:
                    positions[pos_id] = {'in': None, 'out': None}
                
                # DEAL_ENTRY_IN = 0 (open), DEAL_ENTRY_OUT = 1 (close)
                if deal.entry == 0:
                    positions[pos_id]['in'] = deal
                else:
                    positions[pos_id]['out'] = deal
            
            # Build trade records from paired deals
            result = []
            for pos_id, deals_pair in positions.items():
                if deals_pair['in'] and deals_pair['out']:
                    # Paired position - we have both entry and exit
                    entry_deal = deals_pair['in']
                    exit_deal = deals_pair['out']
                    
                    direction = 'buy' if entry_deal.type == 0 else 'sell'
                    
                    result.append({
                        'ticket': entry_deal.ticket,
                        'symbol': 'GOLD',
                        'direction': direction,
                        'entry_price': entry_deal.price,
                        'exit_price': exit_deal.price,
                        'volume': entry_deal.volume,
                        'profit': exit_deal.profit,
                        'timestamp': datetime.fromtimestamp(exit_deal.time).strftime('%Y-%m-%d %H:%M'),
                        'comment': exit_deal.comment or entry_deal.comment,
                        'status': 'CLOSED'
                    })
                elif deals_pair['in'] and not deals_pair['out']:
                    # Still open position - include it
                    entry_deal = deals_pair['in']
                    direction = 'buy' if entry_deal.type == 0 else 'sell'
                    result.append({
                        'ticket': entry_deal.ticket,
                        'symbol': 'GOLD',
                        'direction': direction,
                        'entry_price': entry_deal.price,
                        'exit_price': None,
                        'volume': entry_deal.volume,
                        'profit': None,
                        'timestamp': datetime.fromtimestamp(entry_deal.time).strftime('%Y-%m-%d %H:%M'),
                        'comment': entry_deal.comment,
                        'status': 'OPEN'
                    })
                elif deals_pair['out'] and not deals_pair['in']:
                    # Orphan close deal
                    exit_deal = deals_pair['out']
                    direction = 'buy' if exit_deal.type == 0 else 'sell'
                    result.append({
                        'ticket': exit_deal.ticket,
                        'symbol': 'GOLD',
                        'direction': direction,
                        'entry_price': 0,
                        'exit_price': exit_deal.price,
                        'volume': exit_deal.volume,
                        'profit': exit_deal.profit,
                        'timestamp': datetime.fromtimestamp(exit_deal.time).strftime('%Y-%m-%d %H:%M'),
                        'comment': exit_deal.comment,
                        'status': 'CLOSED'
                    })
            
            mt5.shutdown()
            
            # Sort by time descending and limit
            result = sorted(result, key=lambda x: x['timestamp'] or '', reverse=True)[:limit]
            
            return jsonify({
                'data': result,
                'count': len(result)
            })
        else:
            mt5.shutdown()
    except Exception as e:
        print(f"Error fetching trades: {e}")
    
    # Fallback to database
    trades = get_trade_history(limit)
    return jsonify({
        'data': trades,
        'count': len(trades)
    })


@app.route('/api/positions')
def api_positions():
    """Get open positions from MT5 with real-time P&L."""
    try:
        import MetaTrader5 as mt5
        mt5.initialize()
        
        positions = mt5.positions_get()
        mt5.shutdown()
        
        if positions:
            result = []
            for pos in positions:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'direction': 'buy' if pos.type == 0 else 'sell',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'current_price': pos.price_current,
                    'profit': pos.profit,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'magic': pos.magic,
                    'comment': pos.comment
                })
            return jsonify({
                'data': result,
                'count': len(result)
            })
    except Exception as e:
        pass
    
    # Fallback to database
    positions = get_open_trades()
    return jsonify({
        'data': positions,
        'count': len(positions)
    })


@app.route('/api/close-position', methods=['POST'])
def api_close_position():
    """Close a specific position by ticket ID."""
    data = request.get_json()
    ticket_id = data.get('ticket')
    
    if not ticket_id:
        return jsonify({'success': False, 'error': 'No ticket ID provided'})
    
    # Convert to integer if string
    try:
        ticket_id = int(ticket_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Invalid ticket ID'})
    
    try:
        import MetaTrader5 as mt5
        mt5.initialize()
        
        # Find the position
        positions = mt5.positions_get(ticket=ticket_id)
        if not positions or len(positions) == 0:
            mt5.shutdown()
            return jsonify({'success': False, 'error': 'Position not found'})
        
        pos = positions[0]
        
        # Determine opposite order type
        order_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
        
        # Close the position
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": order_type,
            "position": pos.ticket,
            "type_filling": mt5.ORDER_FILLING_IOC
        }
        
        result = mt5.order_send(close_request)
        mt5.shutdown()
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return jsonify({
                'success': True,
                'message': f'Position {ticket_id} closed',
                'profit': pos.profit
            })
        else:
            return jsonify({
                'success': False,
                'error': result.comment if result else 'Failed to close'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/decisions')
def api_decisions():
    """Get decision history."""
    from database import get_decision_history
    limit = request.args.get('limit', 50, type=int)
    decisions = get_decision_history(limit)
    return jsonify({
        'data': decisions,
        'count': len(decisions)
    })


@app.route('/api/price')
def api_price():
    """Get current gold price from MT5."""
    try:
        import MetaTrader5 as mt5
        mt5.initialize()
        symbol_info = mt5.symbol_info('GOLD')
        account_info = mt5.account_info()
        mt5.shutdown()
        
        if symbol_info:
            return jsonify({
                'symbol': 'GOLD',
                'bid': symbol_info.bid,
                'ask': symbol_info.ask,
                'spread': symbol_info.spread,
                'balance': account_info.balance if account_info else 0,
                'equity': account_info.equity if account_info else 0,
                'currency': account_info.currency if account_info else 'USD'
            })
    except Exception as e:
        pass
    
    return jsonify({
        'symbol': 'GOLD',
        'bid': 0,
        'ask': 0,
        'spread': 0,
        'balance': 0,
        'equity': 0,
        'currency': 'USD',
        'error': 'MT5 not connected'
    })


# =====================================================================
# Template Helpers (for use in HTML)
# =====================================================================

@app.template_filter('format_number')
def format_number(value, decimals=2):
    """Format number with commas."""
    if value is None:
        return '0'
    try:
        return f"{float(value):,.{decimals}f}"
    except:
        return str(value)


@app.template_filter('format_percent')
def format_percent(value):
    """Format as percentage."""
    if value is None:
        return '0%'
    try:
        return f"{float(value):.2f}%"
    except:
        return str(value)


@app.template_filter('format_pnl')
def format_pnl(value):
    """Format P&L with color."""
    if value is None:
        return '0.00'
    try:
        val = float(value)
        color = 'green' if val >= 0 else 'red'
        sign = '+' if val >= 0 else ''
        return f'<span style="color:{color}">{sign}{val:.2f}</span>'
    except:
        return str(value)


@app.template_filter('format_datetime')
def format_datetime(value):
    """Format datetime string."""
    if value is None:
        return ''
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return str(value)


# =====================================================================
# Dashboard Server
# =====================================================================

def run_dashboard(host='0.0.0.0', port=5000):
    """Run the dashboard server."""
    init_database()
    print(f"\n{'='*60}")
    print("MT5 Gold Trader Dashboard")
    print(f"{'='*60}")
    print(f"Local:   http://localhost:{port}")
    print(f"Network: http://{get_local_ip()}:{port}")
    print(f"{'='*60}\n")
    app.run(host=host, port=port, debug=False, threaded=True)


def get_local_ip():
    """Get local IP address."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


# =====================================================================
# Main
# =====================================================================

if __name__ == "__main__":
    # Write PID to file
    with open("dashboard.pid", "w") as f:
        f.write(str(os.getpid()))
    
    run_dashboard()
