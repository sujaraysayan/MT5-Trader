import MetaTrader5 as mt5
mt5.initialize()

# Try common names
test_names = ['GOLD', 'XAUUSD', 'XAUUSDm', 'GOLD.ecn', 'XAUUSD.', 'Gold']
for name in test_names:
    sym = mt5.symbol_info(name)
    if sym:
        print(f'FOUND: {name} - Ask: {sym.ask}, Bid: {sym.bid}')
    else:
        print(f'NOT FOUND: {name}')

# Check if any symbol contains GOLD
symbols = mt5.symbols_total()
print(f'\nTotal symbols: {symbols}')

mt5.shutdown()
