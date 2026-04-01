"""
Volume Spike Strategy
====================
Entry: Unusual volume spike with price move
Exit: Volume normalizes or trend reverses
"""

from typing import Dict
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength


class VolumeSpikeStrategy(BaseStrategy):
    """
    Volume Spike Strategy.
    
    Uses:
    - Volume relative to moving average
    - Price direction on spike
    
    Entry:
    - Volume spikes + price up = BUY
    - Volume spikes + price down = SELL
    """
    
    name = "Volume Spike"
    description = "Volume spike confirmation"
    
    def __init__(self, volume_ma_period: int = 20, spike_multiplier: float = 2.0):
        self.volume_ma_period = volume_ma_period
        self.spike_multiplier = spike_multiplier
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Generate Volume Spike signal."""
        indicators = data.get('indicators', {})
        price = data.get('price', 0)
        history = data.get('history', [])
        
        if len(history) < self.volume_ma_period + 1:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={'reason': 'Not enough data'}
            )
        
        # Get volumes
        volumes = [h.get('volume', 0) for h in history]
        current_volume = volumes[-1] if volumes else 0
        
        # Calculate volume MA
        volume_ma = sum(volumes[-self.volume_ma_period:]) / self.volume_ma_period
        
        # Calculate volume spike
        if volume_ma > 0:
            volume_ratio = current_volume / volume_ma
        else:
            volume_ratio = 1.0
        
        # Price change - safe division
        closes = [h.get('close', 0) for h in history]
        if len(closes) >= 2 and closes[-2] > 0:
            price_change = (closes[-1] - closes[-2]) / closes[-2] * 100
        else:
            price_change = 0
        
        # Spike detection
        is_spike = volume_ratio >= self.spike_multiplier
        
        if is_spike and price_change > 0:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                confidence=min(0.8, volume_ratio / 4),
                entry_price=price,
                metadata={
                    'volume': current_volume,
                    'volume_ma': volume_ma,
                    'volume_ratio': volume_ratio,
                    'price_change': price_change,
                    'reason': 'Volume spike + price up'
                }
            )
        
        elif is_spike and price_change < 0:
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.SELL,
                strength=SignalStrength.MEDIUM,
                confidence=min(0.8, volume_ratio / 4),
                entry_price=price,
                metadata={
                    'volume': current_volume,
                    'volume_ma': volume_ma,
                    'volume_ratio': volume_ratio,
                    'price_change': price_change,
                    'reason': 'Volume spike + price down'
                }
            )
        
        # High volume without spike
        elif volume_ratio > 1.5:
            if price_change > 0:
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.WEAK,
                    confidence=0.5,
                    metadata={
                        'volume_ratio': volume_ratio,
                        'price_change': price_change,
                        'reason': 'High volume, price up'
                    }
                )
            else:
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.WEAK,
                    confidence=0.5,
                    metadata={
                        'volume_ratio': volume_ratio,
                        'price_change': price_change,
                        'reason': 'High volume, price down'
                    }
                )
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            metadata={
                'volume_ratio': volume_ratio,
                'reason': 'Normal volume'
            }
        )
