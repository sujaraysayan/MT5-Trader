"""
Check MT5 positions
"""
import MetaTrader5 as mt5

mt5.initialize()

# Check positions
positions = mt5.positions_get()
print(f"Open Positions: {len(positions)}")

if positions:
    for pos in positions:
        print(f"  Symbol: {pos.symbol}")
        print(f"  Type: {'BUY' if pos.type == 0 else 'SELL'}")
        print(f"  Volume: {pos.volume}")
        print(f"  Price: {pos.price_open}")
        print(f"  Current: {pos.price_current}")
        print(f"  Profit: {pos.profit}")
else:
    print("No open positions")

# Check orders
orders = mt5.orders_get()
print(f"Pending Orders: {len(orders)}")

mt5.shutdown()
