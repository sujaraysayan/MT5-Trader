"""
Structure Strategy
=================
Market structure and price action analysis.
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class StructureStrategy(BaseStrategy):
    """
    Market structure strategy.
    
    Analysis:
    - Higher highs/lows (uptrend)
    - Lower highs/lows (downtrend)
    - Sideways consolidation
    - Key structure levels
    """
    
    name = "Structure"
    description = "Market structure and price action"
    
    def __init__(self, lookback: int = 50):
        self.lookback = lookback
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate structure-based signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        if len(history) < 20:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={'reason': 'Not enough data'}
            )
        
        # Calculate structure
        highs = [h.get('high', 0) for h in history[-self.lookback:]]
        lows = [h.get('low', 0) for h in history[-self.lookback:]]
        closes = [h.get('close', 0) for h in history[-self.lookback:]]
        
        # Recent highs/lows
        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])
        older_high = max(highs[:10])
        older_low = min(lows[:10])
        
        # Trend analysis
        sma_20 = indicators.get('sma_20', price)
        sma_50 = indicators.get('sma_50', price)
        
        # Market structure signals
        structure_bullish = (
            recent_high > older_high and
            recent_low > older_low and
            price > sma_20
        )
        
        structure_bearish = (
            recent_high < older_high and
            recent_low < older_low and
            price < sma_20
        )
        
        # Consolidation
        range_size = recent_high - recent_low
        range_pct = range_size / price * 100
        is_consolidating = range_pct < 3  # Less than 3% range
        
        adx = indicators.get('adx_14', 0)
        rsi = indicators.get('rsi_14', 50)
        
        # Generate signal
        if structure_bullish and not is_consolidating:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG if adx > 30 else SignalStrength.MEDIUM,
                confidence=0.75,
                entry_price=price,
                sl=recent_low,
                tp=recent_high + range_size,
                metadata={
                    'structure': 'higher_highs_higher_lows',
                    'range_pct': range_pct,
                    'reason': 'Bullish structure confirmed'
                }
            )
        
        elif structure_bearish and not is_consolidating:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.STRONG if adx > 30 else SignalStrength.MEDIUM,
                confidence=0.75,
                entry_price=price,
                sl=recent_high,
                tp=recent_low - range_size,
                metadata={
                    'structure': 'lower_highs_lower_lows',
                    'range_pct': range_pct,
                    'reason': 'Bearish structure confirmed'
                }
            )
        
        elif is_consolidating and adx < 20:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={
                    'structure': 'consolidating',
                    'range_pct': range_pct,
                    'reason': 'Market consolidating'
                }
            )
        
        # No clear structure
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={
                'structure': 'undefined',
                'reason': 'No clear market structure'
            }
        )
