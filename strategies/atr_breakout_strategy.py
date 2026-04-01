"""
ATR Breakout Strategy
===================
Entry: Price breaks out with high volatility (ATR)
Exit: Volatility normalizes or trailing stop hit
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class ATRBreakoutStrategy(BaseStrategy):
    """
    ATR Breakout Strategy.
    
    Uses:
    - ATR (Average True Range) for volatility
    - Price momentum
    
    Entry:
    - Price breaks above recent high + ATR expands = BUY
    - Price breaks below recent low + ATR expands = SELL
    """
    
    name = "ATR Breakout"
    description = "ATR-based volatility breakout"
    
    def __init__(self, period: int = 14, atr_multiplier: float = 1.5):
        self.period = period
        self.atr_multiplier = atr_multiplier
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate ATR Breakout signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        if len(history) < self.period + 1:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={'reason': 'Not enough data'}
            )
        
        # Calculate ATR
        atr = indicators.get('atr_14', 0)
        if atr == 0:
            atr = self._calculate_atr(history)
        
        # Calculate recent range
        highs = [h.get('high', 0) for h in history]
        lows = [h.get('low', 0) for h in history]
        closes = [h.get('close', 0) for h in history]
        
        # Recent high/low
        recent_high = max(highs[-self.period:])
        recent_low = min(lows[-self.period:])
        
        # Previous high/low
        prev_high = max(highs[-(self.period + 1):-1])
        prev_low = min(lows[-(self.period + 1):-1])
        
        # ATR expansion detection
        atr_expanded = atr > atr * 1.1  # ATR is increasing
        
        # Safe division - prevent ATR = 0
        safe_atr = atr if atr > 0 else 1.0
        
        # Bullish breakout
        if prev_high <= prev_high and price > recent_high and atr_expanded:
            breakout_strength = (price - recent_high) / safe_atr
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=min(0.85, 0.5 + breakout_strength / 10),
                entry_price=price,
                sl=price - atr * 2,
                tp=price + atr * 3,
                metadata={
                    'atr': atr,
                    'recent_high': recent_high,
                    'breakout_strength': breakout_strength,
                    'reason': 'Bullish ATR breakout'
                }
            )
        
        # Bearish breakdown
        elif prev_low >= prev_low and price < recent_low and atr_expanded:
            breakout_strength = (recent_low - price) / safe_atr
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.MEDIUM,
                confidence=min(0.85, 0.5 + breakout_strength / 10),
                entry_price=price,
                sl=price + atr * 2,
                tp=price - atr * 3,
                metadata={
                    'atr': atr,
                    'recent_low': recent_low,
                    'breakout_strength': breakout_strength,
                    'reason': 'Bearish ATR breakdown'
                }
            )
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={
                'atr': atr,
                'reason': 'No ATR breakout'
            }
        )
    
    def _calculate_atr(self, history: list) -> float:
        """Calculate ATR."""
        highs = [h.get('high', 0) for h in history]
        lows = [h.get('low', 0) for h in history]
        closes = [h.get('close', 0) for h in history]
        
        tr_values = []
        for i in range(len(highs)):
            if i == 0:
                tr = highs[i] - lows[i]
            else:
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1])
                )
            tr_values.append(tr)
        
        if len(tr_values) < self.period:
            return sum(tr_values) / len(tr_values)
        
        return sum(tr_values[-self.period:]) / self.period
    
    def _calculate_atr_simple(self, history: list) -> float:
        """Calculate ATR simplified."""
        return self._calculate_atr(history)
