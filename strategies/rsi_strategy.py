"""
RSI Strategy
============
Entry: RSI exits overbought/oversold zone
Exit: RSI enters opposite zone
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class RSIStrategy(BaseStrategy):
    """
    RSI Strategy.
    
    Uses RSI (Relative Strength Index):
    - RSI > 70 = Overbought
    - RSI < 30 = Oversold
    
    Entry:
    - RSI crosses below 70 (from overbought) = SELL
    - RSI crosses above 30 (from oversold) = BUY
    """
    
    name = "RSI"
    description = "RSI overbought/oversold signals"
    
    def __init__(self, period: int = 14, overbought: float = 70, oversold: float = 30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate RSI signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        # Get RSI from indicators or calculate
        rsi = indicators.get('rsi_14', 50)
        
        if rsi == 50 and len(history) >= self.period + 1:
            rsi = self._calculate_rsi(history)
        
        # Calculate previous RSI for crossover detection
        if len(history) >= self.period + 2:
            prev_rsi = self._calculate_rsi(history[:-1])
            
            # RSI crosses below overbought - SELL
            if prev_rsi >= self.overbought and rsi < self.overbought:
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.STRONG,
                    confidence=0.75,
                    entry_price=price,
                    metadata={
                        'rsi': rsi,
                        'prev_rsi': prev_rsi,
                        'reason': 'RSI exits overbought'
                    }
                )
            
            # RSI crosses above oversold - BUY
            elif prev_rsi <= self.oversold and rsi > self.oversold:
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.STRONG,
                    confidence=0.75,
                    entry_price=price,
                    metadata={
                        'rsi': rsi,
                        'prev_rsi': prev_rsi,
                        'reason': 'RSI exits oversold'
                    }
                )
        
        # Still in overbought zone
        if rsi > self.overbought:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.WEAK,
                confidence=min(0.6, (rsi - self.overbought) / 30),
                metadata={
                    'rsi': rsi,
                    'reason': 'RSI overbought'
                }
            )
        
        # Still in oversold zone
        elif rsi < self.oversold:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.WEAK,
                confidence=min(0.6, (self.oversold - rsi) / 30),
                metadata={
                    'rsi': rsi,
                    'reason': 'RSI oversold'
                }
            )
        
        # Neutral zone
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={
                'rsi': rsi,
                'reason': 'RSI neutral'
            }
        )
    
    def _calculate_rsi(self, history: list) -> float:
        """Calculate RSI."""
        closes = [h.get('close', 0) for h in history]
        
        if len(closes) < self.period + 1:
            return 50
        
        # Calculate price changes
        deltas = []
        for i in range(1, len(closes)):
            deltas.append(closes[i] - closes[i-1])
        
        # Separate gains and losses
        gains = [d if d > 0 else 0 for d in deltas[-self.period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-self.period:]]
        
        # Calculate averages
        avg_gain = sum(gains) / self.period
        avg_loss = sum(losses) / self.period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
