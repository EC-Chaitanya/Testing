"""
Live Scanner Mode - Real-time NIFTY 50 Analysis
Uses 5-minute intraday candles with dual-directional scoring
"""

import time
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from src.engine import ScoringEngine
from src.data_fethcer import DataFetcher
from src.logger import logger
from src.utils import OutputFormatter, SignalFilter, DataValidator
from config import NIFTY_50_STOCKS, THRESHOLD

class LiveScanner:
    """
    Real-time scanner for NIFTY 50 stocks
    Implements dual-directional (bullish/bearish) scoring
    """
    
    def __init__(self, threshold=THRESHOLD):
        self.threshold = threshold
        self.rate_limit_delay = 1.0  # 1-second delay between requests
        self.logger = logger
    
    def scan_stock(self, symbol):
        """
        Scan a single stock and return dual scores
        Returns: dict with symbol, bullish_score, bearish_score, and metrics
        """
        try:
            # Fetch data with rate limiting
            time.sleep(self.rate_limit_delay)
            df = DataFetcher.get_5min_data(symbol)
            
            if df.empty:
                self.logger.warning(f"[{symbol}] No data received from DataFetcher")
                return None
            
            if len(df) < 20:
                self.logger.warning(f"[{symbol}] Insufficient data: {len(df)} rows (need ≥20)")
                return None
            
            # Calculate technical indicators
            df['EMA_20'] = ta.ema(df['Close'], length=20)
            df['EMA_50'] = ta.ema(df['Close'], length=50)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
            
            # Validate data
            is_valid, missing = DataValidator.validate_dataframe(df)
            if not is_valid:
                self.logger.warning(f"{symbol}: Missing columns {missing}")
                return None
            
            # Calculate dual scores
            scores = ScoringEngine.get_dual_scores(df)
            if not scores:
                return None
            
            result = {
                'Symbol': symbol,
                'bullish': scores['bullish'],
                'bearish': scores['bearish'],
                'close': scores['close'],
                'rsi': scores['rsi'],
                'ema20': scores['ema20'],
                'ema50': scores['ema50'],
                'vwap': scores['vwap'],
                'records': len(df),
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(
                f"✓ {symbol}: B={scores['bullish']}, Be={scores['bearish']}, "
                f"RSI={scores['rsi']:.1f}, LTP={scores['close']:.2f}, Data={len(df)}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error scanning {symbol}: {e}", exc_info=True)
            return None
    
    def run_single_scan(self, symbols=None):
        """
        Run a single scan cycle for all or specified symbols
        Returns: (bullish_results, bearish_results)
        """
        if symbols is None:
            symbols = NIFTY_50_STOCKS
        
        print(f"\n{'='*80}")
        print(f"Live Scan Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Scanning {len(symbols)} stocks with {self.rate_limit_delay}s rate limiting...")
        print(f"{'='*80}\n")
        
        results = []
        success = 0
        failed = 0
        
        for idx, symbol in enumerate(symbols, 1):
            print(f"[{idx}/{len(symbols)}] {symbol:<12}", end=' ', flush=True)
            
            result = self.scan_stock(symbol)
            if result:
                results.append(result)
                print(f"✓ B:{result['bullish']:>2} Be:{result['bearish']:>2} RSI:{result['rsi']:>5.1f} Data:{result['records']}")
                success += 1
            else:
                print(f"✗ Failed/No Data")
                failed += 1
        
        print(f"\n{'-'*80}")
        print(f"Scan Summary: {success} successful, {failed} failed")
        print(f"{'-'*80}\n")
        
        # Filter and display results
        bullish, bearish = SignalFilter.filter_by_threshold(results, self.threshold)
        bullish = SignalFilter.rank_by_score(bullish, 'bullish')
        bearish = SignalFilter.rank_by_score(bearish, 'bearish')
        
        OutputFormatter.display_dual_results(bullish, bearish, self.threshold)
        OutputFormatter.display_scan_summary(results, "Live Scan")
        
        return bullish, bearish, results
    
    def run_continuous_scan(self, interval_minutes=5, max_iterations=None):
        """
        Run continuous scans at specified interval
        interval_minutes: Minutes between scans (typically 5 for intraday)
        max_iterations: Maximum number of scans (None = infinite)
        """
        iteration = 0
        
        try:
            while True:
                iteration += 1
                if max_iterations and iteration > max_iterations:
                    print(f"\nCompleted {iteration-1} scans. Exiting.")
                    break
                
                print(f"\n{'='*80}")
                print(f"Scan #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*80}\n")
                
                self.run_single_scan()
                
                print(f"\nNext scan in {interval_minutes} minutes...")
                print(f"Press Ctrl+C to stop continuous scanning")
                
                # Wait for next interval
                time.sleep(interval_minutes * 60)
                
        except KeyboardInterrupt:
            print(f"\n\nContinuous scanning stopped after {iteration} iterations.")
            self.logger.info(f"Continuous scanning stopped. Total iterations: {iteration}")
