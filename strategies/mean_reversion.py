"""
Mean Reversion Strategy
======================
Mean reversion using Bollinger Bands and RSI.
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion strategy using Bollinger Bands.
    
    Entry:
    - Price touches lower BB (oversold) -> BUY
    - Price touches upper BB (overbought) -> SELL
    
    Exit:
    - Price returns to middle BB
    - RSI normalizes
    """
    
    name = "MeanReversion"
    description = "Mean reversion using Bollinger Bands"
    
    def __init__(self, bb_period: int = 20, bb_std: int = 2):
        self.bb_period = bb_period
        self.bb_std = bb_std
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate mean reversion signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        
        bb_upper = indicators.get('bb_upper', price)
        bb_middle = indicators.get('bb_middle', price)
        bb_lower = indicators.get('bb_lower', price)
        rsi = indicators.get('rsi_14', 50)
        
        # Bollinger Band position (0 to 1)
        bb_range = bb_upper - bb_lower
        if bb_range > 0:
            bb_position = (price - bb_lower) / bb_range
        else:
            bb_position = 0.5
            bb_range = 1  # Prevent division errors
        
        # Calculate distance from middle
        distance_from_middle = abs(price - bb_middle) / bb_range
        
        # Signals
        if price <= bb_lower:
            # Oversold - BUY signal
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                confidence=0.85,
                entry_price=price,
                sl=bb_lower - (bb_range * 0.5),
                tp=bb_middle,
                metadata={
                    'bb_position': bb_position,
                    'rsi': rsi,
                    'reason': 'Oversold - touching lower BB'
                }
            )
        
        elif price >= bb_upper:
            # Overbought - SELL signal
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.STRONG,
                confidence=0.85,
                entry_price=price,
                sl=bb_upper + (bb_range * 0.5),
                tp=bb_middle,
                metadata={
                    'bb_position': bb_position,
                    'rsi': rsi,
                    'reason': 'Overbought - touching upper BB'
                }
            )
        
        # Near extremes but not touching
        elif bb_position < 0.2 and rsi < 35:
            # Approaching oversold
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=0.7,
                entry_price=price,
                metadata={
                    'bb_position': bb_position,
                    'rsi': rsi,
                    'reason': 'Approaching oversold'
                }
            )
        
        elif bb_position > 0.8 and rsi > 65:
            # Approaching overbought
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.MEDIUM,
                confidence=0.7,
                entry_price=price,
                metadata={
                    'bb_position': bb_position,
                    'rsi': rsi,
                    'reason': 'Approaching overbought'
                }
            )
        
        # No signal
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={
                'bb_position': bb_position,
                'rsi': rsi,
                'reason': 'Price inside bands - neutral'
            }
        )
