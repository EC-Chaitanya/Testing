# Trading Terminal - Troubleshooting Guide

## Issue: "Insufficient Data" in Live Scanner Mode

### Root Cause
The NSE API (`equity_history`) is returning incomplete or no data for the requested date range. This appears to be a limitation or issue with the nsepython library's data retrieval.

### ✅ Solution: Use Sample CSV Files (Recommended for Testing)

**Step 1:** Generate Sample Data
```bash
python generate_sample_data.py
```
This creates 7 sample CSV files with realistic price data:
- `sample_RELIANCE_data.csv`
- `sample_TCS_data.csv`
- `sample_HDFCBANK_data.csv`
- And 4 more...

**Step 2:** Test with Backtest Mode
1. Run: `python main.py`
2. Select: **[2] Historical Backtest Mode**
3. Select: **[1] Load from Local CSV File**
4. Enter: `sample_RELIANCE_data.csv`
5. Watch the signals and analysis!

### 📊 What You'll See

**Backtest Report Shows:**
- Total candles analyzed (60 business days)
- Number of bullish signals (≥65 score)
- Number of bearish signals (≥65 score)
- Top 10 bullish and bearish opportunities
- Detailed CSV report exported

---

## Alternative: Using NSE API (for Production)

If NSE API access improves, the Live Scanner can work with:
```python
# In live_scanner.py, the system will:
1. Fetch 90 days of historical data
2. Calculate daily technical indicators
3. Score each stock for bullish/bearish
4. Display results in real-time
```

**Note:** For true 5-minute intraday data, you'd need:
- Alternative data provider (Zerodha Kite, Broker APIs)
- WebSocket connections for live data
- Or integrate with other Indian stock APIs

---

## Quick Reference: System Architecture

### Components:
| Component | Purpose | Status |
|-----------|---------|--------|
| `main.py` | CLI Gatekeeper | ✓ Working |
| `src/engine.py` | Dual-directional scoring | ✓ Working |
| `src/live_scanner.py` | Real-time scanner | ⚠️ Needs data source |
| `src/backtest.py` | Historical analysis | ✓ Working |
| `src/data_fethcer.py` | Data retrieval | ⚠️ NSE API issues |
| `sample_*_data.csv` | Test data | ✓ Generated |

### Scoring Logic:
- **Bullish Score:** Price > EMA20 & EMA50 (30) + RSI 55-70 (30) + Price > VWAP (20) - Exhaustion (-20)
- **Bearish Score:** Price < EMA20 & EMA50 (30) + RSI 30-45 (30) + Price < VWAP (20) - Exhaustion (-20)
- **Threshold:** 65 points

---

## Troubleshooting Steps

### Issue 1: "Module not found" errors
**Solution:**
```bash
pip install nsepython pandas pandas_ta python-dotenv
```

### Issue 2: NSE API returns empty data
**Solution:**
- Use sample CSV files (recommended)
- Check internet connection
- Try different date ranges
- Use backtest mode instead

### Issue 3: Insufficient data warnings
**Solution:**
- Make sure CSV has minimum 50 rows
- Check column names: Time, Open, High, Low, Close, Volume
- Use generated sample data files

### Issue 4: "tabulate not installed" warning
**Solution:**
```bash
pip install tabulate
```
(Optional - system works without it, uses basic formatting)

---

## Testing Workflow

```
1. Generate Sample Data
   └─ python generate_sample_data.py

2. Run Main Program
   └─ python main.py

3. Select Backtest Mode [2]
   └─ Choose CSV [1]
   └─ Enter: sample_RELIANCE_data.csv

4. Review Results
   └─ Signals identified
   └─ CSV report generated
   └─ Statistics displayed
```

---

## Next Steps for Production

To move to production trading:

1. **Replace Data Source**
   - Integrate broker APIs (Zerodha, ICICI, etc.)
   - Use paid financial data providers
   - Implement WebSocket for live data

2. **Add Trade Execution**
   - Connect to broker order APIs
   - Implement position management
   - Add risk controls

3. **Enhance Monitoring**
   - Real-time dashboard
   - Email/SMS alerts
   - Performance tracking

4. **Optimize Scoring**
   - Add more indicators
   - Machine learning validation
   - Multi-timeframe analysis

---

**Last Updated:** 2026-01-05
**Version:** 2.0
**Status:** Testing Phase
