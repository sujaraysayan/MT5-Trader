import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/trades.db')
cursor = conn.cursor()

cursor.execute('SELECT action, timestamp, reason FROM decision_history ORDER BY id DESC LIMIT 5')
rows = cursor.fetchall()
print('Recent decisions:')
for r in rows:
    print(r[0], '|', r[1], '|', r[2])

cursor.execute('SELECT COUNT(*) FROM decision_history')
print('Total decisions:', cursor.fetchone()[0])

conn.close()
print('Time:', datetime.now())
