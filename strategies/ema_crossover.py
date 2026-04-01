"""
EMA Crossover Strategy
====================
Entry: Fast EMA crosses above (bullish) / below (bearish) Slow EMA
Exit: Reverse crossover
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class EMACrossoverStrategy(BaseStrategy):
    """
    EMA Crossover Strategy.
    
    Uses 2 EMAs:
    - Fast EMA (default: 9)
    - Slow EMA (default: 21)
    
    Entry:
    - Fast EMA crosses above Slow EMA = BUY
    - Fast EMA crosses below Slow EMA = SELL
    """
    
    name = "EMA Crossover"
    description = "EMA crossover signals"
    
    def __init__(self, fast_period: int = 9, slow_period: int = 21):
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate EMA crossover signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        # Calculate EMAs
        closes = [h.get('close', 0) for h in history]
        if len(closes) < self.slow_period:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={'reason': 'Not enough data'}
            )
        
        # Calculate EMA manually
        fast_ema = self._calculate_ema(closes, self.fast_period)
        slow_ema = self._calculate_ema(closes, self.slow_period)
        
        # Get previous values
        if len(fast_ema) >= 2:
            fast_prev = fast_ema[-2]
            fast_curr = fast_ema[-1]
            slow_prev = slow_ema[-2]
            slow_curr = slow_ema[-1]
        else:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5
            )
        
        # Crossover detection
        bullish_cross = fast_prev <= slow_prev and fast_curr > slow_curr
        bearish_cross = fast_prev >= slow_prev and fast_curr < slow_curr
        
        # Distance from crossover - safe division
        safe_price = price if price > 0 else 1.0
        crossover_distance = abs(fast_curr - slow_curr) / safe_price * 100
        
        if bullish_cross:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM if crossover_distance < 0.1 else SignalStrength.STRONG,
                confidence=min(0.9, 0.5 + crossover_distance * 10),
                entry_price=price,
                metadata={
                    'fast_ema': fast_curr,
                    'slow_ema': slow_curr,
                    'crossover_distance': crossover_distance,
                    'reason': 'Bullish EMA crossover'
                }
            )
        
        elif bearish_cross:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.MEDIUM if crossover_distance < 0.1 else SignalStrength.STRONG,
                confidence=min(0.9, 0.5 + crossover_distance * 10),
                entry_price=price,
                metadata={
                    'fast_ema': fast_curr,
                    'slow_ema': slow_curr,
                    'crossover_distance': crossover_distance,
                    'reason': 'Bearish EMA crossover'
                }
            )
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={
                'fast_ema': fast_curr,
                'slow_ema': slow_curr,
                'reason': 'No crossover'
            }
        )
    
    def _calculate_ema(self, data: list, period: int) -> list:
        """Calculate EMA."""
        if len(data) < period:
            return data
        
        k = 2 / (period + 1)
        ema = [sum(data[:period]) / period]
        
        for i in range(period, len(data)):
            ema.append(data[i] * k + ema[-1] * (1 - k))
        
        return ema
