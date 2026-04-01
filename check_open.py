import sqlite3
conn = sqlite3.connect('data/trades.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM trades WHERE exit_price IS NULL OR exit_price = ''")
print('Open trades in DB:', cursor.fetchone()[0])
cursor.execute("SELECT id, direction, volume, entry_price FROM trades WHERE exit_price IS NULL OR exit_price = ''")
rows = cursor.fetchall()
for r in rows:
    print(r)
conn.close()
