"""
MT5 Gold Trader - Main Trading System
====================================
AI-powered gold trading with real-time dashboard.

Usage:
    # Normal trading (production)
    python main.py
    
    # Backtest mode
    python main.py --backtest --days 365
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import modules
from mt5.connection import MT5Connection
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.breakout import BreakoutStrategy
from strategies.structure import StructureStrategy
from strategies.ema_crossover import EMACrossoverStrategy
from strategies.supertrend import SupertrendStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.adx_trend import ADXTrendStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.bollinger_strategy import BollingerBandsStrategy
from strategies.stochastic_strategy import StochasticStrategy
from strategies.donchian_strategy import DonchianChannelStrategy
from strategies.atr_breakout_strategy import ATRBreakoutStrategy
from strategies.base import CompositeStrategy, TradingSignal, SignalType
from database import (
    init_database, save_signal, get_recent_signals,
    open_trade, close_trade, get_open_trades,
    record_equity, TradeRecord, SignalRecord, save_decision,
    save_position_snapshot, save_market_snapshot, get_all_strategy_scores
)


class TradingSystem:
    """
    Main trading system that:
    1. Connects to MT5
    2. Generates signals from 13 strategies
    3. Saves data to database
    4. Provides data for dashboard
    """
    
    def __init__(self):
        self.mt5 = None
        self.strategies = []
        self.composite = None
        self.running = False
        self.symbol = "GOLD"
        
        # Trading settings
        self.settings = self._load_settings()
        
        # Initialize
        self._init_database()
        self._init_strategies()
    
    def _load_settings(self):
        """Load trading settings from file."""
        import json
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                logger.info(f"Settings loaded: {settings}")
                return settings
        except Exception as e:
            logger.warning(f"Could not load settings: {e}")
        
        # Default settings
        return {
            'lot_min': 0.01,
            'lot_max': 0.1,
            'tp_percent': 1.5,
            'sl_percent': 1.0
        }
    
    def get_lot_size(self, confidence):
        """Calculate lot size based on confidence."""
        lot_min = self.settings.get('lot_min', 0.01)
        lot_max = self.settings.get('lot_max', 0.1)
        
        # Formula: lot = min + (max - min) * confidence
        lot = lot_min + (lot_max - lot_min) * confidence
        
        # Round to 2 decimal places
        lot = round(lot, 2)
        
        # Clamp between min and max
        lot = max(lot_min, min(lot, lot_max))
        
        return lot
    
    def _init_database(self):
        """Initialize database."""
        os.makedirs('data', exist_ok=True)
        init_database()
        logger.info("Database initialized")
    
    def _init_strategies(self):
        """Initialize all 13 trading strategies."""
        self.strategies = [
            MomentumStrategy(),            # 1. Momentum
            MeanReversionStrategy(),       # 2. Mean Reversion
            BreakoutStrategy(),            # 3. Breakout
            StructureStrategy(),            # 4. Structure
            EMACrossoverStrategy(),        # 5. EMA Crossover
            SupertrendStrategy(),          # 6. Supertrend
            MACDStrategy(),                # 7. MACD
            ADXTrendStrategy(),           # 8. ADX Trend Strength
            RSIStrategy(),                # 9. RSI
            BollingerBandsStrategy(),       # 10. Bollinger Bands
            StochasticStrategy(),          # 11. Stochastic
            DonchianChannelStrategy(),     # 12. Donchian Channel
            ATRBreakoutStrategy(),         # 13. ATR Breakout
        ]
        self.composite = CompositeStrategy(self.strategies)
        logger.info(f"Loaded {len(self.strategies)} strategies")
    
    def connect_mt5(self) -> bool:
        """Connect to MT5."""
        self.mt5 = MT5Connection()
        
        if self.mt5.is_connected():
            logger.info("MT5 connected successfully")
            
            # Get account info
            acc = self.mt5.get_account_info()
            if acc:
                logger.info(f"Account: {acc['balance']:,.2f} {acc['currency']}")
            
            return True
        else:
            logger.warning("MT5 not connected - running in simulation mode")
            return False
    
    def disconnect_mt5(self):
        """Disconnect from MT5."""
        if self.mt5:
            self.mt5.disconnect()
            logger.info("MT5 disconnected")
    
    def get_market_data(self) -> dict:
        """Get current market data and indicators."""
        if self.mt5 and self.mt5.is_connected():
            # Get M15 candle
            candle = self.mt5.get_latest_candle(self.symbol, timeframe=15)
            
            # Get M15 indicators
            indicators = self.mt5.get_indicators(self.symbol, timeframe=15)
            
            # Get recent candles for history-based strategies
            rates = self.mt5.get_rates(self.symbol, timeframe=15, count=50)
            history = []
            if rates is not None and len(rates) > 0:
                for r in rates:
                    history.append({
                        'open': r[1],
                        'high': r[2],
                        'low': r[3],
                        'close': r[4],
                        'volume': r[5]
                    })
            logger.info("######### Actual Market data retrieved #########")
            
            return {
                'price': candle['close'] if candle else 0,
                'indicators': indicators,
                'history': history,
                'timeframe': 'M15'
            }
        else:
            # Simulation mode
            logger.info("********* Simulation Market data retrieved *********")
            
            return {
                'price': 2650 + (datetime.now().minute % 100),
                'indicators': {
                    'rsi_14': 45 + (datetime.now().second % 30),
                    'macd': 10,
                    'macd_signal': 8,
                    'macd_hist': 2,
                    'bb_upper': 2700,
                    'bb_middle': 2650,
                    'bb_lower': 2600,
                    'atr_14': 50,
                    'adx_14': 25,
                    'plus_di': 30,
                    'minus_di': 25,
                    'stoch_k': 50,
                    'sma_20': 2640,
                    'sma_50': 2620
                },
                'history': [],
                'timeframe': 'M15'
            }
    
    def analyze_and_signal(self, market_type: str = None) -> TradingSignal:
        """Analyze market and generate signal with market-aware strategy selection."""
        data = self.get_market_data()
        signal = self.composite.analyze(data, market_type=market_type)
        
        # Save signal to database
        signal_record = SignalRecord(
            strategy=signal.strategy_name,
            signal_type=signal.signal_type.value,
            strength=signal.strength.name,
            confidence=signal.confidence,
            price=data['price'],
            timeframe=data['timeframe'],
            sl=signal.sl,
            tp=signal.tp,
            metadata=signal.metadata
        )
        
        try:
            signal_id = save_signal(signal_record)
            logger.debug(f"Signal saved: ID={signal_id}")
        except Exception as e:
            logger.error(f"Failed to save signal: {e}")
        
        return signal
    
    def execute_trade(self, signal: TradingSignal):
        """Execute trade based on signal."""
        print(f"execute_trade: {signal.signal_type.value.upper()} (conf {signal.confidence:.1%})")
        # Check confidence > 45%
        if signal.confidence <= 0.45:
            logger.info(f"Skipping order: confidence {signal.confidence:.0%} <= 45%")
            # Save HOLD decision
            data = self.get_market_data()
            strategies_list = signal.metadata.get('signals', []) if signal.metadata else []
            save_decision(
                action="HOLD",
                reason=f"Confidence {signal.confidence:.0%} <= 45%, skipped",
                price=data['price'],
                volume=0,
                profit=0,
                position_id=None,
                strategies_analyzed=strategies_list,
                final_decision="hold",
                confidence=signal.confidence
            )
            return
        
        # Calculate position size
        account_balance = 500
        if self.mt5 and self.mt5.is_connected():
            acc = self.mt5.get_account_info()
            if acc:
                account_balance = acc['balance']
        
        price = signal.entry_price or self.get_market_data()['price']
        
        # Calculate lot size based on confidence
        volume = self.get_lot_size(signal.confidence)
        
        # === SEND REAL ORDER TO MT5 ===
        if self.mt5 and self.mt5.is_connected():
            try:
                import MetaTrader5 as mt5
                mt5.initialize()
                time.sleep(1)
                # Ensure symbol is selected
                mt5.symbol_select(self.symbol, True)
                
                # Get symbol info with retry
                symbol_info = None
                for attempt in range(3):
                    symbol_info = mt5.symbol_info(self.symbol)
                    if symbol_info:
                        break
                    time.sleep(0.5)
                
                if not symbol_info:
                    logger.error(f"Symbol {self.symbol} not found after 3 attempts")
                    return
                
                # Determine order type and price
                if signal.signal_type.value == 'buy':
                    order_type = mt5.ORDER_TYPE_BUY
                    trade_price = symbol_info.ask
                else:
                    order_type = mt5.ORDER_TYPE_SELL
                    trade_price = symbol_info.bid
                
                # Calculate SL and TP based on percentage settings
                sl_percent = self.settings.get('sl_percent', 1.0) / 100
                tp_percent = self.settings.get('tp_percent', 1.5) / 100
                
                if signal.signal_type.value == 'buy':
                    sl_price = trade_price * (1 - sl_percent)
                    tp_price = trade_price * (1 + tp_percent)
                else:
                    sl_price = trade_price * (1 + sl_percent)
                    tp_price = trade_price * (1 - tp_percent)
                
                logger.info(f"Lot: {volume} (conf: {signal.confidence:.0%})")
                logger.info(f"SL: {sl_price:.2f}, TP: {tp_price:.2f} ({sl_percent*100:.1f}% / {tp_percent*100:.1f}%)")
                
                # Prepare request as dictionary
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": float(volume),
                    "type": order_type,
                    "price": float(trade_price),
                    "sl": float(sl_price),
                    "tp": float(tp_price),
                    "deviation": 20,
                    "magic": 20260330,
                    "comment": f"AI:{signal.strategy_name[:10]}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC
                }
                logger.info(f"Sending {signal.signal_type.value.upper()} order: {volume} lots @ {trade_price}")
                # Send order
                result = mt5.order_send(request)
                logger.info(f"Order result: {result}")
                
                if result:
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        logger.info(f"ORDER SENT! ID={result.order} {signal.signal_type.value.upper()} {volume} lots @ {trade_price}")
                        logger.info(f"SL: {sl_price:.2f}, TP: {tp_price:.2f}")
                        
                        # Record in database
                        trade = TradeRecord(
                            symbol=self.symbol,
                            direction=signal.signal_type.value,
                            entry_price=trade_price,
                            volume=volume,
                            strategy=signal.strategy_name,
                            sl=sl_price,
                            tp=tp_price
                        )
                        trade_id = open_trade(trade)
                        
                        # Save decision to history
                        strategies_list = [
                            {"name": s['name'], "signal": s['signal'], "confidence": s['confidence']}
                            for s in signal.metadata.get('signals', [])
                        ]
                        save_decision(
                            action=signal.signal_type.value.upper(),
                            reason=signal.metadata.get('reason', ''),
                            price=trade_price,
                            volume=volume,
                            profit=0,
                            position_id=trade_id,
                            strategies_analyzed=strategies_list,
                            final_decision=signal.signal_type.value,
                            confidence=signal.confidence
                        )
                    else:
                        error_name = f"CODE_{result.retcode}"
                        logger.error(f"ORDER FAILED: {error_name} (retcode={result.retcode})")
                        logger.error(f"   Comment: {result.comment}")
                else:
                    logger.error(f"ORDER FAILED: No result")
                    logger.error(f"   Last error: {mt5.last_error()}")
                    
            except Exception as e:
                logger.error(f"Order execution error: {e}")
        else:
            # Simulation mode - just record
            trade = TradeRecord(
                symbol=self.symbol,
                direction=signal.signal_type.value,
                entry_price=price,
                volume=volume,
                strategy=signal.strategy_name,
                sl=signal.sl,
                tp=signal.tp
            )
            trade_id = open_trade(trade)
            logger.info(f"[SIMULATION] Trade recorded: {signal.signal_type.value.upper()} {volume} @ {price}")
            
            # Save decision to history
            strategies_list = [
                {"name": s['name'], "signal": s['signal'], "confidence": s['confidence']}
                for s in signal.metadata.get('signals', [])
            ]
            save_decision(
                action=f"EXEC_{signal.signal_type.value.upper()}",
                reason=f"[SIM] Order executed: {signal.signal_type.value}",
                price=price,
                volume=volume,
                profit=0,
                position_id=trade_id,
                strategies_analyzed=strategies_list,
                final_decision=signal.signal_type.value,
                confidence=signal.confidence
            )
    
    def update_equity(self):
        """Record equity curve point."""
        balance = 500
        equity = 500
        open_count = 0
        
        if self.mt5 and self.mt5.is_connected():
            acc = self.mt5.get_account_info()
            if acc:
                balance = acc['balance']
                equity = acc['equity']
        
            
        # Save P&L snapshots for each open position
        try:
            import MetaTrader5 as mt5
            mt5.initialize()
            mt5_positions = mt5.positions_get()
            mt5.shutdown()
            if mt5_positions:
                for pos in mt5_positions:
                    try:
                        save_position_snapshot(
                            position_id=pos.ticket,
                            price=pos.price_current,
                            pnl=pos.profit,
                            equity=equity,
                            balance=balance,
                            volume=pos.volume,
                            direction='buy' if pos.type == 0 else 'sell'
                        )

                    except Exception as snap_err:
                        logger.debug(f"Failed to save position snapshot: {snap_err}")

                logger.info(f"save position snapshot")
                
        except Exception as e:
            logger.debug(f"Failed to get MT5 positions for snapshot: {e}")
    
        try:
            record_equity(balance, equity, open_count)
        except Exception as e:
            logger.error(f"Failed to record equity: {e}")
    
    def check_and_close_profit(self, min_profit: float = 50):
        """
        Check open positions and close if profit target reached.
        Uses strategies to decide if should close early.
        """
        if not self.mt5 or not self.mt5.is_connected():
            return
        
        import MetaTrader5 as mt5
        
        positions = mt5.positions_get()
        if not positions or len(positions) == 0:
            return
        
        # Get current signal
        data = self.get_market_data()
        signal = self.composite.analyze(data)
        
        for pos in positions:
            profit = pos.profit
            
            # Check if profit target reached
            if profit >= min_profit:
                # Check strategy - if opposite signal, close
                should_close = False
                close_reason = ""
                
                if pos.type == 0:  # BUY position
                    if signal.signal_type.value == 'sell':
                        should_close = True
                        close_reason = f"Strategy SELL signal (profit: ${profit:.2f})"
                    elif signal.signal_type.value == 'hold' and signal.confidence < 0.4:
                        should_close = True
                        close_reason = f"Weak signal, taking profit (profit: ${profit:.2f})"
                else:  # SELL position
                    if signal.signal_type.value == 'buy':
                        should_close = True
                        close_reason = f"Strategy BUY signal (profit: ${profit:.2f})"
                    elif signal.signal_type.value == 'hold' and signal.confidence < 0.4:
                        should_close = True
                        close_reason = f"Weak signal, taking profit (profit: ${profit:.2f})"
                
                if should_close:
                    # Close position
                    request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": pos.symbol,
                        "volume": pos.volume,
                        "type": mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY,
                        "position": pos.ticket,
                        "type_filling": mt5.ORDER_FILLING_IOC
                    }
                    
                    result = mt5.order_send(request)
                    
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        logger.info(f"CLOSED position {pos.ticket} for profit: ${profit:.2f}")
                        logger.info(f"   Reason: {close_reason}")
                        
                        # Save decision to history
                        strategies_list = [
                            {"name": s['name'], "signal": s['signal'], "confidence": s['confidence']}
                            for s in signal.metadata.get('signals', [])
                        ]
                        save_decision(
                            action=f"{signal.signal_type.value.upper()}-CLOSE",
                            reason=close_reason,
                            price=pos.price_open,
                            volume=pos.volume,
                            profit=profit,
                            position_id=pos.ticket,
                            strategies_analyzed=strategies_list,
                            final_decision=signal.signal_type.value,
                            confidence=signal.confidence
                        )
                    else:
                        logger.error(f"Failed to close position {pos.ticket}: {result.comment if result else 'No result'}")
    
    def run_once(self):
        """Run one iteration of the trading loop."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Step 1: Get market data
        try:
            data = self.get_market_data()
        except Exception as e:
            import traceback
            logger.error(f"[{timestamp}] ERROR get_market_data: {e} | {traceback.format_exc()}")
            return None
        
        # Step 1b: Detect market type and save
        market_type = "trend_bull"  # default
        try:
            from market.detector import detect_market_type
            market_result = detect_market_type()
            if market_result and 'type' in market_result:
                market_type = market_result['type']
                save_market_snapshot(
                    market_type=market_type,
                    adx=market_result.get('adx'),
                    atr_change=market_result.get('atr_change'),
                    bb_width=market_result.get('bb_width'),
                    ema_slope=market_result.get('ema_slope'),
                    reason=market_result.get('reason')
                )
                logger.info(f"[{timestamp}] Market: {market_type} ({market_result.get('reason', '')})")
        except Exception as e:
            logger.debug(f"[{timestamp}] Market detection error: {e}")
        
        # Step 1c: Check for unscored closed positions
        try:
            from database import get_unscored_closed_positions, calculate_and_save_strategy_scores
            unscored = get_unscored_closed_positions()
            if unscored:
                for pos in unscored:
                    trade_result = 1 if pos.get('profit', 0) > 0 else -1
                    calculate_and_save_strategy_scores(pos['id'], trade_result)
                    logger.info(f"[{timestamp}] Scored closed position {pos['id']}: result={trade_result}")
        except Exception as e:
            logger.debug(f"[{timestamp}] Unscored positions check error: {e}")
        
        # Step 2: Check and close profit
        try:
            self.check_and_close_profit(min_profit=50)
        except Exception as e:
            import traceback
            logger.error(f"[{timestamp}] ERROR check_and_close_profit: {e} | {traceback.format_exc()}")
        
        # Step 3: Get signal (pass market_type for market-aware strategy selection)
        try:
            signal = self.analyze_and_signal(market_type=market_type)
        except Exception as e:
            import traceback
            logger.error(f"[{timestamp}] ERROR analyze_and_signal: {e} | {traceback.format_exc()}")
            return None
        
        # Step 4: Execute trade or save HOLD decision
        print(f"final signal: {signal.signal_type.value}")
        if signal.signal_type.value != 'hold':
            logger.info(f"[{timestamp}] {signal}")
            try:
                self.execute_trade(signal)
            except Exception as e:
                import traceback
                logger.error(f"[{timestamp}] ERROR execute_trade: {e} | {traceback.format_exc()}")
        else:
            # Save HOLD decision
            try:
                strategies_list = [
                    {"Name": s['name'], "signal": s['signal'], "confidence": s['confidence']}
                    for s in signal.metadata.get('signals', [])
                ]
                save_decision(
                    action=signal.signal_type.value.upper(),
                    reason=f"Strategy {signal.signal_type.value} with {signal.confidence:.0%} confidence",
                    price=data['price'],
                    volume=0,
                    profit=0,
                    position_id=None,
                    strategies_analyzed=strategies_list,
                    final_decision=signal.signal_type.value,
                    confidence=signal.confidence
                )
            except Exception as e:
                import traceback
                logger.error(f"[{timestamp}] ERROR save_decision: {e} | {traceback.format_exc()}")
        
        # Step 6: Update equity
        try:
            self.update_equity()
        except Exception as e:
            import traceback
            logger.error(f"[{timestamp}] ERROR update_equity: {e} | {traceback.format_exc()}")
        
        return signal
    
    def run(self, interval: int = 15):
        """
        Run the trading system continuously.
        
        Args:
            interval: Seconds between iterations
        """
        logger.info(f"Starting trading system (interval: {interval}s)")
        self.running = True
        
        iteration = 0
        while self.running:
            try:
                self.run_once()
                iteration += 1
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
            
            time.sleep(interval)
        
        logger.info("Trading system stopped")
    
    def stop(self):
        """Stop the trading system."""
        self.running = False
        self.disconnect_mt5()


# =====================================================================
# BACKTEST MODE
# =====================================================================

class BacktestMode:
    """
    Backtest mode that uses the EXACT same logic as production trading.
    It fetches historical candles and simulates trading decisions.
    """
    
    def __init__(self, symbol="GOLD", timeframe=15, days=365):
        self.symbol = symbol
        self.timeframe = timeframe
        self.days = days
        
        # Initialize system (uses same strategies, same composite)
        self.system = TradingSystem()
        
        # Backtest state
        self.position = None  # {'type': 'buy'/'sell', 'entry': price, 'volume': lot, 'sl': sl, 'tp': tp, 'trade_id': id}
        self.trades = []  # For reporting
        self.equity_curve = []
        
        # Counters
        self.positions_opened = 0
        self.positions_closed = 0
        
        # Initial balance
        self.initial_balance = 300
        self.balance = self.initial_balance
        
        print(f"BacktestMode initialized: {symbol}, TF={timeframe}, {days} days")
        print(f"Using same strategies and CompositeStrategy as production")
    
    def load_historical_candles(self):
        """Load historical candles from MT5."""
        import MetaTrader5 as mt5
        
        if not mt5.initialize():
            raise Exception(f"MT5 init failed: {mt5.last_error()}")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.days)
        
        print(f"Fetching historical data from {start_date} to {end_date}...")
        
        rates = mt5.copy_rates_range(self.symbol, self.timeframe, start_date, end_date)
        mt5.shutdown()
        
        if rates is None or len(rates) == 0:
            raise Exception(f"No historical data returned from MT5")
        
        candles = []
        for r in rates:
            candles.append({
                'time': datetime.fromtimestamp(r['time']),
                'open': r['open'],
                'high': r['high'],
                'low': r['low'],
                'close': r['close'],
                'volume': r['tick_volume']
            })
        
        print(f"Loaded {len(candles)} candles")
        return candles
    
    def get_market_data_at(self, candles, idx):
        """Get market data at a specific candle index (for backtest)."""
        if idx < 0 or idx >= len(candles):
            return None
        
        # Get history (previous 50 candles)
        history = candles[max(0, idx-50):idx]
        
        current = candles[idx]
        price = current['close']
        
        # Build indicators from MT5 data (manual calculation)
        highs = [c['high'] for c in candles[:idx+1]]
        lows = [c['low'] for c in candles[:idx+1]]
        closes = [c['close'] for c in candles[:idx+1]]
        
        indicators = {}
        
        # RSI (14)
        indicators['rsi_14'] = self._calc_rsi(closes, 14)
        
        # Stochastic (14, 3)
        indicators['stoch_k'], indicators['stoch_d'] = self._calc_stochastic(highs, lows, closes, 14, 3)
        
        # MACD (12, 26, 9)
        indicators['macd'], indicators['macd_signal'], indicators['macd_hist'] = self._calc_macd(closes)
        
        # Bollinger Bands (20, 2)
        indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'] = self._calc_bollinger(closes, 20, 2)
        
        # ATR (14)
        indicators['atr_14'] = self._calc_atr(highs, lows, closes, 14)
        
        # ADX (14)
        indicators['adx_14'], indicators['plus_di'], indicators['minus_di'] = self._calc_adx(highs, lows, closes, 14)
        
        # SMAs
        indicators['sma_20'] = self._calc_sma(closes, 20)
        indicators['sma_50'] = self._calc_sma(closes, 50)
        
        return {
            'price': price,
            'indicators': indicators,
            'history': history,
            'timeframe': f'M{self.timeframe}'
        }
    
    def detect_market_type_at(self, candles, idx):
        """Detect market type at a specific candle index."""
        if idx < 100:
            return "sideway"
        
        highs = [c['high'] for c in candles[:idx+1]]
        lows = [c['low'] for c in candles[:idx+1]]
        closes = [c['close'] for c in candles[:idx+1]]
        
        # Calculate indicators for detection
        sma50 = self._calc_ema(closes, 50)
        ema20 = self._calc_ema(closes, 20)
        
        ema_slope = ema20 - (closes[-5] if len(closes) >= 5 else closes[-1])
        
        atr = self._calc_atr(highs, lows, closes, 14)
        atr_prev = self._calc_atr(highs[:-10], lows[:-10], closes[:-10], 14) if len(closes) >= 10 else atr
        atr_change = ((atr - atr_prev) / (atr_prev + 1e-6)) * 100
        
        adx, plus_di, minus_di = self._calc_adx(highs, lows, closes, 14)
        
        bb_upper, bb_middle, bb_lower = self._calc_bollinger(closes, 20, 2)
        bb_width = (bb_upper - bb_lower) / (bb_middle + 1e-6) * 100
        
        # Volatile: ATR spike + BB expansion
        if atr_change > 25 and bb_width > 5:
            return "volatile"
        
        # Strong trend
        if adx > 25 and abs(ema_slope) > 0:
            if closes[-1] > sma50:
                return "trend_bull"
            else:
                return "trend_bear"
        
        return "sideway"
    
    # ============== Indicator Calculations ==============
    
    def _score_strategy(self, trade_id, trade_result, signal):
        """Score each individual strategy based on trade result.
        
        This updates the strategy_scores table for each strategy so that weights are meaningful.
        """
        from database import get_connection
        from datetime import datetime
        
        # Check if already scored
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT position_id FROM scored_positions WHERE position_id = ?", (trade_id,))
        if cursor.fetchone():
            conn.close()
            return
        
        # Get signals from metadata
        signals_data = []
        if signal and signal.metadata and 'signals' in signal.metadata:
            signals_data = signal.metadata['signals']
        
        # Score each strategy that contributed to the decision
        for strat in signals_data:
            strategy_name = strat.get('name', 'Unknown')
            strat_signal = strat.get('signal', 'hold')  # buy, sell, hold
            strat_confidence = strat.get('confidence', 0.5)
            strat_contribution = strat.get('contribution', 0)
            
            # Skip if strategy had no contribution or was HOLD
            if strat_contribution == 0 or strat_signal == 'hold':
                continue
            
            # Get current score for this strategy
            cursor.execute("""
                SELECT score, total_trades, correct_trades 
                FROM strategy_scores 
                WHERE strategy_name = ?
            """, (strategy_name,))
            
            row = cursor.fetchone()
            
            if row:
                current_score = row[0]
                total_trades = row[1]
                correct_trades = row[2]
            else:
                current_score = 0
                total_trades = 0
                correct_trades = 0
            
            # Calculate new score: score[i] = score[i] * 0.95 + (confidence * result)
            new_score = current_score * 0.95 + (strat_confidence * trade_result)
            
            # Update correct trades count
            if trade_result == 1:  # Won
                correct_trades += 1
            
            total_trades += 1
            
            # UPDATE or INSERT
            if row:
                cursor.execute("""
                    UPDATE strategy_scores 
                    SET score = ?, total_trades = ?, correct_trades = ?, updated_at = ?
                    WHERE strategy_name = ?
                """, (new_score, total_trades, correct_trades, datetime.now().isoformat(), strategy_name))
            else:
                cursor.execute("""
                    INSERT INTO strategy_scores (strategy_name, score, total_trades, correct_trades, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (strategy_name, new_score, total_trades, correct_trades, datetime.now().isoformat()))
        
        # Also score the Composite strategy as a whole
        strategy_name = 'Composite'
        composite_confidence = signal.confidence if signal and hasattr(signal, 'confidence') else 0.5
        
        cursor.execute("""
            SELECT score, total_trades, correct_trades 
            FROM strategy_scores 
            WHERE strategy_name = ?
        """, (strategy_name,))
        
        row = cursor.fetchone()
        
        if row:
            current_score = row[0]
            total_trades = row[1]
            correct_trades = row[2]
        else:
            current_score = 0
            total_trades = 0
            correct_trades = 0
        
        # Calculate new score: score[i] = score[i] * 0.95 + (confidence * result)
        new_score = current_score * 0.95 + (composite_confidence * trade_result)
        
        if trade_result == 1:
            correct_trades += 1
        
        total_trades += 1
        
        if row:
            cursor.execute("""
                UPDATE strategy_scores 
                SET score = ?, total_trades = ?, correct_trades = ?, updated_at = ?
                WHERE strategy_name = ?
            """, (new_score, total_trades, correct_trades, datetime.now().isoformat(), strategy_name))
        else:
            cursor.execute("""
                INSERT INTO strategy_scores (strategy_name, score, total_trades, correct_trades, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (strategy_name, new_score, total_trades, correct_trades, datetime.now().isoformat()))
        
        # Mark as scored
        cursor.execute("""
            INSERT OR IGNORE INTO scored_positions (position_id, scored_at)
            VALUES (?, ?)
        """, (trade_id, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def _calc_rsi(self, closes, period=14):
        if len(closes) < period + 1:
            return 50
        
        deltas = np.diff(closes[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calc_stochastic(self, highs, lows, closes, k_period=14, d_period=3):
        if len(closes) < k_period:
            return 50, 50
        
        low_min = min(lows[-k_period:])
        high_max = max(highs[-k_period:])
        
        if high_max == low_min:
            return 50, 50
        
        k = 100 * (closes[-1] - low_min) / (high_max - low_min)
        
        # Calculate D
        k_values = []
        for i in range(k_period - 1, len(closes)):
            low_i = min(lows[i-k_period+1:i+1])
            high_i = max(highs[i-k_period+1:i+1])
            if high_i != low_i:
                k_values.append(100 * (closes[i] - low_i) / (high_i - low_i))
            else:
                k_values.append(50)
        
        d = np.mean(k_values[-d_period:]) if len(k_values) >= d_period else 50
        
        return k, d
    
    def _calc_macd(self, closes, fast=12, slow=26, signal_period=9):
        if len(closes) < slow:
            return 0, 0, 0
        
        ema_fast = self._calc_ema_list(closes, fast)
        ema_slow = self._calc_ema_list(closes, slow)
        
        macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
        signal_line = self._calc_ema_list(macd_line, signal_period)
        
        macd = macd_line[-1]
        sig = signal_line[-1] if len(signal_line) > 0 else 0
        hist = macd - sig
        
        return macd, sig, hist
    
    def _calc_ema(self, data, period):
        if len(data) < period:
            return data[-1] if len(data) > 0 else 0
        
        alpha = 2 / (period + 1)
        ema = [sum(data[:period]) / period]
        
        for i in range(period, len(data)):
            ema.append(alpha * data[i] + (1 - alpha) * ema[-1])
        
        return ema[-1]
    
    def _calc_ema_list(self, data, period):
        if len(data) < period:
            return [data[-1]] * len(data) if len(data) > 0 else [0] * len(data)
        
        alpha = 2 / (period + 1)
        result = [0] * (period - 1)
        result.append(sum(data[:period]) / period)
        
        for i in range(period, len(data)):
            result.append(alpha * data[i] + (1 - alpha) * result[-1])
        
        return result
    
    def _calc_sma(self, data, period):
        if len(data) < period:
            return data[-1] if len(data) > 0 else 0
        return np.mean(data[-period:])
    
    def _calc_bollinger(self, closes, period=20, std_dev=2):
        if len(closes) < period:
            return closes[-1], closes[-1], closes[-1] if len(closes) > 0 else 0, 0, 0
        
        sma = np.mean(closes[-period:])
        std = np.std(closes[-period:])
        
        return sma + std_dev * std, sma, sma - std_dev * std
    
    def _calc_atr(self, highs, lows, closes, period=14):
        if len(closes) < period + 1:
            return 0
        
        tr_values = []
        for i in range(1, min(len(closes), period + 1)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_values.append(tr)
        
        if len(tr_values) < period:
            return np.mean(tr_values) if len(tr_values) > 0 else 0
        
        atr = np.mean(tr_values)
        return atr
    
    def _calc_adx(self, highs, lows, closes, period=14):
        """Simplified ADX calculation for backtest."""
        if len(closes) < period * 2 + 1:
            return 25, 25, 25
        
        # Calculate True Range and Directional Movement
        tr_list = []
        plus_dm_list = []
        minus_dm_list = []
        
        for i in range(1, min(len(closes), period * 2 + 1)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
            
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            
            plus_dm = up_move if up_move > down_move and up_move > 0 else 0
            minus_dm = down_move if down_move > up_move and down_move > 0 else 0
            
            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)
        
        if len(tr_list) < period:
            return 25, 25, 25
        
        # Calculate smoothed ATR
        atr = np.mean(tr_list[-period:])
        
        # Calculate smoothed +DI and -DI
        plus_di = 100 * np.mean(plus_dm_list[-period:]) / atr if atr > 0 else 0
        minus_di = 100 * np.mean(minus_dm_list[-period:]) / atr if atr > 0 else 0
        
        # Calculate DX (simplified - just use current values)
        if plus_di + minus_di == 0:
            dx = 0
        else:
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # Simplified ADX - average of DX values
        adx = min(max(dx, 10), 50)  # Clamp to reasonable range
        
        return adx, plus_di, minus_di
    
    # ============== Backtest Execution ==============
    
    def run(self):
        """Run the backtest."""
        print(f"\n{'='*60}")
        print("BACKTEST MODE - Using Production Logic")
        print(f"{'='*60}")
        
        # Load historical data
        candles = self.load_historical_candles()
        n = len(candles)
        
        warmup = 100  # Need warmup for indicators
        sl_pct = self.system.settings.get('sl_percent', 1.0) / 100
        tp_pct = self.system.settings.get('tp_percent', 1.5) / 100
        lot_min = self.system.settings.get('lot_min', 0.01)
        lot_max = self.system.settings.get('lot_max', 0.1)
        
        print(f"Running backtest from candle {warmup} to {n}...")
        
        start_time = time.time()
        last_progress = 0
        
        for idx in range(warmup, n):
            # Progress every 10%
            pct = (idx - warmup) / (n - warmup) * 100
            if pct - last_progress >= 10:
                elapsed = time.time() - start_time
                print(f"Progress: {pct:.0f}% ({idx}/{n}) - {elapsed:.1f}s - Balance: ${self.balance:,.2f}")
                last_progress = pct
            
            current_candle = candles[idx]
            price = current_candle['close']
            current_time = current_candle['time']
            
            # Get market data
            data = self.get_market_data_at(candles, idx)
            
            # Detect market type
            market_type = self.detect_market_type_at(candles, idx)
            
            # Get signal using CompositeStrategy (verbose=False for speed)
            signal = self.system.composite.analyze(data, market_type=market_type, verbose=False)
            
            # Get action from signal metadata
            action = signal.metadata.get('action', 'NO_TRADE') if signal.metadata else 'NO_TRADE'
            
            # ============== Check and close position ==============
            if self.position:
                pos = self.position
                
                # Calculate P&L
                if pos['type'] == 'buy':
                    pnl = (price - pos['entry']) * pos['volume'] * 100
                else:
                    pnl = (pos['entry'] - price) * pos['volume'] * 100
                
                should_close = False
                reason = ""
                exit_price = price
                
                # Check SL
                if pos['type'] == 'buy':
                    if price <= pos['sl']:
                        should_close, reason = True, "SL"
                        pnl = (pos['sl'] - pos['entry']) * pos['volume'] * 100
                        exit_price = pos['sl']
                    elif price >= pos['tp']:
                        should_close, reason = True, "TP"
                        pnl = (pos['tp'] - pos['entry']) * pos['volume'] * 100
                        exit_price = pos['tp']
                else:
                    if price >= pos['sl']:
                        should_close, reason = True, "SL"
                        pnl = (pos['entry'] - pos['sl']) * pos['volume'] * 100
                        exit_price = pos['sl']
                    elif price <= pos['tp']:
                        should_close, reason = True, "TP"
                        pnl = (pos['entry'] - pos['tp']) * pos['volume'] * 100
                        exit_price = pos['tp']
                
                # Close on opposite signal
                if not should_close:
                    if action == 'SELL' if pos['type'] == 'buy' else action == 'BUY':
                        should_close, reason = True, "OppSignal"
                
                # Close if profit >= $50
                current_pnl = (price - pos['entry']) * pos['volume'] * 100 if pos['type'] == 'buy' else (pos['entry'] - price) * pos['volume'] * 100
                if not should_close and current_pnl >= 50:
                    should_close, reason = True, f"Profit${current_pnl:.0f}"
                
                if should_close:
                    # Calculate pnl_pct
                    pnl_pct = (pnl / (pos['entry'] * pos['volume'] * 100)) * 100 if pos['entry'] > 0 else 0
                    
                    self.trades.append({
                        'entry_time': pos['entry_time'],
                        'exit_time': current_time,
                        'type': pos['type'],
                        'entry': pos['entry'],
                        'exit': exit_price,
                        'volume': pos['volume'],
                        'pnl': pnl,
                        'reason': reason
                    })
                    
                    # Save to trades table
                    if 'trade_id' in pos and pos['trade_id']:
                        from database import close_trade
                        ts_close = current_time.isoformat() if hasattr(current_time, 'isoformat') else str(current_time)
                        close_trade(pos['trade_id'], exit_price, pnl, pnl_pct, timestamp_close=ts_close)
                        self.positions_closed += 1
                        
                        # Score the position
                        trade_result = 1 if pnl > 0 else -1
                        self._score_strategy(pos['trade_id'], trade_result, signal)
                    
                    self.balance += pnl
                    self.position = None
            
            # ============== Open new position ==============
            if not self.position and action in ['BUY', 'SELL']:
                volume = lot_min + (lot_max - lot_min) * signal.confidence
                volume = max(lot_min, min(lot_max, round(volume, 2)))
                
                if action == 'BUY':
                    sl_price = price * (1 - sl_pct)
                    tp_price = price * (1 + tp_pct)
                else:
                    sl_price = price * (1 + sl_pct)
                    tp_price = price * (1 - tp_pct)
                
                # Save to trades table (OPEN)
                from database import open_trade, TradeRecord
                ts_open = current_time.isoformat() if hasattr(current_time, 'isoformat') else str(current_time)
                trade_record = TradeRecord(
                    symbol=self.symbol,
                    direction=action.lower(),
                    entry_price=price,
                    volume=volume,
                    strategy='Composite',
                    sl=sl_price,
                    tp=tp_price
                )
                trade_id = open_trade(trade_record, timestamp_open=ts_open)
                self.positions_opened += 1
                
                self.position = {
                    'type': action.lower(),
                    'entry': price,
                    'sl': sl_price,
                    'tp': tp_price,
                    'volume': volume,
                    'entry_time': current_time,
                    'trade_id': trade_id
                }
            
            # Record equity every 100 candles
            if idx % 100 == 0:
                equity = self.balance
                if self.position:
                    if self.position['type'] == 'buy':
                        equity += (price - self.position['entry']) * self.position['volume'] * 100
                    else:
                        equity += (self.position['entry'] - price) * self.position['volume'] * 100
                
                self.equity_curve.append({
                    'time': current_time,
                    'balance': self.balance,
                    'equity': equity
                })
        
        # Close remaining position at end
        if self.position:
            price = candles[-1]['close']
            pos = self.position
            
            pnl = (price - pos['entry']) * pos['volume'] * 100 if pos['type'] == 'buy' else (pos['entry'] - price) * pos['volume'] * 100
            pnl_pct = (pnl / (pos['entry'] * pos['volume'] * 100)) * 100 if pos['entry'] > 0 else 0
            
            self.trades.append({
                'entry_time': pos['entry_time'],
                'exit_time': candles[-1]['time'],
                'type': pos['type'],
                'entry': pos['entry'],
                'exit': price,
                'volume': pos['volume'],
                'pnl': pnl,
                'reason': 'End'
            })
            
            # Save to trades table (CLOSE)
            if 'trade_id' in pos and pos['trade_id']:
                from database import close_trade
                ts_close = candles[-1]['time'].isoformat() if hasattr(candles[-1]['time'], 'isoformat') else str(candles[-1]['time'])
                close_trade(pos['trade_id'], price, pnl, pnl_pct, timestamp_close=ts_close)
                self.positions_closed += 1
            
            self.balance += pnl
            
            self.balance += pnl
        
        elapsed = time.time() - start_time
        
        return self._generate_report(elapsed)
    
    def _generate_report(self, elapsed):
        """Generate backtest report."""
        print(f"\n{'='*60}")
        print("BACKTEST RESULTS")
        print(f"{'='*60}")
        print(f"Duration: {elapsed:.1f} seconds")
        print(f"Total Candles: {len(self.equity_curve) * 100 if self.equity_curve else 0}")
        print(f"{'-'*40}")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Final Balance:   ${self.balance:,.2f}")
        print(f"Total P&L:       ${self.balance - self.initial_balance:,.2f}")
        print(f"Return:          {(self.balance - self.initial_balance) / self.initial_balance * 100:.2f}%")
        
        if self.trades:
            pnls = [t['pnl'] for t in self.trades]
            winning = [p for p in pnls if p > 0]
            losing = [p for p in pnls if p < 0]
            
            # Max drawdown
            equity = self.initial_balance
            peak = self.initial_balance
            max_dd = 0
            for pnl in pnls:
                equity += pnl
                if equity > peak:
                    peak = equity
                dd = peak - equity
                if dd > max_dd:
                    max_dd = dd
            
            print(f"{'-'*40}")
            print(f"Positions Opened: {self.positions_opened}")
            print(f"Positions Closed:  {self.positions_closed}")
            print(f"Total Trades:    {len(self.trades)}")
            print(f"Winning Trades:  {len(winning)}")
            print(f"Losing Trades:   {len(losing)}")
            print(f"Win Rate:        {len(winning) / len(self.trades) * 100:.1f}%")
            print(f"{'-'*40}")
            print(f"Avg Win:         ${np.mean(winning):.2f}" if winning else "Avg Win:         N/A")
            print(f"Avg Loss:        ${np.mean(losing):.2f}" if losing else "Avg Loss:        N/A")
            print(f"Largest Win:     ${max(winning):.2f}" if winning else "Largest Win:     N/A")
            print(f"Largest Loss:    ${min(losing):.2f}" if losing else "Largest Loss:    N/A")
            print(f"Profit Factor:   {abs(sum(winning) / sum(losing)):.2f}" if losing and sum(losing) != 0 else "Profit Factor:   N/A")
            print(f"Max Drawdown:    ${max_dd:.2f}")
        
        print(f"{'='*60}")
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_pnl': self.balance - self.initial_balance,
            'total_trades': len(self.trades),
            'winning_trades': len([t for t in self.trades if t['pnl'] > 0]),
            'losing_trades': len([t for t in self.trades if t['pnl'] <= 0]),
            'win_rate': len([t for t in self.trades if t['pnl'] > 0]) / len(self.trades) * 100 if self.trades else 0,
            'elapsed_seconds': elapsed
        }
    
    def save_to_database(self):
        """Save backtest results to database."""
        from database import save_decision, record_equity
        
        print("\nSaving results to database...")
        
        for trade in self.trades:
            # Use candle timestamp for the decision
            ts = trade['exit_time'].isoformat() if hasattr(trade['exit_time'], 'isoformat') else str(trade['exit_time'])
            save_decision(
                action=trade['type'].upper(),
                reason=trade['reason'],
                price=trade['exit'],
                volume=trade['volume'],
                profit=trade['pnl'],
                position_id=None,
                strategies_analyzed=[],
                final_decision=trade['type'],
                confidence=0.5,
                timestamp=ts
            )
        
        for point in self.equity_curve:
            record_equity(
                balance=point['balance'],
                equity=point['equity'],
                open_positions=0
            )
        
        print(f"Saved {self.positions_opened} open + {self.positions_closed} closed positions to trades table")
        print(f"Saved {len(self.equity_curve)} equity points and {len(self.trades)} decisions to decision_history")


# Need numpy for indicator calculations
import numpy as np


# =====================================================================
# Main Entry Points
# =====================================================================

def run_trading():
    """Run the trading system only (no dashboard)."""
    system = TradingSystem()
    system.connect_mt5()
    
    try:
        system.run(interval=900)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        system.stop()


def run_dashboard_only():
    """Run the dashboard only."""
    from dashboard import run_dashboard
    run_dashboard()


def run_full_system():
    """Run both trading system and dashboard."""
    def run_trading_process():
        system = TradingSystem()
        system.connect_mt5()
        
        try:
            system.run(interval=900)
        except KeyboardInterrupt:
            pass
        finally:
            system.stop()
    
    # Start trading in background
    import multiprocessing
    trading_process = multiprocessing.Process(target=run_trading_process)
    trading_process.start()
    
    logger.info("Trading process started in background")
    
    # Start dashboard
    from dashboard import run_dashboard
    run_dashboard()


def run_backtest(args):
    """Run backtest mode."""
    # Reset database if requested
    if args.reset_db:
        db_path = project_root / 'data' / 'trades.db'
        if db_path.exists():
            backup = str(db_path) + f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(db_path, backup)
            print(f"Backed up database to: {backup}")
        
        init_database()
        print("Database reset complete\n")
    
    # Run backtest
    backtest = BacktestMode(
        symbol=args.symbol,
        timeframe=args.timeframe,
        days=args.days
    )
    
    report = backtest.run()
    
    if report:
        backtest.save_to_database()
    
    print("\nBacktest completed!")


# =====================================================================
# Main
# =====================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MT5 Gold Trader')
    parser.add_argument('--backtest', action='store_true', help='Run in backtest mode')
    parser.add_argument('--days', type=int, default=365, help='Days to backtest (default: 365)')
    parser.add_argument('--symbol', type=str, default='GOLD', help='Symbol to trade (default: GOLD)')
    parser.add_argument('--timeframe', type=int, default=15, help='Timeframe in minutes (default: 15)')
    parser.add_argument('--reset-db', action='store_true', help='Reset database before backtest')
    
    args = parser.parse_args()
    
    # Write PID to file
    with open("main.pid", "w") as f:
        f.write(str(os.getpid()))
    
    if args.backtest:
        run_backtest(args)
    else:
        run_trading()

if __name__ == "__main__":
    main()
