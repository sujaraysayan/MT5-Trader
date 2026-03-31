import re

with open('dashboard.py', 'r') as f:
    content = f.read()

# Define the new performance function
new_function = """@app.route('/api/performance')
def api_performance():
    \"\"\"Get performance summary with real MT5 data.\"\"\"
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
"""

# Replace the function using a simpler approach
# Find the start and end of the old function
start_marker = "@app.route('/api/performance')"
end_marker = "@app.route('/api/equity')"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + new_function + "\n\n" + content[end_idx:]
    
    with open('dashboard.py', 'w') as f:
        f.write(new_content)
    print("Done!")
else:
    print(f"Start found: {start_idx}, End found: {end_idx}")
