"""
Base Strategy Class
==================
Abstract base class for all trading strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum


class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class SignalStrength(Enum):
    WEAK = 1
    MEDIUM = 2
    STRONG = 3


@dataclass
class TradingSignal:
    """Trading signal data class."""
    strategy_name: str
    signal_type: SignalType
    strength: SignalStrength
    confidence: float  # 0.0 to 1.0
    entry_price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    metadata: Optional[Dict] = None
    
    def __str__(self):
        return f"{self.strategy_name}: {self.signal_type.value.upper()} ({self.strength.name}) - {self.confidence:.0%}"


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    
    All strategies must implement:
    - analyze(): Generate signal from indicators
    - name: Strategy name
    """
    
    name: str = "BaseStrategy"
    description: str = "Base strategy description"
    
    @abstractmethod
    def analyze(self, data: Dict) -> TradingSignal:
        """
        Analyze market data and generate signal.
        
        Args:
            data: Dictionary containing:
                - price: Current price
                - indicators: Technical indicators dict
                - timeframe: Current timeframe
                
        Returns:
            TradingSignal object
        """
        pass
    
    def calculate_position_size(self, signal: TradingSignal, 
                                 account_balance: float,
                                 risk_per_trade: float = 0.02) -> float:
        """
        Calculate position size based on risk.
        
        Args:
            signal: TradingSignal with SL
            account_balance: Account balance
            risk_per_trade: Risk percentage (default 2%)
            
        Returns:
            Position size in lots
        """
        if signal.sl is None or signal.entry_price is None:
            return 0.0
        
        risk_amount = account_balance * risk_per_trade
        price_risk = abs(signal.entry_price - signal.sl)
        
        if price_risk == 0:
            return 0.0
        
        # Convert to lot size (Gold is usually 100 oz per lot)
        lot_size = risk_amount / price_risk
        return max(0.01, round(lot_size, 2))  # Min 0.01 lot


class CompositeStrategy(BaseStrategy):
    """
    Combines multiple strategies for consensus trading.
    """
    
    def __init__(self, strategies: list):
        self.strategies = strategies
        self.name = "Composite"
        self.description = "Combines multiple strategies"
    
    def analyze(self, data: Dict) -> TradingSignal:
        """Analyze using all strategies and find consensus.
        
        Logic:
        1. If BUY count >= 3 → BUY
        2. If SELL count >= 3 → SELL
        3. If BUY == SELL → compare avg confidence
        4. Otherwise → HOLD
        """
        signals = []
        strategy_result_list = []
        for strategy in self.strategies:
            sig = strategy.analyze(data)
            signals.append(sig)
            strategy_result_list.append({"name": strategy.name, "signal": sig.signal_type.value, "confidence": sig.confidence})
        
        # Count signals
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
      
        buy_count = len(buy_signals)
        sell_count = len(sell_signals)
        
        # Calculate average confidence
        avg_buy_conf = sum(s.confidence for s in buy_signals) / buy_count if buy_count > 0 else 0
        avg_sell_conf = sum(s.confidence for s in sell_signals) / sell_count if sell_count > 0 else 0
        
        # Decision logic
        if buy_count >= 3 and sell_count >= 3:
            # Both have enough signals - compare counts then confidence
            if buy_count > sell_count:
                # Check avg confidence > 50%
                if avg_buy_conf > 0.5:
                    reason = f"BUY: {buy_count} > {sell_count} strategies, conf {avg_buy_conf:.1%}"
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.BUY,
                        strength=SignalStrength.STRONG if buy_count > 6 else SignalStrength.MEDIUM,
                        confidence=avg_buy_conf,
                        metadata={'signals': strategy_result_list, 'reason': reason}
                    )
                else:
                    reason = f"HOLD: BUY signal but avg confidence {avg_buy_conf:.1%} <= 50%"
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.HOLD,
                        strength=SignalStrength.WEAK,
                        confidence=avg_buy_conf,
                        metadata={'signals': strategy_result_list, 'reason': reason}
                    )
            elif sell_count > buy_count:
                # Check avg confidence > 50%
                if avg_sell_conf > 0.5:
                    reason = f"SELL: {sell_count} > {buy_count} strategies, conf {avg_sell_conf:.1%}"
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.SELL,
                        strength=SignalStrength.STRONG if sell_count > 6 else SignalStrength.MEDIUM,
                        confidence=avg_sell_conf,
                        metadata={'signals': strategy_result_list, 'reason': reason}
                    )
                else:
                    reason = f"HOLD: SELL signal but avg confidence {avg_sell_conf:.1%} <= 50%"
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.HOLD,
                        strength=SignalStrength.WEAK,
                        confidence=avg_sell_conf,
                        metadata={'signals': strategy_result_list, 'reason': reason}
                    )
            else:
                # Equal counts - tie breaker by confidence (must be > 50%)
                if avg_buy_conf > avg_sell_conf and avg_buy_conf > 0.5:
                    reason = f"TIE BUY: {buy_count}={sell_count}, conf {avg_buy_conf:.1%} > {avg_sell_conf:.1%}"
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.BUY,
                        strength=SignalStrength.MEDIUM,
                        confidence=avg_buy_conf,
                        metadata={'signals': strategy_result_list, 'reason': reason}
                    )
                elif avg_sell_conf > avg_buy_conf and avg_sell_conf > 0.5:
                    reason = f"TIE SELL: {buy_count}={sell_count}, conf {avg_sell_conf:.1%} > {avg_buy_conf:.1%}"
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.SELL,
                        strength=SignalStrength.MEDIUM,
                        confidence=avg_sell_conf,
                        metadata={'signals': strategy_result_list, 'reason': reason}
                    )
                else:
                    reason = f"HOLD: TIE but avg confidence <= 50%"
                    return TradingSignal(
                        strategy_name=self.name,
                        signal_type=SignalType.HOLD,
                        strength=SignalStrength.WEAK,
                        confidence=0.5,
                        metadata={'signals': strategy_result_list, 'reason': reason}
                    )
        elif buy_count >= 3:
            # Only BUY has enough signals - check avg confidence > 50%
            if avg_buy_conf > 0.5:
                reason = f"BUY: {buy_count} strategies >= 3, conf {avg_buy_conf:.1%}"
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.STRONG if buy_count > 6 else SignalStrength.MEDIUM,
                    confidence=avg_buy_conf,
                    metadata={'signals': strategy_result_list, 'reason': reason}
                )
            else:
                reason = f"HOLD: BUY signal but avg confidence {avg_buy_conf:.1%} <= 50%"
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.HOLD,
                    strength=SignalStrength.WEAK,
                    confidence=avg_buy_conf,
                    metadata={'signals': strategy_result_list, 'reason': reason}
                )
        elif sell_count >= 3:
            # Only SELL has enough signals - check avg confidence > 50%
            if avg_sell_conf > 0.5:
                reason = f"SELL: {sell_count} strategies >= 3, conf {avg_sell_conf:.1%}"
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.STRONG if sell_count > 6 else SignalStrength.MEDIUM,
                    confidence=avg_sell_conf,
                    metadata={'signals': strategy_result_list, 'reason': reason}
                )
            else:
                reason = f"HOLD: SELL signal but avg confidence {avg_sell_conf:.1%} <= 50%"
                return TradingSignal(
                    strategy_name=self.name,
                    signal_type=SignalType.HOLD,
                    strength=SignalStrength.WEAK,
                    confidence=avg_sell_conf,
                    metadata={'signals': strategy_result_list, 'reason': reason}
                )
        else:
            # Not enough signals (both must be >= 3)
            reason = f"HOLD: BUY={buy_count}, SELL={sell_count} (need both >= 3)"
            return TradingSignal(
                strategy_name=self.name,
                signal_type=SignalType.HOLD,
                strength=SignalStrength.WEAK,
                confidence=0.5,
                metadata={'signals': strategy_result_list, 'reason': reason}
            )
