"""
Momentum Strategy
================
Trend-following strategy using RSI and ADX.
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class MomentumStrategy(BaseStrategy):
    """
    Momentum-based trend following strategy.
    
    Entry:
    - RSI crosses above 50 (bullish) or below 50 (bearish)
    - ADX > 25 confirms trend strength
    
    Exit:
    - RSI crosses back
    - ADX drops below 20
    """
    
    name = "Momentum"
    description = "Trend following using RSI and ADX"
    
    def __init__(self, rsi_period: int = 14, adx_period: int = 14):
        self.rsi_period = rsi_period
        self.adx_period = adx_period
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate momentum signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        
        rsi = indicators.get('rsi_14', 50)
        adx = indicators.get('adx_14', 0)
        plus_di = indicators.get('plus_di', 0)
        minus_di = indicators.get('minus_di', 0)
        
        # Calculate RSI trend
        rsi_prev = indicators.get('rsi_14_prev', 50)
        
        # Signals
        if adx > 25:  # Strong trend
            if plus_di > minus_di and rsi > 50:
                # Bullish momentum
                confidence = min(0.9, (adx / 100) * (rsi / 100))
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.STRONG if adx > 40 else SignalStrength.MEDIUM,
                    confidence=confidence,
                    entry_price=price,
                    metadata={
                        'rsi': rsi,
                        'adx': adx,
                        'reason': 'Bullish momentum confirmed'
                    }
                )
            elif minus_di > plus_di and rsi < 50:
                # Bearish momentum
                confidence = min(0.9, (adx / 100) * ((100 - rsi) / 100))
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.STRONG if adx > 40 else SignalStrength.MEDIUM,
                    confidence=confidence,
                    entry_price=price,
                    metadata={
                        'rsi': rsi,
                        'adx': adx,
                        'reason': 'Bearish momentum confirmed'
                    }
                )
        
        # Weak/no trend
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={
                'rsi': rsi,
                'adx': adx,
                'reason': 'No strong momentum'
            }
        )
