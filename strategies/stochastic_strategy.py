"""
Stochastic Strategy
=================
Entry: Stochastic crosses oversold/overbought levels
Exit: Reverse crossover
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class StochasticStrategy(BaseStrategy):
    """
    Stochastic Oscillator Strategy.
    
    Uses:
    - %K line (main)
    - %D line (signal)
    
    Entry:
    - %K crosses above %D in oversold zone (<20) = BUY
    - %K crosses below %D in overbought zone (>80) = SELL
    """
    
    name = "Stochastic"
    description = "Stochastic oscillator signals"
    
    def __init__(self, k_period: int = 14, d_period: int = 3, overbought: float = 80, oversold: float = 20):
        self.k_period = k_period
        self.d_period = d_period
        self.overbought = overbought
        self.oversold = oversold
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate Stochastic signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        # Get Stochastic values or calculate
        stoch_k = indicators.get('stoch_k', 50)
        
        if stoch_k == 50 and len(history) >= self.k_period:
            stoch_k, stoch_d = self._calculate_stochastic(history)
        else:
            stoch_d = indicators.get('stoch_d', 50)
        
        # Crossover detection
        if len(history) >= self.k_period + 1:
            prev_stoch_k, prev_stoch_d = self._calculate_stochastic(history[:-1])
            
            # Bullish crossover in oversold
            if prev_stoch_k <= prev_stoch_d and stoch_k > stoch_d:
                if stoch_k < self.oversold:
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.BUY,
                        strength=SignalStrength.MEDIUM,
                        confidence=0.7,
                        entry_price=price,
                        metadata={
                            'stoch_k': stoch_k,
                            'stoch_d': stoch_d,
                            'reason': 'Bullish crossover in oversold'
                        }
                    )
            
            # Bearish crossover in overbought
            elif prev_stoch_k >= prev_stoch_d and stoch_k < stoch_d:
                if stoch_k > self.overbought:
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.SELL,
                        strength=SignalStrength.MEDIUM,
                        confidence=0.7,
                        entry_price=price,
                        metadata={
                            'stoch_k': stoch_k,
                            'stoch_d': stoch_d,
                            'reason': 'Bearish crossover in overbought'
                        }
                    )
        
        # Overbought/Oversold signals without crossover
        if stoch_k < self.oversold:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={
                    'stoch_k': stoch_k,
                    'stoch_d': stoch_d,
                    'reason': 'Stochastic oversold'
                }
            )
        
        elif stoch_k > self.overbought:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={
                    'stoch_k': stoch_k,
                    'stoch_d': stoch_d,
                    'reason': 'Stochastic overbought'
                }
            )
        
        # Neutral
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={
                'stoch_k': stoch_k,
                'stoch_d': stoch_d,
                'reason': 'Stochastic neutral'
            }
        )
    
    def _calculate_stochastic(self, history: list) -> tuple:
        """Calculate Stochastic %K and %D."""
        if len(history) < self.k_period:
            return 50, 50
        
        lows = [h.get('low', 0) for h in history]
        highs = [h.get('high', 0) for h in history]
        closes = [h.get('close', 0) for h in history]
        
        # Calculate %K values
        k_values = []
        for i in range(self.k_period - 1, len(closes)):
            low_n = min(lows[i - self.k_period + 1:i + 1])
            high_n = max(highs[i - self.k_period + 1:i + 1])
            
            if high_n != low_n:
                k = 100 * (closes[i] - low_n) / (high_n - low_n)
            else:
                k = 50
            
            k_values.append(k)
        
        # %D is SMA of %K
        k_values_arr = k_values[-self.d_period:] if len(k_values) >= self.d_period else k_values
        d = sum(k_values_arr) / len(k_values_arr)
        k = k_values[-1] if k_values else 50
        
        return k, d
