from database import get_decision_history
import json

decisions = get_decision_history(10)
print(f'Decisions: {len(decisions)}')
for d in decisions:
    ts = d['timestamp'][11:19]
    action = d['action']
    reason = (d['reason'] or 'N/A')[:50]
    print(f'  {ts} | {action:6} | {reason}')
