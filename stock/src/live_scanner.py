# """
# Live Scanner Mode - Real-time NIFTY 50 Analysis
# Uses 5-minute intraday candles with dual-directional scoring
# Optimized with concurrent processing for fast scanning
# """

# import time
# import pandas as pd
# import pandas_ta as ta
# from datetime import datetime
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from typing import List, Dict, Tuple, Optional
# from src.engine import ScoringEngine
# from src.data_fethcer import DataFetcher
# from src.logger import logger
# from src.utils import OutputFormatter, SignalFilter, DataValidator
# from config import NIFTY_50_STOCKS, THRESHOLD

# class LiveScanner:
#     """
#     Real-time scanner for NIFTY 50 stocks
#     Implements dual-directional (bullish/bearish) scoring
#     Optimized with concurrent multithreading for fast parallel scanning
    
#     ✓ Uses provider-agnostic DataFetcher
#     - Currently: yfinance (stable interim backend)
#     - Future: Kite, Shoonya, m.Stock (swap provider string)
#     """
    
#     def __init__(self, threshold=THRESHOLD, max_workers=10, data_provider: str = 'mstock'):
#         self.threshold = threshold
#         self.max_workers = max_workers  # Concurrent threads for parallel scanning
#         self.logger = logger
#         self.data_fetcher = DataFetcher(provider=data_provider)  # Initialize with provider
#         # Minimal per-thread delay to avoid overwhelming APIs
#         self.per_thread_delay = 0.05  # 50ms minimal delay
    
#     def scan_stock(self, symbol: str) -> Optional[Dict]:
#         """
#         Scan a single stock and return dual scores
#         Thread-safe concurrent processing
        
#         Returns: dict with symbol, bullish_score, bearish_score, and metrics
#         """
#         try:
#             # Minimal per-thread delay to avoid API overwhelming
#             time.sleep(self.per_thread_delay)
            
#             # Fetch data using configured data provider
#             df = self.data_fetcher.fetch_5min_data(symbol)
            
#             if df.empty:
#                 self.logger.debug(f"[{symbol}] No data received")
#                 return None
            
#             if len(df) < 20:
#                 self.logger.debug(f"[{symbol}] Insufficient data: {len(df)} < 20")
#                 return None
            
#             # Make a deep copy to avoid thread-safety issues and data sharing
#             # CRITICAL: Use deepcopy to ensure complete independence from original
#             df = df.copy(deep=True)
            
#             # ✓ CRITICAL FIX: Do NOT reset index - preserve DatetimeIndex for VWAP
#             # The DatetimeIndex is required for pandas-ta and VWAP calculations
#             # df.reset_index(drop=False) would break VWAP calculations
#             # Instead, we keep the DatetimeIndex intact
            
#             # Verify we have DatetimeIndex for VWAP calculations
#             if not isinstance(df.index, pd.DatetimeIndex):
#                 logger.warning(f"[{symbol}] DataFrame missing DatetimeIndex - creating from Time column if available")
#                 if 'Time' in df.columns:
#                     df.set_index('Time', inplace=True)
#                 else:
#                     logger.error(f"[{symbol}] Cannot reconstruct DatetimeIndex - skipping")
#                     return None
            
#             # Filter to NSE market hours (09:15-15:30 IST)
#             from src.indicators import TechnicalIndicators
#             df = TechnicalIndicators.filter_nse_market_hours(df)
            
#             if df.empty:
#                 self.logger.debug(f"[{symbol}] No data within NSE market hours")
#                 return None
            
#             # Calculate technical indicators
#             # Create Series copies before passing to ta functions
#             close_series = pd.Series(df['Close'].values, index=df.index)
#             high_series = pd.Series(df['High'].values, index=df.index)
#             low_series = pd.Series(df['Low'].values, index=df.index)
#             volume_series = pd.Series(df['Volume'].values, index=df.index)
            
#             df['EMA_20'] = ta.ema(close_series, length=20)
#             df['EMA_50'] = ta.ema(close_series, length=50)
#             df['RSI'] = ta.rsi(close_series, length=14)
            
#             # ✓ CRITICAL FIX: Use VWAP with daily reset instead of rolling VWAP
#             # This ensures VWAP reflects intraday price value correctly
#             df = TechnicalIndicators.calculate_vwap_with_daily_reset(df)
            
#             # Validate data
#             is_valid, missing = DataValidator.validate_dataframe(df)
#             if not is_valid:
#                 self.logger.warning(f"{symbol}: Missing columns {missing}")
#                 return None
            
#             # Calculate dual scores
#             scores = ScoringEngine.get_dual_scores(df)
#             if not scores:
#                 return None
            
#             # CRITICAL: Convert all float values to native Python types to avoid thread-safety issues
#             # with numpy/pandas shared references
#             result = {
#                 'Symbol': str(symbol),
#                 'bullish': int(scores['bullish']),
#                 'bearish': int(scores['bearish']),
#                 'close': float(scores['close']) if scores['close'] is not None else 0,
#                 'rsi': float(scores['rsi']) if scores['rsi'] is not None else 0,
#                 'ema20': float(scores['ema20']) if scores['ema20'] is not None else 0,
#                 'ema50': float(scores['ema50']) if scores['ema50'] is not None else 0,
#                 'vwap': float(scores['vwap']) if scores['vwap'] is not None else 0,
#                 'records': int(len(df)),
#                 'timestamp': str(datetime.now().isoformat())
#             }
            
#             self.logger.info(
#                 f"✓ {symbol}: B={scores['bullish']}, Be={scores['bearish']}, "
#                 f"RSI={scores['rsi']:.1f}, LTP={scores['close']:.2f}, Data={len(df)}"
#             )
            
#             return result
            
#         except Exception as e:
#             self.logger.error(f"Error scanning {symbol}: {e}", exc_info=True)
#             return None
    
#     def run_single_scan(self, symbols: Optional[List[str]] = None) -> Tuple[List, List, List]:
#         """
#         Run a single scan cycle using concurrent multithreading
        
#         BUG FIX #1: SEQUENTIAL BOTTLENECK
#         - Old: Scanned 50 stocks one-by-one = 60+ seconds
#         - New: Concurrent scanning with ThreadPoolExecutor = 6-8 seconds (10x faster)
#         - max_workers=10 processes 10 stocks in parallel
        
#         Args:
#             symbols: List of symbols to scan (default: NIFTY_50_STOCKS)
        
#         Returns: (bullish_results, bearish_results, all_results)
#         """
#         if symbols is None:
#             symbols = NIFTY_50_STOCKS
        
#         scan_start_time = datetime.now()
        
#         print(f"\n{'='*80}")
#         print(f"Live Scan Started: {scan_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
#         print(f"Scanning {len(symbols)} stocks with {self.max_workers} concurrent workers...")
#         print(f"{'='*80}\n")
        
#         results = []
#         success = 0
#         failed = 0
        
#         # CONCURRENT SCANNING: Process multiple stocks in parallel
#         with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
#             # Submit all scan tasks
#             future_to_symbol = {executor.submit(self.scan_stock, symbol): symbol 
#                                for symbol in symbols}
            
#             # Process results as they complete
#             completed = 0
#             for future in as_completed(future_to_symbol):
#                 symbol = future_to_symbol[future]
#                 completed += 1
                
#                 try:
#                     result = future.result()
#                     if result:
#                         results.append(result)
#                         print(f"[{completed}/{len(symbols)}] {symbol:<12} ", end='')
#                         print(f"B:{result['bullish']:>2} Be:{result['bearish']:>2} "
#                               f"RSI:{result['rsi']:>5.1f} Data:{result['records']}")
#                         success += 1
#                     else:
#                         print(f"[{completed}/{len(symbols)}] {symbol:<12} FAILED")
#                         failed += 1
#                 except Exception as e:
#                     print(f"[{completed}/{len(symbols)}] {symbol:<12} ERROR: {str(e)[:30]}")
#                     failed += 1
        
#         # Calculate scan duration
#         scan_duration = (datetime.now() - scan_start_time).total_seconds()
#         avg_per_stock = scan_duration / len(symbols) if symbols else 0
        
#         print(f"\n{'-'*80}")
#         print(f"Scan Complete: {success} successful, {failed} failed in {scan_duration:.1f}s ({avg_per_stock:.2f}s per stock)")
#         print(f"Performance: ~{success * 10 / scan_duration:.1f}x faster than sequential (estimate)")
#         print(f"{'-'*80}\n")
        
#         # Filter and display results
#         bullish, bearish = SignalFilter.filter_by_threshold(results, self.threshold)
#         bullish = SignalFilter.rank_by_score(bullish, 'bullish')
#         bearish = SignalFilter.rank_by_score(bearish, 'bearish')
        
#         OutputFormatter.display_dual_results(bullish, bearish, self.threshold)
#         OutputFormatter.display_scan_summary(results, "Live Scan")
        
#         return bullish, bearish, results
    
#     def run_continuous_scan(self, interval_minutes=5, max_iterations=None):
#         """
#         Run continuous scans at specified interval
#         interval_minutes: Minutes between scans (typically 5 for intraday)
#         max_iterations: Maximum number of scans (None = infinite)
#         """
#         iteration = 0
        
#         try:
#             while True:
#                 iteration += 1
#                 if max_iterations and iteration > max_iterations:
#                     print(f"\nCompleted {iteration-1} scans. Exiting.")
#                     break
                
#                 print(f"\n{'='*80}")
#                 print(f"Scan #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
#                 print(f"{'='*80}\n")
                
#                 self.run_single_scan()
                
#                 print(f"\nNext scan in {interval_minutes} minutes...")
#                 print(f"Press Ctrl+C to stop continuous scanning")
                
#                 # Wait for next interval
#                 time.sleep(interval_minutes * 60)
                
#         except KeyboardInterrupt:
#             print(f"\n\nContinuous scanning stopped after {iteration} iterations.")
#             self.logger.info(f"Continuous scanning stopped. Total iterations: {iteration}")

# 2nd

# import pandas as pd
# import time
# from datetime import datetime
# from src.engine import ScoringEngine
# from src.logger import logger
# from src.market_status import can_scan_now, time_to_market_open
# from src.risk_manager import RiskManager
# import config
# from src.notifier import send_telegram_msg

# class LiveScanner:
#     def __init__(self, session, threshold=65):
#         self.session = session 
#         self.threshold = threshold
#         self.engine = ScoringEngine()
#         # Initialize DataFetcher with authenticated session
#         from src.data_fethcer import DataFetcher
#         self.data_fetcher = DataFetcher(provider='mstock', session=session)
#         # Initialize risk manager
#         self.risk_manager = RiskManager(account_size=100000, risk_per_trade=0.02)

#     def fetch_mstock_candles(self, symbol):
#         """
#         Fetches 5-minute historical data using DataFetcher and calculates indicators.
        
#         Uses the proper DataFetcher which fetches 20+ candles via get_historical,
#         NOT just the current candle via get_ohlc.
#         """
#         try:
#             import pandas_ta as ta
#             import warnings
            
#             # Use DataFetcher to get 5-minute historical data (20+ candles)
#             df = self.data_fetcher.fetch_5min_data(symbol, lookback_days=5)
            
#             if df is None or df.empty:
#                 logger.debug(f"[{symbol}] DataFetcher returned no data")
#                 return None
            
#             # Verify minimum candles
#             MIN_CANDLES = 20
#             if len(df) < MIN_CANDLES:
#                 logger.error(f"[{symbol}] Insufficient candles: {len(df)}/{MIN_CANDLES}. Skipping.")
#                 return None
            
#             # Verify required columns exist
#             required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
#             missing_cols = [col for col in required_cols if col not in df.columns]
#             if missing_cols:
#                 logger.error(f"[{symbol}] Missing columns: {missing_cols}. Available: {list(df.columns)}")
#                 return None
            
#             # Ensure numeric columns
#             for col in required_cols:
#                 df[col] = pd.to_numeric(df[col], errors='coerce')
            
#             # Check if we have valid OHLCV data (not all NaN)
#             if df[required_cols].isna().all().all():
#                 logger.warning(f"[{symbol}] All OHLCV data is NaN - API returned no valid data")
#                 return None
            
#             # Calculate technical indicators
#             with warnings.catch_warnings():
#                 warnings.filterwarnings('ignore')
                
#                 # VWAP with daily reset
#                 df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
                
#                 # RSI
#                 df['RSI'] = ta.rsi(df['Close'], length=14)
                
#                 # SuperTrend (20, 2)
#                 st = ta.supertrend(df['High'], df['Low'], df['Close'], length=20, multiplier=2)
#                 if st is not None and len(st) > 0:
#                     df['SuperTrend_Signal'] = st['SUPERTd_20_2']
#                 else:
#                     logger.warning(f"[{symbol}] SuperTrend calculation returned None")
                
#             logger.debug(f"[{symbol}] Successfully fetched and processed {len(df)} record(s)")
#             return df
            
#         except Exception as e:
#             logger.error(f"Error fetching/calculating data for {symbol}: {e}")
#             import traceback
#             logger.debug(f"[{symbol}] Full traceback: {traceback.format_exc()}")
#             return None
#     def run_single_scan(self):
#         """
#         Scan all stocks with proper gates/validation
        
#         GATES (in order):
#         1. Is NSE open right now? (Market hours + trading day)
#         2. Can we enter new trade? (Risk checks)
#         3. For each stock: Do we have sufficient data? (20+ candles)
#         4. Is data fresh? (Not stale from previous day)
#         5. Do indicators work? (No NaN)
#         6. Generate signal
#         """
        
#         # ✅ GATE 1: Market status
#         can_scan, reason = can_scan_now()
#         if not can_scan:
#             print(f"\n❌ {reason}")
#             if "Outside market hours" in reason:
#                 secs = time_to_market_open()
#                 mins = secs // 60
#                 print(f"   Next scan in ~{mins} minutes")
#             return None
        
#         print(f"\n--- Scan Started at {datetime.now().strftime('%H:%M:%S')} ---")
        
#         results = []
#         success = 0
#         failed = 0
#         skipped = 0
        
#         for symbol, token in config.STOCK_TOKENS.items():
#             # ✅ GATE 2: Risk check (can we take more positions?)
#             can_enter, risk_reason = self.risk_manager.can_enter_trade()
#             if not can_enter:
#                 logger.debug(f"[{symbol}] Skipped: {risk_reason}")
#                 skipped += 1
#                 continue
            
#             # ✅ GATE 3: Fetch data with proper window
#             df = self.fetch_mstock_candles(symbol)
            
#             if df is None or df.empty:
#                 logger.debug(f"[{symbol}] No data received")
#                 failed += 1
#                 continue
            
#             # ✅ GATE 4: Minimum candle check (critical!)
#             MIN_CANDLES = 20
#             if len(df) < MIN_CANDLES:
#                 logger.error(
#                     f"[{symbol}] Insufficient candles: {len(df)}/{MIN_CANDLES}. Skipping."
#                 )
#                 failed += 1
#                 continue
            
#             # ✅ GATE 5: Data freshness check
#             last_candle_time = df.index[-1]
#             age_minutes = (datetime.now(df.index.tz) - last_candle_time).total_seconds() / 60
            
#             if age_minutes > 5:  # Data older than 5 minutes
#                 logger.warning(
#                     f"[{symbol}] Data is stale: {age_minutes:.1f} minutes old. Skipping."
#                 )
#                 skipped += 1
#                 continue
            
#             # ✅ GATE 6: Calculate score
#             try:
#                 score_data = self.engine.calculate_full_score(df)
#             except Exception as e:
#                 logger.error(f"[{symbol}] Indicator calculation failed: {e}")
#                 failed += 1
#                 continue
            
#             score = score_data.get('total_score', 0)
#             signal = score_data.get('signal', False)
            
#             # Display result
#             if score >= self.threshold and signal:
#                 current_price = df['Close'].iloc[-1]
                
#                 # Calculate trade parameters
#                 stop_loss = current_price * 0.98  # -2% stop
#                 profit_target = current_price * 1.01  # +1% target
#                 shares = self.risk_manager.calculate_position_size(current_price, stop_loss)
                
#                 if shares > 0:
#                     self.risk_manager.record_entry(symbol, current_price, shares, stop_loss, profit_target)
#                     print(f"[{symbol}] 🔥 BUY | Score: {score} | Price: {current_price:.2f} | "
#                           f"Shares: {shares} | SL: {stop_loss:.2f} | PT: {profit_target:.2f}")
#                     results.append({'symbol': symbol, 'score': score, 'price': current_price})
#                     success += 1
#                 else:
#                     print(f"[{symbol}] ⚠️ Signal OK but insufficient capital for position sizing")
#                     skipped += 1
#             else:
#                 logger.debug(f"[{symbol}] Score: {score} - No signal")
#                 success += 1  # Counted as success (just no signal)
        
#         # Summary
#         print(f"\n--- Scan Complete ---")
#         print(f"Success: {success}, Failed: {failed}, Skipped: {skipped}")
#         print(f"Signals: {len(results)}, Open positions: {len(self.risk_manager.open_trades)}")
        
#         return results


#     def run_continuous_scan(self, interval_minutes=5):
#         """
#         Runs the scanner repeatedly at set interval
#         Automatically skips when market is closed
#         """
#         print(f"\n🚀 Continuous Scanning Started (Interval: {interval_minutes} min)")
#         print("Press Ctrl+C to stop the scanner.")
        
#         try:
#             while True:
#                 # Check if can scan right now
#                 can_scan, reason = can_scan_now()
                
#                 if not can_scan:
#                     # Market is closed, calculate wait time
#                     secs_to_open = time_to_market_open()
#                     mins_to_open = (secs_to_open // 60) + 1
                    
#                     print(f"\n⏰ Market closed: {reason}")
#                     print(f"   Next scan: ~{mins_to_open} minutes")
                    
#                     # Sleep in 1-minute chunks so user can Ctrl+C quickly
#                     for _ in range(mins_to_open):
#                         time.sleep(60)
#                     continue
                
#                 # Market is open, run scan
#                 self.run_single_scan()
                
#                 # Summary
#                 self.risk_manager.summary()
                
#                 print(f"✅ Waiting {interval_minutes} minutes for next scan...")
#                 print(f"Press Ctrl+C to stop\n")
                
#                 # Sleep for interval
#                 time.sleep(interval_minutes * 60)
                
#         except KeyboardInterrupt:
#             print("\n\n🛑 Continuous scanning stopped by user.")
#             self.risk_manager.summary()


"""
Live Scanner Mode - Real-time NIFTY 50 Analysis
Features: 
- Hybrid Data (yfinance + mStock)
- Telegram Full Scan Reports
- Instant Strategy Alerts
"""

import time
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

from src.engine import ScoringEngine
from src.data_fethcer import DataFetcher
from src.logger import logger
from src.utils import OutputFormatter, DataValidator
from src.notifier import send_telegram_msg

# Use STOCK_TOKENS from config to get symbols
from config import STOCK_TOKENS, THRESHOLD 

class LiveScanner:
    def __init__(self, session=None, threshold=THRESHOLD, max_workers=10):
        self.threshold = threshold
        self.max_workers = max_workers
        self.session = session
        # Initialize DataFetcher
        self.data_fetcher = DataFetcher(provider='mstock', session=session)
        self.engine = ScoringEngine()
        self.formatter = OutputFormatter()
        # Extract stock symbols from config dictionary
        self.symbols_to_scan = list(STOCK_TOKENS.keys())

    def scan_stock(self, symbol: str) -> Optional[Dict]:
        """Analyzes a single stock and returns results."""
        try:
            # FIX: Changed from get_intraday_data to fetch_5min_data to match your DataFetcher
            df = self.data_fetcher.fetch_5min_data(symbol, lookback_days=5)
            
            if df is None or df.empty:
                return None

            if not DataValidator.is_valid(df, min_candles=20):
                return None

            results = self.engine.calculate_total_score(df, symbol)
            return results

        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return None

    def run_single_scan(self):
        """Performs the scan and sends results to Telegram."""
        start_time = time.time()
        now_str = datetime.now().strftime('%H:%M:%S')
        print(f"\n--- Scan Started at {now_str} ---")
        
        all_results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_stock = {executor.submit(self.scan_stock, s): s for s in self.symbols_to_scan}
            
            for future in as_completed(future_to_stock):
                res = future.result()
                if res:
                    all_results.append(res)

        # Sort by best score
        all_results.sort(key=lambda x: x['total_score'], reverse=True)

        if all_results:
            # 1. Individual Telegram Alerts
            top_signals = [r for r in all_results if r['total_score'] >= self.threshold]
            for signal in top_signals:
                send_telegram_msg(
                    stock_name=signal['symbol'],
                    price=signal['close'],
                    stoploss=round(signal.get('indicators', {}).get('supertrend_val', 0), 2)
                )

            # 2. Summary Telegram Report
            summary = f"📊 *SCAN REPORT ({now_str})*\n"
            summary += "--------------------------\n"
            for r in all_results[:8]: 
                status = "🚀" if r['total_score'] >= self.threshold else "📈"
                summary += f"{status} *{r['symbol']}*: Score {r['total_score']} | ₹{r['close']}\n"
            
            summary += f"\nTotal Stocks Scanned: {len(all_results)}"
            self.send_report_to_phone(summary)

        # FIX: Ensure we use the correct method name for displaying table
        # If display_table fails, we use print as fallback
        try:
            self.formatter.display_results(all_results)
        except AttributeError:
            print(all_results[:10]) 
        
        duration = time.time() - start_time
        print(f"--- Scan Complete ({duration:.2f}s) ---")

    def send_report_to_phone(self, text: str):
        from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try:
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
        except Exception as e:
            logger.error(f"Telegram Report Error: {e}")

    def start_continuous_scanning(self, interval_minutes: int = 5):
        print(f"\n🚀 Scanner Active. Updates every {interval_minutes} minutes.")
        try:
            while True:
                self.run_single_scan()
                print(f"Waiting for {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n🛑 Stopped.")
        except Exception as e:
            print(f"⚠️ Continuous scanner stopped: {e}")