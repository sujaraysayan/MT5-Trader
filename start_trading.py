"""
Start Trading System with Dashboard
=================================
Runs the trading system and dashboard together.
"""
import os
import sys
import time
import threading
import logging
from pathlib import Path

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from main import TradingSystem
from database import init_database, record_equity, save_signal, SignalRecord

def run_trading_loop():
    """Run the trading system."""
    logger.info("Starting trading system...")
    
    system = TradingSystem()
    system.connect_mt5()
    
    logger.info("Trading system connected to MT5")
    logger.info(f"Loaded {len(system.strategies)} strategies")
    
    iteration = 0
    while True:
        try:
            # Run one iteration
            signal = system.run_once()
            
            # Log signals
            timestamp = time.strftime("%H:%M:%S")
            if signal.signal_type.value != 'hold':
                logger.info(f"[{timestamp}] {signal}")
            else:
                logger.debug(f"[{timestamp}] {signal}")
            
            iteration += 1
            
            # Log every minute
            if iteration % 4 == 0:
                logger.info(f"Iteration {iteration} - System running")
            
            # Wait 15 seconds
            time.sleep(15)
            
        except KeyboardInterrupt:
            logger.info("Trading loop stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            time.sleep(15)

def run_dashboard():
    """Run the dashboard."""
    from dashboard import app
    logger.info("Starting dashboard on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

def main():
    print("=" * 60)
    print("MT5 Gold Trader - Full System")
    print("=" * 60)
    print()
    print("Starting:")
    print("  1. Trading System (13 strategies)")
    print("  2. Dashboard (http://localhost:5000)")
    print()
    print("Dashboard: Open http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    # Start dashboard in separate thread
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    
    # Run trading loop in main thread
    run_trading_loop()

if __name__ == "__main__":
    main()
