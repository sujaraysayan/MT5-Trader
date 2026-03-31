"""
MT5 Connection Module
====================
Connects to MetaTrader 5 terminal for trading XAU/USD (Gold).
"""

import time
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MT5Connection:
    """
    MetaTrader 5 connection class.
    
    Requires MT5 terminal to be installed and running.
    """
    
    def __init__(self):
        self.connected = False
        self.mt5 = None
        self._initialize()
    
    def _initialize(self):
        """Import and initialize MT5."""
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            logger.info("MT5 library loaded")
        except ImportError:
            logger.error("MetaTrader5 not installed. Run: pip install MetaTrader5")
            return
        
        # Initialize
        if not self.mt5.initialize():
            logger.error(f"MT5 init failed: {self.mt5.last_error()}")
            self.connected = False
        else:
            self.connected = True
            logger.info("MT5 connected successfully")
    
    def connect(self) -> bool:
        """Connect to MT5 terminal."""
        if self.mt5 is None:
            return False
        if not self.connected:
            if self.mt5.initialize():
                self.connected = True
        return self.connected
    
    def disconnect(self):
        """Disconnect from MT5."""
        if self.mt5 and self.connected:
            self.mt5.shutdown()
            self.connected = False
            logger.info("MT5 disconnected")
    
    def is_connected(self) -> bool:
        return self.connected and self.mt5 is not None
    
    # =====================================================================
    # Account & Symbol Info
    # =====================================================================
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information."""
        if not self.is_connected():
            return None
        info = self.mt5.account_info()
        if info is None:
            return None
        return {
            'balance': info.balance,
            'equity': info.equity,
            'margin': info.margin,
            'free_margin': info.margin_free,
            'leverage': info.leverage,
            'currency': info.currency,
        }
    
    def get_symbol_info(self, symbol: str = "XAUUSD") -> Optional[Dict]:
        """Get symbol information."""
        if not self.is_connected():
            return None
        info = self.mt5.symbol_info(symbol)
        if info is None:
            return None
        return {
            'symbol': info.name,
            'bid': info.bid,
            'ask': info.ask,
            'spread': info.spread,
            'digits': info.digits,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
        }
    
    # =====================================================================
    # Price Data
    # =====================================================================
    
    def get_rates(self, symbol: str = "XAUUSD", timeframe: int = 1, count: int = 100) -> Optional[List]:
        """
        Get OHLCV data.
        
        Timeframes:
            1 = M1, 5 = M5, 15 = M15, 30 = M30
            60 = H1, 240 = H4, 1440 = D1
        """
        if not self.is_connected():
            return None
        rates = self.mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        return rates
    
    def get_latest_candle(self, symbol: str = "XAUUSD", timeframe: int = 1) -> Optional[Dict]:
        """Get the most recent candle."""
        rates = self.get_rates(symbol, timeframe, 1)
        if rates is None or len(rates) == 0:
            return None
        r = rates[0]
        return {
            'time': datetime.fromtimestamp(r[0]),
            'open': r[1],
            'high': r[2],
            'low': r[3],
            'close': r[4],
            'volume': r[5],
        }
    
    # =====================================================================
    # Indicators (Built-in MT5)
    # =====================================================================
    
    def get_indicators(self, symbol: str = "XAUUSD", timeframe: int = 1) -> Dict:
        """
        Get all indicators for a symbol.
        Uses custom calculation (MT5 has limited built-in indicator functions).
        """
        rates = self.get_rates(symbol, timeframe, 100)
        if rates is None:
            return {}
        
        df = self._rates_to_dataframe(rates)
        return self._calculate_indicators(df)
    
    def _rates_to_dataframe(self, rates: List) -> 'DataFrame':
        """Convert rates array to DataFrame."""
        import pandas as pd
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    
    def _calculate_indicators(self, df) -> Dict:
        """Calculate technical indicators."""
        import pandas as pd
        import numpy as np
        
        close = df['close']
        high = df['high']
        low = df['low']
        
        indicators = {}
        
        # RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        indicators['rsi_14'] = 100 - (100 / (1 + rs)).iloc[-1]
        
        # MACD (12, 26, 9)
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        indicators['macd'] = macd.iloc[-1]
        indicators['macd_signal'] = signal.iloc[-1]
        indicators['macd_hist'] = (macd - signal).iloc[-1]
        
        # Bollinger Bands (20, 2)
        sma = close.rolling(20).mean()
        std = close.rolling(20).std()
        indicators['bb_upper'] = (sma + 2 * std).iloc[-1]
        indicators['bb_middle'] = sma.iloc[-1]
        indicators['bb_lower'] = (sma - 2 * std).iloc[-1]
        
        # ATR (14)
        high_low = high - low
        high_close = abs(high - close.shift(1))
        low_close = abs(low - close.shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        indicators['atr_14'] = tr.rolling(14).mean().iloc[-1]
        
        # ADX (14)
        plus_dm = high_low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm = -high_low.diff()
        minus_dm[minus_dm < 0] = 0
        plus_di = 100 * (plus_dm.rolling(14).mean() / indicators['atr_14'])
        minus_di = 100 * (minus_dm.rolling(14).mean() / indicators['atr_14'])
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        indicators['adx_14'] = dx.rolling(14).mean().iloc[-1]
        indicators['plus_di'] = plus_di.iloc[-1]
        indicators['minus_di'] = minus_di.iloc[-1]
        
        # Stochastic
        low_14 = low.rolling(14).min()
        high_14 = high.rolling(14).max()
        indicators['stoch_k'] = (100 * (close - low_14) / (high_14 - low_14)).iloc[-1]
        indicators['stoch_d'] = indicators['stoch_k'].rolling(3).mean().iloc[-1] if hasattr(indicators['stoch_k'], 'rolling') else 50
        
        # Price vs SMA
        indicators['sma_20'] = close.rolling(20).mean().iloc[-1]
        indicators['sma_50'] = close.rolling(50).mean().iloc[-1]
        
        return indicators
    
    # =====================================================================
    # Trading
    # =====================================================================
    
    def place_order(self, symbol: str, volume: float, order_type: str,
                   sl: float = None, tp: float = None, comment: str = "") -> Optional[Dict]:
        """
        Place a trading order.
        
        order_type: 'buy' or 'sell'
        """
        if not self.is_connected():
            return None
        
        if order_type.lower() == 'buy':
            trade_type = self.mt5.ORDER_TYPE_BUY
            price = self.mt5.symbol_info(symbol).ask
        else:
            trade_type = self.mt5.ORDER_TYPE_SELL
            price = self.mt5.symbol_info(symbol).bid
        
        request = {
            'symbol': symbol,
            'volume': volume,
            'type': trade_type,
            'price': price,
            'comment': comment,
            'type_filling': self.mt5.ORDER_FILLING_RETURN,
        }
        
        if sl:
            request['sl'] = sl
        if tp:
            request['tp'] = tp
        
        result = self.mt5.order_send(request)
        
        if result is None:
            return None
        
        return {
            'order_id': result.order,
            'retcode': result.retcode,
            'deal': result.deal,
            'volume': result.volume,
            'price': result.price,
        }
    
    def close_position(self, ticket: int, symbol: str, volume: float) -> bool:
        """Close a position."""
        if not self.is_connected():
            return False
        
        positions = self.mt5.positions_get(ticket=ticket)
        if not positions:
            return False
        
        pos = positions[0]
        order_type = self.mt5.ORDER_TYPE_SELL if pos.type == 0 else self.mt5.ORDER_TYPE_BUY
        
        request = {
            'symbol': symbol,
            'volume': volume,
            'type': order_type,
            'position': ticket,
            'type_filling': self.mt5.ORDER_FILLING_RETURN,
        }
        
        result = self.mt5.order_send(request)
        return result is not None and result.retcode == 10009
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions."""
        if not self.is_connected():
            return []
        
        positions = self.mt5.positions_get()
        result = []
        for pos in positions:
            result.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'buy' if pos.type == 0 else 'sell',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'sl': pos.sl,
                'tp': pos.tp,
            })
        return result


# =====================================================================
# Convenience Functions
# =====================================================================

def get_timeframe_minutes(tf: int) -> int:
    """Convert MT5 timeframe to minutes."""
    mapping = {
        1: 1,    # M1
        5: 5,    # M5
        15: 15,  # M15
        30: 30,  # M30
        60: 60,  # H1
        240: 240, # H4
        1440: 1440, # D1
    }
    return mapping.get(tf, 1)


# =====================================================================
# Example Usage
# =====================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MT5 Gold Trader - Connection Test")
    print("=" * 60)
    
    mt5 = MT5Connection()
    
    if mt5.is_connected():
        # Account
        acc = mt5.get_account_info()
        print(f"\nAccount: {acc}")
        
        # Symbol
        sym = mt5.get_symbol_info("XAUUSD")
        print(f"\nXAUUSD: {sym}")
        
        # Indicators
        ind = mt5.get_indicators("XAUUSD", timeframe=60)  # H1
        print(f"\nH1 Indicators: {ind}")
    else:
        print("\nMT5 not connected. Install MT5 Terminal and run again.")
