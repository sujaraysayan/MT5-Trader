"""
Test all 13 strategies
"""
from main import TradingSystem

system = TradingSystem()
system.connect_mt5()

print("Testing all 13 strategies...")
print()

# Get market data
market_data = system.get_market_data()
price = market_data['price']
print(f"Current Gold Price: {price}")
print()

# Test each strategy
print("Strategy Results:")
print("-" * 50)
for i, strategy in enumerate(system.strategies, 1):
    signal = strategy.analyze(market_data)
    sig_type = signal.signal_type.value.upper()
    conf = f"{signal.confidence:.0%}"
    print(f"{i:2}. {signal.strategy_name:22} -> {sig_type:5} ({conf})")

print()
print(f"Total strategies: {len(system.strategies)}")

system.stop()
