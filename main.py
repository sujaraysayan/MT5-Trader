"""
MT5 Gold Trader - Main Trading System
====================================
AI-powered gold trading with real-time dashboard.
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime
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
from strategies.base import CompositeStrategy, TradingSignal
from database import (
    init_database, save_signal, get_recent_signals,
    open_trade, close_trade, get_open_trades,
    record_equity, TradeRecord, SignalRecord, save_decision
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
            
            return {
                'price': candle['close'] if candle else 0,
                'indicators': indicators,
                'history': history,
                'timeframe': 'M15'
            }
        else:
            # Simulation mode
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
    
    def analyze_and_signal(self) -> TradingSignal:
        """Analyze market and generate signal."""
        data = self.get_market_data()
        signal = self.composite.analyze(data)
        
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
        if signal.signal_type.value == 'hold':
            return
        
        # Check current positions count - limit to max 3 positions
        open_positions = get_open_trades()
        
        if open_positions and len(open_positions) >= 3:
            logger.debug(f"Already have {len(open_positions)} positions, skipping")
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
                
                # Ensure symbol is selected
                mt5.symbol_select(self.symbol, True)
                
                # Get symbol info
                symbol_info = mt5.symbol_info(self.symbol)
                if not symbol_info:
                    logger.error(f"Symbol {self.symbol} not found")
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
                            {"name": s.name, "signal": s.analyze(data).signal_type.value, "confidence": s.analyze(data).confidence}
                            for s in self.strategies
                        ]
                        save_decision(
                            action="OPEN",
                            reason=f"Strategy {signal.signal_type.value} signal",
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
                {"Name": s.name, "signal": s.analyze(data).signal_type.value, "confidence": s.analyze(data).confidence}
                for s in self.strategies
            ]
            save_decision(
                action="OPEN_SIM",
                reason=f"[SIMULATION] Strategy {signal.signal_type.value}",
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
        
        open_positions = get_open_trades()
        if open_positions:
            open_count = len(open_positions)
        
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
                            {"name": s.name, "signal": s.analyze(data).signal_type.value, "confidence": s.analyze(data).confidence}
                            for s in self.strategies
                        ]
                        save_decision(
                            action="CLOSE",
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
        
        # Get market data first
        data = self.get_market_data()
        
        # Check and close profit if target reached
        self.check_and_close_profit(min_profit=50)
        
        # Get signal
        signal = self.analyze_and_signal()
        
        # Always save decision to history
        strategies_list = [
            {"name": s.name, "signal": s.analyze(data).signal_type.value, "confidence": s.analyze(data).confidence}
            for s in self.strategies
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
        
        # Execute trade if BUY or SELL signal
        if signal.signal_type.value != 'hold':
            logger.info(f"[{timestamp}] {signal}")
            self.execute_trade(signal)
        
        # Update equity
        self.update_equity()
        
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
                
                if iteration % 10 == 0:
                    logger.info(f"Iteration {iteration} completed")
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
            
            time.sleep(interval)
        
        logger.info("Trading system stopped")
    
    def stop(self):
        """Stop the trading system."""
        self.running = False
        self.disconnect_mt5()


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


# =====================================================================
# Main
# =====================================================================

def main():
    """Main entry point."""
    run_trading()

if __name__ == "__main__":
    main()
