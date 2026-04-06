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
    
    Steps (per user spec):
    1. Convert signals to numbers: BUY=+1, SELL=-1, HOLD=0
    2. Get historical score from DB, convert to weight: weight = 1 / (1 + exp(-score))
    3. Calculate group_score = Σ(weight * signal * confidence) per group
    4. Normalize group scores to get group_weight: group_weight[g] = |group_score[g]| / Σ|group_score|
    5. Final score = Σ(group_weight * group_score)
    6. Threshold = 0.3 for decision
    7. Market-adjusted final decision
    """
    
    def __init__(self, strategies: list, market_type: str = None):
        self.strategies = strategies
        self.market_type = market_type
        self.name = "Composite"
        self.description = "Weighted scoring composite strategy"
    
    def _sigmoid(self, x: float) -> float:
        """Sigmoid function: 1 / (1 + exp(-x))"""
        import math
        # Clamp to prevent overflow
        x = max(-700, min(700, x))
        return 1 / (1 + math.exp(-x))
    
    def _signal_to_number(self, signal_type: SignalType) -> int:
        """Convert SignalType enum to number."""
        if signal_type == SignalType.BUY:
            return 1
        elif signal_type == SignalType.SELL:
            return -1
        else:
            return 0
    
    def _get_strategy_weight(self, strategy_name: str, all_scores: Dict[str, float]) -> float:
        """Get strategy weight from historical score using sigmoid function.
        
        weight = 1 / (1 + exp(-score))
        
        Args:
            strategy_name: Name of the strategy
            all_scores: Pre-fetched dict of strategy_name -> score
        
        Returns:
            float between 0 and 1
        """
        score = all_scores.get(strategy_name, 0)
        return self._sigmoid(score)
    
    def analyze(self, data: Dict, market_type: str = None, verbose: bool = True) -> TradingSignal:
        """Analyze using weighted scoring system with market-adjusted decision.
        
        Args:
            data: Market data dictionary
            market_type: Market type (trend_bull, trend_bear, sideway, volatile)
            verbose: If False, suppress all print statements for backtesting
        """
        from strategies.mapping import GROUPS
        from database import get_all_strategy_scores
        import io
        import contextlib
        
        # Suppress output if verbose=False
        if not verbose:
            devnull = io.StringIO()
            with contextlib.redirect_stdout(devnull):
                return self._analyze_impl(data, market_type)
        
        return self._analyze_impl(data, market_type)
    
    def _analyze_impl(self, data: Dict, market_type: str = None) -> TradingSignal:
        """Internal implementation of analyze."""
        from strategies.mapping import GROUPS
        from database import get_all_strategy_scores
        
        # Fixed threshold as per spec
        THRESHOLD = 0.3
        
        # Determine market type
        active_market = market_type or self.market_type or "trend_bull"
        
        print(f"\n{'='*60}")
        print(f"MARKET TYPE: {active_market.upper()}")
        print(f"THRESHOLD: {THRESHOLD}")
        print(f"{'='*60}")
        
        # ============================================================
        # STEP 0: Get all historical scores in ONE DB call
        # ============================================================
        all_scores = get_all_strategy_scores()
        print(f"Strategy historical scores: {all_scores}")
        
        # ============================================================
        # STEP 1: Calculate contribution for EACH strategy
        # contribution = weight * signal_num * confidence
        # ============================================================
        strategy_results = []
        
        for strategy in self.strategies:
            sig = strategy.analyze(data)
            
            # Step 1a: Convert signal to number
            signal_num = self._signal_to_number(sig.signal_type)
            
            # Step 1b: Get historical weight
            weight = self._get_strategy_weight(strategy.name, all_scores)
            
            # Step 1c: Calculate contribution
            contribution = weight * signal_num * sig.confidence
            
            print(f"  {strategy.name}: {sig.signal_type.value.upper()}({signal_num:+d}) "
                  f"conf={sig.confidence:.1%} weight={weight:.3f} contrib={contribution:+.4f}")
            
            strategy_results.append({
                'name': strategy.name,
                'signal': sig.signal_type.value,
                'signal_num': signal_num,
                'confidence': sig.confidence,
                'weight': weight,
                'contribution': contribution
            })
        
        # ============================================================
        # STEP 2: Calculate group scores
        # group_score = Σ(weight * signal * confidence) for strategies in group
        # ============================================================
        group_scores = {}
        
        for group_name, group_strategies_list in GROUPS.items():
            # Sum contributions for strategies that belong to this group
            group_score = sum(
                r['contribution'] 
                for r in strategy_results 
                if r['name'] in group_strategies_list
            )
            
            group_scores[group_name] = {
                'score': group_score,
                'strategies': [
                    r for r in strategy_results 
                    if r['name'] in group_strategies_list
                ]
            }
            
            print(f"\n  GROUP [{group_name}]: score={group_score:+.4f}")
            for r in group_scores[group_name]['strategies']:
                print(f"    - {r['name']}: {r['contribution']:+.4f}")
        
        # ============================================================
        # STEP 3: Normalize group scores to get group weights
        # group_weight[g] = |group_score[g]| / Σ|group_score|
        # ============================================================
        total_abs_score = sum(abs(gs['score']) for gs in group_scores.values())
        
        if total_abs_score > 0:
            for group_name in group_scores:
                raw_score = group_scores[group_name]['score']
                group_scores[group_name]['weight'] = abs(raw_score) / total_abs_score
        else:
            # All group scores are 0 or near-zero
            for group_name in group_scores:
                group_scores[group_name]['weight'] = 0.0
        
        print(f"\n  GROUP WEIGHTS (normalized):")
        for group_name, gs in group_scores.items():
            print(f"    {group_name}: weight={gs['weight']:.4f}, score={gs['score']:+.4f}")
        
        # ============================================================
        # STEP 4: Calculate final score
        # final_score = Σ(group_weight * group_score)
        # ============================================================
        final_score = sum(
            gs['weight'] * gs['score'] 
            for gs in group_scores.values()
        )
        
        print(f"\n  FINAL SCORE: {final_score:+.4f}")
        print(f"  (positive = BUY pressure, negative = SELL pressure, near 0 = unclear)")
        
        # ============================================================
        # STEP 5: Preliminary decision based on threshold
        # ============================================================
        if final_score > THRESHOLD:
            preliminary_action = "BUY"
        elif final_score < -THRESHOLD:
            preliminary_action = "SELL"
        else:
            preliminary_action = "NO_TRADE"
        
        print(f"  PRELIMINARY: {preliminary_action} (threshold={THRESHOLD})")
        
        # ============================================================
        # STEP 6: Market-adjusted final decision
        # ============================================================
        print(f"\n  MARKET-ADJUSTED DECISION:")
        
        if active_market == "trend_bull":
            if final_score > THRESHOLD:
                action = "BUY"
                reason = f"Bull trend: BUY because final_score ({final_score:+.4f}) > threshold ({THRESHOLD})"
            else:
                action = "NO_TRADE"
                reason = f"Bull trend: NO_TRADE because final_score ({final_score:+.4f}) <= threshold ({THRESHOLD})"
                
        elif active_market == "trend_bear":
            if final_score < -THRESHOLD:
                action = "SELL"
                reason = f"Bear trend: SELL because final_score ({final_score:+.4f}) < -threshold ({-THRESHOLD})"
            else:
                action = "NO_TRADE"
                reason = f"Bear trend: NO_TRADE because final_score ({final_score:+.4f}) >= -threshold ({-THRESHOLD})"
                
        elif active_market == "sideway":
            # In sideway, inverse logic (mean reversion)
            if final_score > THRESHOLD:
                action = "SELL"  # Price too high, expect reversion down
                reason = f"Sideway: SELL because final_score ({final_score:+.4f}) > threshold ({THRESHOLD})"
            elif final_score < -THRESHOLD:
                action = "BUY"   # Price too low, expect reversion up
                reason = f"Sideway: BUY because final_score ({final_score:+.4f}) < -threshold ({-THRESHOLD})"
            else:
                action = "NO_TRADE"
                reason = f"Sideway: NO_TRADE because |final_score| ({abs(final_score):.4f}) <= threshold ({THRESHOLD})"
                
        elif active_market == "volatile":
            if final_score > THRESHOLD:
                action = "BUY"
                reason = f"Volatile: BUY because final_score ({final_score:+.4f}) > threshold ({THRESHOLD})"
            elif final_score < -THRESHOLD:
                action = "SELL"
                reason = f"Volatile: SELL because final_score ({final_score:+.4f}) < -threshold ({-THRESHOLD})"
            else:
                action = "NO_TRADE"
                reason = f"Volatile: NO_TRADE because |final_score| ({abs(final_score):.4f}) <= threshold ({THRESHOLD})"
        else:
            # Unknown market type, use preliminary decision
            action = preliminary_action
            reason = f"Unknown market type ({active_market}), using preliminary: {preliminary_action}"
        
        print(f"    -> {action}")
        print(f"    -> Reason: {reason}")
        
        # ============================================================
        # STEP 7: Build TradingSignal
        # ============================================================
        if action == "BUY":
            signal_type = SignalType.BUY
            # confidence based on how strong the BUY signal is (scaled)
            confidence = min(abs(final_score) * 1.5, 1.0)
            strength = (
                SignalStrength.STRONG if abs(final_score) > 0.6 else
                SignalStrength.MEDIUM if abs(final_score) > 0.4 else
                SignalStrength.WEAK
            )
        elif action == "SELL":
            signal_type = SignalType.SELL
            confidence = min(abs(final_score) * 1.5, 1.0)
            strength = (
                SignalStrength.STRONG if abs(final_score) > 0.6 else
                SignalStrength.MEDIUM if abs(final_score) > 0.4 else
                SignalStrength.WEAK
            )
        else:
            signal_type = SignalType.HOLD
            confidence = 0.5
            strength = SignalStrength.WEAK
        
        return TradingSignal(
            strategy_name=self.name,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            metadata={
                'signals': strategy_results,
                'group_scores': {
                    k: {'score': v['score'], 'weight': v['weight']} 
                    for k, v in group_scores.items()
                },
                'final_score': final_score,
                'threshold': THRESHOLD,
                'preliminary_action': preliminary_action,
                'action': action,
                'reason': reason,
                'market_type': active_market
            }
        )
