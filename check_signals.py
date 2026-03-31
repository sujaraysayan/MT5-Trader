"""
Show recent signals
"""
from database import get_recent_signals

sigs = get_recent_signals(13)
print("Recent Signals:")
print("-" * 60)
for s in sigs:
    ts = s['timestamp'][11:19]
    strat = s['strategy'][:15].ljust(15)
    sig_type = s['signal_type'].upper()
    conf = s['confidence'] * 100
    print(f"{ts} | {strat} | {sig_type:5} | {conf:.0f}%")
