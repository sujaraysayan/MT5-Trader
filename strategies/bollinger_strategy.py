"""
Bollinger Bands Strategy
=======================
Entry: Price touches or exits bands
Exit: Price returns to middle band
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands Strategy.
    
    Uses:
    - Upper Band (+2 STD)
    - Middle Band (20 SMA)
    - Lower Band (-2 STD)
    
    Entry:
    - Price touches lower band = BUY (oversold)
    - Price touches upper band = SELL (overbought)
    """
    
    name = "Bollinger Bands"
    description = "Bollinger Bands volatility signals"
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate Bollinger Bands signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        # Get values from indicators or calculate
        bb_upper = indicators.get('bb_upper', price)
        bb_middle = indicators.get('bb_middle', price)
        bb_lower = indicators.get('bb_lower', price)
        
        if bb_upper == price and len(history) >= self.period:
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger(history)
        
        # Calculate band width and position
        band_width = bb_upper - bb_lower
        bb_position = (price - bb_lower) / band_width if band_width > 0 else 0.5
        
        # Signals
        if price <= bb_lower:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=0.7,
                entry_price=price,
                sl=bb_lower * 0.995,
                tp=bb_middle,
                metadata={
                    'bb_upper': bb_upper,
                    'bb_middle': bb_middle,
                    'bb_lower': bb_lower,
                    'bb_position': bb_position,
                    'reason': 'Price at lower band - oversold'
                }
            )
        
        elif price >= bb_upper:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.MEDIUM,
                confidence=0.7,
                entry_price=price,
                sl=bb_upper * 1.005,
                tp=bb_middle,
                metadata={
                    'bb_upper': bb_upper,
                    'bb_middle': bb_middle,
                    'bb_lower': bb_lower,
                    'bb_position': bb_position,
                    'reason': 'Price at upper band - overbought'
                }
            )
        
        # Near extremes
        elif bb_position < 0.15:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.WEAK,
                confidence=0.6,
                metadata={
                    'bb_position': bb_position,
                    'reason': 'Approaching lower band'
                }
            )
        
        elif bb_position > 0.85:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.WEAK,
                confidence=0.6,
                metadata={
                    'bb_position': bb_position,
                    'reason': 'Approaching upper band'
                }
            )
        
        # Inside bands - neutral
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={
                'bb_position': bb_position,
                'reason': 'Price inside bands'
            }
        )
    
    def _calculate_bollinger(self, history: list) -> tuple:
        """Calculate Bollinger Bands."""
        closes = [h.get('close', 0) for h in history]
        
        if len(closes) < self.period:
            return closes[-1], closes[-1], closes[-1]
        
        recent_closes = closes[-self.period:]
        sma = sum(recent_closes) / self.period
        
        variance = sum((c - sma) ** 2 for c in recent_closes) / self.period
        std = variance ** 0.5
        
        upper = sma + (self.std_dev * std)
        lower = sma - (self.std_dev * std)
        
        return upper, sma, lower
