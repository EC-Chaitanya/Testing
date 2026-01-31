# """
# M.Stock Trading API Provider
# Uses get_historical_chart with Instrument Tokens for multi-candle historical data.
# This is CRITICAL: get_ohlc() returns only 1 candle (real-time snapshot).
# """

# import pandas as pd
# from datetime import datetime, timedelta
# import pytz
# from threading import Lock
# from src.logger import logger
# from .base import DataProviderBase

# # IST timezone
# IST = pytz.timezone('Asia/Kolkata')

# # Thread lock for API requests
# _mstock_lock = Lock()

# # Global authenticated session
# _authenticated_mstock_session = None


# class MStockProvider(DataProviderBase):
#     """
#     M.Stock provider using get_historical_chart with Instrument Tokens.
#     """
    
#     def __init__(self, api_key: str = None, session=None):
#         global _authenticated_mstock_session
#         self.provider_name = "M.Stock Trading API"
#         self.api_key = api_key
        
#         if session:
#             self.session = session
#             _authenticated_mstock_session = session
#         elif _authenticated_mstock_session:
#             self.session = _authenticated_mstock_session
#         else:
#             raise ValueError("M.Stock provider requires authenticated session")
        
#         logger.info(f"Initialized {self.provider_name}")

#     def fetch_5min_data(self, symbol: str, lookback_days: int = 5) -> pd.DataFrame:
#         """
#         Fetch 5-minute intraday candles using get_intraday_chart.
#         CRITICAL: get_intraday_chart returns recent trading session data (20+ candles typically).
#         """
#         try:
#             logger.info(f"[{symbol}] Fetching 5-min data...")
            
#             # Call get_intraday_chart (doesn't need date range, returns recent session)
#             with _mstock_lock:
#                 df = self._call_get_historical_chart(
#                     symbol=symbol,
#                     token="",  # Not used with get_intraday_chart
#                     interval='5',  # 5-minute candles
#                     from_date="",  # Not used
#                     to_date=""  # Not used
#                 )
            
#             if df is None or df.empty:
#                 logger.error(f"[{symbol}] No data from get_intraday_chart")
#                 return pd.DataFrame()
            
#             # Validate minimum candles needed for indicators
#             MIN_CANDLES = 20
#             if len(df) < MIN_CANDLES:
#                 logger.error(f"[{symbol}] INSUFFICIENT: {len(df)} candles (need {MIN_CANDLES})")
#                 return pd.DataFrame()
            
#             # Timezone handling
#             if df.index.tz is None:
#                 df.index = df.index.tz_localize(IST, ambiguous='NaT', nonexistent='NaT')
#             else:
#                 df.index = df.index.tz_convert(IST)
            
#             # Sort and filter to NSE hours
#             df = df.sort_index()
#             df = self._filter_nse_hours(df)
            
#             if len(df) < MIN_CANDLES:
#                 logger.error(f"[{symbol}] After NSE hours filter: {len(df)} candles (need {MIN_CANDLES})")
#                 return pd.DataFrame()
            
#             logger.info(f"[{symbol}] ✓ Got {len(df)} candles (5-min)")
#             return df
            
#         except Exception as e:
#             logger.error(f"[{symbol}] fetch_5min_data failed: {e}")
#             return pd.DataFrame()

#     def _call_get_historical_chart(self, symbol: str, token: str, interval: str, 
#                                    from_date: str, to_date: str) -> pd.DataFrame:
#         """
#         Call M.Stock SDK's get_intraday_chart (fallback to get_ohlc if needed).
        
#         Args:
#             symbol: Stock symbol (for logging)
#             token: Numerical Instrument Token from STOCK_TOKENS (not used with get_intraday_chart)
#             interval: "5" for 5-min (mapped to "5" in SDK)
#             from_date: DD-MM-YYYY format (not used with get_intraday_chart)
#             to_date: DD-MM-YYYY format (not used with get_intraday_chart)
        
#         Returns:
#             DataFrame with OHLCV data and DatetimeIndex (IST)
#         """
#         try:
#             logger.debug(f"[{symbol}] Calling get_intraday_chart(symbol={symbol}, interval={interval})")
            
#             # Try get_intraday_chart first (doesn't require token, returns recent 5-min data)
#             try:
#                 response = self.session.get_intraday_chart(
#                     _segment_id="1",    # NSE Equity
#                     _symbol=symbol,     # Stock symbol (e.g., "RELIANCE")
#                     _interval=interval  # "5" for 5-minute
#                 )
                
#                 data = response.json() if hasattr(response, 'json') else response
                
#                 logger.debug(f"[{symbol}] get_intraday_chart response: status={data.get('status')}, keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
                
#                 if data and data.get('status') == 'success':
#                     # Extract candles from response
#                     candles = data.get('data', [])
#                     logger.debug(f"[{symbol}] 'data' field type={type(candles)}, value={str(candles)[:200]}")
                    
#                     if candles:
#                         records = self._parse_candles(symbol, candles)
#                         if records:
#                             df = pd.DataFrame(records)
#                             df['Time'] = pd.to_datetime(df['Time'], unit='s', errors='coerce')
#                             df.set_index('Time', inplace=True)
#                             df = df[~df.index.isna()]
                            
#                             for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
#                                 df[col] = pd.to_numeric(df[col], errors='coerce')
#                             df = df.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
                            
#                             logger.debug(f"[{symbol}] get_intraday_chart returned {len(df)} candles")
#                             return df
#             except Exception as e:
#                 logger.debug(f"[{symbol}] get_intraday_chart failed: {type(e).__name__}: {str(e)[:80]}")
            
#             # Fallback to get_ohlc for real-time quote
#             logger.debug(f"[{symbol}] Trying get_ohlc fallback...")
#             try:
#                 response = self.session.get_ohlc(ohlc_input=[f"NSE:{symbol}"])
#                 data = response.json() if hasattr(response, 'json') else response
                
#                 logger.debug(f"[{symbol}] get_ohlc response: status={data.get('status')}, keys={list(data.keys())}")
                
#                 if data and data.get('status') == 'success':
#                     stock_data = data.get('data', {}).get(f"NSE:{symbol}")
#                     logger.debug(f"[{symbol}] stock_data: {str(stock_data)[:200]}")
                    
#                     if stock_data:
#                         record = self._parse_single_quote(symbol, stock_data)
#                         if record:
#                             df = pd.DataFrame([record])
#                             df['Time'] = pd.to_datetime(df['Time'], unit='s', errors='coerce')
#                             df.set_index('Time', inplace=True)
                            
#                             for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
#                                 df[col] = pd.to_numeric(df[col], errors='coerce')
#                             df = df.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
                            
#                             logger.debug(f"[{symbol}] get_ohlc returned {len(df)} candle(s)")
#                             return df
#             except Exception as e:
#                 logger.debug(f"[{symbol}] get_ohlc fallback failed: {type(e).__name__}")
            
#             return pd.DataFrame()
            
#         except Exception as e:
#             logger.error(f"[{symbol}] All API methods failed: {type(e).__name__}: {str(e)[:100]}")
#             return pd.DataFrame()
    
#     @staticmethod
#     def _parse_candles(symbol: str, candles: list) -> list:
#         """Parse list of candles from API response."""
#         records = []
#         try:
#             logger.debug(f"[{symbol}] _parse_candles: candles type={type(candles)}, len={len(candles) if isinstance(candles, (list, dict)) else 'N/A'}")
            
#             if isinstance(candles, dict):
#                 # If API returns a dict instead of list, try to extract list from it
#                 logger.debug(f"[{symbol}] Candles is dict with keys: {list(candles.keys())}")
#                 # Try to find a list in the dict
#                 for key, val in candles.items():
#                     if isinstance(val, list):
#                         logger.debug(f"[{symbol}] Found list under key '{key}': {len(val)} items")
#                         candles = val
#                         break
            
#             if isinstance(candles, list):
#                 for i, candle in enumerate(candles):
#                     if isinstance(candle, dict):
#                         logger.debug(f"[{symbol}] Candle {i}: {candle}")
#                         records.append({
#                             'Time': candle.get('ts') or candle.get('timestamp'),
#                             'Open': float(candle.get('o') or candle.get('open', 0)),
#                             'High': float(candle.get('h') or candle.get('high', 0)),
#                             'Low': float(candle.get('l') or candle.get('low', 0)),
#                             'Close': float(candle.get('c') or candle.get('close', 0)),
#                             'Volume': int(candle.get('v') or candle.get('volume', 0))
#                         })
#         except Exception as e:
#             logger.debug(f"[{symbol}] Candle parsing error: {e}")
        
#         logger.debug(f"[{symbol}] Parsed {len(records)} candle records")
#         return records
    
#     @staticmethod
#     def _parse_single_quote(symbol: str, stock_data: dict) -> dict:
#         """Parse single quote from get_ohlc response."""
#         try:
#             ohlc = stock_data.get('ohlc', stock_data)
#             return {
#                 'Time': stock_data.get('ts') or int(pd.Timestamp.now().timestamp()),
#                 'Open': float(ohlc.get('open') or ohlc.get('o', 0)),
#                 'High': float(ohlc.get('high') or ohlc.get('h', 0)),
#                 'Low': float(ohlc.get('low') or ohlc.get('l', 0)),
#                 'Close': float(ohlc.get('close') or ohlc.get('c', 0)),
#                 'Volume': int(stock_data.get('volume') or stock_data.get('v', 0))
#             }
#         except Exception as e:
#             logger.debug(f"[{symbol}] Quote parsing error: {e}")
#             return {}

#     def fetch_daily_data(self, symbol: str, lookback_days: int = 365) -> pd.DataFrame:
#         """
#         Fetch daily candles using get_intraday_chart or get_ohlc.
#         """
#         try:
#             logger.info(f"[{symbol}] Fetching daily data...")
            
#             # For daily data, use a 1-day interval with get_intraday_chart
#             with _mstock_lock:
#                 df = self._call_get_historical_chart(
#                     symbol=symbol,
#                     token="",  # Not needed for get_intraday_chart
#                     interval="1d",
#                     from_date="",
#                     to_date=""
#                 )
            
#             if df is None or df.empty:
#                 logger.warning(f"[{symbol}] No daily data")
#                 return pd.DataFrame()
            
#             # Timezone handling
#             if df.index.tz is None:
#                 df.index = df.index.tz_localize(IST, ambiguous='NaT', nonexistent='NaT')
#             else:
#                 df.index = df.index.tz_convert(IST)
            
#             df = df.sort_index()
            
#             logger.info(f"[{symbol}] ✓ Got {len(df)} daily candles")
#             return df
            
#         except Exception as e:
#             logger.error(f"[{symbol}] Daily fetch failed: {e}")
#             return pd.DataFrame()

#     @staticmethod
#     def _filter_nse_hours(df: pd.DataFrame) -> pd.DataFrame:
#         """
#         Filter to NSE market hours (09:15-15:30 IST).
#         """
#         if df.empty:
#             return df
        
#         try:
#             times = df.index.hour + df.index.minute / 60.0
#             # 09:15 = 9.25, 15:30 = 15.5
#             filtered = df[(times >= 9.25) & (times <= 15.5)]
            
#             if len(filtered) < len(df):
#                 logger.debug(f"NSE hours filter: {len(df)} -> {len(filtered)} candles")
            
#             return filtered
#         except Exception as e:
#             logger.warning(f"NSE hours filter failed: {e}")
#             return df


"""
M.Stock Trading API Provider - CORRECTED VERSION
Uses get_historical with proper date ranges for multi-candle historical data.

CRITICAL FIX: 
- get_ohlc() returns only 1 candle (real-time snapshot) ❌
- get_historical() returns 20+ candles for technical indicators ✅
"""
  
# 2nd code from gemini , claude and github copilot combined:

# import pandas as pd
# from datetime import datetime, timedelta
# import pytz
# from threading import Lock
# from src.logger import logger
# from .base import DataProviderBase

# # IST timezone
# IST = pytz.timezone('Asia/Kolkata')

# # Thread lock for API requests
# _mstock_lock = Lock()

# # Global authenticated session
# _authenticated_mstock_session = None


# class MStockProvider(DataProviderBase):
#     """
#     M.Stock provider using get_historical for multi-candle data.
    
#     IMPORTANT: This uses get_historical which requires:
#     - Segment ID (e.g., "NSE" for NSE Equity)
#     - Symbol name (e.g., "RELIANCE")
#     - Date range
#     - Interval (e.g., "5" for 5-minute, "D" for daily)
#     """
    
#     def __init__(self, api_key: str = None, session=None):
#         global _authenticated_mstock_session
#         self.provider_name = "M.Stock Trading API"
#         self.api_key = api_key
        
#         if session:
#             self.session = session
#             _authenticated_mstock_session = session
#         elif _authenticated_mstock_session:
#             self.session = _authenticated_mstock_session
#         else:
#             raise ValueError("M.Stock provider requires authenticated session")
        
#         logger.info(f"Initialized {self.provider_name}")
        
#         # Load instrument tokens if available
#         self.instrument_tokens = self._load_instrument_tokens()

#     def _load_instrument_tokens(self):
#         """Load instrument tokens from config"""
#         try:
#             import config
#             if hasattr(config, 'STOCK_TOKENS'):
#                 logger.info(f"Loaded {len(config.STOCK_TOKENS)} instrument tokens from config")
#                 return config.STOCK_TOKENS
#         except Exception as e:
#             logger.warning(f"Could not load instrument tokens: {e}")
#         return {}

#     def fetch_5min_data(self, symbol: str, lookback_days: int = 5) -> pd.DataFrame:
#         """
#         Fetch 5-minute intraday candles using get_historical.
        
#         CRITICAL: This method fetches multiple candles (20+) needed for indicators.
        
#         Args:
#             symbol: Stock symbol (e.g., "RELIANCE")
#             lookback_days: Number of days to look back (default 5)
            
#         Returns:
#             DataFrame with DatetimeIndex (IST) and OHLCV columns
#         """
#         try:
#             logger.info(f"[{symbol}] Fetching 5-min data for {lookback_days} days...")
            
#             # Calculate date range
#             end_date = datetime.now(IST)
#             # Add buffer for weekends/holidays to ensure we get enough trading days
#             start_date = end_date - timedelta(days=lookback_days + 19)
            
#             # Try multiple methods in order of preference
#             df = None
            
#             # Method 1: Try get_historical (most reliable for multi-candle data)
#             df = self._try_get_historical(symbol, start_date, end_date, interval='5')
            
#             # Method 2: Fallback to get_historical_chart if available
#             if df is None or df.empty:
#                 df = self._try_get_historical_chart(symbol, start_date, end_date, interval='5')
            
#             # Method 3: Last resort - try get_intraday_chart (may only return current session)
#             if df is None or df.empty:
#                 df = self._try_get_intraday_chart(symbol, interval='5')
            
#             if df is None or df.empty:
#                 logger.error(f"[{symbol}] No data from any M.Stock API method")
#                 return pd.DataFrame()
            
#             # Validate minimum candles needed for indicators
#             MIN_CANDLES = 20
#             if len(df) < MIN_CANDLES:
#                 logger.error(f"[{symbol}] INSUFFICIENT: {len(df)} candles (need {MIN_CANDLES}+)")
#                 logger.error(f"[{symbol}] This will cause indicator calculation to FAIL")
#                 logger.error(f"[{symbol}] Solution: Increase lookback_days or check if market was open")
#                 return pd.DataFrame()
            
#             # Post-processing
#             df = self._postprocess_dataframe(symbol, df)
            
#             if df is None or df.empty:
#                 logger.error(f"[{symbol}] Data failed post-processing validation")
#                 return pd.DataFrame()
            
#             logger.info(f"[{symbol}] ✅ Successfully fetched {len(df)} candles (5-min)")
#             return df
            
#         except Exception as e:
#             logger.error(f"[{symbol}] fetch_5min_data failed: {e}", exc_info=True)
#             return pd.DataFrame()

#     def _try_get_historical(self, symbol: str, start_date: datetime, 
#                            end_date: datetime, interval: str = '5') -> pd.DataFrame:
#         """
#         Method 1: Try M.Stock get_historical API
        
#         This is the CORRECT method for fetching multi-candle historical data.
        
#         Args:
#             symbol: Stock symbol
#             start_date: Start datetime
#             end_date: End datetime
#             interval: Interval ('5' for 5-min, 'D' for daily)
#         """
#         try:
#             logger.debug(f"[{symbol}] Trying get_historical...")
            
#             with _mstock_lock:
#                 # Format dates as required by M.Stock API
#                 from_date_str = start_date.strftime('%Y-%m-%d')
#                 to_date_str = end_date.strftime('%Y-%m-%d')
                
#                 # Map interval to M.Stock format
#                 interval_map = {
#                     '1': '1',    # 1-minute
#                     '5': '5',    # 5-minute
#                     '15': '15',  # 15-minute
#                     '30': '30',  # 30-minute
#                     '60': '60',  # 1-hour
#                     'D': 'D'     # Daily
#                 }
#                 mstock_interval = interval_map.get(interval, '5')
                
#                 # Try different API signatures (SDK versions vary)
#                 response = None
                
#                 # Signature 1: segment, security_id (newer SDK)
#                 try:
#                     response = self.session.get_historical(
#                         segment='E',  # E for NSE Equity
#                         security_id=symbol,
#                         interval=mstock_interval,
#                         from_date=from_date_str,
#                         to_date=to_date_str
#                     )
#                 except TypeError:
#                     # Signature 2: exchange, symbol (older SDK)
#                     try:
#                         response = self.session.get_historical(
#                             exchange='NSE',
#                             symbol=symbol,
#                             interval=mstock_interval,
#                             from_date=from_date_str,
#                             to_date=to_date_str
#                         )
#                     except:
#                         pass
                
#                 if response is None:
#                     logger.debug(f"[{symbol}] get_historical returned None")
#                     return pd.DataFrame()
                
#                 # Parse response
#                 data = response.json() if hasattr(response, 'json') else response
                
#                 if not data or data.get('status') != 'success':
#                     logger.debug(f"[{symbol}] get_historical status: {data.get('status') if data else 'None'}")
#                     return pd.DataFrame()
                
#                 # Extract candles from response
#                 candles_data = data.get('data', {})
                
#                 # Handle different response structures
#                 candles = None
#                 if isinstance(candles_data, dict):
#                     # Structure 1: {symbol: [candles]}
#                     if symbol in candles_data:
#                         candles = candles_data[symbol]
#                     # Structure 2: {token: [candles]} - try first value that's a list
#                     else:
#                         for value in candles_data.values():
#                             if isinstance(value, list):
#                                 candles = value
#                                 break
#                 elif isinstance(candles_data, list):
#                     # Structure 3: Direct list
#                     candles = candles_data
                
#                 if not candles:
#                     logger.debug(f"[{symbol}] No candles in get_historical response")
#                     return pd.DataFrame()
                
#                 # Parse candles into DataFrame
#                 df = self._parse_candles_to_dataframe(symbol, candles)
#                 logger.debug(f"[{symbol}] get_historical returned {len(df)} candles")
#                 return df
                
#         except Exception as e:
#             logger.debug(f"[{symbol}] get_historical failed: {type(e).__name__}: {str(e)[:100]}")
#             return pd.DataFrame()

#     def _try_get_historical_chart(self, symbol: str, start_date: datetime,
#                                   end_date: datetime, interval: str = '5') -> pd.DataFrame:
#         """
#         Method 2: Try get_historical_chart if available
        
#         Some M.Stock SDK versions have this method with instrument tokens.
#         """
#         try:
#             logger.debug(f"[{symbol}] Trying get_historical_chart...")
            
#             # Get instrument token for this symbol
#             token = self.instrument_tokens.get(symbol)
#             if not token:
#                 logger.debug(f"[{symbol}] No instrument token found, skipping get_historical_chart")
#                 return pd.DataFrame()
            
#             with _mstock_lock:
#                 from_date_str = start_date.strftime('%d-%m-%Y')
#                 to_date_str = end_date.strftime('%d-%m-%Y')
                
#                 response = self.session.get_historical_chart(
#                     token=token,
#                     interval=interval,
#                     from_date=from_date_str,
#                     to_date=to_date_str
#                 )
                
#                 data = response.json() if hasattr(response, 'json') else response
                
#                 if not data or data.get('status') != 'success':
#                     return pd.DataFrame()
                
#                 candles = data.get('data', [])
#                 df = self._parse_candles_to_dataframe(symbol, candles)
#                 logger.debug(f"[{symbol}] get_historical_chart returned {len(df)} candles")
#                 return df
                
#         except AttributeError:
#             logger.debug(f"[{symbol}] get_historical_chart not available in this SDK version")
#             return pd.DataFrame()
#         except Exception as e:
#             logger.debug(f"[{symbol}] get_historical_chart failed: {type(e).__name__}")
#             return pd.DataFrame()

#     def _try_get_intraday_chart(self, symbol: str, interval: str = '5') -> pd.DataFrame:
#         """
#         Method 3: Try get_intraday_chart (current session only - may be insufficient)
        
#         WARNING: This typically returns only the current trading session,
#         which may not be enough candles for indicators.
#         """
#         try:
#             logger.debug(f"[{symbol}] Trying get_intraday_chart...")
            
#             with _mstock_lock:
#                 response = self.session.get_intraday_chart(
#                     _segment_id="1",    # NSE Equity
#                     _symbol=symbol,
#                     _interval=interval
#                 )
                
#                 data = response.json() if hasattr(response, 'json') else response
                
#                 if not data or data.get('status') != 'success':
#                     return pd.DataFrame()
                
#                 candles = data.get('data', [])
#                 df = self._parse_candles_to_dataframe(symbol, candles)
                
#                 logger.debug(f"[{symbol}] get_intraday_chart returned {len(df)} candles")
#                 logger.warning(f"[{symbol}] Using intraday_chart - may have insufficient history")
#                 return df
                
#         except AttributeError:
#             logger.debug(f"[{symbol}] get_intraday_chart not available")
#             return pd.DataFrame()
#         except Exception as e:
#             logger.debug(f"[{symbol}] get_intraday_chart failed: {type(e).__name__}")
#             return pd.DataFrame()

#     def _parse_candles_to_dataframe(self, symbol: str, candles) -> pd.DataFrame:
#         """
#         Parse candles from M.Stock API into standardized DataFrame.
        
#         Handles multiple candle format variations:
#         - Lowercase fields: {o, h, l, c, v, ts}
#         - Full name fields: {open, high, low, close, volume, timestamp}
#         - Nested OHLC: {ohlc: {o, h, l, c}, v, ts}
#         """
#         if not candles:
#             return pd.DataFrame()
        
#         records = []
        
#         try:
#             # Handle dict of candles (extract the list)
#             if isinstance(candles, dict):
#                 for key, value in candles.items():
#                     if isinstance(value, list):
#                         candles = value
#                         break
            
#             # Parse each candle
#             if isinstance(candles, list):
#                 for candle in candles:
#                     if not isinstance(candle, dict):
#                         continue
                    
#                     # Extract OHLC data (handle nested structure)
#                     if 'ohlc' in candle:
#                         ohlc = candle['ohlc']
#                     else:
#                         ohlc = candle
                    
#                     # Build record with all field name variations
#                     record = {
#                         'Time': candle.get('ts') or candle.get('timestamp'),
#                         'Open': float(ohlc.get('o') or ohlc.get('open', 0)),
#                         'High': float(ohlc.get('h') or ohlc.get('high', 0)),
#                         'Low': float(ohlc.get('l') or ohlc.get('low', 0)),
#                         'Close': float(ohlc.get('c') or ohlc.get('close', 0)),
#                         'Volume': int(candle.get('v') or candle.get('volume', 0))
#                     }
                    
#                     # Validate record
#                     if all(record[k] for k in ['Time', 'Open', 'High', 'Low', 'Close']):
#                         records.append(record)
            
#             if not records:
#                 logger.debug(f"[{symbol}] No valid records parsed from {len(candles) if isinstance(candles, list) else 0} candles")
#                 return pd.DataFrame()
            
#             # Create DataFrame
#             df = pd.DataFrame(records)
            
#             # Convert timestamp to datetime
#             df['Time'] = pd.to_datetime(df['Time'], unit='s', errors='coerce')
#             df = df.dropna(subset=['Time'])
#             df.set_index('Time', inplace=True)
            
#             # Ensure numeric types
#             for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
#                 df[col] = pd.to_numeric(df[col], errors='coerce')
            
#             # Drop invalid rows
#             df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
            
#             return df
            
#         except Exception as e:
#             logger.error(f"[{symbol}] Candle parsing error: {e}", exc_info=True)
#             return pd.DataFrame()

#     def _postprocess_dataframe(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
#         """
#         Post-process DataFrame: timezone, sorting, market hours filtering.
#         """
#         try:
#             if df.empty:
#                 return df
            
#             # Timezone handling
#             if df.index.tz is None:
#                 df.index = df.index.tz_localize(IST, ambiguous='NaT', nonexistent='NaT')
#             else:
#                 df.index = df.index.tz_convert(IST)
            
#             # Remove NaT entries
#             df = df[~df.index.isna()]
            
#             # Sort by time
#             df = df.sort_index()
            
#             # Filter to NSE market hours (09:15 - 15:30 IST)
#             df = self._filter_nse_hours(df)
            
#             # Validate OHLC relationships
#             df = self._validate_ohlc(symbol, df)
            
#             return df
            
#         except Exception as e:
#             logger.error(f"[{symbol}] Post-processing failed: {e}")
#             return pd.DataFrame()

#     @staticmethod
#     def _filter_nse_hours(df: pd.DataFrame) -> pd.DataFrame:
#         """Filter to NSE market hours (09:15-15:30 IST)."""
#         if df.empty:
#             return df
        
#         try:
#             times = df.index.hour + df.index.minute / 60.0
#             # 09:15 = 9.25, 15:30 = 15.5
#             filtered = df[(times >= 9.25) & (times <= 15.5)]
            
#             if len(filtered) < len(df):
#                 logger.debug(f"NSE hours filter: {len(df)} -> {len(filtered)} candles")
            
#             return filtered
#         except Exception as e:
#             logger.warning(f"NSE hours filter failed: {e}")
#             return df

#     @staticmethod
#     def _validate_ohlc(symbol: str, df: pd.DataFrame) -> pd.DataFrame:
#         """Validate OHLC price relationships and remove invalid candles."""
#         if df.empty:
#             return df
        
#         try:
#             # Check logical relationships
#             valid = (
#                 (df['Low'] <= df['Open']) &
#                 (df['Low'] <= df['Close']) &
#                 (df['Low'] <= df['High']) &
#                 (df['High'] >= df['Open']) &
#                 (df['High'] >= df['Close']) &
#                 (df['Open'] > 0) &
#                 (df['High'] > 0) &
#                 (df['Low'] > 0) &
#                 (df['Close'] > 0)
#             )
            
#             invalid_count = (~valid).sum()
#             if invalid_count > 0:
#                 logger.warning(f"[{symbol}] Removing {invalid_count} invalid candles (OHLC logic violated)")
#                 df = df[valid]
            
#             return df
            
#         except Exception as e:
#             logger.warning(f"[{symbol}] OHLC validation failed: {e}")
#             return df

#     def fetch_daily_data(self, symbol: str, lookback_days: int = 365) -> pd.DataFrame:
#         """
#         Fetch daily candles using get_historical.
        
#         Args:
#             symbol: Stock symbol
#             lookback_days: Number of days to look back
            
#         Returns:
#             DataFrame with daily OHLCV data
#         """
#         try:
#             logger.info(f"[{symbol}] Fetching daily data for {lookback_days} days...")
            
#             end_date = datetime.now(IST)
#             start_date = end_date - timedelta(days=lookback_days + 60)  # Buffer for weekends
            
#             # Try get_historical with daily interval
#             df = self._try_get_historical(symbol, start_date, end_date, interval='D')
            
#             if df is None or df.empty:
#                 logger.warning(f"[{symbol}] No daily data available")
#                 return pd.DataFrame()
            
#             # Post-process
#             df = self._postprocess_dataframe(symbol, df)
            
#             logger.info(f"[{symbol}] ✅ Got {len(df)} daily candles")
#             return df
            
#         except Exception as e:
#             logger.error(f"[{symbol}] Daily fetch failed: {e}")
#             return pd.DataFrame()

"""
M.Stock Trading API Provider - Hybrid Implementation
Uses yfinance for historical warm-up (20+ candles) 
Uses mStock get_ohlc for real-time, zero-delay execution.
"""

# import pandas as pd
# import yfinance as yf
# from datetime import datetime, timedelta
# import pytz
# from threading import Lock
# from src.logger import logger
# from .base import DataProviderBase

# # IST timezone for Indian Stock Market
# IST = pytz.timezone('Asia/Kolkata')

# # Thread lock for API requests
# _mstock_lock = Lock()

# class MStockProvider(DataProviderBase):
#     """
#     Hybrid Data Provider:
#     - yfinance: Provides the historical background needed for SuperTrend/VWAP.
#     - mStock: Provides the latest price to ensure no delay in trade entry.
#     """
    
#     def __init__(self, api_key: str = None, session=None):
#         self.provider_name = "Hybrid (yfinance + mStock)"
#         self.session = session
#         if not self.session:
#             raise ValueError("M.Stock provider requires an authenticated session for live data.")
#         logger.info(f"Initialized {self.provider_name}")

#     def fetch_5min_data(self, symbol: str, lookback_days: int = 5) -> pd.DataFrame:
#         """
#         The 'Stitch' Method: Combines delayed history with real-time broker data.
#         """
#         try:
#             # 1. Get History from yfinance (Standard symbols use .NS suffix)
#             yf_symbol = f"{symbol}.NS"
#             logger.info(f"[{symbol}] Fetching history from yfinance...")
            
#             # Fetching 5 days of 5-minute data
#             hist_df = yf.download(yf_symbol, period="5d", interval="5m", progress=False)
            
#             if hist_df.empty:
#                 logger.error(f"[{symbol}] yfinance returned no data. Check internet connection.")
#                 return pd.DataFrame()

#             # Clean columns (Fixes potential MultiIndex issues in newer yfinance versions)
#             if isinstance(hist_df.columns, pd.MultiIndex):
#                 hist_df.columns = hist_df.columns.get_level_values(0)
            
#             hist_df = hist_df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

#             # 2. Get Real-time Snapshot from mStock (Zero Delay)
#             logger.info(f"[{symbol}] Fetching live quote from mStock...")
#             formatted_symbol = f"NSE:{symbol}"
            
#             with _mstock_lock:
#                 quote_res = self.session.get_ohlc(ohlc_input=[formatted_symbol])
            
#             data = quote_res.json() if hasattr(quote_res, 'json') else quote_res
#             live_entry = data.get('data', {}).get(formatted_symbol)

#             if live_entry and live_entry.get('status') != 'error':
#                 ohlc = live_entry.get('ohlc', live_entry)
#                 # Use current IST time for the live candle
#                 current_time = pd.Timestamp.now(tz=IST).floor('5min')
                
#                 live_df = pd.DataFrame([{
#                     'Open': float(ohlc.get('open', 0)),
#                     'High': float(ohlc.get('high', 0)),
#                     'Low': float(ohlc.get('low', 0)),
#                     'Close': float(live_entry.get('last_price', 0)),
#                     'Volume': int(live_entry.get('volume', 0))
#                 }], index=[current_time])
                
#                 # 3. Stitch: Append live candle to the end of history
#                 # We remove the last yfinance candle if it overlaps with the current time
#                 hist_df = hist_df[hist_df.index < current_time]
#                 final_df = pd.concat([hist_df, live_df])
#             else:
#                 logger.warning(f"[{symbol}] mStock live fetch failed, using yfinance only.")
#                 final_df = hist_df

#             # 4. Final Processing & Filtering
#             final_df = final_df.drop_duplicates().sort_index()
            
#             # Ensure index is IST
#             if final_df.index.tz is None:
#                 final_df.index = final_df.index.tz_localize(IST)
#             else:
#                 final_df.index = final_df.index.tz_convert(IST)

#             # Filter for NSE Market Hours
#             final_df = self._filter_nse_hours(final_df)

#             # Minimum data check (Strategy needs 20 for indicators)
#             if len(final_df) < 20:
#                 logger.error(f"[{symbol}] Insufficient data for indicators ({len(final_df)} candles).")
#                 return pd.DataFrame()

#             return final_df

#         except Exception as e:
#             logger.error(f"[{symbol}] Hybrid fetch failed: {str(e)}")
#             return pd.DataFrame()

#     @staticmethod
#     def _filter_nse_hours(df: pd.DataFrame) -> pd.DataFrame:
#         """
#         Filters data to standard NSE market hours (09:15 - 15:30 IST).
#         """
#         if df.empty:
#             return df
#         times = df.index.hour + df.index.minute / 60.0
#         # 9.25 = 09:15; 15.5 = 15:30
#         return df[(times >= 9.25) & (times <= 15.5)]

#     def fetch_daily_data(self, symbol: str, lookback_days: int = 365) -> pd.DataFrame:
#         """
#         Fetches daily data using yfinance.
#         """
#         yf_symbol = f"{symbol}.NS"
#         df = yf.download(yf_symbol, period="1y", interval="1d", progress=False)
#         if isinstance(df.columns, pd.MultiIndex):
#             df.columns = df.columns.get_level_values(0)
#         return df
       
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
from src.logger import logger
from .base import DataProviderBase

IST = pytz.timezone('Asia/Kolkata')

class MStockProvider(DataProviderBase):
    def __init__(self, api_key=None, session=None):
        self.provider_name = "Hybrid (yfinance + mStock)"
        self.session = session
        # logger.info(f"Initialized {self.provider_name}")

    def fetch_5min_data(self, symbol: str, lookback_days: int = 5) -> pd.DataFrame:
        """
        Fetches 5-minute intraday data. 
        Accepts lookback_days to match DataFetcher requirements.
        """
        try:
            # 1. Fetch History from yfinance (Use .NS suffix)
            yf_ticker = f"{symbol}.NS"
            # Limit period to 5 days to avoid the 60-day Yahoo limit
            hist_df = yf.download(yf_ticker, period="5d", interval="5m", progress=False)
            
            if hist_df.empty:
                logger.error(f"[{symbol}] yfinance failed. Check if {yf_ticker} is correct.")
                return pd.DataFrame()

            # Clean MultiIndex columns and duplicates
            if isinstance(hist_df.columns, pd.MultiIndex):
                hist_df.columns = hist_df.columns.get_level_values(0)
            
            # Remove duplicate timestamps to prevent 'Reindexing' error
            hist_df = hist_df[~hist_df.index.duplicated(keep='last')]

            # 2. Get Live Quote from mStock
            formatted_symbol = f"NSE:{symbol}"
            quote_res = self.session.get_ohlc(ohlc_input=[formatted_symbol])
            quote_data = quote_res.json() if hasattr(quote_res, 'json') else quote_res
            
            live_entry = quote_data.get('data', {}).get(formatted_symbol)
            if live_entry:
                ohlc = live_entry.get('ohlc', live_entry)
                current_time = pd.Timestamp.now(tz=IST).floor('5min')
                
                live_df = pd.DataFrame([{
                    'Open': float(ohlc.get('open', 0)),
                    'High': float(ohlc.get('high', 0)),
                    'Low': float(ohlc.get('low', 0)),
                    'Close': float(live_entry.get('last_price', 0)),
                    'Volume': int(live_entry.get('volume', 0))
                }], index=[current_time])
                
                # Combine and ensure unique index
                final_df = pd.concat([hist_df, live_df])
                final_df = final_df[~final_df.index.duplicated(keep='last')]
                return final_df.sort_index()
            
            return hist_df

        except Exception as e:
            logger.error(f"[{symbol}] 5min fetch failed: {e}")
            return pd.DataFrame()

    def fetch_daily_data(self, symbol: str, lookback_days: int = 365) -> pd.DataFrame:
        """Required by DataProviderBase contract"""
        # try:
        #     yf_symbol = f"{symbol}.NS"
        #     df = yf.download(yf_symbol, period="1y", interval="1d", progress=False)
        #     if isinstance(df.columns, pd.MultiIndex):
        #         df.columns = df.columns.get_level_values(0)
        #     return df
        # except Exception as e:
        #     logger.error(f"[{symbol}] Daily fetch failed: {e}")
        #     return pd.DataFrame()
        return yf.download(f"{symbol}.NS", period="1y", interval="1d", progress=False)