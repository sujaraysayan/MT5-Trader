"""
Candlestick Pattern Strategy
=========================
Entry: Major candlestick patterns
Exit: Opposite pattern or pattern failure
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class CandlestickPatternStrategy(BaseStrategy):
    """
    Candlestick Pattern Strategy.
    
    Detects common reversal patterns:
    - Bullish Engulfing
    - Bearish Engulfing
    - Hammer
    - Inverted Hammer
    - Doji
    - Morning/Evening Star
    """
    
    name = "Candlestick Pattern"
    description = "Japanese candlestick patterns"
    
    def __init__(self):
        self.patterns_confidence = {
            'bullish_engulfing': 0.75,
            'bearish_engulfing': 0.75,
            'hammer': 0.65,
            'inverted_hammer': 0.60,
            'doji': 0.50,
            'morning_star': 0.70,
            'evening_star': 0.70,
        }
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate Candlestick Pattern signal."""
        price = data.get('price', 0)
        history = data.get('history', [])
        
        if len(history) < 3:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={'reason': 'Not enough data'}
            )
        
        # Get last 3 candles
        candles = []
        for i in range(1, 4):
            if len(history) >= i:
                h = history[-i]
                candles.append({
                    'open': h.get('open', 0),
                    'high': h.get('high', 0),
                    'low': h.get('low', 0),
                    'close': h.get('close', 0),
                })
        
        # Detect patterns
        pattern = self._detect_pattern(candles)
        
        if pattern is None:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={'reason': 'No pattern detected'}
            )
        
        pattern_name = pattern['name']
        signal_type = pattern['signal']
        confidence = self.patterns_confidence.get(pattern_name, 0.5)
        
        if signal_type == 'buy':
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM if confidence >= 0.65 else SignalStrength.WEAK,
                confidence=confidence,
                entry_price=price,
                metadata={
                    'pattern': pattern_name,
                    'reason': f'{pattern_name.replace("_", " ").title()} detected'
                }
            )
        else:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.MEDIUM if confidence >= 0.65 else SignalStrength.WEAK,
                confidence=confidence,
                entry_price=price,
                metadata={
                    'pattern': pattern_name,
                    'reason': f'{pattern_name.replace("_", " ").title()} detected'
                }
            )
    
    def _detect_pattern(self, candles: list) -> Dict:
        """Detect candlestick patterns."""
        if len(candles) < 3:
            return None
        
        c1 = candles[2]  # Oldest
        c2 = candles[1]  # Middle
        c3 = candles[0]  # Most recent
        
        # Bullish Engulfing
        if self._is_bullish_engulfing(c1, c2, c3):
            return {'name': 'bullish_engulfing', 'signal': 'buy'}
        
        # Bearish Engulfing
        if self._is_bearish_engulfing(c1, c2, c3):
            return {'name': 'bearish_engulfing', 'signal': 'sell'}
        
        # Hammer
        if self._is_hammer(c3):
            return {'name': 'hammer', 'signal': 'buy'}
        
        # Inverted Hammer
        if self._is_inverted_hammer(c3):
            return {'name': 'inverted_hammer', 'signal': 'buy'}
        
        # Doji
        if self._is_doji(c3):
            return {'name': 'doji', 'signal': 'hold'}
        
        # Morning Star
        if self._is_morning_star(c1, c2, c3):
            return {'name': 'morning_star', 'signal': 'buy'}
        
        # Evening Star
        if self._is_evening_star(c1, c2, c3):
            return {'name': 'evening_star', 'signal': 'sell'}
        
        return None
    
    def _is_bullish_engulfing(self, c1, c2, c3) -> bool:
        """Bullish Engulfing: Current green engulfs previous red."""
        c1_red = c1['close'] < c1['open']
        c3_green = c3['close'] > c3['open']
        
        if not (c1_red and c3_green):
            return False
        
        # c3 body engulfs c1 body
        return (c3['open'] < c1['close'] and c3['close'] > c1['open'])
    
    def _is_bearish_engulfing(self, c1, c2, c3) -> bool:
        """Bearish Engulfing: Current red engulfs previous green."""
        c1_green = c1['close'] > c1['open']
        c3_red = c3['close'] < c3['open']
        
        if not (c1_green and c3_red):
            return False
        
        # c3 body engulfs c1 body
        return (c3['open'] > c1['close'] and c3['close'] < c1['open'])
    
    def _is_hammer(self, candle) -> bool:
        """Hammer: Small body, long lower shadow, little upper shadow."""
        body = abs(candle['close'] - candle['open'])
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        
        if lower_shadow == 0:
            return False
        
        # Lower shadow at least 2x body
        # Upper shadow less than 10% of total range
        total_range = candle['high'] - candle['low']
        
        return (lower_shadow > body * 2 and 
                upper_shadow < total_range * 0.1 and
                lower_shadow > total_range * 0.5)
    
    def _is_inverted_hammer(self, candle) -> bool:
        """Inverted Hammer: Small body, long upper shadow."""
        body = abs(candle['close'] - candle['open'])
        upper_shadow = candle['high'] - max(candle['open'], candle['close'])
        lower_shadow = min(candle['open'], candle['close']) - candle['low']
        
        if upper_shadow == 0:
            return False
        
        total_range = candle['high'] - candle['low']
        
        return (upper_shadow > body * 2 and
                lower_shadow < total_range * 0.1 and
                upper_shadow > total_range * 0.5)
    
    def _is_doji(self, candle) -> bool:
        """Doji: Open and close are equal or very close."""
        body = abs(candle['close'] - candle['open'])
        total_range = candle['high'] - candle['low']
        
        if total_range == 0:
            return False
        
        return body / total_range < 0.1
    
    def _is_morning_star(self, c1, c2, c3) -> bool:
        """Morning Star: 3-candle reversal pattern."""
        # c1: Red candle
        # c2: Small body (star)
        # c3: Green candle
        c1_red = c1['close'] < c1['open']
        c3_green = c3['close'] > c3['open']
        
        c1_body = abs(c1['close'] - c1['open'])
        c2_body = abs(c2['close'] - c2['open'])
        
        gap_down = c2['high'] < c1['low']
        gap_up = c3['open'] > c2['low']
        
        return (c1_red and c3_green and 
                c2_body < c1_body * 0.3 and
                gap_down and gap_up)
    
    def _is_evening_star(self, c1, c2, c3) -> bool:
        """Evening Star: 3-candle reversal pattern."""
        # c1: Green candle
        # c2: Small body (star)
        # c3: Red candle
        c1_green = c1['close'] > c1['open']
        c3_red = c3['close'] < c3['open']
        
        c1_body = abs(c1['close'] - c1['open'])
        c2_body = abs(c2['close'] - c2['open'])
        
        gap_up = c2['low'] > c1['high']
        gap_down = c3['open'] < c2['high']
        
        return (c1_green and c3_red and
                c2_body < c1_body * 0.3 and
                gap_up and gap_down)
