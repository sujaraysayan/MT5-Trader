import MetaTrader5 as mt5

mt5.initialize()

positions = mt5.positions_get()
print(f"Open Positions: {len(positions)}")

for pos in positions:
    print(f"\nPosition {pos.ticket}:")
    print(f"  Symbol: {pos.symbol}")
    print(f"  Type: {'BUY' if pos.type == 0 else 'SELL'}")
    print(f"  Entry: {pos.price_open}")
    print(f"  Current: {pos.price_current}")
    
    entry = pos.price_open
    atr = 50
    
    if pos.type == 0:  # BUY
        sl = entry - 2 * atr
        tp = entry + 3 * atr
    else:  # SELL
        sl = entry + 2 * atr
        tp = entry - 3 * atr
    
    print(f"  Setting SL: {sl:.2f}, TP: {tp:.2f}")
    
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": pos.ticket,
        "sl": sl,
        "tp": tp,
        "type_filling": mt5.ORDER_FILLING_IOC
    }
    
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"  SUCCESS: SL/TP set!")
    else:
        print(f"  FAILED: {result.comment if result else 'No result'}")

mt5.shutdown()
