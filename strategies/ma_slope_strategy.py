"""
Moving Average Slope Strategy
==========================
Entry: MA slope changes direction
Exit: Slope flattens or reverses
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class MASlopeStrategy(BaseStrategy):
    """
    Moving Average Slope Strategy.
    
    Uses:
    - MA slope (rate of change)
    - Positive slope = uptrend
    - Negative slope = downtrend
    
    Entry:
    - Slope turns positive = BUY
    - Slope turns negative = SELL
    """
    
    name = "Moving Average Slope"
    description = "MA slope trend changes"
    
    def __init__(self, ma_period: int = 20, slope_threshold: float = 0.0001):
        self.ma_period = ma_period
        self.slope_threshold = slope_threshold  # Minimum slope to consider
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate MA Slope signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        if len(history) < self.ma_period + 2:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={'reason': 'Not enough data'}
            )
        
        # Calculate MA slope
        closes = [h.get('close', 0) for h in history]
        ma_values = self._calculate_ma(closes, self.ma_period)
        
        # Current and previous slope
        current_ma = ma_values[-1] if ma_values else price
        prev_ma = ma_values[-2] if len(ma_values) >= 2 else price
        
        # Calculate slope as rate of change
        current_slope = (current_ma - prev_ma) / prev_ma if prev_ma != 0 else 0
        
        # Calculate previous slope for turn detection
        if len(ma_values) >= 3:
            prev_prev_ma = ma_values[-3]
            prev_slope = (prev_ma - prev_prev_ma) / prev_prev_ma if prev_prev_ma != 0 else 0
        else:
            prev_slope = current_slope
        
        # Slope turn detection
        if prev_slope <= 0 and current_slope > self.slope_threshold:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=min(0.8, abs(current_slope) * 1000),
                entry_price=price,
                metadata={
                    'ma': current_ma,
                    'slope': current_slope,
                    'reason': 'MA slope turns positive'
                }
            )
        
        elif prev_slope >= 0 and current_slope < -self.slope_threshold:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.MEDIUM,
                confidence=min(0.8, abs(current_slope) * 1000),
                entry_price=price,
                metadata={
                    'ma': current_ma,
                    'slope': current_slope,
                    'reason': 'MA slope turns negative'
                }
            )
        
        # Strong slope without turn
        if current_slope > self.slope_threshold * 2:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.WEAK,
                confidence=min(0.6, abs(current_slope) * 500),
                metadata={
                    'ma': current_ma,
                    'slope': current_slope,
                    'reason': 'Strong positive slope'
                }
            )
        
        elif current_slope < -self.slope_threshold * 2:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.WEAK,
                confidence=min(0.6, abs(current_slope) * 500),
                metadata={
                    'ma': current_ma,
                    'slope': current_slope,
                    'reason': 'Strong negative slope'
                }
            )
        
        # Flat slope
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={
                'ma': current_ma,
                'slope': current_slope,
                'reason': 'MA slope flat'
            }
        )
    
    def _calculate_ma(self, data: list, period: int) -> list:
        """Calculate Moving Average."""
        ma = []
        for i in range(len(data)):
            if i < period - 1:
                ma.append(sum(data[:i+1]) / (i+1))
            else:
                ma.append(sum(data[i-period+1:i+1]) / period)
        return ma
