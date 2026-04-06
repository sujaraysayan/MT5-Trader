"""
Strategy Mapping based on Market Type
Determines which strategy groups to use based on detected market condition
"""

# Strategy group definitions
# Note: Strategy names must match the `name` attribute of each strategy class
GROUPS = {
    "momentum": ["Momentum", "RSI", "Stochastic", "MACD"],
    "trend": ["EMA Crossover", "Supertrend", "MACD", "ADX Trend Strength"],
    "mean_reversion": ["MeanReversion", "RSI", "Stochastic", "Bollinger Bands"],
    "breakout": ["Breakout", "Donchian Channel", "ATR Breakout"],
    "volatility": ["ATR Breakout", "Bollinger Bands"],
    "structure": ["Structure"]
}

# Market type to active groups mapping
MARKET_STRATEGY_MAP = {
    "trend_bull": ["trend", "momentum", "breakout"],
    "trend_bear": ["trend", "momentum", "breakout"],
    "sideway": ["mean_reversion"],
    "volatile": ["breakout", "volatility"]
}


def get_active_strategies(market_type: str) -> list:
    """
    Get list of active strategies based on market type.
    
    Args:
        market_type: Detected market type (trend_bull, trend_bear, sideway, volatile)
    
    Returns:
        List of strategy names to use
    """
    active_groups = MARKET_STRATEGY_MAP.get(market_type, ["momentum", "trend"])
    
    active_strategies = []
    for group in active_groups:
        if group in GROUPS:
            active_strategies.extend(GROUPS[group])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_strategies = []
    for s in active_strategies:
        if s not in seen:
            seen.add(s)
            unique_strategies.append(s)
    
    return unique_strategies


def get_strategy_groups(market_type: str) -> dict:
    """
    Get strategy groups for each market type.
    
    Returns dict with:
    - active_groups: list of group names
    - active_strategies: list of strategy names
    - excluded_strategies: list of strategy names NOT to use
    """
    active_groups = MARKET_STRATEGY_MAP.get(market_type, ["momentum", "trend"])
    
    active_strategies = []
    for group in active_groups:
        if group in GROUPS:
            active_strategies.extend(GROUPS[group])
    
    active_strategies = list(set(active_strategies))
    
    # All available strategies
    all_strategies = []
    for strategies in GROUPS.values():
        all_strategies.extend(strategies)
    all_strategies = list(set(all_strategies))
    
    # Excluded strategies
    excluded_strategies = [s for s in all_strategies if s not in active_strategies]
    
    return {
        "market_type": market_type,
        "active_groups": active_groups,
        "active_strategies": active_strategies,
        "excluded_strategies": excluded_strategies
    }


if __name__ == "__main__":
    for market_type in ["trend_bull", "trend_bear", "sideway", "volatile"]:
        result = get_strategy_groups(market_type)
        print(f"\n{market_type.upper()}:")
        print(f"  Active Groups: {result['active_groups']}")
        print(f"  Active Strategies: {result['active_strategies']}")
        print(f"  Excluded: {result['excluded_strategies']}")
