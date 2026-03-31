"""
Breakout Strategy
================
Breakout trading using support/resistance and momentum.
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class BreakoutStrategy(BaseStrategy):
    """
    Breakout strategy.
    
    Entry:
    - Price breaks above resistance with volume
    - ADX confirms momentum
    
    Exit:
    - Price closes below support
    - Trailing stop hit
    """
    
    name = "Breakout"
    description = "Breakout trading on support/resistance"
    
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate breakout signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        # Calculate support/resistance from recent highs/lows
        if len(history) >= self.lookback:
            recent_highs = [h.get('high', 0) for h in history[-self.lookback:]]
            recent_lows = [h.get('low', 0) for h in history[-self.lookback:]]
            
            resistance = max(recent_highs)
            support = min(recent_lows)
        else:
            resistance = price * 1.01
            support = price * 0.99
        
        adx = indicators.get('adx_14', 0)
        rsi = indicators.get('rsi_14', 50)
        
        # Breakout calculations
        resistance_distance = (price - resistance) / resistance * 100
        support_distance = (support - price) / support * 100
        
        # Bullish breakout
        if price > resistance and adx > 25:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG if adx > 35 else SignalStrength.MEDIUM,
                confidence=min(0.9, (adx / 100)),
                entry_price=price,
                sl=support,
                tp=resistance + (resistance - support) * 1.5,
                metadata={
                    'resistance': resistance,
                    'support': support,
                    'breakout_pct': resistance_distance,
                    'reason': 'Bullish breakout'
                }
            )
        
        # Bearish breakdown
        elif price < support and adx > 25:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.STRONG if adx > 35 else SignalStrength.MEDIUM,
                confidence=min(0.9, (adx / 100)),
                entry_price=price,
                sl=resistance,
                tp=support - (resistance - support) * 1.5,
                metadata={
                    'resistance': resistance,
                    'support': support,
                    'breakdown_pct': support_distance,
                    'reason': 'Bearish breakdown'
                }
            )
        
        # Near breakout levels
        elif resistance_distance < 1 and adx > 20:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=0.6,
                entry_price=price,
                metadata={
                    'resistance': resistance,
                    'near_breakout': True,
                    'reason': 'Near resistance breakout'
                }
            )
        
        # No signal
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={
                'resistance': resistance,
                'support': support,
                'price_in_range': True,
                'reason': 'Price in range - no breakout'
            }
        )
