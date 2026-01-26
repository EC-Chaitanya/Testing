# ACTION PLAN: How To Make This Actually Tradeable

**Status:** System is NOT ready for live trading  
**Goal:** Make it actually profitable  
**Timeframe:** 3-6 months minimum  

---

## Phase 1: VALIDATION (Weeks 1-4)

### Step 1.1: Get Real Data Source
**Why:** yfinance will fail in production. Needs NSE-direct or professional feed.

**Options:**
1. **Zerodha Kite (RECOMMENDED)** - ₹0/month
   - Free tier: 1-year historical data
   - Real-time 5-min candles
   - Direct NSE feed
   - Reliable, professional
   
2. **NSE Shoonya** - ₹1,000-2,000/month  
   - Professional-grade data
   - Guaranteed SLA
   - Direct exchange feed
   
3. **Stay with yfinance** - ₹0/month but RISKY
   - Works for now but will break eventually
   - Don't rely on this for production

**Action:** Subscribe to Zerodha (free) or NSE Shoonya (paid). Switch data source in code.

**Code Change Required:**
```python
# Current (unreliable):
from yfinance import download

# New (reliable):
from kiteconnect import KiteConnect  # Zerodha
# or use NSE Shoonya API
```

**Effort:** 2-4 hours  
**Cost:** ₹0-2,000/month

---

### Step 1.2: Backtest On Real Historical Data (3 Years)
**Why:** Prove the strategy actually works before risking real money.

**What to do:**
1. Download 3 years of NIFTY 5-min historical data (2023-2026)
2. Run your system on this data
3. Calculate metrics:
   - Total trades
   - Win rate %
   - Average winning trade
   - Average losing trade
   - Max consecutive losses
   - Max drawdown %
   - Profit factor (total wins / total losses)
   - Sharpe ratio

**What to expect:**
- If win rate < 55%: **SYSTEM IS UNPROFITABLE. Stop here.**
- If win rate 55-60%: **Marginal. Needs cost analysis.**
- If win rate > 60%: **Promising. Continue to phase 2.**

**Code Required:**
Create a backtesting module:
```python
class BacktestEngine:
    def run_backtest(self, historical_data, start_capital=500000):
        trades = []
        for each_5_min_candle:
            signal = self.get_signal(candle)
            if signal:
                entry = simulate_execution(signal)
                exit = simulate_exit(signal)
                trade_pnl = calculate_pnl(entry, exit)
                trades.append(trade_pnl)
        
        return {
            'total_trades': len(trades),
            'win_rate': sum(1 for t in trades if t > 0) / len(trades),
            'avg_win': sum(t for t in trades if t > 0) / sum(1 for t in trades if t > 0),
            'avg_loss': sum(t for t in trades if t < 0) / sum(1 for t in trades if t < 0),
            'max_loss': min(trades),
            'max_consecutive_loss': calculate_consecutive_losses(trades),
            'sharpe_ratio': calculate_sharpe(trades)
        }
```

**Effort:** 4-8 hours  
**Cost:** ₹0 (use free data)

---

### Step 1.3: Add Slippage & Cost Model
**Why:** Backtests lie if they don't include real costs.

**What to include in simulation:**
```python
# Entry slippage (spread + price movement)
entry_slippage = avg_spread + 1 point  # Conservative

# Brokerage (both entry and exit)
brokerage_pct = 0.02%  # 2 basis points
brokerage_entry = notional * brokerage_pct
brokerage_exit = notional * brokerage_pct

# Taxes
stt = 0.01% (on exit for index futures)
gst = 18% (on brokerage)

# Real P&L
gross_pnl = entry_points × contract_multiplier
net_pnl = gross_pnl - brokerage - gst - stt
```

**Effect on Expected Returns:**
If backtest shows +₹100 profit:
- Minus spread cost: -₹50
- Minus brokerage: -₹15
- Minus taxes: -₹10
- **Net: +₹25 (75% of expected profit lost to costs)**

**Effort:** 2-3 hours  
**Cost:** ₹0

---

## Phase 2: PROOF OF CONCEPT (Weeks 5-8)

### Step 2.1: Paper Trade For 2 Weeks
**Why:** Prove backtest assumptions match real market reality.

**How to:**
1. Run live system (not using real money)
2. Log every signal generated
3. Log entry price (market price at signal time)
4. Log actual entry price (where you would execute)
5. Log exit price (where you would exit)
6. Calculate real P&L including slippage
7. Compare to backtest expectations

**What to track:**
```
Date | Time | Signal | Entry Signal | Entry Actual | Exit | P&L | Backtest Expected
2026-01-24 | 10:15 | BUY NIFTY | 23100 | 23104 | 23150 | +4600 | +5000
2026-01-24 | 11:30 | BUY NIFTY | 23200 | 23206 | 23140 | -6600 | -5000
...
```

**Success Criteria:**
- Paper win rate ≥ backtest win rate (expected: backtest is usually 5-10% optimistic)
- Real entries within 5 points of signal price
- Slippage ≤ 10 points per trade

**Failure Criteria:**
- Paper win rate < 50%: **System doesn't work. Restart.**
- Slippage > 20 points average: **Data quality issue. Fix data source.**
- Can't get consistent entries: **Liquidity issue. Check market times.**

**Effort:** 2 weeks (passive monitoring)  
**Cost:** ₹0

---

### Step 2.2: Adjust Parameters Based On Reality
**Why:** Your synthetic backtesting assumptions might be wrong.

**What to adjust:**
1. **Reversal candle threshold:** If hammers too common, increase wick multiplier (2x → 3x)
2. **Volume confirmation:** If high volume gives false signals, increase multiplier (1.5x → 2.0x)
3. **SuperTrend period:** If too many false signals, try period 30 or 40 (instead of 20)
4. **Stop loss placement:** If frequently hit on noise, increase buffer (0.5 pts → 2 pts)
5. **Entry timing:** If missing entries, should you enter immediately or wait for confirmation candle?

**How to adjust:**
- Paper trade 100-200 trades with ORIGINAL parameters
- Calculate win rate
- If < 55%, adjust ONE parameter
- Paper trade another 50 trades
- Repeat until win rate > 55%

**Effort:** 2-4 weeks  
**Cost:** ₹0

---

## Phase 3: LIVE TRADING (Weeks 9+)

### Step 3.1: Start Small (1 lot, 1% risk)
**Why:** Limit damage while learning.

**Position sizing:**
```
Account: ₹5,00,000
Risk per trade: 1% = ₹5,000
Stop loss: 50 points
Position size: ₹5,000 / 50 = 1 lot (100 rupees per point)

If this trade is wrong:
- Loss: ₹5,000 maximum
- Account impact: 1% (recoverable)
```

**Daily loss limit:**
```
Daily max loss: 5% of account = ₹25,000
If you hit -₹25,000, STOP trading for the day
Don't try to recover losses
```

**Effort:** Daily 15 min monitoring  
**Cost:** ₹50-100 per day (brokerage)

---

### Step 3.2: Track Metrics Daily
**Why:** Know immediately if it's working or not.

**Daily tracking:**
```
Date: 2026-02-15
Trades: 3
- Trade 1: +₹5,200
- Trade 2: -₹3,100
- Trade 3: +₹6,800
Daily P&L: +₹8,900

Win rate: 67% (2/3)
Avg win: +₹6,000
Avg loss: -₹3,100
```

**Weekly tracking:**
```
Week of Jan 27:
Total trades: 15
Winning: 9 (60%)
Losing: 6 (40%)
Weekly P&L: +₹42,000
Drawdown from high: 5%
```

**Monthly tracking:**
```
January 2026:
Total trades: 60
Win rate: 58%
Avg winning trade: +₹5,100
Avg losing trade: -₹3,800
Monthly P&L: +₹82,000
Max daily loss: -₹18,000 (3.6%)
Return: 16.4% (monthly)
```

**What to look for:**
- ✅ Win rate ≥ 55%: Good
- ✅ Avg win > Avg loss: Good  
- ✅ Monthly return stable: Good
- ❌ Win rate < 50%: STOP immediately
- ❌ Consecutive 3 losses: Review system
- ❌ Monthly return < expected: Adjust or stop

**Effort:** 15 min/day, 30 min/week  
**Cost:** ₹0

---

### Step 3.3: Increase Size Gradually
**Why:** Only increase risk if system is consistently profitable.

**Size progression:**
```
Month 1: 1 lot (1% risk per trade)
  - If profitable and stable
Month 2: 2 lots (2% risk per trade)
  - If still profitable
Month 3: 5 lots (5% risk per trade)
  - If returns are consistent
Month 6: Full size (10% risk per trade)
  - Once track record is 6+ months
```

**Never increase size if:**
- Win rate < 55%
- Had 3+ consecutive losses this month
- Monthly return < expected by > 20%
- Max drawdown > 10%

**Effort:** 2 min/month (size decision)  
**Cost:** Increases with size

---

## Critical Checkpoints

### Checkpoint 1: After Backtesting (Week 4)
**Decision:**
- ✅ Win rate ≥ 55% → Continue to Phase 2
- ❌ Win rate < 55% → Go back to design phase. Strategy doesn't work.

### Checkpoint 2: After Paper Trading (Week 8)
**Decision:**
- ✅ Paper win rate ≥ backtest-2% → Continue to Phase 3
- ⚠️ Paper win rate = backtest-5% → Adjust parameters, re-test
- ❌ Paper win rate < 50% → System doesn't work on real data. Redesign.

### Checkpoint 3: After 1 Month Live (Week 13)
**Decision:**
- ✅ Live win rate ≥ 55% AND profit > expected → Increase size
- ⚠️ Live win rate = 50-55% → Keep current size, continue monitoring
- ❌ Live win rate < 50% → STOP. Something is wrong.

### Checkpoint 4: After 3 Months Live (Week 25)
**Decision:**
- ✅ 3-month win rate ≥ 55% AND consistent monthly profits → Increase to full size
- ⚠️ 3-month win rate inconsistent (50-60%) → Reduce expectations or stop
- ❌ Average loss > average win → System is broken. Fix or abandon.

---

## Specific Changes Needed In Code

### 1. Add Backtest Mode
```python
# src/backtest.py - needs to be expanded
class BacktestEngine:
    def __init__(self, historical_data, start_capital):
        self.data = historical_data
        self.capital = start_capital
        self.trades = []
    
    def run(self):
        for each_candle:
            signal = self.get_signal()
            if signal:
                entry_price = self.simulate_entry(signal)
                exit_price = self.simulate_exit(signal)
                pnl = self.calculate_pnl(entry_price, exit_price)
                self.trades.append(pnl)
    
    def get_statistics(self):
        return {
            'total_trades': len(self.trades),
            'win_rate': winning_trades / total_trades,
            'avg_win': avg(winning_trades),
            'avg_loss': avg(losing_trades),
            'max_loss': min(self.trades),
            'profit_factor': sum(wins) / sum(losses),
            'sharpe_ratio': calculate_sharpe(self.trades)
        }
```

### 2. Add Real Cost Model
```python
def calculate_realistic_pnl(entry, exit, quantity):
    gross_pnl = (exit - entry) * quantity * 100
    
    # Spread cost (average bid-ask)
    entry_spread = 3 * 100  # 3 points per lot
    exit_spread = 3 * 100   # 3 points per lot
    
    # Brokerage (0.02%)
    notional = entry * quantity * 200
    brokerage = notional * 0.0002
    
    # Taxes
    stt = exit * quantity * 100 * 0.0001
    gst = brokerage * 0.18
    
    net_pnl = gross_pnl - entry_spread - exit_spread - brokerage - stt - gst
    return net_pnl
```

### 3. Add Position Sizing
```python
def calculate_position_size(account, risk_pct, stop_loss_points):
    max_risk = account * risk_pct
    points_to_loss = abs(stop_loss_points)
    per_point_value = 100  # NIFTY/BANKNIFTY
    
    position_size = max_risk / (points_to_loss * per_point_value)
    return int(position_size)  # Round down to whole lots
```

### 4. Add Daily Loss Limit
```python
def check_daily_loss_limit(daily_pnl, account, limit_pct=5):
    if abs(daily_pnl) > account * limit_pct / 100:
        return False  # Don't trade - limit reached
    return True
```

---

## Summary: What Actually Needs To Happen

| Phase | What | Timeline | Cost | Success Metric |
|-------|------|----------|------|----------------|
| **1** | Backtest 3 years data | 2-4 weeks | ₹0 | Win rate ≥ 55% |
| **1** | Paper trade 2 weeks | 2 weeks | ₹0 | Paper matches backtest |
| **1** | Add cost model | 1 week | ₹0 | Still profitable after costs |
| **2** | Adjust parameters | 2-4 weeks | ₹0 | Win rate stabilizes |
| **3** | Live 1 lot for month | 4 weeks | ₹5-10k | Win rate ≥ 55% |
| **3** | Increase to 2 lots | 4 weeks | ₹10-20k | Still ≥ 55% |
| **3** | Scale to full size | 8+ weeks | ₹50-100k | 3-month consistency |

**Total timeline:** Minimum 3-6 months before you should trade at full size

**Bottom line:** Don't skip steps. Every step is designed to catch fatal flaws before they cost real money.

---

**Status:** Current system ❌ NOT READY  
**Required work:** Phases 1-2 complete before ANY live trading  
**Estimated effort:** 200-300 hours  
**Estimated cost:** ₹5,000-50,000 (depending on data source chosen)

This is what trading really looks like. Not theory. Not exciting. Just disciplined validation before risking real money.
