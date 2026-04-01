import sqlite3
import json

conn = sqlite3.connect('data/trades.db')
cursor = conn.cursor()

cursor.execute('SELECT strategies_analyzed FROM decision_history ORDER BY id DESC LIMIT 1')
row = cursor.fetchone()
strategies = json.loads(row[0])

buy_count = sum(1 for s in strategies if s['signal'] == 'buy')
sell_count = sum(1 for s in strategies if s['signal'] == 'sell')

print('Latest Decision Analysis:')
print('BUY signals:', buy_count)
print('SELL signals:', sell_count)
print()
for s in strategies:
    if s['signal'] != 'hold':
        print(s['name'], ':', s['signal'], '-', s['confidence']*100, '%')

conn.close()
