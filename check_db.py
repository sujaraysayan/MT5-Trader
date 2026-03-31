"""
Check database status
"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/trades.db')
cursor = conn.cursor()

# Get counts
cursor.execute('SELECT COUNT(*) FROM signals')
signal_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM trades')
trade_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM equity_curve')
equity_count = cursor.fetchone()[0]

print('=== Database Records ===')
print(f'Signals: {signal_count}')
print(f'Trades: {trade_count}')
print(f'Equity Points: {equity_count}')
print()

# Get latest equity
cursor.execute('SELECT * FROM equity_curve ORDER BY timestamp DESC LIMIT 1')
eq = cursor.fetchone()
if eq:
    print('=== Current Equity ===')
    print(f'Time: {eq[1]}')
    print(f'Balance: {eq[2]:,.2f}')
    print(f'Equity: {eq[3]:,.2f}')
    print()

# Get recent signals
print('=== Recent Signals ===')
cursor.execute('SELECT timestamp, strategy, signal_type, confidence, price FROM signals ORDER BY timestamp DESC LIMIT 5')
for row in cursor.fetchall():
    dt = datetime.fromisoformat(row[0])
    time_str = dt.strftime('%H:%M:%S')
    print(f'{time_str} | {row[2]:6} | {row[3]*100:5.0f}% | {row[4]:,.2f}')

conn.close()
