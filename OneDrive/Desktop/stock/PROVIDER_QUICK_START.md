# Data Provider Abstraction - Quick Start

## What Changed?

You now have a **provider-agnostic architecture** that lets you swap data sources (yfinance → Kite → Shoonya → m.Stock) with **one line of code**.

## What's Preserved?

✅ All 5 critical fixes are built into the architecture:
- 5-minute intervals (not daily)
- DatetimeIndex preservation
- IST timezone conversion
- VWAP daily reset logic
- NSE market hours filtering (09:15-15:30)

## Usage (No Changes Required!)

Existing code works unchanged:

```python
from src.data_fethcer import DataFetcher

# This uses yfinance automatically (default)
df = DataFetcher.get_5min_data('RELIANCE')
```

## To Use Different Provider

```python
# Current: yfinance (stable interim backend)
fetcher = DataFetcher(provider='yfinance')
df = fetcher.get_5min_data('RELIANCE')

# Future: Just change the provider string!
fetcher = DataFetcher(provider='kite')        # Zerodha Kite
fetcher = DataFetcher(provider='shoonya')     # IIFL Shoonya
fetcher = DataFetcher(provider='mstock')      # m.Stock (when available)
```

## For Scanner

```python
from src.live_scanner import LiveScanner

# Current: yfinance
scanner = LiveScanner(max_workers=10, data_provider='yfinance')

# Future: Switch provider easily
scanner = LiveScanner(max_workers=10, data_provider='kite')
```

## Next Steps

1. **Validate Current Setup** (yfinance)
   - Run: `python test_critical_fixes.py`
   - Verify: SuperTrend, VWAP, multi-symbol scanning

2. **When Moving to Professional Data** (Kite/Shoonya/m.Stock)
   - Follow: `DATA_PROVIDER_ARCHITECTURE.md` → "Adding a New Data Provider"
   - One provider implementation per broker
   - Trading logic works unchanged

## Architecture Files

```
src/data_providers/
├── base.py                    ← Abstract interface
├── factory.py                 ← Provider registry
├── yfinance_provider.py       ← Current (yfinance)
└── [future providers]

src/data_fethcer.py           ← Routes to providers
DATA_PROVIDER_ARCHITECTURE.md  ← Full documentation
```

---

**Status:** ✅ Ready for validation with yfinance
**Next:** Testing SuperTrend, VWAP, NIFTY 50 scanning
