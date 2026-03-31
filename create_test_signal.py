"""
Create test BUY signal
"""
import sqlite3
from datetime import datetime
import MetaTrader5 as mt5

# Get current price
mt5.initialize()
symbol = mt5.symbol_info('GOLD')
price = symbol.bid if symbol else 4540
mt5.shutdown()

# Insert test signal
conn = sqlite3.connect('data/trades.db')
cursor = conn.cursor()

cursor.execute('''
    INSERT INTO signals (timestamp, strategy, signal_type, strength, confidence, price, sl, tp, timeframe, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    datetime.now().isoformat(),
    'TEST BUY Signal',
    'buy',
    'STRONG',
    0.85,
    price,
    price - 20,
    price + 40,
    'M5',
    '{"reason": "Test signal for demo"}'
))

conn.commit()
print('=' * 50)
print('TEST BUY SIGNAL CREATED!')
print('=' * 50)
print(f'Strategy: TEST BUY Signal')
print(f'Type:     BUY')
print(f'Price:    {price}')
print(f'SL:       {price - 20}')
print(f'TP:       {price + 40}')
print(f'Confidence: 85%')
print('=' * 50)

conn.close()
