"""
Supertrend Strategy
==================
Entry: Price crosses above/below Supertrend line
Exit: Reverse signal
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class SupertrendStrategy(BaseStrategy):
    """
    Supertrend Strategy.
    
    Uses ATR-based bands with multiplier.
    - Price above upper band = Uptrend (BUY)
    - Price below lower band = Downtrend (SELL)
    """
    
    name = "Supertrend"
    description = "ATR-based trend indicator"
    
    def __init__(self, period: int = 10, multiplier: float = 3.0):
        self.period = period
        self.multiplier = multiplier
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate Supertrend signal."""
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
        
        # Calculate Supertrend
        closes = [h.get('close', 0) for h in history]
        highs = [h.get('high', 0) for h in history]
        lows = [h.get('low', 0) for h in history]
        
        atr = self._calculate_atr(highs, lows, closes, self.period)
        supertrend, direction = self._calculate_supertrend(
            highs, lows, closes, atr, self.multiplier
        )
        
        current_direction = direction[-1] if direction else 0
        current_st = supertrend[-1] if supertrend else price
        
        # Signal based on direction change
        if len(direction) >= 2:
            prev_direction = direction[-2]
            
            if current_direction == 1 and prev_direction == -1:
                # Bullish reversal
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.STRONG,
                    confidence=0.8,
                    entry_price=price,
                    sl=current_st * 0.998,
                    metadata={
                        'supertrend': current_st,
                        'direction': 'uptrend',
                        'reason': 'Supertrend bullish reversal'
                    }
                )
            
            elif current_direction == -1 and prev_direction == 1:
                # Bearish reversal
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.STRONG,
                    confidence=0.8,
                    entry_price=price,
                    sl=current_st * 1.002,
                    metadata={
                        'supertrend': current_st,
                        'direction': 'downtrend',
                        'reason': 'Supertrend bearish reversal'
                    }
                )
        
        # Current trend
        if current_direction == 1:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=0.6,
                metadata={
                    'supertrend': current_st,
                    'direction': 'uptrend',
                    'reason': 'In uptrend'
                }
            )
        else:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.MEDIUM,
                confidence=0.6,
                metadata={
                    'supertrend': current_st,
                    'direction': 'downtrend',
                    'reason': 'In downtrend'
                }
            )
    
    def _calculate_atr(self, highs, lows, closes, period: int) -> list:
        """Calculate ATR."""
        tr = []
        for i in range(len(highs)):
            if i == 0:
                tr.append(highs[i] - lows[i])
            else:
                hl = highs[i] - lows[i]
                hc = abs(highs[i] - closes[i-1])
                lc = abs(lows[i] - closes[i-1])
                tr.append(max(hl, hc, lc))
        
        atr = []
        for i in range(len(tr)):
            if i < period:
                atr.append(sum(tr[:i+1]) / (i+1))
            else:
                atr.append((atr[-1] * (period - 1) + tr[i]) / period)
        
        return atr
    
    def _calculate_supertrend(self, highs, lows, closes, atr, multiplier: float):
        """Calculate Supertrend line and direction."""
        supertrend = []
        direction = []  # 1 = uptrend, -1 = downtrend
        
        for i in range(len(closes)):
            hl2 = (highs[i] + lows[i]) / 2
            upper_band = hl2 + multiplier * atr[i]
            lower_band = hl2 - multiplier * atr[i]
            
            if i == 0:
                supertrend.append(lower_band)
                direction.append(1)
            else:
                prev_st = supertrend[-1]
                prev_dir = direction[-1]
                
                if closes[i] > prev_st:
                    direction.append(1)
                    supertrend.append(lower_band)
                else:
                    direction.append(-1)
                    supertrend.append(upper_band)
        
        return supertrend, direction
