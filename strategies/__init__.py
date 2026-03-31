# Strategies Package - All 13 Trading Strategies
from strategies.base import BaseStrategy, TradingSignal, SignalType, SignalStrength

# Original strategies
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.breakout import BreakoutStrategy
from strategies.structure import StructureStrategy

# New strategies (1-13)
from strategies.ema_crossover import EMACrossoverStrategy
from strategies.supertrend import SupertrendStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.adx_trend import ADXTrendStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.bollinger_strategy import BollingerBandsStrategy
from strategies.stochastic_strategy import StochasticStrategy
from strategies.donchian_strategy import DonchianChannelStrategy
from strategies.atr_breakout_strategy import ATRBreakoutStrategy
from strategies.sr_break_strategy import SRBreakStrategy
from strategies.volume_spike_strategy import VolumeSpikeStrategy
from strategies.ma_slope_strategy import MASlopeStrategy
from strategies.candlestick_pattern_strategy import CandlestickPatternStrategy

# All 13 strategies list
ALL_STRATEGIES = [
    MomentumStrategy(),           # 1
    MeanReversionStrategy(),     # 2
    BreakoutStrategy(),           # 3
    StructureStrategy(),         # 4
    EMACrossoverStrategy(),       # 5
    SupertrendStrategy(),        # 6
    MACDStrategy(),              # 7
    ADXTrendStrategy(),          # 8
    RSIStrategy(),               # 9
    BollingerBandsStrategy(),    # 10
    StochasticStrategy(),       # 11
    DonchianChannelStrategy(),   # 12
    ATRBreakoutStrategy(),       # 13 (using as 13th)
    # Note: SR Break, Volume Spike, MA Slope, Candlestick could replace some above
    # Keeping 13 total strategies
]

__all__ = [
    'BaseStrategy',
    'TradingSignal',
    'SignalType',
    'SignalStrength',
    # Original
    'MomentumStrategy',
    'MeanReversionStrategy',
    'BreakoutStrategy',
    'StructureStrategy',
    # New
    'EMACrossoverStrategy',
    'SupertrendStrategy',
    'MACDStrategy',
    'ADXTrendStrategy',
    'RSIStrategy',
    'BollingerBandsStrategy',
    'StochasticStrategy',
    'DonchianChannelStrategy',
    'ATRBreakoutStrategy',
    'SRBreakStrategy',
    'VolumeSpikeStrategy',
    'MASlopeStrategy',
    'CandlestickPatternStrategy',
    # Lists
    'ALL_STRATEGIES',
]
