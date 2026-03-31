"""
Run trading system with real MT5 data
"""
from main import TradingSystem
from datetime import datetime

system = TradingSystem()
system.connect_mt5()

print("Running trading system with REAL MT5 data...")
print()
print("Current Gold Price from MT5:")
market_data = system.get_market_data()
print(f"  Price: {market_data['price']}")
print(f"  Indicators:")
for k, v in market_data['indicators'].items():
    print(f"    {k}: {v}")
print()

# Run a few iterations
for i in range(3):
    signal = system.run_once()
    print(f"[{i+1}] {datetime.now().strftime('%H:%M:%S')} - {signal}")
    print()

system.stop()
