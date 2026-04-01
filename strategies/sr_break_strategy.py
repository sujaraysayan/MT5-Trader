"""
Support Resistance Break Strategy
================================
Entry: Price breaks key S/R levels with momentum
Exit: Price closes back below/above level
"""

from typing import Dict, List, Tuple
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class SRBreakStrategy(BaseStrategy):
    """
    Support/Resistance Break Strategy.
    
    Identifies key S/R levels and trades breaks.
    
    Entry:
    - Price breaks above resistance = BUY
    - Price breaks below support = SELL
    """
    
    name = "Support/Resistance Break"
    description = "Support/Resistance level breaks"
    
    def __init__(self, lookback: int = 50, tolerance: float = 0.001):
        self.lookback = lookback
        self.tolerance = tolerance  # 0.1% tolerance for break
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate S/R Break signal."""
        price = data.get('price', 0)
        history = data.get('history', [])
        
        if len(history) < self.lookback:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={'reason': 'Not enough data'}
            )
        
        # Find S/R levels
        highs = [h.get('high', 0) for h in history]
        lows = [h.get('low', 0) for h in history]
        closes = [h.get('close', 0) for h in history]
        
        # Find swing highs and lows
        resistance_levels = self._find_swing_highs(highs)
        support_levels = self._find_swing_lows(lows)
        
        # Get nearest levels
        nearest_resistance = min([r for r in resistance_levels if r > price * 0.99], default=price * 1.02)
        nearest_support = max([s for s in support_levels if s < price * 1.01], default=price * 0.98)
        
        # Breakout detection
        tolerance_amount = price * self.tolerance
        
        # Safe division
        safe_price = price if price > 0 else 1.0
        
        # Bullish breakout
        if price > nearest_resistance + tolerance_amount:
            break_strength = (price - nearest_resistance) / safe_price * 100
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=min(0.8, 0.5 + break_strength / 5),
                entry_price=price,
                sl=nearest_support,
                tp=price + (price - nearest_support) * 1.5,
                metadata={
                    'resistance': nearest_resistance,
                    'support': nearest_support,
                    'break_strength': break_strength,
                    'reason': 'Resistance breakout'
                }
            )
        
        # Bearish breakdown
        elif price < nearest_support - tolerance_amount:
            break_strength = (nearest_support - price) / safe_price * 100
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.MEDIUM,
                confidence=min(0.8, 0.5 + break_strength / 5),
                entry_price=price,
                sl=nearest_resistance,
                tp=price - (nearest_resistance - price) * 1.5,
                metadata={
                    'resistance': nearest_resistance,
                    'support': nearest_support,
                    'break_strength': break_strength,
                    'reason': 'Support breakdown'
                }
            )
        
        # Near resistance
        if price > nearest_support and price < nearest_resistance:
            midpoint = (nearest_resistance + nearest_support) / 2
            if price > midpoint:
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.WEAK,
                    confidence=0.5,
                    metadata={
                        'position': 'between levels, above midpoint',
                        'reason': 'Neutral - above midpoint'
                    }
                )
            else:
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.WEAK,
                    confidence=0.5,
                    metadata={
                        'position': 'between levels, below midpoint',
                        'reason': 'Neutral - below midpoint'
                    }
                )
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={'reason': 'No S/R break'}
        )
    
    def _find_swing_highs(self, highs: List[float]) -> List[float]:
        """Find swing high levels."""
        levels = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                levels.append(highs[i])
        return levels[-10:] if len(levels) > 10 else levels
    
    def _find_swing_lows(self, lows: List[float]) -> List[float]:
        """Find swing low levels."""
        levels = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                levels.append(lows[i])
        return levels[-10:] if len(levels) > 10 else levels
