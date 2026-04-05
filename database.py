"""
Database Module
==============
SQLite database for storing trades and signals.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
import json


DATABASE_PATH = "data/trades.db"


def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Signals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            strategy TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            strength TEXT NOT NULL,
            confidence REAL NOT NULL,
            price REAL NOT NULL,
            sl REAL,
            tp REAL,
            timeframe TEXT NOT NULL,
            metadata TEXT
        )
    """)
    
    # Trades table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_open TEXT NOT NULL,
            timestamp_close TEXT,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL,
            volume REAL NOT NULL,
            sl REAL,
            tp REAL,
            pnl REAL,
            pnl_pct REAL,
            status TEXT NOT NULL,
            strategy TEXT NOT NULL,
            signal_id INTEGER,
            metadata TEXT,
            FOREIGN KEY (signal_id) REFERENCES signals (id)
        )
    """)
    
    # Equity curve table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equity_curve (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            balance REAL NOT NULL,
            equity REAL NOT NULL,
            open_positions INTEGER NOT NULL,
            daily_pnl REAL
        )
    """)
    
    # Performance metrics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            total_trades INTEGER DEFAULT 0,
            winning_trades INTEGER DEFAULT 0,
            losing_trades INTEGER DEFAULT 0,
            total_pnl REAL DEFAULT 0,
            win_rate REAL DEFAULT 0,
            avg_win REAL DEFAULT 0,
            avg_loss REAL DEFAULT 0,
            profit_factor REAL DEFAULT 0,
            max_drawdown REAL DEFAULT 0,
            sharpe_ratio REAL DEFAULT 0
        )
    """)
    
    # Decision history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            reason TEXT NOT NULL,
            price REAL,
            volume REAL,
            profit REAL,
            position_id INTEGER,
            metadata TEXT,
            strategies_analyzed TEXT,
            final_decision TEXT,
            confidence REAL
        )
    """)
    
    # Position P&L snapshots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS position_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            price REAL NOT NULL,
            pnl REAL NOT NULL,
            equity REAL NOT NULL,
            balance REAL NOT NULL,
            volume REAL,
            direction TEXT,
            FOREIGN KEY (position_id) REFERENCES trades (id)
        )
    """)
    
    # Market detection snapshots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            market_type TEXT NOT NULL,
            adx REAL,
            atr_change REAL,
            bb_width REAL,
            ema_slope REAL,
            reason TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"Database initialized: {DATABASE_PATH}")


# =====================================================================
# Signal Operations
# =====================================================================

@dataclass
class SignalRecord:
    """Signal record dataclass."""
    strategy: str
    signal_type: str
    strength: str
    confidence: float
    price: float
    timeframe: str
    sl: Optional[float] = None
    tp: Optional[float] = None
    metadata: Optional[Dict] = None


def save_signal(signal: SignalRecord) -> int:
    """Save a trading signal to database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO signals (timestamp, strategy, signal_type, strength, confidence, 
                          price, sl, tp, timeframe, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        signal.strategy,
        signal.signal_type,
        signal.strength,
        signal.confidence,
        signal.price,
        signal.sl,
        signal.tp,
        signal.timeframe,
        json.dumps(signal.metadata) if signal.metadata else None
    ))
    
    signal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return signal_id


def get_recent_signals(limit: int = 20) -> List[Dict]:
    """Get recent signals."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM signals 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# =====================================================================
# Decision History Operations
# =====================================================================

def save_decision(action: str, reason: str, price: float = None, 
                 volume: float = None, profit: float = None,
                 position_id: int = None, metadata: Dict = None,
                 strategies_analyzed: List[Dict] = None, 
                 final_decision: str = None, confidence: float = None) -> int:
    """Save a trading decision to history."""
    conn = get_connection()
    cursor = conn.cursor()
    
    strategies_json = json.dumps(strategies_analyzed) if strategies_analyzed else None
    metadata_json = json.dumps(metadata) if metadata else None
    
    cursor.execute("""
        INSERT INTO decision_history 
        (timestamp, action, reason, price, volume, profit, position_id, metadata, strategies_analyzed, final_decision, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        action,
        reason,
        price,
        volume,
        profit,
        position_id,
        metadata_json,
        strategies_json,
        final_decision,
        confidence
    ))
    
    decision_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return decision_id


def get_decision_history(limit: int = 50) -> List[Dict]:
    """Get decision history."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM decision_history 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def save_position_snapshot(position_id: int, price: float, pnl: float, 
                         equity: float, balance: float, volume: float = None,
                         direction: str = None) -> int:
    """Save a position P&L snapshot for curve tracking."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO position_snapshots 
        (position_id, timestamp, price, pnl, equity, balance, volume, direction)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        position_id,
        datetime.now().isoformat(),
        price,
        pnl,
        equity,
        balance,
        volume,
        direction
    ))
    
    snapshot_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return snapshot_id


def get_position_snapshots(position_id: int) -> List[Dict]:
    """Get P&L history for a specific position."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM position_snapshots 
        WHERE position_id = ?
        ORDER BY timestamp ASC
    """, (position_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def save_market_snapshot(market_type: str, adx: float = None, atr_change: float = None,
                       bb_width: float = None, ema_slope: float = None, reason: str = None) -> int:
    """Save a market type detection snapshot."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO market_snapshots 
        (timestamp, market_type, adx, atr_change, bb_width, ema_slope, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        market_type,
        adx,
        atr_change,
        bb_width,
        ema_slope,
        reason
    ))
    
    snapshot_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return snapshot_id


# =====================================================================
# Trade Operations
# =====================================================================

@dataclass
class TradeRecord:
    """Trade record dataclass."""
    symbol: str
    direction: str
    entry_price: float
    volume: float
    strategy: str
    sl: Optional[float] = None
    tp: Optional[float] = None
    signal_id: Optional[int] = None
    metadata: Optional[Dict] = None


def open_trade(trade: TradeRecord) -> int:
    """Record a new open trade."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO trades (timestamp_open, symbol, direction, entry_price, 
                          volume, sl, tp, status, strategy, signal_id, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        trade.symbol,
        trade.direction,
        trade.entry_price,
        trade.volume,
        trade.sl,
        trade.tp,
        "OPEN",
        trade.strategy,
        trade.signal_id,
        json.dumps(trade.metadata) if trade.metadata else None
    ))
    
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return trade_id


def close_trade(trade_id: int, exit_price: float, pnl: float, pnl_pct: float):
    """Close a trade."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE trades 
        SET timestamp_close = ?,
            exit_price = ?,
            pnl = ?,
            pnl_pct = ?,
            status = ?
        WHERE id = ?
    """, (
        datetime.now().isoformat(),
        exit_price,
        pnl,
        pnl_pct,
        "CLOSED",
        trade_id
    ))
    
    conn.commit()
    conn.close()


def get_open_trades() -> List[Dict]:
    """Get all open trades. Auto-cleans stale records by syncing with MT5."""
    try:
        import MetaTrader5 as mt5
        mt5.initialize()
        mt5_positions = mt5.positions_get()
        mt5.shutdown()
        
        if mt5_positions:
            mt5_tickets = set(pos.ticket for pos in mt5_positions)
        else:
            mt5_tickets = set()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get open trades from DB
        cursor.execute("SELECT id, status FROM trades WHERE status = 'OPEN'")
        db_trades = cursor.fetchall()
        
        # Delete stale records (in DB but not in MT5)
        deleted = 0
        for (trade_id, status) in db_trades:
            if trade_id not in mt5_tickets:
                cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
                deleted += 1
        
        if deleted > 0:
            conn.commit()
            print(f"[DB Cleanup] Removed {deleted} stale trades")
        
        # Get fresh list
        cursor.execute("SELECT * FROM trades WHERE status = 'OPEN'")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        # If MT5 not available, just return DB records
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades WHERE status = 'OPEN'")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


def get_trade_history(limit: int = 50) -> List[Dict]:
    """Get trade history."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM trades 
        WHERE status = 'CLOSED'
        ORDER BY timestamp_open DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# =====================================================================
# Equity Operations
# =====================================================================

def record_equity(balance: float, equity: float, open_positions: int, daily_pnl: float = 0):
    """Record equity curve point."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO equity_curve (timestamp, balance, equity, open_positions, daily_pnl)
        VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        balance,
        equity,
        open_positions,
        daily_pnl
    ))
    
    conn.commit()
    conn.close()


def get_equity_curve(days: int = 30) -> List[Dict]:
    """Get equity curve data."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM equity_curve 
        WHERE timestamp >= datetime('now', '-' || ? || ' days')
        ORDER BY timestamp ASC
    """, (days,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# =====================================================================
# Performance Metrics
# =====================================================================

def update_daily_performance():
    """Calculate and update daily performance metrics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get closed trades for today
    cursor.execute("""
        SELECT * FROM trades 
        WHERE status = 'CLOSED' 
        AND date(timestamp_open) = ?
    """, (today,))
    
    trades = [dict(row) for row in cursor.fetchall()]
    
    if not trades:
        conn.close()
        return
    
    # Calculate metrics
    total = len(trades)
    wins = sum(1 for t in trades if t['pnl'] > 0)
    losses = sum(1 for t in trades if t['pnl'] <= 0)
    win_rate = wins / total if total > 0 else 0
    
    total_pnl = sum(t['pnl'] for t in trades)
    avg_win = sum(t['pnl'] for t in trades if t['pnl'] > 0) / wins if wins > 0 else 0
    avg_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0) / losses) if losses > 0 else 0
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
    
    # Max drawdown (simplified)
    cursor.execute("""
        SELECT equity FROM equity_curve 
        WHERE date(timestamp) = ?
        ORDER BY equity ASC
    """, (today,))
    
    equity_rows = cursor.fetchall()
    max_dd = 0
    if equity_rows:
        equities = [r['equity'] for r in equity_rows]
        peak = max(equities)
        trough = min(equities)
        max_dd = (peak - trough) / peak if peak > 0 else 0
    
    # Upsert performance
    cursor.execute("""
        INSERT INTO performance (date, total_trades, winning_trades, losing_trades,
                               total_pnl, win_rate, avg_win, avg_loss, profit_factor, max_drawdown)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            total_trades = excluded.total_trades,
            winning_trades = excluded.winning_trades,
            losing_trades = excluded.losing_trades,
            total_pnl = excluded.total_pnl,
            win_rate = excluded.win_rate,
            avg_win = excluded.avg_win,
            avg_loss = excluded.avg_loss,
            profit_factor = excluded.profit_factor,
            max_drawdown = excluded.max_drawdown
    """, (today, total, wins, losses, total_pnl, win_rate, avg_win, avg_loss, profit_factor, max_dd))
    
    conn.commit()
    conn.close()


def get_performance_summary() -> Dict:
    """Get performance summary."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # All time stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
            SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losing_trades,
            SUM(pnl) as total_pnl,
            AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
            AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
        FROM trades WHERE status = 'CLOSED'
    """)
    
    row = cursor.fetchone()
    stats = dict(row) if row else {}
    
    # Recent equity
    cursor.execute("""
        SELECT equity FROM equity_curve ORDER BY timestamp DESC LIMIT 1
    """)
    eq_row = cursor.fetchone()
    current_equity = eq_row['equity'] if eq_row else 0
    
    # Initial balance (assuming 500 as starting)
    initial_balance = 500
    
    conn.close()
    
    return {
        'total_trades': stats.get('total_trades', 0),
        'winning_trades': stats.get('winning_trades', 0),
        'losing_trades': stats.get('losing_trades', 0),
        'win_rate': (stats.get('winning_trades', 0) / stats.get('total_trades', 1) * 100) if stats.get('total_trades', 0) > 0 else 0,
        'total_pnl': stats.get('total_pnl', 0),
        'avg_win': stats.get('avg_win', 0),
        'avg_loss': abs(stats.get('avg_loss') or 0),
        'current_equity': current_equity,
        'initial_balance': initial_balance,
        'total_return': ((current_equity - initial_balance) / initial_balance * 100) if current_equity > 0 else 0
    }


# =====================================================================
# Main
# =====================================================================

if __name__ == "__main__":
    init_database()
    print("Database setup complete!")
