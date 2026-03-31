"""
MACD Strategy
============
Entry: MACD crosses above/below signal line
Exit: Reverse crossover or divergence
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class MACDStrategy(BaseStrategy):
    """
    MACD Strategy.
    
    Uses:
    - MACD Line (12, 26)
    - Signal Line (9)
    - Histogram
    
    Entry:
    - MACD crosses above Signal = BUY
    - MACD crosses below Signal = SELL
    """
    
    name = "MACD"
    description = "MACD crossover signals"
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate MACD signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        # Get MACD values from indicators or calculate
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        macd_hist = indicators.get('macd_histogram', 0)
        
        # Calculate if not available
        if macd == 0 and len(history) >= self.slow:
            macd, macd_signal = self._calculate_macd(history)
            macd_hist = macd - macd_signal
        
        # Crossover detection (simplified using recent values)
        if len(history) >= 2:
            closes = [h.get('close', 0) for h in history]
            macd_prev, signal_prev = self._calculate_macd_simple(closes[:-1])
            macd_curr, signal_curr = self._calculate_macd_simple(closes)
            
            hist_prev = macd_prev - signal_prev
            hist_curr = macd_curr - signal_curr
            
            # Bullish crossover
            if hist_prev < 0 and hist_curr > 0:
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    confidence=0.7,
                    entry_price=price,
                    metadata={
                        'macd': macd_curr,
                        'signal': signal_curr,
                        'histogram': hist_curr,
                        'reason': 'MACD bullish crossover'
                    }
                )
            
            # Bearish crossover
            elif hist_prev > 0 and hist_curr < 0:
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.MEDIUM,
                    confidence=0.7,
                    entry_price=price,
                    metadata={
                        'macd': macd_curr,
                        'signal': signal_curr,
                        'histogram': hist_curr,
                        'reason': 'MACD bearish crossover'
                    }
                )
        
        # Trend direction based on histogram
        if macd_hist > 0:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.WEAK,
                confidence=0.5 + min(abs(macd_hist) / price * 100, 0.3),
                metadata={
                    'macd': macd,
                    'signal': macd_signal,
                    'histogram': macd_hist,
                    'reason': 'MACD above signal'
                }
            )
        else:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.WEAK,
                confidence=0.5 + min(abs(macd_hist) / price * 100, 0.3),
                metadata={
                    'macd': macd,
                    'signal': macd_signal,
                    'histogram': macd_hist,
                    'reason': 'MACD below signal'
                }
            )
    
    def _calculate_macd_simple(self, closes: list) -> tuple:
        """Calculate MACD for a list of closes."""
        if len(closes) < self.slow:
            return 0, 0
        
        # EMAs
        ema_fast = self._ema(closes, self.fast)
        ema_slow = self._ema(closes, self.slow)
        macd = ema_fast - ema_slow
        
        # Signal line (approximation)
        signal = macd * 0.9  # Simplified
        
        return macd, signal
    
    def _calculate_macd(self, history: list) -> tuple:
        """Calculate full MACD."""
        closes = [h.get('close', 0) for h in history]
        return self._calculate_macd_simple(closes)
    
    def _ema(self, data: list, period: int) -> float:
        """Calculate EMA."""
        if len(data) < period:
            return sum(data) / len(data) if data else 0
        
        k = 2 / (period + 1)
        ema = sum(data[:period]) / period
        
        for i in range(period, len(data)):
            ema = data[i] * k + ema * (1 - k)
        
        return ema
