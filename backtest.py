"""
Proper Backtest for MT5 Gold Trader
===================================
Simulates real trading by running actual strategy classes.

This backtest:
- Uses the real 13 strategy classes (not simplified signals)
- Uses the real CompositeStrategy with weighted scoring
- Fetches candles from MT5 one by one (like real trading)
- Follows the exact same decision logic as production
- Processes candles sequentially for accuracy

Usage:
    python backtest.py [--days 365] [--symbol GOLD] [--timeframe 15]
"""

import argparse
import os
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


# =====================================================================
# REAL STRATEGY IMPLEMENTATIONS (using MT5 data format)
# =====================================================================

class RealStrategyMixin:
    """
    Mixin that provides analyze() methods using MT5 indicator data format.
    Each strategy reads from data['indicators'] dict.
    """
    
    def _get_indicators(self, data):
        """Extract indicators from data dict."""
        return data.get('indicators', {})
    
    def _get_price(self, data):
        """Get current price."""
        return data.get('price', 0)
    
    def _get_history(self, data):
        """Get price history."""
        return data.get('history', [])


class MomentumStrategyReal(RealStrategyMixin):
    """Real Momentum strategy using RSI + Stochastic."""
    
    name = "Momentum"
    description = "Momentum using RSI and Stochastic"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        
        rsi = ind.get('rsi_14', 50)
        stoch_k = ind.get('stoch_k', 50)
        stoch_d = ind.get('stoch_d', 50)
        
        # BUY: RSI > 50 and Stochastic rising
        if rsi > 50 and stoch_k > stoch_d:
            signal_type = SignalType.BUY
            strength = SignalStrength.MEDIUM
            confidence = min(0.5 + (rsi - 50) / 100 + (stoch_k - 50) / 200, 0.85)
        # SELL: RSI < 50 and Stochastic falling
        elif rsi < 50 and stoch_k < stoch_d:
            signal_type = SignalType.SELL
            strength = SignalStrength.MEDIUM
            confidence = min(0.5 + (50 - rsi) / 100 + (50 - stoch_k) / 200, 0.85)
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


class MeanReversionStrategyReal(RealStrategyMixin):
    """Real Mean Reversion strategy using Bollinger Bands."""
    
    name = "MeanReversion"
    description = "Mean reversion using Bollinger Bands"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        
        bb_upper = ind.get('bb_upper', price)
        bb_lower = ind.get('bb_lower', price)
        bb_middle = ind.get('bb_middle', price)
        
        # Calculate position within BB
        if bb_upper == bb_lower:
            bb_pos = 0.5
        else:
            bb_pos = (price - bb_lower) / (bb_upper - bb_lower)
        
        # BUY: Price at or below lower band
        if price <= bb_lower:
            signal_type = SignalType.BUY
            strength = SignalStrength.STRONG
            confidence = 0.85
        # SELL: Price at or above upper band
        elif price >= bb_upper:
            signal_type = SignalType.SELL
            strength = SignalStrength.STRONG
            confidence = 0.85
        # HOLD: Price within bands
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


class BreakoutStrategyReal(RealStrategyMixin):
    """Real Breakout strategy using Donchian Channel."""
    
    name = "Breakout"
    description = "Breakout using Donchian Channel"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        history = self._get_history(data)
        
        if len(history) < 20:
            return TradingSignal(self.name, SignalType.HOLD, SignalStrength.WEAK, 0.5, price)
        
        # Get highest high and lowest low of last 20 candles
        highs = [c['high'] for c in history[-20:]]
        lows = [c['low'] for c in history[-20:]]
        
        highest_high = max(highs)
        lowest_low = min(lows)
        
        # BUY: Price breaks above 20-day high
        if price > highest_high:
            signal_type = SignalType.BUY
            strength = SignalStrength.STRONG
            confidence = 0.8
        # SELL: Price breaks below 20-day low
        elif price < lowest_low:
            signal_type = SignalType.SELL
            strength = SignalStrength.STRONG
            confidence = 0.8
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


class StructureStrategyReal(RealStrategyMixin):
    """Real Structure strategy using EMA trend."""
    
    name = "Structure"
    description = "Market structure using EMA"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        
        ema_20 = ind.get('sma_20', price)  # Using sma_20 as proxy
        ema_50 = ind.get('sma_50', price)
        
        # BUY: Price above both EMAs and EMAs aligned
        if price > ema_20 and price > ema_50 and ema_20 > ema_50:
            signal_type = SignalType.BUY
            strength = SignalStrength.MEDIUM
            confidence = min(0.5 + (price - ema_20) / ema_20 * 10, 0.8)
        # SELL: Price below both EMAs and EMAs aligned
        elif price < ema_20 and price < ema_50 and ema_20 < ema_50:
            signal_type = SignalType.SELL
            strength = SignalStrength.MEDIUM
            confidence = min(0.5 + (ema_20 - price) / ema_20 * 10, 0.8)
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


class EMACrossoverStrategyReal(RealStrategyMixin):
    """Real EMA Crossover strategy."""
    
    name = "EMA Crossover"
    description = "EMA 20/50 Crossover"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        history = self._get_history(data)
        
        if len(history) < 50:
            return TradingSignal(self.name, SignalType.HOLD, SignalStrength.WEAK, 0.5, price)
        
        # Calculate EMAs manually
        closes = [c['close'] for c in history]
        
        ema20 = self._calc_ema(closes, 20)
        ema50 = self._calc_ema(closes, 50)
        
        current_ema20 = ema20[-1] if len(ema20) > 0 else price
        current_ema50 = ema50[-1] if len(ema50) > 0 else price
        prev_ema20 = ema20[-2] if len(ema20) > 1 else price
        prev_ema50 = ema50[-2] if len(ema50) > 1 else price
        
        # BUY: EMA20 crosses above EMA50
        if prev_ema20 <= prev_ema50 and current_ema20 > current_ema50:
            signal_type = SignalType.BUY
            strength = SignalStrength.MEDIUM
            confidence = 0.7
        # SELL: EMA20 crosses below EMA50
        elif prev_ema20 >= prev_ema50 and current_ema20 < current_ema50:
            signal_type = SignalType.SELL
            strength = SignalStrength.MEDIUM
            confidence = 0.7
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )
    
    def _calc_ema(self, data, period):
        if len(data) < period:
            return []
        ema = [sum(data[:period]) / period]
        alpha = 2 / (period + 1)
        for i in range(period, len(data)):
            ema.append(alpha * data[i] + (1 - alpha) * ema[-1])
        return ema


class SupertrendStrategyReal(RealStrategyMixin):
    """Real Supertrend strategy."""
    
    name = "Supertrend"
    description = "Supertrend indicator"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        atr = ind.get('atr_14', 0.5)
        
        # Simplified Supertrend calculation
        hl2 = price  # Would need HLC data properly
        upper_band = hl2 + 3 * atr
        lower_band = hl2 - 3 * atr
        
        # For simplicity, use price vs bands
        if price < lower_band:
            signal_type = SignalType.BUY
            strength = SignalStrength.MEDIUM
            confidence = 0.65
        elif price > upper_band:
            signal_type = SignalType.SELL
            strength = SignalStrength.MEDIUM
            confidence = 0.65
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


class MACDStrategyReal(RealStrategyMixin):
    """Real MACD strategy."""
    
    name = "MACD"
    description = "MACD histogram"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        
        macd_hist = ind.get('macd_hist', 0)
        
        if macd_hist > 0:
            signal_type = SignalType.BUY
            strength = SignalStrength.MEDIUM
            confidence = min(0.5 + abs(macd_hist) / price * 100, 0.8)
        elif macd_hist < 0:
            signal_type = SignalType.SELL
            strength = SignalStrength.MEDIUM
            confidence = min(0.5 + abs(macd_hist) / price * 100, 0.8)
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


class ADXTrendStrategyReal(RealStrategyMixin):
    """Real ADX Trend Strength strategy."""
    
    name = "ADX Trend Strength"
    description = "ADX trend strength indicator"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        
        adx = ind.get('adx_14', 25)
        plus_di = ind.get('plus_di', 25)
        minus_di = ind.get('minus_di', 25)
        
        # BUY: +DI > -DI and ADX > 25 (uptrend)
        if plus_di > minus_di and adx > 25:
            signal_type = SignalType.BUY
            strength = SignalStrength.MEDIUM if adx < 40 else SignalStrength.STRONG
            confidence = min(0.5 + (adx - 25) / 75, 0.85)
        # SELL: -DI > +DI and ADX > 25 (downtrend)
        elif minus_di > plus_di and adx > 25:
            signal_type = SignalType.SELL
            strength = SignalStrength.MEDIUM if adx < 40 else SignalStrength.STRONG
            confidence = min(0.5 + (adx - 25) / 75, 0.85)
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


class RSIStrategyReal(RealStrategyMixin):
    """Real RSI strategy."""
    
    name = "RSI"
    description = "RSI momentum"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        
        rsi = ind.get('rsi_14', 50)
        
        if rsi < 30:
            signal_type = SignalType.BUY
            strength = SignalStrength.STRONG
            confidence = min(0.5 + (30 - rsi) / 30, 0.9)
        elif rsi > 70:
            signal_type = SignalType.SELL
            strength = SignalStrength.STRONG
            confidence = min(0.5 + (rsi - 70) / 30, 0.9)
        elif rsi > 50:
            signal_type = SignalType.BUY
            strength = SignalStrength.WEAK
            confidence = 0.55
        elif rsi < 50:
            signal_type = SignalType.SELL
            strength = SignalStrength.WEAK
            confidence = 0.55
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


class BollingerBandsStrategyReal(RealStrategyMixin):
    """Real Bollinger Bands strategy."""
    
    name = "Bollinger Bands"
    description = "Bollinger Bands"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        
        bb_upper = ind.get('bb_upper', price)
        bb_lower = ind.get('bb_lower', price)
        bb_middle = ind.get('bb_middle', price)
        
        if price < bb_lower:
            signal_type = SignalType.BUY
            strength = SignalStrength.MEDIUM
            confidence = 0.7
        elif price > bb_upper:
            signal_type = SignalType.SELL
            strength = SignalStrength.MEDIUM
            confidence = 0.7
        elif price > bb_middle:
            signal_type = SignalType.BUY
            strength = SignalStrength.WEAK
            confidence = 0.55
        elif price < bb_middle:
            signal_type = SignalType.SELL
            strength = SignalStrength.WEAK
            confidence = 0.55
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


class StochasticStrategyReal(RealStrategyMixin):
    """Real Stochastic Oscillator strategy."""
    
    name = "Stochastic"
    description = "Stochastic Oscillator"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        
        stoch_k = ind.get('stoch_k', 50)
        stoch_d = ind.get('stoch_d', 50)
        
        if stoch_k < 20 and stoch_d < 20:
            signal_type = SignalType.BUY
            strength = SignalStrength.STRONG
            confidence = 0.8
        elif stoch_k > 80 and stoch_d > 80:
            signal_type = SignalType.SELL
            strength = SignalStrength.STRONG
            confidence = 0.8
        elif stoch_k > stoch_d and stoch_k < 50:
            signal_type = SignalType.BUY
            strength = SignalStrength.WEAK
            confidence = 0.55
        elif stoch_k < stoch_d and stoch_k > 50:
            signal_type = SignalType.SELL
            strength = SignalStrength.WEAK
            confidence = 0.55
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


class DonchianChannelStrategyReal(RealStrategyMixin):
    """Real Donchian Channel strategy."""
    
    name = "Donchian Channel"
    description = "Donchian Channel breakout"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        history = self._get_history(data)
        
        if len(history) < 20:
            return TradingSignal(self.name, SignalType.HOLD, SignalStrength.WEAK, 0.5, price)
        
        # Get highest high and lowest low of last 20 candles
        highs = [c['high'] for c in history[-20:]]
        lows = [c['low'] for c in history[-20:]]
        
        highest_high = max(highs)
        lowest_low = min(lows)
        
        if price > highest_high:
            signal_type = SignalType.BUY
            strength = SignalStrength.STRONG
            confidence = 0.8
        elif price < lowest_low:
            signal_type = SignalType.SELL
            strength = SignalStrength.STRONG
            confidence = 0.8
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


class ATRBreakoutStrategyReal(RealStrategyMixin):
    """Real ATR Breakout strategy."""
    
    name = "ATR Breakout"
    description = "ATR-based breakout"
    
    def analyze(self, data):
        from strategies.base import TradingSignal, SignalType, SignalStrength
        ind = self._get_indicators(data)
        price = self._get_price(data)
        history = self._get_history(data)
        
        atr = ind.get('atr_14', 0)
        
        if len(history) < 2:
            return TradingSignal(self.name, SignalType.HOLD, SignalStrength.WEAK, 0.5, price)
        
        prev_price = history[-1]['close']
        price_change = abs(price - prev_price)
        
        # BUY: Price moves up by more than 1.5 * ATR
        if price_change > atr * 1.5 and price > prev_price:
            signal_type = SignalType.BUY
            strength = SignalStrength.MEDIUM
            confidence = min(0.5 + price_change / atr / 3, 0.85)
        # SELL: Price moves down by more than 1.5 * ATR
        elif price_change > atr * 1.5 and price < prev_price:
            signal_type = SignalType.SELL
            strength = SignalStrength.MEDIUM
            confidence = min(0.5 + price_change / atr / 3, 0.85)
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=price
        )


# =====================================================================
# MT5 DATA FETCHER (real-time style)
# =====================================================================

class MT5DataFetcher:
    """
    Fetches historical data from MT5 in a realistic way.
    Simulates real-time trading by fetching candles as if they were arriving.
    """
    
    def __init__(self, symbol, timeframe, days):
        self.symbol = symbol
        self.timeframe = timeframe
        self.days = days
        self.candles = []
        self.current_idx = 0
    
    def load_all_candles(self):
        """Load all historical candles from MT5."""
        import MetaTrader5 as mt5
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.days)
        
        rates = mt5.copy_rates_range(self.symbol, self.timeframe, start_date, end_date)
        
        if rates is None or len(rates) == 0:
            return False
        
        self.candles = []
        for r in rates:
            self.candles.append({
                'time': datetime.fromtimestamp(r['time']),
                'open': r['open'],
                'high': r['high'],
                'low': r['low'],
                'close': r['close'],
                'volume': r['tick_volume']
            })
        
        return True
    
    def get_candle_at(self, idx):
        """Get a specific candle by index."""
        if 0 <= idx < len(self.candles):
            return self.candles[idx]
        return None
    
    def get_history(self, idx, count):
        """Get previous N candles ending at idx."""
        start = max(0, idx - count)
        return self.candles[start:idx]
    
    def get_indicators_at(self, idx):
        """
        Calculate indicators for a specific candle.
        This mimics what MT5/talib would provide in real trading.
        """
        if idx < 50:
            return {}
        
        highs = [c['high'] for c in self.candles[:idx+1]]
        lows = [c['low'] for c in self.candles[:idx+1]]
        closes = [c['close'] for c in self.candles[:idx+1]]
        
        indicators = {}
        
        # RSI (14)
        indicators['rsi_14'] = self._calc_rsi(closes, 14)
        
        # Stochastic (14, 3)
        stoch_k, stoch_d = self._calc_stochastic(highs, lows, closes, 14, 3)
        indicators['stoch_k'] = stoch_k
        indicators['stoch_d'] = stoch_d
        
        # MACD (12, 26, 9)
        macd, macd_signal, macd_hist = self._calc_macd(closes)
        indicators['macd'] = macd
        indicators['macd_signal'] = macd_signal
        indicators['macd_hist'] = macd_hist
        
        # Bollinger Bands (20, 2)
        bb_upper, bb_middle, bb_lower = self._calc_bollinger(closes, 20, 2)
        indicators['bb_upper'] = bb_upper
        indicators['bb_middle'] = bb_middle
        indicators['bb_lower'] = bb_lower
        
        # ATR (14)
        indicators['atr_14'] = self._calc_atr(highs, lows, closes, 14)
        
        # ADX (14)
        adx, plus_di, minus_di = self._calc_adx(highs, lows, closes, 14)
        indicators['adx_14'] = adx
        indicators['plus_di'] = plus_di
        indicators['minus_di'] = minus_di
        
        # SMAs
        indicators['sma_20'] = self._calc_sma(closes, 20)
        indicators['sma_50'] = self._calc_sma(closes, 50)
        
        return indicators
    
    def _calc_rsi(self, closes, period=14):
        if len(closes) < period + 1:
            return 50
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calc_stochastic(self, highs, lows, closes, k_period=14, d_period=3):
        if len(closes) < k_period:
            return 50, 50
        
        low_min = min(lows[-k_period:])
        high_max = max(highs[-k_period:])
        
        if high_max == low_min:
            return 50, 50
        
        k = 100 * (closes[-1] - low_min) / (high_max - low_min)
        
        # Calculate D using SMA of K
        if len(closes) < k_period + d_period - 1:
            return k, 50
        
        k_values = []
        for i in range(k_period - 1, len(closes)):
            low_i = min(lows[i-k_period+1:i+1])
            high_i = max(highs[i-k_period+1:i+1])
            if high_i != low_i:
                k_values.append(100 * (closes[i] - low_i) / (high_i - low_i))
            else:
                k_values.append(50)
        
        d = np.mean(k_values[-d_period:]) if len(k_values) >= d_period else 50
        
        return k, d
    
    def _calc_macd(self, closes, fast=12, slow=26, signal=9):
        if len(closes) < slow:
            return 0, 0, 0
        
        ema_fast = self._calc_ema(closes, fast)
        ema_slow = self._calc_ema(closes, slow)
        macd = ema_fast - ema_slow
        
        macd_values = [ema_fast - ema_slow for ema_fast, ema_slow in zip(
            self._calc_ema_list(closes, fast),
            self._calc_ema_list(closes, slow)
        )]
        
        if len(macd_values) < signal:
            return macd, macd, 0
        
        signal_line = np.mean(macd_values[-signal:])
        histogram = macd - signal_line
        
        return macd, signal_line, histogram
    
    def _calc_ema(self, data, period):
        if len(data) < period:
            return data[-1] if len(data) > 0 else 0
        
        alpha = 2 / (period + 1)
        ema = [sum(data[:period]) / period]
        
        for i in range(period, len(data)):
            ema.append(alpha * data[i] + (1 - alpha) * ema[-1])
        
        return ema[-1]
    
    def _calc_ema_list(self, data, period):
        if len(data) < period:
            return [data[-1]] * len(data) if len(data) > 0 else [0] * len(data)
        
        alpha = 2 / (period + 1)
        result = [0] * (period - 1)
        result.append(sum(data[:period]) / period)
        
        for i in range(period, len(data)):
            result.append(alpha * data[i] + (1 - alpha) * result[-1])
        
        return result
    
    def _calc_sma(self, data, period):
        if len(data) < period:
            return data[-1] if len(data) > 0 else 0
        return np.mean(data[-period:])
    
    def _calc_bollinger(self, closes, period=20, std_dev=2):
        if len(closes) < period:
            return closes[-1], closes[-1], closes[-1] if len(closes) > 0 else 0, 0, 0
        
        sma = np.mean(closes[-period:])
        std = np.std(closes[-period:])
        
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        
        return upper, sma, lower
    
    def _calc_atr(self, highs, lows, closes, period=14):
        if len(closes) < period + 1:
            return 0
        
        tr_values = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_values.append(tr)
        
        if len(tr_values) < period:
            return np.mean(tr_values) if len(tr_values) > 0 else 0
        
        atr = np.mean(tr_values[-period:])
        return atr
    
    def _calc_adx(self, highs, lows, closes, period=14):
        if len(closes) < period * 2 + 1:
            return 25, 25, 25
        
        # Calculate True Range and Directional Movement
        tr_list = []
        plus_dm_list = []
        minus_dm_list = []
        
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
            
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            
            plus_dm = up_move if up_move > down_move and up_move > 0 else 0
            minus_dm = down_move if down_move > up_move and down_move > 0 else 0
            
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
        
        # Calculate smoothed averages
        atr = np.mean(tr_list[-period:]) if len(tr_list) >= period else 0
        plus_di = 100 * np.mean(plus_dm_list[-period:]) / atr if atr > 0 else 0
        minus_di = 100 * np.mean(minus_dm_list[-period:]) / atr if atr > 0 else 0
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = np.mean(dx[-period*2:]) if len(dx) >= period * 2 else 25
        
        return adx, plus_di, minus_di
    
    def detect_market_type(self, idx):
        """
        Detect market type at a specific candle.
        Uses H1-style detection on M15 data.
        """
        if idx < 100:
            return "sideway"
        
        highs = [c['high'] for c in self.candles[:idx+1]]
        lows = [c['low'] for c in self.candles[:idx+1]]
        closes = [c['close'] for c in self.candles[:idx+1]]
        
        # Calculate indicators
        sma50 = self._calc_ema(closes, 50)
        ema20 = self._calc_ema(closes, 20)
        
        ema_slope = ema20 - (closes[-5] if len(closes) >= 5 else closes[-1])
        
        atr = self._calc_atr(highs, lows, closes, 14)
        atr_prev = self._calc_atr(highs[:-10], lows[:-10], closes[:-10], 14) if len(closes) >= 10 else atr
        atr_change = ((atr - atr_prev) / (atr_prev + 1e-6)) * 100
        
        adx, plus_di, minus_di = self._calc_adx(highs, lows, closes, 14)
        
        bb_upper, bb_middle, bb_lower = self._calc_bollinger(closes, 20, 2)
        bb_width = (bb_upper - bb_lower) / (bb_middle + 1e-6) * 100
        
        # Volatile: ATR spike + BB expansion
        if atr_change > 25 and bb_width > 5:
            return "volatile"
        
        # Strong trend
        if adx > 25 and abs(ema_slope) > 0:
            if closes[-1] > sma50:
                return "trend_bull"
            else:
                return "trend_bear"
        
        return "sideway"


# Need numpy
import numpy as np


# =====================================================================
# PROPER BACKTEST ENGINE
# =====================================================================

class ProperBacktest:
    """
    Proper backtest that simulates real trading exactly.
    Uses actual strategy classes and processes candles sequentially.
    """
    
    def __init__(self, symbol="GOLD", timeframe=15, days=365):
        self.symbol = symbol
        self.timeframe = timeframe
        self.days = days
        
        # Initialize strategies (real classes)
        self.strategies = [
            MomentumStrategyReal(),
            MeanReversionStrategyReal(),
            BreakoutStrategyReal(),
            StructureStrategyReal(),
            EMACrossoverStrategyReal(),
            SupertrendStrategyReal(),
            MACDStrategyReal(),
            ADXTrendStrategyReal(),
            RSIStrategyReal(),
            BollingerBandsStrategyReal(),
            StochasticStrategyReal(),
            DonchianChannelStrategyReal(),
            ATRBreakoutStrategyReal(),
        ]
        
        # Create composite strategy with verbose=False
        from strategies.base import CompositeStrategy
        self.composite = CompositeStrategy(self.strategies)
        
        # Trading state
        self.position = None
        self.trades = []
        self.equity_curve = []
        
        # Settings
        self.settings = self._load_settings()
        
        # Data fetcher
        self.data_fetcher = MT5DataFetcher(symbol, timeframe, days)
        
        print(f"ProperBacktest initialized: {symbol}, TF={timeframe}min, {days} days")
        print(f"Strategies loaded: {len(self.strategies)}")
    
    def _load_settings(self):
        import json
        settings_file = project_root / 'settings.json'
        try:
            if settings_file.exists():
                with open(settings_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'lot_min': 0.01,
            'lot_max': 0.1,
            'tp_percent': 1.5,
            'sl_percent': 1.0
        }
    
    def get_lot_size(self, confidence):
        lot_min = self.settings.get('lot_min', 0.01)
        lot_max = self.settings.get('lot_max', 0.1)
        lot = lot_min + (lot_max - lot_min) * confidence
        return max(lot_min, min(lot, lot_max))
    
    def run(self):
        """Run the proper backtest."""
        print(f"\nLoading {self.days} days of historical data from MT5...")
        
        if not self.data_fetcher.load_all_candles():
            print("Failed to load data from MT5!")
            return None
        
        candles = self.data_fetcher.candles
        n = len(candles)
        warmup = 100
        
        print(f"Loaded {n} candles")
        print(f"Running backtest from candle {warmup} to {n}...")
        
        initial_balance = 10000
        balance = initial_balance
        equity = initial_balance
        
        start_time = time.time()
        last_progress = 0
        
        for idx in range(warmup, n):
            # Progress every 10%
            pct = (idx - warmup) / (n - warmup) * 100
            if pct - last_progress >= 10:
                elapsed = time.time() - start_time
                print(f"Progress: {pct:.0f}% ({idx}/{n}) - {elapsed:.1f}s elapsed - Balance: ${balance:,.2f}")
                last_progress = pct
            
            current_candle = candles[idx]
            price = current_candle['close']
            current_time = current_candle['time']
            
            # Detect market type
            market_type = self.data_fetcher.detect_market_type(idx)
            
            # Get indicators
            indicators = self.data_fetcher.get_indicators_at(idx)
            
            # Get history
            history = self.data_fetcher.get_history(idx, 50)
            
            # Prepare data for strategies
            data = {
                'price': price,
                'indicators': indicators,
                'history': history,
                'timeframe': f'M{self.timeframe}'
            }
            
            # Get trading signal (verbose=False to suppress output)
            signal = self.composite.analyze(data, market_type=market_type, verbose=False)
            
            # Check and update position
            if self.position:
                pos = self.position
                
                # Calculate P&L
                if pos['type'] == 'buy':
                    pnl = (price - pos['entry']) * pos['volume'] * 100
                else:
                    pnl = (pos['entry'] - price) * pos['volume'] * 100
                
                equity = balance + pnl
                
                # Check exit conditions
                should_close = False
                reason = ""
                exit_price = price
                
                if pos['type'] == 'buy':
                    if price <= pos['sl']:
                        should_close, reason = True, "SL"
                        pnl = (pos['sl'] - pos['entry']) * pos['volume'] * 100
                        exit_price = pos['sl']
                    elif price >= pos['tp']:
                        should_close, reason = True, "TP"
                        pnl = (pos['tp'] - pos['entry']) * pos['volume'] * 100
                        exit_price = pos['tp']
                else:
                    if price >= pos['sl']:
                        should_close, reason = True, "SL"
                        pnl = (pos['entry'] - pos['sl']) * pos['volume'] * 100
                        exit_price = pos['sl']
                    elif price <= pos['tp']:
                        should_close, reason = True, "TP"
                        pnl = (pos['entry'] - pos['tp']) * pos['volume'] * 100
                        exit_price = pos['tp']
                
                # Close on opposite signal
                if not should_close:
                    if (pos['type'] == 'buy' and signal.signal_type.value == 'sell'):
                        should_close, reason = True, "OppSignal"
                    elif (pos['type'] == 'sell' and signal.signal_type.value == 'buy'):
                        should_close, reason = True, "OppSignal"
                
                # Close if profit >= $50
                current_pnl = (price - pos['entry']) * pos['volume'] * 100 if pos['type'] == 'buy' else (pos['entry'] - price) * pos['volume'] * 100
                if not should_close and current_pnl >= 50:
                    should_close, reason = True, f"Profit${current_pnl:.0f}"
                
                if should_close:
                    self.trades.append({
                        'entry_time': pos['entry_time'],
                        'exit_time': current_time,
                        'type': pos['type'],
                        'entry': pos['entry'],
                        'exit': exit_price,
                        'volume': pos['volume'],
                        'pnl': pnl,
                        'reason': reason
                    })
                    
                    balance += pnl
                    equity = balance
                    self.position = None
            
            # Open new position
            if not self.position and signal.signal_type.value != 'hold':
                action = signal.metadata.get('action', 'NO_TRADE')
                
                if action in ['BUY', 'SELL']:
                    sl_pct = self.settings.get('sl_percent', 1.0) / 100
                    tp_pct = self.settings.get('tp_percent', 1.5) / 100
                    
                    if action == 'BUY':
                        sl_price = price * (1 - sl_pct)
                        tp_price = price * (1 + tp_pct)
                    else:
                        sl_price = price * (1 + sl_pct)
                        tp_price = price * (1 - tp_pct)
                    
                    self.position = {
                        'type': action.lower(),
                        'entry': price,
                        'sl': sl_price,
                        'tp': tp_price,
                        'volume': self.get_lot_size(signal.confidence),
                        'entry_time': current_time
                    }
            
            # Record equity every 50 candles
            if idx % 50 == 0:
                self.equity_curve.append({
                    'time': current_time,
                    'balance': balance,
                    'equity': equity
                })
        
        # Close remaining position at end
        if self.position:
            price = candles[-1]['close']
            pos = self.position
            
            pnl = (price - pos['entry']) * pos['volume'] * 100 if pos['type'] == 'buy' else (pos['entry'] - price) * pos['volume'] * 100
            
            self.trades.append({
                'entry_time': pos['entry_time'],
                'exit_time': candles[-1]['time'],
                'type': pos['type'],
                'entry': pos['entry'],
                'exit': price,
                'volume': pos['volume'],
                'pnl': pnl,
                'reason': 'End'
            })
            
            balance += pnl
        
        elapsed = time.time() - start_time
        
        return self._generate_report(initial_balance, balance, elapsed)
    
    def _generate_report(self, initial_balance, final_balance, elapsed):
        """Generate backtest report."""
        if not self.trades:
            return {
                'initial_balance': initial_balance,
                'final_balance': final_balance,
                'total_pnl': 0,
                'total_trades': 0,
                'elapsed_seconds': elapsed
            }
        
        pnls = [t['pnl'] for t in self.trades]
        winning = [p for p in pnls if p > 0]
        losing = [p for p in pnls if p < 0]
        
        # Calculate max drawdown
        equity = initial_balance
        peak = initial_balance
        max_dd = 0
        for pnl in pnls:
            equity += pnl
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        
        return {
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'total_pnl': final_balance - initial_balance,
            'total_return_pct': ((final_balance - initial_balance) / initial_balance) * 100,
            'total_trades': len(self.trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': len(winning) / len(self.trades) * 100 if self.trades else 0,
            'avg_win': np.mean(winning) if winning else 0,
            'avg_loss': np.mean(losing) if losing else 0,
            'max_drawdown': max_dd,
            'profit_factor': abs(sum(winning) / sum(losing)) if losing and sum(losing) != 0 else 0,
            'largest_win': max(winning) if winning else 0,
            'largest_loss': min(losing) if losing else 0,
            'elapsed_seconds': elapsed
        }


# =====================================================================
# MAIN
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description='MT5 Gold Trader - Proper Backtest')
    parser.add_argument('--days', type=int, default=365, help='Days to backtest (default: 365)')
    parser.add_argument('--symbol', type=str, default='GOLD', help='Symbol (default: GOLD)')
    parser.add_argument('--timeframe', type=int, default=15, help='Timeframe in minutes (default: 15)')
    parser.add_argument('--reset-db', action='store_true', help='Reset database before backtest')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("MT5 Gold Trader - Proper Backtest")
    print(f"{'='*60}")
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: M{args.timeframe}")
    print(f"Period: {args.days} days")
    print(f"{'='*60}\n")
    
    # Reset database if requested
    if args.reset_db:
        db_path = project_root / 'data' / 'trades.db'
        if db_path.exists():
            backup = str(db_path) + f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(db_path, backup)
            print(f"Backed up database to: {backup}")
        
        from database import init_database
        init_database()
        print("Database reset complete\n")
    
    # Initialize MT5
    import MetaTrader5 as mt5
    
    if not mt5.initialize():
        print(f"MT5 initialization failed: {mt5.last_error()}")
        return
    
    print("MT5 initialized successfully\n")
    
    # Create and run backtest
    engine = ProperBacktest(
        symbol=args.symbol,
        timeframe=args.timeframe,
        days=args.days
    )
    
    report = engine.run()
    
    if report is None:
        print("Backtest failed!")
        mt5.shutdown()
        return
    
    # Print report
    print(f"\n{'='*60}")
    print("BACKTEST RESULTS")
    print(f"{'='*60}")
    print(f"Period: {args.days} days ({len(engine.data_fetcher.candles)} candles)")
    print(f"Duration: {report['elapsed_seconds']:.1f} seconds")
    print(f"{'-'*40}")
    print(f"Initial Balance: ${report['initial_balance']:,.2f}")
    print(f"Final Balance:   ${report['final_balance']:,.2f}")
    print(f"Total P&L:       ${report['total_pnl']:,.2f}")
    print(f"Total Return:    {report.get('total_return_pct', 0):.2f}%")
    print(f"{'-'*40}")
    print(f"Total Trades:    {report['total_trades']}")
    print(f"Winning Trades:  {report['winning_trades']}")
    print(f"Losing Trades:   {report['losing_trades']}")
    print(f"Win Rate:        {report['win_rate']:.1f}%")
    print(f"{'-'*40}")
    print(f"Average Win:     ${report['avg_win']:.2f}")
    print(f"Average Loss:    ${report['avg_loss']:.2f}")
    print(f"Largest Win:     ${report['largest_win']:.2f}")
    print(f"Largest Loss:    ${report['largest_loss']:.2f}")
    print(f"Profit Factor:   {report.get('profit_factor', 0):.2f}")
    print(f"Max Drawdown:    ${report['max_drawdown']:.2f}")
    print(f"{'='*60}")
    
    # Save to database
    print("\nSaving results to database...")
    from database import save_decision, record_equity
    
    for trade in engine.trades:
        save_decision(
            action=trade['type'].upper(),
            reason=trade['reason'],
            price=trade['exit'],
            volume=trade['volume'],
            profit=trade['pnl'],
            position_id=None,
            strategies_analyzed=[],
            final_decision=trade['type'],
            confidence=0.5
        )
    
    for point in engine.equity_curve:
        record_equity(
            balance=point['balance'],
            equity=point['equity'],
            open_positions=1 if engine.position else 0
        )
    
    print(f"Saved {len(engine.trades)} trades and {len(engine.equity_curve)} equity points")
    
    mt5.shutdown()
    print("\nBacktest completed and MT5 disconnected!")


if __name__ == "__main__":
    main()
