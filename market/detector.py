import MetaTrader5 as mt5
import numpy as np
from datetime import datetime


class MarketDetector:
    def __init__(self, symbol='GOLD', timeframe=mt5.TIMEFRAME_H1):
        self.symbol = symbol
        self.timeframe = timeframe

    def get_data(self, bars=300):
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, bars)
        if rates is None or len(rates) < 100:
            return None

        return rates

    # =========================
    # INDICATORS (IMPROVED)
    # =========================

    def ema(self, data, period):
        ema = np.zeros_like(data)
        ema[period-1] = np.mean(data[:period])

        alpha = 2 / (period + 1)
        for i in range(period, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]

        return ema

    def atr(self, high, low, close, period=14):
        tr = np.maximum.reduce([
            high[1:] - low[1:],
            np.abs(high[1:] - close[:-1]),
            np.abs(low[1:] - close[:-1])
        ])

        atr = np.zeros_like(tr)
        atr[period] = np.mean(tr[:period])

        for i in range(period+1, len(tr)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

        return atr

    def adx(self, high, low, close, period=14):
        tr = np.maximum.reduce([
            high[1:] - low[1:],
            np.abs(high[1:] - close[:-1]),
            np.abs(low[1:] - close[:-1])
        ])

        up_move = high[1:] - high[:-1]
        down_move = low[:-1] - low[1:]

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        atr = np.zeros_like(tr)
        atr[period] = np.mean(tr[:period])

        plus_dm_s = np.zeros_like(tr)
        minus_dm_s = np.zeros_like(tr)

        plus_dm_s[period] = np.mean(plus_dm[:period])
        minus_dm_s[period] = np.mean(minus_dm[:period])

        for i in range(period+1, len(tr)):
            atr[i] = (atr[i-1]*(period-1) + tr[i]) / period
            plus_dm_s[i] = (plus_dm_s[i-1]*(period-1) + plus_dm[i]) / period
            minus_dm_s[i] = (minus_dm_s[i-1]*(period-1) + minus_dm[i]) / period

        plus_di = np.divide(
            100 * plus_dm_s,
            atr,
            out=np.zeros_like(atr),
            where=atr != 0
        )

        minus_di = np.divide(
            100 * minus_dm_s,
            atr,
            out=np.zeros_like(atr),
            where=atr != 0
        )

        denom = plus_di + minus_di

        dx = np.divide(
            100 * np.abs(plus_di - minus_di),
            denom,
            out=np.zeros_like(denom),
            where=denom != 0
        )

        adx = np.zeros_like(dx)
        adx[period*2] = np.mean(dx[period:period*2])

        for i in range(period*2+1, len(dx)):
            adx[i] = (adx[i-1]*(period-1) + dx[i]) / period

        return adx

    def bb_width(self, close, period=20):
        sma = np.convolve(close, np.ones(period)/period, mode='same')

        std = np.zeros_like(close)
        for i in range(period, len(close)):
            std[i] = np.std(close[i-period:i])

        upper = sma + 2*std
        lower = sma - 2*std

        width = np.where(sma != 0, (upper - lower) / sma * 100, 0)
        return width

    # =========================
    # DETECT MARKET
    # =========================

    def detect(self):
        data = self.get_data()
        if data is None:
            return {'type': 'unknown', 'error': 'No data'}

        high = data['high']
        low = data['low']
        close = data['close']

        # Indicators
        ema50 = self.ema(close, 50)
        ema200 = self.ema(close, 200)

        adx = self.adx(high, low, close)
        atr = self.atr(high, low, close)
        bb = self.bb_width(close)

        # Smooth
        adx_mean = np.mean(adx[-10:])
        atr_mean = np.mean(atr[-10:])
        atr_prev = np.mean(atr[-20:-10])
        bb_mean = np.mean(bb[-10:])
        bb_avg = np.mean(bb[-50:])

        atr_change = (atr_mean - atr_prev) / atr_prev * 100 if atr_prev != 0 else 0

        # EMA slope (กัน fake trend)
        ema_slope = ema50[-1] - ema50[-5]

        result = {
            'type': 'unknown',
            'adx': round(adx_mean, 2),
            'atr_change': round(atr_change, 2),
            'bb_width': round(bb_mean, 2),
            'ema_slope': round(ema_slope, 5),
            'timestamp': datetime.now().isoformat()
        }

        # =========================
        # CLASSIFICATION (IMPROVED)
        # =========================

        # 1. Volatile (priority สูงสุด)
        if atr_change > 25 and bb_mean > bb_avg:
            result['type'] = 'volatile'
            result['reason'] = 'ATR spike + BB expansion'

        # 2. Trend
        elif adx_mean > 25 and abs(ema_slope) > 0:
            if ema50[-1] > ema200[-1]:
                result['type'] = 'trend_bull'
            else:
                result['type'] = 'trend_bear'
            result['reason'] = 'Strong ADX + EMA direction'

        # 3. Sideway
        else:
            result['type'] = 'sideway'
            result['reason'] = 'Weak trend / low ADX'

        return result


# =========================
# QUICK FUNCTION
# =========================

def detect_market_type(symbol='GOLD'):
    mt5.initialize()
    detector = MarketDetector(symbol)
    result = detector.detect()
    mt5.shutdown()
    return result


# =========================
# TEST
# =========================

if __name__ == "__main__":
    res = detect_market_type()
    print(res)