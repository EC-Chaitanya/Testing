"""
DATA PROVIDER ARCHITECTURE DOCUMENTATION

This document explains the new provider-agnostic data fetching system
that allows easy swapping between different data sources.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The system is split into 3 layers:

1. **DATA PROVIDER (src/data_providers/)**
   - Abstract interface: DataProviderBase
   - Concrete implementations: YFinanceProvider, KiteProvider (future), etc.
   - Handles actual data fetching, validation, timezone conversion
   - Returns guaranteed format: DatetimeIndex, IST timezone, OHLCV columns

2. **DATA FETCHER (src/data_fethcer.py)**
   - Provider-agnostic factory/router
   - Can use any registered provider
   - Maintains backward compatibility with static method calls
   - Main entry point for trading logic

3. **TRADING LOGIC (src/engine.py, src/live_scanner.py, etc.)**
   - Completely broker-agnostic
   - Works with any provider's returned data
   - No coupling to data source


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT STATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Available Providers:
  - YFinanceProvider (stable, interim backend)

✓ Critical Fixes Preserved:
  - 5-minute intervals (interval='5m')
  - DatetimeIndex preservation (not reset_index)
  - IST timezone conversion
  - NSE market hours filtering (09:15-15:30)
  - VWAP daily reset logic
  - Thread-safe concurrent access

✓ Backward Compatible:
  - Existing code using DataFetcher.get_5min_data() works unchanged
  - New code can use instance-based calls with provider selection


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USAGE EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### OPTION 1: Backward Compatible (existing code, unchanged)
───────────────────────────────────────────────────────────────────────────────

from src.data_fethcer import DataFetcher

# Uses default yfinance provider automatically
df = DataFetcher.get_5min_data('RELIANCE', lookback_days=90)


### OPTION 2: Instance-Based (new code, with provider selection)
───────────────────────────────────────────────────────────────────────────────

from src.data_fethcer import DataFetcher

# Current: yfinance (stable interim backend)
fetcher = DataFetcher(provider='yfinance')
df = fetcher.get_5min_data('RELIANCE')

# Future: Switch to professional broker API (one line change!)
fetcher = DataFetcher(provider='kite')        # Zerodha Kite
# OR
fetcher = DataFetcher(provider='shoonya')     # IIFL Shoonya
# OR
fetcher = DataFetcher(provider='mstock')      # m.Stock (when available)


### OPTION 3: Scanner with Custom Provider
───────────────────────────────────────────────────────────────────────────────

from src.live_scanner import LiveScanner

# Current: yfinance
scanner = LiveScanner(max_workers=10, data_provider='yfinance')

# Future: Zerodha Kite
scanner = LiveScanner(max_workers=10, data_provider='kite')


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADDING A NEW DATA PROVIDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example: Adding Zerodha Kite API

### STEP 1: Create src/data_providers/kite_provider.py
───────────────────────────────────────────────────────────────────────────────

import pandas as pd
from .base import DataProviderBase
from src.logger import logger
import pytz

IST = pytz.timezone('Asia/Kolkata')

class KiteProvider(DataProviderBase):
    \"\"\"
    Zerodha Kite data provider
    Official, reliable, institutional-grade data
    \"\"\"
    
    def __init__(self, api_key, access_token):
        \"\"\"
        Initialize with Kite credentials
        
        Args:
            api_key: Your Kite API key
            access_token: Your Kite access token
        \"\"\"
        from kiteconnect import KiteConnect
        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)
        logger.info("Initialized Kite provider")
    
    def fetch_5min_data(self, symbol, lookback_days=90):
        \"\"\"
        Fetch 5-minute data using Kite API
        
        Returns:
            DataFrame with DatetimeIndex (IST), OHLCV columns
        \"\"\"
        try:
            # Kite API call for intraday data
            # Details: https://kite.trade/docs/connect/v1/market-quotes/
            
            # Example response processing:
            kite_symbol = f"NSE:{symbol}"
            
            # Get historical data (interval='5minute')
            # kite.historical_data(instrument_token, from_date, to_date, interval)
            
            # Convert response to DataFrame
            # Ensure DatetimeIndex, IST timezone, NSE hours filtering
            
            # Return validated DataFrame
            logger.info(f"[{symbol}] Fetched via Kite API")
            return df
            
        except Exception as e:
            logger.error(f"[{symbol}] Kite fetch failed: {e}")
            return pd.DataFrame()
    
    def fetch_daily_data(self, symbol, lookback_days=365):
        # Similar implementation for daily data
        pass


### STEP 2: Register in src/data_providers/__init__.py
───────────────────────────────────────────────────────────────────────────────

from .kite_provider import KiteProvider

__all__ = [
    ...
    'KiteProvider',
]


### STEP 3: Register in src/data_providers/factory.py
───────────────────────────────────────────────────────────────────────────────

from .kite_provider import KiteProvider

_providers = {
    'yfinance': YFinanceProvider,
    'kite': KiteProvider,      # ← ADD THIS
    # 'shoonya': ShooonyaProvider,
}


### STEP 4: Use immediately
───────────────────────────────────────────────────────────────────────────────

fetcher = DataFetcher(provider='kite')
df = fetcher.get_5min_data('RELIANCE')

# Trading logic works unchanged!


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATA PROVIDER CONTRACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All providers MUST return data with these guarantees:

✓ DataFrame structure:
  - Columns: Open, High, Low, Close, Volume (at minimum)
  - All numeric types (float64)
  - No NaN values in OHLCV columns

✓ Index:
  - Type: pandas.DatetimeIndex (NOT integer index)
  - Timezone: IST (Asia/Kolkata)
  - Name: 'Time'
  - Sorted: Chronologically ascending

✓ Content:
  - Only NSE market hours: 09:15-15:30 IST
  - 5-minute candles (for fetch_5min_data)
  - Daily candles (for fetch_daily_data)

✓ Error handling:
  - Return empty DataFrame on failure (not raise exception)
  - Log all errors with [SYMBOL] prefix


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MIGRATION TIMELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PHASE 1 (CURRENT) - VALIDATION:
  ✓ Architecture in place
  ✓ YFinance provider working
  ✓ All critical fixes preserved
  ✓ GOAL: Validate SuperTrend, VWAP, multi-symbol scanning

PHASE 2 - PROFESSIONAL DATA:
  [ ] Choose: Kite / Shoonya / Angel One
  [ ] Implement provider for chosen platform
  [ ] Swap provider string (1 line!)
  [ ] Validate with live/paper trading

PHASE 3 - M.STOCK (IF OFFICIAL API):
  [ ] Obtain m.Stock API documentation
  [ ] Implement MStockProvider
  [ ] Swap provider (1 line!)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TESTING & VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use test_critical_fixes.py to validate:

1. ✓ 5-minute interval fetching (not daily)
2. ✓ DatetimeIndex preservation
3. ✓ VWAP daily reset logic
4. ✓ IST timezone localization
5. ✓ NSE market hours filtering

Run:
  python test_critical_fixes.py


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILES STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

src/data_providers/
├── __init__.py              ← Package exports
├── base.py                  ← Abstract DataProviderBase class
├── factory.py               ← DataProviderRegistry & get_data_provider()
└── yfinance_provider.py     ← YFinanceProvider (current)
    # Future:
    # ├── kite_provider.py
    # ├── shoonya_provider.py
    # ├── angel_provider.py
    # └── mstock_provider.py

src/data_fethcer.py         ← DataFetcher (routes to providers)
src/live_scanner.py         ← Uses DataFetcher with provider selection
src/engine.py               ← Trading logic (broker-agnostic)
src/indicators.py           ← Technical indicators (broker-agnostic)
"""
