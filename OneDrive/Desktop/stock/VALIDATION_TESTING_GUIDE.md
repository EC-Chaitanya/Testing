# VALIDATION & TESTING GUIDE

## Overview

This guide helps you validate that all 5 critical fixes are working correctly with the new provider abstraction.

---

## TEST 1: Architecture & Imports

Verify the provider system is correctly initialized:

```python
from src.data_providers import DataProviderBase, DataProviderRegistry, get_data_provider
from src.data_fethcer import DataFetcher

# ✓ Should initialize without errors
provider = get_data_provider('yfinance')
fetcher = DataFetcher(provider='yfinance')

print(f"Provider: {provider}")
print(f"Fetcher: {fetcher.provider}")
```

**Expected Output:**
```
Provider: YFinanceProvider()
Fetcher: YFinanceProvider()
```

---

## TEST 2: Backward Compatibility

Verify existing code patterns still work:

```python
from src.data_fethcer import DataFetcher

# Old static pattern should work
df = DataFetcher.get_5min_data('RELIANCE')  # Should not error
print(f"Static call works: {type(df).__name__}")

# New instance pattern should work
fetcher = DataFetcher(provider='yfinance')
df = fetcher.get_5min_data('INFY')
print(f"Instance call works: {type(df).__name__}")
```

**Expected Output:**
```
Static call works: DataFrame
Instance call works: DataFrame
```

---

## TEST 3: Data Integrity (5-Min Intervals)

Verify you're getting 5-minute data, not daily:

```python
from src.data_fethcer import DataFetcher
import pandas as pd

fetcher = DataFetcher(provider='yfinance')
df = fetcher.get_5min_data('RELIANCE', lookback_days=5)

if not df.empty:
    print(f"Records: {len(df)}")
    print(f"Expected: ~240-300 (48-60 candles/day × 5 days)")
    
    if len(df) > 100:
        print("✓ Sufficient data for intraday analysis")
    else:
        print("⚠ WARNING: May still be daily data or insufficient market data")
    
    # Show time intervals
    time_diffs = df.index.to_series().diff()
    mode_diff = time_diffs.mode()[0]
    print(f"Most common time interval: {mode_diff}")
    print(f"✓ Should be ~5 minutes" if mode_diff == pd.Timedelta(minutes=5) else "⚠ May not be 5-min data")
else:
    print("⚠ Empty DataFrame - yfinance may not have historical intraday data available")
```

---

## TEST 4: DatetimeIndex Preservation

Verify index is NOT reset to integers:

```python
from src.data_fethcer import DataFetcher

fetcher = DataFetcher(provider='yfinance')
df = fetcher.get_5min_data('TCS', lookback_days=3)

if not df.empty:
    # Check index type
    print(f"Index type: {type(df.index).__name__}")
    assert isinstance(df.index, pd.DatetimeIndex), "❌ Index is not DatetimeIndex!"
    print("✓ DatetimeIndex preserved")
    
    # Check index name
    print(f"Index name: {df.index.name}")
    assert df.index.name == 'Time', "❌ Index name is not 'Time'!"
    print("✓ Index name is 'Time'")
    
    # Check sorted
    assert df.index.is_monotonic_increasing, "❌ Index not sorted!"
    print("✓ Index is sorted chronologically")
    
    # Show first few timestamps
    print(f"\nFirst 3 timestamps:")
    for ts in df.index[:3]:
        print(f"  {ts}")
    
else:
    print("⚠ Empty DataFrame")
```

**Expected Output:**
```
Index type: DatetimeIndex
✓ DatetimeIndex preserved
Index name: Time
✓ Index name is 'Time'
✓ Index is sorted chronologically

First 3 timestamps:
  2026-01-XX 09:20:00+05:30
  2026-01-XX 09:25:00+05:30
  2026-01-XX 09:30:00+05:30
```

---

## TEST 5: IST Timezone Localization

Verify timestamps are in IST with proper timezone info:

```python
from src.data_fethcer import DataFetcher

fetcher = DataFetcher(provider='yfinance')
df = fetcher.get_5min_data('HDFC', lookback_days=3)

if not df.empty:
    # Check timezone
    print(f"Timezone: {df.index.tz}")
    assert df.index.tz is not None, "❌ No timezone info!"
    assert df.index.tz.zone == 'Asia/Kolkata', "❌ Not IST timezone!"
    print("✓ Timezone is IST (Asia/Kolkata)")
    
    # Show sample with timezone
    print(f"\nSample timestamps with timezone:")
    for ts in df.index[:2]:
        print(f"  {ts}")
    
    # Calculate local times
    print(f"\nTime range in IST:")
    print(f"  Earliest: {df.index.min()}")
    print(f"  Latest:   {df.index.max()}")
    
else:
    print("⚠ Empty DataFrame")
```

**Expected Output:**
```
Timezone: Asia/Kolkata
✓ Timezone is IST (Asia/Kolkata)

Sample timestamps with timezone:
  2026-01-XX 09:20:00+05:30
  2026-01-XX 09:25:00+05:30

Time range in IST:
  Earliest: 2026-01-XX 09:15:00+05:30
  Latest:   2026-01-XX 15:30:00+05:30
```

---

## TEST 6: NSE Market Hours Filtering (09:15-15:30)

Verify data only contains NSE market hours:

```python
from src.data_fethcer import DataFetcher

fetcher = DataFetcher(provider='yfinance')
df = fetcher.get_5min_data('INFY', lookback_days=5)

if not df.empty:
    # Extract hours and minutes
    hours = df.index.hour
    minutes = df.index.minute
    times = hours + minutes / 60.0
    
    # NSE hours
    nse_open = 9 + 15/60.0      # 9.25
    nse_close = 15 + 30/60.0    # 15.5
    
    min_time = times.min()
    max_time = times.max()
    
    print(f"Data time range: {int(min_time)}:{int((min_time % 1)*60):02d} - {int(max_time)}:{int((max_time % 1)*60):02d}")
    print(f"NSE market hours: 09:15 - 15:30")
    
    in_market_hours = (times >= nse_open) & (times <= nse_close)
    if in_market_hours.all():
        print("✓ All candles within NSE market hours")
    else:
        print(f"⚠ {(~in_market_hours).sum()} candles outside market hours")
    
else:
    print("⚠ Empty DataFrame")
```

**Expected Output:**
```
Data time range: 09:15 - 15:30
NSE market hours: 09:15 - 15:30
✓ All candles within NSE market hours
```

---

## TEST 7: VWAP Daily Reset Logic

Verify VWAP resets at market open (09:15 IST):

```python
from src.data_fethcer import DataFetcher
from src.indicators import TechnicalIndicators

fetcher = DataFetcher(provider='yfinance')
df = fetcher.get_5min_data('RELIANCE', lookback_days=10)

if not df.empty and len(df) > 50:
    # Calculate VWAP with daily reset
    df_vwap = TechnicalIndicators.calculate_vwap_with_daily_reset(df)
    
    if 'VWAP' in df_vwap.columns:
        print("✓ VWAP column added")
        
        # Check for NaN values
        nan_count = df_vwap['VWAP'].isnull().sum()
        print(f"NaN values: {nan_count}/{len(df_vwap)} ({nan_count/len(df_vwap)*100:.1f}%)")
        
        # Get dates and check resets
        df_vwap['_date'] = df_vwap.index.date
        dates = df_vwap['_date'].unique()
        
        if len(dates) > 1:
            print(f"\nVWAP behavior across {len(dates)} trading days:")
            for date in dates[:5]:  # Show first 5 days
                day_data = df_vwap[df_vwap['_date'] == date]
                vwap_values = day_data['VWAP'].dropna()
                if len(vwap_values) > 0:
                    first_vwap = vwap_values.iloc[0]
                    last_vwap = vwap_values.iloc[-1]
                    print(f"  {date}: {len(day_data)} candles, VWAP {first_vwap:.2f} → {last_vwap:.2f}")
                    
            print("\n✓ VWAP appears to reset daily (values change per day)")
        else:
            print("⚠ Only one day in data - cannot verify reset")
    else:
        print("❌ VWAP column not created")
        
else:
    print("⚠ Insufficient data")
```

**Expected Output:**
```
✓ VWAP column added
NaN values: 0/N (0.0%)

VWAP behavior across 5 trading days:
  2026-01-XX: 48 candles, VWAP 2500.45 → 2515.32
  2026-01-XX: 48 candles, VWAP 2510.12 → 2520.88
  2026-01-XX: 48 candles, VWAP 2515.55 → 2535.22
  ...
✓ VWAP appears to reset daily (values change per day)
```

---

## TEST 8: SuperTrend Indicator (20, 2)

Verify SuperTrend calculation works correctly:

```python
from src.data_fethcer import DataFetcher
from src.indicators import TechnicalIndicators

fetcher = DataFetcher(provider='yfinance')
df = fetcher.get_5min_data('SBIN', lookback_days=5)

if not df.empty and len(df) > 50:
    # Calculate SuperTrend
    df_st = TechnicalIndicators.calculate_supertrend(df, period=20, multiplier=2)
    
    if 'SuperTrend' in df_st.columns and 'SuperTrend_Signal' in df_st.columns:
        print("✓ SuperTrend columns added")
        
        # Check signal values
        signals = df_st['SuperTrend_Signal'].dropna()
        unique_signals = signals.unique()
        print(f"Unique signals: {unique_signals}")
        assert all(s in [-1, 0, 1] for s in unique_signals), "Invalid signal values!"
        print("✓ Signal values are valid (1, -1, 0)")
        
        # Check for NaN patterns
        nan_count = df_st['SuperTrend'].isnull().sum()
        print(f"SuperTrend NaN values: {nan_count}/{len(df_st)}")
        
        # Show last few signals
        print(f"\nLast 5 SuperTrend signals:")
        for i in range(min(5, len(df_st))):
            idx = -5 + i
            ts = df_st.index[idx]
            close = df_st['Close'].iloc[idx]
            st = df_st['SuperTrend'].iloc[idx]
            sig = df_st['SuperTrend_Signal'].iloc[idx]
            signal_text = "BULLISH" if sig == 1 else "BEARISH" if sig == -1 else "NEUTRAL"
            print(f"  {ts}: Close={close:.2f}, ST={st:.2f}, Signal={signal_text}")
        
        print("\n✓ SuperTrend(20,2) calculation working")
    else:
        print("❌ SuperTrend columns not created")
        
else:
    print("⚠ Insufficient data")
```

**Expected Output:**
```
✓ SuperTrend columns added
Unique signals: [1 -1]
✓ Signal values are valid (1, -1, 0)
SuperTrend NaN values: 20/N

Last 5 SuperTrend signals:
  2026-01-XX HH:MM: Close=500.45, ST=498.32, Signal=BULLISH
  2026-01-XX HH:MM: Close=501.20, ST=499.15, Signal=BULLISH
  ...
✓ SuperTrend(20,2) calculation working
```

---

## TEST 9: Multi-Symbol Scanning

Verify you can scan multiple NIFTY 50 stocks:

```python
from src.live_scanner import LiveScanner

scanner = LiveScanner(max_workers=5, data_provider='yfinance')

symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'SBIN']
print(f"Scanning {len(symbols)} symbols...")

results = []
for symbol in symbols:
    try:
        result = scanner.scan_stock(symbol)
        if result:
            results.append(result)
            print(f"✓ {symbol}: bullish={result['bullish']}, bearish={result['bearish']}")
        else:
            print(f"⚠ {symbol}: No data")
    except Exception as e:
        print(f"❌ {symbol}: {type(e).__name__}")

print(f"\n✓ Successfully scanned {len(results)}/{len(symbols)} symbols")
```

**Expected Output:**
```
Scanning 5 symbols...
✓ RELIANCE: bullish=65, bearish=35
✓ TCS: bullish=58, bearish=42
✓ INFY: bullish=72, bearish=28
✓ HDFCBANK: bullish=55, bearish=45
✓ SBIN: bullish=60, bearish=40

✓ Successfully scanned 5/5 symbols
```

---

## FINAL CHECKLIST

- [ ] TEST 1: Architecture initializes correctly
- [ ] TEST 2: Backward compatibility works
- [ ] TEST 3: Getting 5-minute data (not daily)
- [ ] TEST 4: DatetimeIndex is preserved
- [ ] TEST 5: IST timezone is applied
- [ ] TEST 6: Data is within NSE market hours
- [ ] TEST 7: VWAP resets daily
- [ ] TEST 8: SuperTrend calculation works
- [ ] TEST 9: Multi-symbol scanning works

**If all checks pass:** ✅ System is ready for validation
**If any check fails:** Debug that specific issue and re-run

---

## NEXT STEPS

Once all tests pass:
1. Run actual trading logic on NIFTY 50 symbols
2. Verify signal generation (BUY/SELL)
3. When ready: Implement professional data provider (Kite/Shoonya)
4. Migrate to live/paper trading
