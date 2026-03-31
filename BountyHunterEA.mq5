//+------------------------------------------------------------------+
//|                                            BountyHunterEA.mq5     |
//|                                    MT5 Gold Trading EA           |
//|                                         Version 1.0              |
//+------------------------------------------------------------------+
#property copyright "BountyHunter EA"
#property link      "https://bh.probably-anything.com"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+

// Trading
input group "=== Trading Settings ==="
input double   LotSize = 0.1;              // Lot Size
input int      MagicNumber = 20260330;      // Magic Number
input string  TradeComment = "BountyHunter"; // Trade Comment

// Risk Management
input group "=== Risk Management ==="
input double   MaxRiskPercent = 2.0;       // Max Risk Per Trade (%)
input double   MaxDailyLoss = 10.0;        // Max Daily Loss (%)
input double   TrailingStop ATRMulti = 3.0; // Trailing Stop (ATR x)
input double   StopLoss ATRMultiSL = 2.0;  // Stop Loss (ATR x)

// Timeframes
input group "=== Timeframes ==="
input ENUM_TIMEFRAMES Timeframe1 = PERIOD_M5;  // Primary TF
input ENUM_TIMEFRAMES Timeframe2 = PERIOD_M15; // Secondary TF
input ENUM_TIMEFRAMES Timeframe3 = PERIOD_H1;  // Tertiary TF

// Strategy Weights
input group "=== Strategy Weights ==="
input double   WeightMomentum = 1.0;
input double   WeightMeanRev = 1.0;
input double   WeightBreakout = 1.0;
input double   WeightStructure = 1.0;
input double   WeightEMACross = 1.0;
input double   WeightSupertrend = 1.0;
input double   WeightMACD = 1.0;
input double   WeightADX = 1.0;
input double   WeightRSI = 1.0;
input double   WeightBollinger = 1.0;
input double   WeightStochastic = 1.0;
input double   WeightDonchian = 1.0;
input double   WeightATRBreakout = 1.0;

// Signal Consensus
input group "=== Signal Consensus ==="
input int      MinStrategiesAgree = 7;      // Min strategies to agree
input double   MinConfidence = 0.6;         // Min confidence to trade

//+------------------------------------------------------------------+
//| Global Variables                                                  |
//+------------------------------------------------------------------+
datetime lastTradeTime = 0;
datetime lastUpdateTime = 0;
double lastHighPrice = 0;
double lastLowPrice = 0;
double dailyLoss = 0;
datetime dailyResetTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   // Validate inputs
   if(LotSize <= 0)
   {
      Print("Error: LotSize must be > 0");
      return(INIT_PARAMETERS_INCORRECT);
   }
   
   if(MinStrategiesAgree < 1 || MinStrategiesAgree > 13)
   {
      Print("Error: MinStrategiesAgree must be between 1 and 13");
      return(INIT_PARAMETERS_INCORRECT);
   }
   
   // Reset daily tracking
   dailyResetTime = StringToTime(TimeToString(TimeCurrent(), TIME_DATE));
   dailyLoss = 0;
   
   Print("=== BountyHunter EA Initialized ===");
   Print("Symbol: ", _Symbol);
   Print("Timeframes: M5=", EnumToString(Timeframe1), 
         " M15=", EnumToString(Timeframe2), 
         " H1=", EnumToString(Timeframe3));
   Print("Min Strategies: ", MinStrategiesAgree, "/ 13");
   Print("=====================================");
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("=== BountyHunter EA Deinitialized ===");
   Comment("");
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check if new bar
   if(!IsNewBar())
      return;
   
   // Check daily loss limit
   if(CheckDailyLossLimit())
      return;
   
   // Update indicators and check signals
   CheckAndTrade();
}

//+------------------------------------------------------------------+
//| Check for new bar                                                 |
//+------------------------------------------------------------------+
bool IsNewBar()
{
   datetime currentTime = iTime(_Symbol, Timeframe1, 0);
   
   if(currentTime != lastUpdateTime)
   {
      lastUpdateTime = currentTime;
      return true;
   }
   
   return false;
}

//+------------------------------------------------------------------+
//| Main trading logic                                                |
//+------------------------------------------------------------------+
void CheckAndTrade()
{
   // Get signal strength from each strategy
   double buySignals = 0;
   double sellSignals = 0;
   double totalWeight = 0;
   
   // Count signals with weights
   buySignals += GetMomentumSignal() * WeightMomentum;
   buySignals += GetMeanReversionSignal() * WeightMeanRev;
   buySignals += GetBreakoutSignal() * WeightBreakout;
   buySignals += GetStructureSignal() * WeightStructure;
   buySignals += GetEMACrossSignal() * WeightEMACross;
   buySignals += GetSupertrendSignal() * WeightSupertrend;
   buySignals += GetMACDSignal() * WeightMACD;
   buySignals += GetADXSignal() * WeightADX;
   buySignals += GetRSISignal() * WeightRSI;
   buySignals += GetBollingerSignal() * WeightBollinger;
   buySignals += GetStochasticSignal() * WeightStochastic;
   buySignals += GetDonchianSignal() * WeightDonchian;
   buySignals += GetATRBreakoutSignal() * WeightATRBreakout;
   
   totalWeight = WeightMomentum + WeightMeanRev + WeightBreakout + WeightStructure +
                 WeightEMACross + WeightSupertrend + WeightMACD + WeightADX +
                 WeightRSI + WeightBollinger + WeightStochastic + WeightDonchian +
                 WeightATRBreakout;
   
   // Normalize signals
   double buyRatio = buySignals / totalWeight;
   double sellRatio = sellSignals / totalWeight;
   
   // Get consensus
   int strategiesAgreeingBuy = (int)(buyRatio * 13);
   int strategiesAgreeingSell = (int)(sellRatio * 13);
   
   // Check for trading signals
   double atr = iATR(_Symbol, Timeframe1, 14).MA(0);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   // Close conditions
   if(PositionsTotal() > 0)
   {
      CheckTrailingStop(atr);
      CheckExitConditions();
      return;
   }
   
   // Open conditions
   if(strategiesAgreeingBuy >= MinStrategiesAgree && buyRatio >= MinConfidence)
   {
      OpenBuy(atr, price);
   }
   else if(strategiesAgreeingSell >= MinStrategiesAgree && sellRatio >= MinConfidence)
   {
      OpenSell(atr, price);
   }
}

//+------------------------------------------------------------------+
//| Get Signal from each strategy (-1 to 1)                          |
//+------------------------------------------------------------------+

double GetMomentumSignal()
{
   // RSI and ADX momentum
   double rsi = iRSI(_Symbol, Timeframe1, 14, PRICE_CLOSE).MA(0);
   double adx = iADX(_Symbol, Timeframe1, 14).MA(0);
   double plusDi = iADX(_Symbol, Timeframe1, 14).Plus(0);
   double minusDi = iADX(_Symbol, Timeframe1, 14).Minus(0);
   
   if(adx > 25 && plusDi > minusDi && rsi > 50)
      return 1.0;
   else if(adx > 25 && minusDi > plusDi && rsi < 50)
      return -1.0;
   
   return 0;
}

double GetMeanReversionSignal()
{
   // Bollinger Bands
   double upper = iBands(_Symbol, Timeframe1, 20, 0, 2, PRICE_CLOSE).Upper(0);
   double lower = iBands(_Symbol, Timeframe1, 20, 0, 2, PRICE_CLOSE).Lower(0);
   double mid = iBands(_Symbol, Timeframe1, 20, 0, 2, PRICE_CLOSE).Base(0);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   if(price <= lower)
      return 1.0;
   else if(price >= upper)
      return -1.0;
   
   return 0;
}

double GetBreakoutSignal()
{
   // Donchian-style breakout
   double highest = iHighest(_Symbol, Timeframe1, MODE_HIGH, 20, 1);
   double lowest = iLowest(_Symbol, Timeframe1, MODE_LOW, 20, 1);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   if(price > highest)
      return 1.0;
   else if(price < lowest)
      return -1.0;
   
   return 0;
}

double GetStructureSignal()
{
   // Higher highs/lows detection
   double high1 = iHigh(_Symbol, Timeframe1, 1);
   double high2 = iHigh(_Symbol, Timeframe1, 2);
   double high3 = iHigh(_Symbol, Timeframe1, 3);
   double low1 = iLow(_Symbol, Timeframe1, 1);
   double low2 = iLow(_Symbol, Timeframe1, 2);
   double low3 = iLow(_Symbol, Timeframe1, 3);
   
   if(high1 > high2 && high2 > high3)
      return 1.0;
   else if(low1 < low2 && low2 < low3)
      return -1.0;
   
   return 0;
}

double GetEMACrossSignal()
{
   double ema9 = iMA(_Symbol, Timeframe1, 9, 0, MODE_EMA, PRICE_CLOSE).MA(0);
   double ema21 = iMA(_Symbol, Timeframe1, 21, 0, MODE_EMA, PRICE_CLOSE).MA(0);
   double ema9_prev = iMA(_Symbol, Timeframe1, 9, 0, MODE_EMA, PRICE_CLOSE).MA(1);
   double ema21_prev = iMA(_Symbol, Timeframe1, 21, 0, MODE_EMA, PRICE_CLOSE).MA(1);
   
   if(ema9_prev <= ema21_prev && ema9 > ema21)
      return 1.0;
   else if(ema9_prev >= ema21_prev && ema9 < ema21)
      return -1.0;
   
   return 0;
}

double GetSupertrendSignal()
{
   // Simplified Supertrend
   double atr = iATR(_Symbol, Timeframe1, 10).MA(0);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double hl2 = (iHigh(_Symbol, Timeframe1, 0) + iLow(_Symbol, Timeframe1, 0)) / 2;
   
   double upper = hl2 + 3 * atr;
   double lower = hl2 - 3 * atr;
   
   static double supertrend = 0;
   static int direction = 1;
   
   if(price > upper)
   {
      direction = 1;
      supertrend = lower;
   }
   else if(price < lower)
   {
      direction = -1;
      supertrend = upper;
   }
   
   return direction;
}

double GetMACDSignal()
{
   double macdMain = iMACD(_Symbol, Timeframe1, 12, 26, 9, PRICE_CLOSE).Main(0);
   double macdSignal = iMACD(_Symbol, Timeframe1, 12, 26, 9, PRICE_CLOSE).Signal(0);
   double macdMainPrev = iMACD(_Symbol, Timeframe1, 12, 26, 9, PRICE_CLOSE).Main(1);
   double macdSignalPrev = iMACD(_Symbol, Timeframe1, 12, 26, 9, PRICE_CLOSE).Signal(1);
   
   if(macdMainPrev <= macdSignalPrev && macdMain > macdSignal)
      return 1.0;
   else if(macdMainPrev >= macdSignalPrev && macdMain < macdSignal)
      return -1.0;
   
   return 0;
}

double GetADXSignal()
{
   double adx = iADX(_Symbol, Timeframe1, 14).MA(0);
   double plusDi = iADX(_Symbol, Timeframe1, 14).Plus(0);
   double minusDi = iADX(_Symbol, Timeframe1, 14).Minus(0);
   
   if(adx > 25 && plusDi > minusDi)
      return 1.0;
   else if(adx > 25 && minusDi > plusDi)
      return -1.0;
   
   return 0;
}

double GetRSISignal()
{
   double rsi = iRSI(_Symbol, Timeframe1, 14, PRICE_CLOSE).MA(0);
   double rsiPrev = iRSI(_Symbol, Timeframe1, 14, PRICE_CLOSE).MA(1);
   
   if(rsiPrev <= 30 && rsi > 30)
      return 1.0;
   else if(rsiPrev >= 70 && rsi < 70)
      return -1.0;
   
   if(rsi < 30)
      return 0.7;
   else if(rsi > 70)
      return -0.7;
   
   return 0;
}

double GetBollingerSignal()
{
   double upper = iBands(_Symbol, Timeframe1, 20, 0, 2, PRICE_CLOSE).Upper(0);
   double lower = iBands(_Symbol, Timeframe1, 20, 0, 2, PRICE_CLOSE).Lower(0);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   if(price <= lower)
      return 1.0;
   else if(price >= upper)
      return -1.0;
   
   return 0;
}

double GetStochasticSignal()
{
   double k = iStochastic(_Symbol, Timeframe1, 14, 3, 3, MODE_SMA, STO_LOWHISH).K(0);
   double d = iStochastic(_Symbol, Timeframe1, 14, 3, 3, MODE_SMA, STO_LOWHISH).D(0);
   double kPrev = iStochastic(_Symbol, Timeframe1, 14, 3, 3, MODE_SMA, STO_LOWHISH).K(1);
   double dPrev = iStochastic(_Symbol, Timeframe1, 14, 3, 3, MODE_SMA, STO_LOWHISH).D(1);
   
   if(kPrev <= dPrev && k > d && k < 20)
      return 1.0;
   else if(kPrev >= dPrev && k < d && k > 80)
      return -1.0;
   
   return 0;
}

double GetDonchianSignal()
{
   double upper = iHighest(_Symbol, Timeframe1, MODE_HIGH, 20, 1);
   double lower = iLowest(_Symbol, Timeframe1, MODE_LOW, 20, 1);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   if(price > upper)
      return 1.0;
   else if(price < lower)
      return -1.0;
   
   return 0;
}

double GetATRBreakoutSignal()
{
   double atr = iATR(_Symbol, Timeframe1, 14).MA(0);
   double highest = iHighest(_Symbol, Timeframe1, MODE_HIGH, 14, 1);
   double lowest = iLowest(_Symbol, Timeframe1, MODE_LOW, 14, 1);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   if(price > highest + atr * 0.5)
      return 1.0;
   else if(price < lowest - atr * 0.5)
      return -1.0;
   
   return 0;
}

//+------------------------------------------------------------------+
//| Open Buy Position                                                |
//+------------------------------------------------------------------+
void OpenBuy(double atr, double price)
{
   double sl = price - StopLoss * atr;
   double tp = price + (StopLoss * atr) * 2;
   double volume = CalculateLotSize(atr, sl, price);
   
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = volume;
   request.type = ORDER_TYPE_BUY;
   request.price = price;
   request.sl = sl;
   request.tp = tp;
   request.magic = MagicNumber;
   request.comment = TradeComment;
   request.type_filling = ORDER_FILLING_RETURN;
   
   OrderSend(request, result);
   
   if(result.retcode == TRADE_RETCODE_DONE)
   {
      Print("Buy opened: Volume=", volume, " Price=", price, " SL=", sl, " TP=", tp);
   }
   else
   {
      Print("Buy open failed: ", result.retcode);
   }
}

//+------------------------------------------------------------------+
//| Open Sell Position                                                |
//+------------------------------------------------------------------+
void OpenSell(double atr, double price)
{
   double sl = price + StopLoss * atr;
   double tp = price - (StopLoss * atr) * 2;
   double volume = CalculateLotSize(atr, sl, price);
   
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = volume;
   request.type = ORDER_TYPE_SELL;
   request.price = price;
   request.sl = sl;
   request.tp = tp;
   request.magic = MagicNumber;
   request.comment = TradeComment;
   request.type_filling = ORDER_FILLING_RETURN;
   
   OrderSend(request, result);
   
   if(result.retcode == TRADE_RETCODE_DONE)
   {
      Print("Sell opened: Volume=", volume, " Price=", price, " SL=", sl, " TP=", tp);
   }
   else
   {
      Print("Sell open failed: ", result.retcode);
   }
}

//+------------------------------------------------------------------+
//| Calculate Lot Size based on risk                                 |
//+------------------------------------------------------------------+
double CalculateLotSize(double atr, double sl, double price)
{
   double riskAmount = AccountInfoDouble(ACCOUNT_BALANCE) * MaxRiskPercent / 100;
   double slDistance = MathAbs(price - sl);
   
   if(slDistance == 0)
      return LotSize;
   
   // Gold lot size (100 oz per lot)
   double lotSize = riskAmount / (slDistance * 100);
   
   // Normalize to lot size limits
   lotSize = MathMax(0.01, MathMin(lotSize, 1.0));
   
   return NormalizeDouble(lotSize, 2);
}

//+------------------------------------------------------------------+
//| Check Trailing Stop                                              |
//+------------------------------------------------------------------+
void CheckTrailingStop(double atr)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) != _Symbol)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;
      
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double price = PositionGetDouble(POSITION_PRICE_CURRENT);
      
      int type = (int)PositionGetInteger(POSITION_TYPE);
      
      if(type == POSITION_TYPE_BUY)
      {
         double newSL = price - TrailingStop * atr;
         if(newSL > sl && newSL > openPrice)
         {
            ModifyPosition(sl, tp);
         }
      }
      else if(type == POSITION_TYPE_SELL)
      {
         double newSL = price + TrailingStop * atr;
         if(newSL < sl || sl == 0)
         {
            ModifyPosition(newSL, tp);
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Modify Position                                                   |
//+------------------------------------------------------------------+
void ModifyPosition(double newSL, double newTP)
{
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_SLTP;
   request.position = PositionGetInteger(POSITION_TICKET);
   request.sl = newSL;
   request.tp = newTP;
   request.magic = MagicNumber;
   
   OrderSend(request, result);
}

//+------------------------------------------------------------------+
//| Check Exit Conditions                                             |
//+------------------------------------------------------------------+
void CheckExitConditions()
{
   // Check all open positions for exit signals
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) != _Symbol)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber)
         continue;
      
      int type = (int)PositionGetInteger(POSITION_TYPE);
      double rsi = iRSI(_Symbol, Timeframe1, 14, PRICE_CLOSE).MA(0);
      
      if(type == POSITION_TYPE_BUY && rsi > 75)
      {
         ClosePosition(PositionGetInteger(POSITION_TICKET));
      }
      else if(type == POSITION_TYPE_SELL && rsi < 25)
      {
         ClosePosition(PositionGetInteger(POSITION_TICKET));
      }
   }
}

//+------------------------------------------------------------------+
//| Close Position                                                    |
//+------------------------------------------------------------------+
void ClosePositionulong ticket)
{
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.position = ticket;
   request.volume = PositionGetDouble(POSITION_VOLUME);
   request.magic = MagicNumber;
   request.type_filling = ORDER_FILLING_RETURN;
   
   if((int)PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
   {
      request.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      request.type = ORDER_TYPE_SELL;
   }
   else
   {
      request.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      request.type = ORDER_TYPE_BUY;
   }
   
   OrderSend(request, result);
}

//+------------------------------------------------------------------+
//| Check Daily Loss Limit                                           |
//+------------------------------------------------------------------+
bool CheckDailyLossLimit()
{
   datetime currentTime = StringToTime(TimeToString(TimeCurrent(), TIME_DATE));
   
   // Reset daily tracking
   if(currentTime > dailyResetTime)
   {
      dailyResetTime = currentTime;
      dailyLoss = 0;
   }
   
   // Calculate today's P&L
   double todayPL = AccountInfoDouble(ACCOUNT_PROFIT);
   
   if(todayPL < 0)
   {
      dailyLoss = MathAbs(todayPL);
      double maxLoss = AccountInfoDouble(ACCOUNT_BALANCE) * MaxDailyLoss / 100;
      
      if(dailyLoss >= maxLoss)
      {
         Print("Daily loss limit reached: ", dailyLoss, " / ", maxLoss);
         return true;
      }
   }
   
   return false;
}

//+------------------------------------------------------------------+
//| Chart Comment                                                     |
//+------------------------------------------------------------------+
void UpdateChartComment()
{
   string comment = "=== BountyHunter EA ===\n";
   comment += "Symbol: " + _Symbol + "\n";
   comment += "Timeframes: M5, M15, H1\n";
   comment += "Strategies: 13\n";
   comment += "Min Consensus: " + IntegerToString(MinStrategiesAgree) + "/13\n";
   comment += "Min Confidence: " + DoubleToString(MinConfidence * 100, 0) + "%\n";
   comment += "\nRisk Management:\n";
   comment += "Max Risk: " + DoubleToString(MaxRiskPercent, 1) + "%\n";
   comment += "Max Daily Loss: " + DoubleToString(MaxDailyLoss, 1) + "%\n";
   comment += "Trailing Stop: " + DoubleToString(TrailingStop, 1) + " ATR\n";
   comment += "\nPositions: " + IntegerToString(PositionsTotal()) + "\n";
   
   Comment(comment);
}

//+------------------------------------------------------------------+
