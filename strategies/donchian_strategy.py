"""
Donchian Channel Strategy
========================
Entry: Price breaks above/below channel
Exit: Price reverses through channel
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class DonchianChannelStrategy(BaseStrategy):
    """
    Donchian Channel Strategy.
    
    Uses:
    - Upper Channel (highest high in period)
    - Lower Channel (lowest low in period)
    - Middle Channel (average of upper and lower)
    
    Entry:
    - Price breaks above upper channel = BUY
    - Price breaks below lower channel = SELL
    """
    
    name = "Donchian Channel"
    description = "Donchian channel breakout"
    
    def __init__(self, period: int = 20):
        self.period = period
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate Donchian Channel signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        if len(history) < self.period:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={'reason': 'Not enough data'}
            )
        
        # Calculate channel
        highs = [h.get('high', 0) for h in history]
        lows = [h.get('low', 0) for h in history]
        
        upper_channel = max(highs[-self.period:])
        lower_channel = min(lows[-self.period:])
        middle_channel = (upper_channel + lower_channel) / 2
        channel_width = upper_channel - lower_channel
        
        # Previous channel
        if len(history) >= self.period + 1:
            prev_upper = max(highs[-(self.period + 1):-1])
            prev_lower = min(lows[-(self.period + 1):-1])
        else:
            prev_upper = upper_channel
            prev_lower = lower_channel
        
        # Breakout detection
        prev_high = highs[-2] if len(highs) >= 2 else highs[-1]
        prev_low = lows[-2] if len(lows) >= 2 else lows[-1]
        
        # Bullish breakout
        if prev_high <= prev_upper and price > upper_channel:
            breakout_pct = (price - upper_channel) / price * 100
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=min(0.8, 0.5 + breakout_pct / 10),
                entry_price=price,
                sl=lower_channel,
                tp=upper_channel + channel_width,
                metadata={
                    'upper': upper_channel,
                    'middle': middle_channel,
                    'lower': lower_channel,
                    'breakout_pct': breakout_pct,
                    'reason': 'Bullish channel breakout'
                }
            )
        
        # Bearish breakdown
        elif prev_low >= prev_lower and price < lower_channel:
            breakdown_pct = (lower_channel - price) / price * 100
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.MEDIUM,
                confidence=min(0.8, 0.5 + breakdown_pct / 10),
                entry_price=price,
                sl=upper_channel,
                tp=lower_channel - channel_width,
                metadata={
                    'upper': upper_channel,
                    'middle': middle_channel,
                    'lower': lower_channel,
                    'breakdown_pct': breakdown_pct,
                    'reason': 'Bearish channel breakdown'
                }
            )
        
        # Inside channel
        if price > middle_channel:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={
                    'position': 'above middle',
                    'reason': 'Price above channel middle'
                }
            )
        else:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={
                    'position': 'below middle',
                    'reason': 'Price below channel middle'
                }
            )
