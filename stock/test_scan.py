#!/usr/bin/env python3
"""Quick test of the corrected M.Stock provider"""

import sys
sys.path.insert(0, '.')

from src.auth import get_session
from src.data_fethcer import DataFetcher
from src.live_scanner import LiveScanner
from src.logger import logger
from config import USER_ID, PASSWORD, DOB

# Quick test with just 3 stocks
TEST_STOCKS = ["RELIANCE", "TCS", "HDFCBANK"]

print("\n=== Testing Corrected M.Stock Provider ===\n")

try:
    # Get authenticated session
    print("Connecting to mStock...")
    session = get_session(USER_ID, PASSWORD, DOB)
    print("✓ Connected\n")
    
    # Initialize DataFetcher
    fetcher = DataFetcher(session=session)
    
    # Test fetching data for a few stocks
    for symbol in TEST_STOCKS:
        print(f"[{symbol}] Fetching 5-min data...")
        df = fetcher.fetch_5min_data(symbol, lookback_days=5)
        
        if df is None or df.empty:
            print(f"  ✗ No data")
        else:
            print(f"  ✓ Got {len(df)} candles")
            print(f"    Time range: {df.index[0]} to {df.index[-1]}")
            print(f"    Last close: {df['Close'].iloc[-1]:.2f}")
    
    print("\n=== Test Complete ===")
    
except KeyboardInterrupt:
    print("\n\nInterrupted by user")
    sys.exit(0)
except Exception as e:
    logger.error(f"Test failed: {e}", exc_info=True)
    print(f"\nError: {e}")
    sys.exit(1)
