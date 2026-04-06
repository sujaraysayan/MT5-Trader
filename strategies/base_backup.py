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
    Combines multiple strategies using weighted scoring system.
    
    New Logic:
    1. Convert signals to numbers: BUY=+1, SELL=-1, HOLD=0
    2. Get historical score from DB, convert to weight: weight = 1 / (1 + exp(-score))
    3. Calculate group_score = Σ(weight * signal * confidence) per group
    4. Normalize group scores to get group_weight
    5. Final score = Σ(group_weight * group_score)
    6. Threshold = 0.3 for decision
    7. Market-adjusted final action
    """
    
    def __init__(self, strategies: list, market_type: str = None):
        self.strategies = strategies
        self.market_type = market_type
        self.name = "Composite"
        self.description = "Weighted scoring composite strategy"
    
    def _get_strategy_weight(self, strategy_name: str, all_scores: Dict[str, float] = None) -> float:
        """Get strategy weight from historical score using sigmoid function.
        
        weight = 1 / (1 + exp(-score))
        
        Args:
            strategy_name: Name of the strategy
            all_scores: Optional pre-fetched dict of all scores
        
        Returns:
            float between 0 and 1 (sigmoid of historical score)
        """
        import math
        
        # Get historical score from database (batch or single)
        if all_scores is not None:
            score = all_scores.get(strategy_name, 0)
        else:
            from database import get_strategy_score
            score_data = get_strategy_score(strategy_name)
            score = score_data.get('score', 0)
        
        # Sigmoid function: 1 / (1 + exp(-score))
        weight = 1 / (1 + math.exp(-score))
        
        return weight
    
    def _signal_to_number(self, signal_type: SignalType) -> int:
        """Convert SignalType enum to number."""
        if signal_type == SignalType.BUY:
            return 1
        elif signal_type == SignalType.SELL:
            return -1
        else:
            return 0
    
    def analyze(self, data: Dict, market_type: str = None) -> TradingSignal:
        """Analyze using weighted scoring system with market-adjusted decision."""
        from strategies.mapping import GROUPS
        from database import get_all_strategy_scores
        
        # Determine market type
        active_market = market_type or self.market_type or "trend_bull"
        threshold = 0.3
        
        print(f"\n{'='*60}")
        print(f"MARKET TYPE: {active_market.upper()}")
        print(f"THRESHOLD: {threshold}")
        print(f"{'='*60}")
        
        # Fetch all strategy scores in ONE DB call
        all_scores = get_all_strategy_scores()
        print(f"Strategy historical scores: {all_scores}")
        
        # Step 1: Get all strategy signals
        strategy_results = []
        for strategy in self.strategies:
            sig = strategy.analyze(data)
            
            # Convert signal to number: BUY=+1, SELL=-1, HOLD=0
            signal_num = self._signal_to_number(sig.signal_type)
            
            # Get historical weight (using pre-fetched scores)
            weight = self._get_strategy_weight(strategy.name, all_scores)
            
            # Calculate contribution: weight * signal * confidence
            contribution = weight * signal_num * sig.confidence
            
            print(f"  {strategy.name}: {sig.signal_type.value.upper()}({signal_num:+d}) "
                  f"conf={sig.confidence:.1%} weight={weight:.3f} contrib={contribution:+.4f}")
            
            strategy_results.append({
                'strategy': strategy,
                'signal': sig,
                'signal_num': signal_num,
                'confidence': sig.confidence,
                'weight': weight,
                'contribution': contribution
            })
        
        # Step 2: Calculate group scores
        group_scores = {}
        for group_name, group_strategies in GROUPS.items():
            group_score = 0.0
            group_contributions = []
            
            for result in strategy_results:
                if result['strategy'].name in group_strategies:
                    group_score += result['contribution']
                    group_contributions.append({
                        'name': result['strategy'].name,
                        'contribution': result['contribution']
                    })
            
            group_scores[group_name] = {
                'score': group_score,
                'strategies': group_contributions
            }
            
            print(f"\n  GROUP [{group_name}]: score={group_score:+.4f}")
            for c in group_contributions:
                print(f"    - {c['name']}: {c['contribution']:+.4f}")
        
        # Step 3: Normalize group scores to get group weights
        # group_weight[g] = |group_score[g]| / Σ|group_score|
        total_abs = sum(abs(gs['score']) for gs in group_scores.values())
        
        if total_abs > 0:
            for group_name in group_scores:
                raw_score = group_scores[group_name]['score']
                group_scores[group_name]['weight'] = abs(raw_score) / total_abs
        else:
            # All group scores are 0
            for group_name in group_scores:
                group_scores[group_name]['weight'] = 0.0
        
        print(f"\n  GROUP WEIGHTS:")
        for group_name, gs in group_scores.items():
            print(f"    {group_name}: weight={gs['weight']:.4f}")
        
        # Step 4: Calculate final score
        # final_score = Σ(group_weight * group_score)
        final_score = sum(
            gs['weight'] * gs['score'] 
            for gs in group_scores.values()
        )
        
        print(f"\n  FINAL SCORE: {final_score:+.4f}")
        print(f"  (positive = BUY pressure, negative = SELL pressure, near 0 = unclear)")
        
        # Step 5: Preliminary decision based on threshold
        if final_score > threshold:
            preliminary_action = "BUY"
        elif final_score < -threshold:
            preliminary_action = "SELL"
        else:
            preliminary_action = "NO TRADE"
        
        print(f"  PRELIMINARY: {preliminary_action} (threshold={threshold})")
        
        # Step 6: Market-adjusted final decision
        print(f"\n  MARKET-ADJUSTED DECISION:")
        
        if active_market == "trend_bull":
            if final_score > threshold:
                final_action = "BUY"
                reason = f"Bull trend: BUY because final_score ({final_score:+.4f}) > threshold ({threshold})"
            else:
                final_action = "NO TRADE"
                reason = f"Bull trend: NO TRADE because final_score ({final_score:+.4f}) <= threshold ({threshold})"
                
        elif active_market == "trend_bear":
            if final_score < -threshold:
                final_action = "SELL"
                reason = f"Bear trend: SELL because final_score ({final_score:+.4f}) < -threshold ({-threshold})"
            else:
                final_action = "NO TRADE"
                reason = f"Bear trend: NO TRADE because final_score ({final_score:+.4f}) >= -threshold ({-threshold})"
                
        elif active_market == "sideway":
            # In sideway, inverse logic (mean reversion)
            if final_score > threshold:
                final_action = "SELL"  # Price too high, expect reversion down
                reason = f"Sideway: SELL because final_score ({final_score:+.4f}) > threshold ({threshold})"
            elif final_score < -threshold:
                final_action = "BUY"   # Price too low, expect reversion up
                reason = f"Sideway: BUY because final_score ({final_score:+.4f}) < -threshold ({-threshold})"
            else:
                final_action = "NO TRADE"
                reason = f"Sideway: NO TRADE because final_score ({final_score:+.4f}) near 0"
                
        elif active_market == "volatile":
            if final_score > threshold:
                final_action = "BUY"
                reason = f"Volatile: BUY because final_score ({final_score:+.4f}) > threshold ({threshold})"
            elif final_score < -threshold:
                final_action = "SELL"
                reason = f"Volatile: SELL because final_score ({final_score:+.4f}) < -threshold ({-threshold})"
            else:
                final_action = "NO TRADE"
                reason = f"Volatile: NO TRADE because final_score ({final_score:+.4f}) near 0"
        else:
            # Unknown market type, use preliminary
            final_action = preliminary_action
            reason = f"Unknown market type ({active_market}), using preliminary decision"
        
        print(f"    -> {final_action}")
        print(f"    -> Reason: {reason}")
        
        # Build strategy result list for metadata
        strategy_result_list = [
            {
                "name": r['strategy'].name,
                "signal": r['signal'].signal_type.value,
                "signal_num": r['signal_num'],
                "confidence": r['confidence'],
                "weight": r['weight'],
                "contribution": r['contribution']
            }
            for r in strategy_results
        ]
        
        # Build group scores for metadata
        group_scores_meta = {
            group_name: {
                'score': gs['score'],
                'weight': gs['weight']
            }
            for group_name, gs in group_scores.items()
        }
        
        # Determine signal type and strength
        if final_action == "BUY":
            signal_type = SignalType.BUY
            strength = SignalStrength.STRONG if abs(final_score) > 0.6 else SignalStrength.MEDIUM if abs(final_score) > 0.4 else SignalStrength.WEAK
            confidence = min(abs(final_score) * 1.5, 1.0)  # Scale confidence from score
        elif final_action == "SELL":
            signal_type = SignalType.SELL
            strength = SignalStrength.STRONG if abs(final_score) > 0.6 else SignalStrength.MEDIUM if abs(final_score) > 0.4 else SignalStrength.WEAK
            confidence = min(abs(final_score) * 1.5, 1.0)
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            metadata={
                'signals': strategy_result_list,
                'group_scores': group_scores_meta,
                'final_score': final_score,
                'threshold': threshold,
                'preliminary_action': preliminary_action,
                'reason': reason,
                'market_type': active_market
            }
        )
