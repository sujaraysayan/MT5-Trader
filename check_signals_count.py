from database import get_recent_signals

sigs = get_recent_signals(5)
print(f'Signals: {len(sigs)}')
for s in sigs:
    ts = s['timestamp'][11:19]
    print(f'  {ts} | {s["signal_type"]}')
