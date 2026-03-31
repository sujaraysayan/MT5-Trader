"""
ADX Trend Strength Strategy
==========================
Entry: ADX confirms trend strength + DI crossover
Exit: ADX weakens or reverse DI crossover
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class ADXTrendStrategy(BaseStrategy):
    """
    ADX Trend Strength Strategy.
    
    Uses:
    - ADX (14): Trend strength (>25 = strong trend)
    - +DI: Bullish directional indicator
    - -DI: Bearish directional indicator
    
    Entry:
    - +DI crosses above -DI + ADX > 25 = BUY
    - -DI crosses above +DI + ADX > 25 = SELL
    """
    
    name = "ADX Trend Strength"
    description = "ADX-based trend confirmation"
    
    def __init__(self, period: int = 14, adx_threshold: float = 25):
        self.period = period
        self.adx_threshold = adx_threshold
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate ADX trend signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        adx = indicators.get('adx_14', 0)
        plus_di = indicators.get('plus_di', 0)
        minus_di = indicators.get('minus_di', 0)
        
        # Calculate if not available
        if adx == 0 and len(history) >= self.period + 1:
            adx, plus_di, minus_di = self._calculate_adx(history)
        
        # Calculate previous DI values for crossover
        if len(history) >= self.period + 2:
            prev_adx, prev_plus_di, prev_minus_di = self._calculate_adx(history[:-1])
            
            # Bullish DI crossover
            if prev_plus_di <= prev_minus_di and plus_di > minus_di:
                if adx >= self.adx_threshold:
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.BUY,
                        strength=SignalStrength.STRONG,
                        confidence=min(0.9, adx / 50),
                        entry_price=price,
                        metadata={
                            'adx': adx,
                            'plus_di': plus_di,
                            'minus_di': minus_di,
                            'reason': 'Bullish DI crossover + strong trend'
                        }
                    )
                else:
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.BUY,
                        strength=SignalStrength.WEAK,
                        confidence=0.4,
                        metadata={
                            'adx': adx,
                            'plus_di': plus_di,
                            'minus_di': minus_di,
                            'reason': 'Bullish DI crossover, weak trend'
                        }
                    )
            
            # Bearish DI crossover
            elif prev_plus_di >= prev_minus_di and plus_di < minus_di:
                if adx >= self.adx_threshold:
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.SELL,
                        strength=SignalStrength.STRONG,
                        confidence=min(0.9, adx / 50),
                        entry_price=price,
                        metadata={
                            'adx': adx,
                            'plus_di': plus_di,
                            'minus_di': minus_di,
                            'reason': 'Bearish DI crossover + strong trend'
                        }
                    )
                else:
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.SELL,
                        strength=SignalStrength.WEAK,
                        confidence=0.4,
                        metadata={
                            'adx': adx,
                            'plus_di': plus_di,
                            'minus_di': minus_di,
                            'reason': 'Bearish DI crossover, weak trend'
                        }
                    )
        
        # No crossover - trend direction based on DI
        if plus_di > minus_di:
            strength = SignalStrength.MEDIUM if adx >= self.adx_threshold else SignalStrength.WEAK
            confidence = min(0.7, adx / 50) if adx >= self.adx_threshold else 0.4
            
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=strength,
                confidence=confidence,
                metadata={
                    'adx': adx,
                    'plus_di': plus_di,
                    'minus_di': minus_di,
                    'reason': 'Bullish trend, no crossover'
                }
            )
        else:
            strength = SignalStrength.MEDIUM if adx >= self.adx_threshold else SignalStrength.WEAK
            confidence = min(0.7, adx / 50) if adx >= self.adx_threshold else 0.4
            
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=strength,
                confidence=confidence,
                metadata={
                    'adx': adx,
                    'plus_di': plus_di,
                    'minus_di': minus_di,
                    'reason': 'Bearish trend, no crossover'
                }
            )
    
    def _calculate_adx(self, history: list) -> tuple:
        """Calculate ADX, +DI, -DI."""
        highs = [h.get('high', 0) for h in history]
        lows = [h.get('low', 0) for h in history]
        closes = [h.get('close', 0) for h in history]
        
        # Calculate True Range and Directional Movement
        tr_list = []
        plus_dm = []
        minus_dm = []
        
        for i in range(1, len(highs)):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]
            
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
            
            plus_dm.append(high_diff if high_diff > low_diff and high_diff > 0 else 0)
            minus_dm.append(low_diff if low_diff > high_diff and low_diff > 0 else 0)
        
        # Smooth values
        atr = sum(tr_list[-self.period:]) / self.period if len(tr_list) >= self.period else sum(tr_list) / len(tr_list)
        plus_di = 100 * sum(plus_dm[-self.period:]) / atr / self.period if atr > 0 else 0
        minus_di = 100 * sum(minus_dm[-self.period:]) / atr / self.period if atr > 0 else 0
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        adx = dx  # Simplified
        
        return adx, plus_di, minus_di
