# MT5 Gold Trader - AI Trading System

ระบบเทรดทองคำอัตโนมัติด้วย AI พร้อม Dashboard แสดงผลแบบเรียลไทม์

---

## 🎯 ภาพรวมระบบ

### สิ่งที่ระบบทำได้

- ✅ เชื่อมต่อ MT5 อัตโนมัติ
- ✅ วิเคราะห์ 13 Trading Strategies
- ✅ ตัดสินใจ BUY/SELL/HOLD อัตโนมัติ
- ✅ เปิด/ปิด Position อัตโนมัติ
- ✅ Dashboard แสดงผลแบบเรียลไทม์
- ✅ ดู History, Equity Curve, Performance
- ✅ ตั้งค่า Lot Size, SL, TP ได้
- ✅ ปิด Position มือผ่าน Dashboard

---

## 💻 การติดตั้ง

### ความต้องการของระบบ

- Python 3.8+
- MetaTrader 5 (MT5)
- Internet connection

### ติดตั้ง Dependencies

```bash
cd D:\PythonApp\mt5-gold-trader
pip install -r requirements.txt
```

### Dependencies ที่ใช้

```
MetaTrader5
flask
```

---

## 🚀 การใช้งาน

### 1. เปิด MT5

ตรวจสอบว่า MT5 เปิดอยู่และเชื่อมต่อกับ Server

### 2. รันระบบ

```bash
cd D:\PythonApp\mt5-gold-trader
python main.py
```

### 3. เลือกโหมดการทำงาน

```
============================================================
MT5 Gold Trader - AI Trading System
============================================================

Options:
  1. Run Trading System Only
  2. Run Dashboard Only
  3. Run Full System (Trading + Dashboard)

Select option (1/2/3):
```

- **Option 1**: รันแค่ระบบเทรด
- **Option 2**: รันแค่ Dashboard  
- **Option 3**: รันทั้งคู่ (แนะนำ)

### 4. เปิด Dashboard

เปิด Browser ไปที่: http://localhost:5000

---

## 📊 Dashboard

### หน้าหลัก

Dashboard แสดงข้อมูล:

| ส่วน | รายละเอียด |
|------|-------------|
| **Portfolio** | ยอดเงิน, Equity, P&L |
| **Open Positions** | รายการ Position ที่เปิดอยู่ + ปุ่มปิด |
| **Signals** | สัญญาณจาก 13 Strategies |
| **Decision History** | ประวัติการตัดสินใจ (กดดูรายละเอียดได้) |
| **Equity Curve** | กราฟ Equity ย้อนหลัง |
| **Trade History** | ประวัติการเทรดที่ปิดแล้ว |

### Remote Access

เข้าถึง Dashboard จากข้างนอกได้โดยใช้ ngrok:

```bash
cd D:\PythonApp\mt5-gold-trader
ngrok.exe http 5000
```

---

## ⚙️ การตั้งค่า

### การตั้งค่าผ่าน Dashboard

1. กดปุ่ม **⚙️ Settings** ที่หัวข้อ Open Positions
2. ตั้งค่า:
   - **Lot Min**: ขนาด Lot ขั้นต่ำ (เช่น 0.01)
   - **Lot Max**: ขนาด Lot สูงสุด (เช่น 0.1)
   - **SL Percent**: % สำหรับ Stop Loss
   - **TP Percent**: % สำหรับ Take Profit

### สูตรคำนวณ

**Lot Size:**
```
lot = min_lot + (max_lot - min_lot) × confidence
```

**SL/TP:**
```
SL = entry_price × (1 - sl_percent/100)
TP = entry_price × (1 + tp_percent/100)
```

---

## 📈 Strategies

ระบบมี 13 Strategies ที่ทำงานพร้อมกัน:

| # | Strategy | คำอธิบาย |
|---|---------|---------|
| 1 | Momentum | วิเคราะห์แรงผลักดันของราคา |
| 2 | Mean Reversion | หาราคาที่กลับเข้า mean |
| 3 | Breakout | ตรวจจับการทะลุแนวรับ/แนวต้าน |
| 4 | Structure | วิเคราะห์โครงสร้างราคา |
| 5 | EMA Crossover | EMA 9/21 ตัดกัน |
| 6 | Supertrend | เทรนด์ตามด้วย Supertrend |
| 7 | MACD | MACD Histogram |
| 8 | ADX Trend | ความแข็งแรงของเทรนด์ |
| 9 | RSI | RSI 14 ช่วง overbought/oversold |
| 10 | Bollinger Bands | กรอบราคา 2 SD |
| 11 | Stochastic | Stochastic Oscillator |
| 12 | Donchian Channel | High/Low ช่วง 20 |
| 13 | ATR Breakout | ทะลุ ATR |

### การตัดสินใจ (Voting System)

```
1. ถ้า BUY strategies >= 3 → BUY
2. ถ้า SELL strategies >= 3 → SELL
3. ถ้า BUY == SELL → ดู avg confidence
4. ไม่เข้าเงื่อนไข → HOLD
```

---

## 🔢 การคำนวณ Lot Size

### ตัวอย่าง

| Confidence | Lot Min=0.01 | Lot Max=0.1 | ผลลัพธ์ |
|------------|--------------|-------------|----------|
| 30% | 0.01 | 0.1 | 0.04 |
| 50% | 0.01 | 0.1 | 0.06 |
| 70% | 0.01 | 0.1 | 0.07 |
| 90% | 0.01 | 0.1 | 0.09 |

### สูตร

```
lot_size = lot_min + (lot_max - lot_min) × confidence
```

---

## ⚙️ การทำงานของระบบ

### Main Loop

```
1. ดึงข้อมูลตลาด (M15 candles)
2. คำนวณ Indicators ทั้ง 13 ตัว
3. แต่ละ Strategy สร้าง Signal
4. Composite Strategy รวม Signal (Voting)
5. ถ้า BUY >= 3 หรือ SELL >= 3 → เปิด Position
6. บันทึก Decision ลง Database
7. แสดงผลบน Dashboard
```

### Timeframe

- **Candles**: M15
- **Check Interval**: ทุก 15 นาที (หรือตามตั้งค่า)

### SL/TP

- **SL**: ตั้งตาม SL Percent จาก entry price
- **TP**: ตั้งตาม TP Percent จาก entry price

### Take Profit Logic

ระบบจะปิด Position อัตโนมัติเมื่อ:
1. ได้กำไร >= $50
2. Strategy บอกทิศตรงข้าม (เช่น ถือ BUY แต่ Strategy บอก SELL)

---

## 📁 โครงสร้างไฟล์

```
D:\PythonApp\mt5-gold-trader\
├── main.py                    # ระบบเทรดหลัก
├── dashboard.py                # Flask Dashboard
├── database.py                 # SQLite Database
├── settings.json               # ตั้งค่าผู้ใช้
├── requirements.txt            # Python dependencies
├── README.md                   # เอกสารนี้
│
├── mt5/
│   ├── __init__.py
│   └── connection.py          # MT5 Connection
│
├── strategies/
│   ├── __init__.py
│   ├── base.py                 # Base Strategy + Composite
│   ├── momentum.py
│   ├── mean_reversion.py
│   ├── breakout.py
│   ├── structure.py
│   ├── ema_crossover.py
│   ├── supertrend.py
│   ├── macd_strategy.py
│   ├── adx_trend.py
│   ├── rsi_strategy.py
│   ├── bollinger_strategy.py
│   ├── stochastic_strategy.py
│   ├── donchian_strategy.py
│   └── atr_breakout_strategy.py
│
├── templates/
│   └── dashboard.html          # Dashboard HTML/CSS/JS
│
└── data/
    └── trades.db               # SQLite Database
```

---

## 🔧 Troubleshooting

### MT5 ไม่เชื่อมต่อ

1. ตรวจสอบว่า MT5 เปิดอยู่
2. ตรวจสอบว่า MT5 เชื่อมต่อ Server แล้ว
3. Restart MT5

### Dashboard ไม่โหลด

1. ตรวจสอบว่า Python process รันอยู่
2. ลอง Restart ระบบ

### ปิด Position ไม่ได้

1. ตรวจสอบว่า Position ยังเปิดอยู่ใน MT5
2. Refresh Dashboard

---

## 📝 Database Schema

### Tables

**trades**
- id, symbol, direction, entry_price, exit_price, volume, sl, tp, profit, status, timestamp_open, timestamp_close

**signals**
- id, strategy_name, signal_type, confidence, timestamp

**decision_history**
- id, action, confidence, final_decision, strategies_analyzed, timestamp, position_id, price, volume, profit, reason

**equity_curve**
- id, equity, timestamp

**performance**
- id, metric, value, timestamp

---

## 🙏 Credits

พัฒนาโดย AI Assistant สำหรับ Jay

---

## 📄 License

MIT License
