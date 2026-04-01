import sqlite3
import json

conn = sqlite3.connect('data/trades.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT id, action, reason, timestamp, strategies_analyzed, price, volume, profit
    FROM decision_history 
    ORDER BY id DESC 
    LIMIT 1
''')
row = cursor.fetchone()

print('=== LATEST DECISION ===')
print('ID:', row[0])
print('Action:', row[1])
print('Reason:', row[2])
print('Time:', row[3])
print('Price:', row[5])
print('Volume:', row[6])
print('Profit:', row[7])

# Parse strategies
strategies = json.loads(row[4])
buy_signals = [s for s in strategies if s['signal'] == 'buy']
sell_signals = [s for s in strategies if s['signal'] == 'sell']

print()
print('BUY count:', len(buy_signals))
print('SELL count:', len(sell_signals))
print()
for s in strategies:
    if s['signal'] != 'hold':
        print(s['name'], ':', s['signal'], '-', s['confidence']*100, '%')

conn.close()
