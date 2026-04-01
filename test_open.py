import MetaTrader5 as mt5
import time

mt5.initialize()
time.sleep(1)

acc = mt5.account_info()
print('Account:', acc.login, 'Balance:', acc.balance)

symbol = mt5.symbol_info('GOLD')
print('GOLD Ask:', symbol.ask, 'Bid:', symbol.bid)

# Try to open SELL 0.01 lot
# For SELL: SL above entry, TP below entry
sl_price = symbol.bid * 1.005  # 0.5% above
tp_price = symbol.bid * 0.993  # 0.7% below

request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": "GOLD",
    "volume": 0.01,
    "type": mt5.ORDER_TYPE_SELL,
    "price": symbol.bid,
    "sl": sl_price,
    "tp": tp_price,
    "deviation": 20,
    "magic": 20260330,
    "comment": "Test SELL",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC
}

print(f'SL: {sl_price} ({((sl_price/symbol.bid)-1)*100:.2f}%)')
print(f'TP: {tp_price} ({((tp_price/symbol.bid)-1)*100:.2f}%)')

print('Sending SELL order...')
result = mt5.order_send(request)
print('Result:', result.retcode, result.comment)

if result.retcode == mt5.TRADE_RETCODE_DONE:
    print('ORDER DONE! Ticket:', result.order)
else:
    print('ORDER FAILED:', result.comment)

mt5.shutdown()
