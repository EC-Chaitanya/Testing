"""
M.Stock Trading API Provider
Real-time India stock data provider for NSE stocks
Uses M.Stock trading API SDK with authenticated session

✓ Features:
- 5-minute interval data (real-time capable)
- DatetimeIndex preservation  
- IST timezone localization
- NSE market hours filtering (09:15-15:30)
- Thread-safe concurrent access
- Uses authenticated trading session from auth.py
"""

import pandas as pd
from datetime import datetime, timedelta
import pytz
from threading import Lock
from src.logger import logger
from .base import DataProviderBase
import json

# IST timezone for Indian Stock Market
IST = pytz.timezone('Asia/Kolkata')

# Thread lock for API requests
_mstock_lock = Lock()

# Global authenticated session object (set by live_scanner.py)
_authenticated_mstock_session = None


class MStockProvider(DataProviderBase):
    """
    M.Stock Trading API provider for NSE stocks
    
    Uses authenticated session from get_session()
    Safe for concurrent access with automatic locking
    Fetches 5-minute candles with proper indexing
    """
    
    def __init__(self, api_key: str = None, session=None):
        """
        Initialize M.Stock provider
        
        Args:
            api_key: M.Stock API key (optional if session provided)
            session: Authenticated MConnect session object from get_session()
        
        Raises:
            ValueError: If neither api_key nor session provided
        """
        global _authenticated_mstock_session
        
        self.provider_name = "M.Stock Trading API"
        self.api_key = api_key
        
        # Use provided session or global authenticated session
        if session:
            self.session = session
            _authenticated_mstock_session = session
            logger.info(f"Initialized {self.provider_name} with provided authenticated session")
        elif _authenticated_mstock_session:
            self.session = _authenticated_mstock_session
            logger.info(f"Initialized {self.provider_name} with global authenticated session")
        else:
            raise ValueError(
                "M.Stock provider requires authenticated session. "
                "Pass session parameter or use live_scanner with authenticated session."
            )
        
        logger.info(f"Initialized {self.provider_name}")
    
    def fetch_5min_data(self, symbol: str, lookback_days: int = 5) -> pd.DataFrame:
        """
        Fetch 5-minute historical data from M.Stock API
        
        CRITICAL: For intraday 5-min data, ONLY request recent trading days
        M.Stock 5-min candles are available for ~30-45 trading days max
        
        Args:
            symbol: Stock symbol without .NS suffix (e.g., 'RELIANCE')
            lookback_days: Trading days to fetch (NOT calendar days, max 5)
        
        Returns:
            DataFrame with DatetimeIndex (IST), OHLCV columns
            Empty DataFrame if insufficient data (< 20 candles)
        """
        try:
            # ✅ CRITICAL FIX: Cap intraday lookback to realistic M.Stock limits
            MAX_INTRADAY_DAYS = 5  # M.Stock 5-min data: recent only
            
            if lookback_days > MAX_INTRADAY_DAYS:
                logger.warning(
                    f"[{symbol}] Requested {lookback_days} days, "
                    f"capping to {MAX_INTRADAY_DAYS} (M.Stock 5-min limit)"
                )
                lookback_days = MAX_INTRADAY_DAYS
            
            # Calculate date range (multiply by 2 because not all days are trading days)
            start_date = (datetime.now() - timedelta(days=lookback_days*2)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"[{symbol}] Fetching 5-min data: {lookback_days} trading days")
            
            # Thread-safe M.Stock API access
            with _mstock_lock:
                df = self._call_mstock_api(
                    symbol=symbol,
                    interval='5m',
                    start_date=start_date,
                    end_date=end_date
                )
            
            if df is None or df.empty:
                logger.error(f"[{symbol}] No data from M.Stock API - skipping")
                return pd.DataFrame()
            
            df = df.copy()
            
            # ✅ CRITICAL FIX: Validate we have MINIMUM candles before proceeding
            MIN_CANDLES_REQUIRED = 20  # SuperTrend needs 20+ to initialize
            
            if len(df) < MIN_CANDLES_REQUIRED:
                logger.error(
                    f"[{symbol}] INSUFFICIENT DATA: Only {len(df)} candles, "
                    f"need {MIN_CANDLES_REQUIRED} minimum. Skipping."
                )
                return pd.DataFrame()
            
            # Validate OHLCV columns
            is_valid, df = self.validate_columns(df)
            if not is_valid:
                logger.error(f"[{symbol}] Column validation failed")
                return pd.DataFrame()
            
            # ✓ CRITICAL: Ensure DatetimeIndex is in IST
            if not isinstance(df.index, pd.DatetimeIndex):
                logger.error(f"[{symbol}] No DatetimeIndex found")
                return pd.DataFrame()
            
            # M.Stock returns IST natively, but normalize just in case
            if df.index.tz is None:
                df.index = df.index.tz_localize('Asia/Kolkata', ambiguous='NaT', nonexistent='NaT')
            else:
                current_tz = str(df.index.tz) if df.index.tz else None
                if current_tz != 'Asia/Kolkata':
                    df.index = df.index.tz_convert(IST)
            
            # Ensure sorted chronologically
            if not df.index.is_monotonic_increasing:
                df = df.sort_index()
            
            # ✓ CRITICAL: Filter to NSE market hours (09:15-15:30 IST)
            df = self._filter_nse_hours(df)
            
            if df.empty:
                logger.warning(f"[{symbol}] No data within NSE market hours")
                return pd.DataFrame()
            
            # ✅ Final validation: still enough after filtering?
            if len(df) < MIN_CANDLES_REQUIRED:
                logger.error(
                    f"[{symbol}] After filtering to market hours: only {len(df)} candles. "
                    f"Insufficient for indicators."
                )
                return pd.DataFrame()
            
            logger.info(
                f"[{symbol}] ✓ Fetched {len(df)} candles (5-min), "
                f"IST timezone, ready for indicators"
            )
            return df
            
        except Exception as e:
            logger.error(f"[{symbol}] M.Stock fetch failed: {type(e).__name__}: {str(e)[:100]}")
            return pd.DataFrame()
    
    def _call_mstock_api(self, symbol: str, interval: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Call M.Stock trading API using authenticated session
        
        Args:
            symbol: Stock symbol without .NS
            interval: '5m', '1h', '1d', etc.
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
        
        Returns:
            DataFrame with OHLCV data and DatetimeIndex
        """
        try:
            # M.Stock API uses lowercase column names: o, h, l, c, v, ts
            # Use get_historical for historical data with date range
            formatted_symbol = f"NSE:{symbol}"
            
            # Try get_historical method with date range for more candles
            response = None
            try:
                logger.debug(f"[{symbol}] Calling get_historical with interval={interval}, dates={start_date} to {end_date}")
                response = self.session.get_historical(
                    segment='NSE',
                    security_id=formatted_symbol,
                    interval=interval,
                    from_date=start_date,
                    to_date=end_date
                )
                logger.debug(f"[{symbol}] get_historical returned successfully")
            except (AttributeError, TypeError, Exception) as e:
                # Fallback to get_ohlc if get_historical doesn't work
                logger.debug(f"[{symbol}] get_historical failed ({type(e).__name__}: {str(e)[:50]}), trying get_ohlc")
                try:
                    response = self.session.get_ohlc(ohlc_input=[formatted_symbol])
                    logger.debug(f"[{symbol}] get_ohlc returned (note: only returns current candle)")
                except Exception as ohlc_err:
                    logger.error(f"[{symbol}] Both get_historical and get_ohlc failed: {ohlc_err}")
                    return pd.DataFrame()
            
            # Convert response to JSON dictionary
            if hasattr(response, 'json'):
                data = response.json()
            else:
                data = response
            
            logger.debug(f"[{symbol}] M.Stock API response status: {data.get('status')}")
            
            # Check response status
            if data.get('status') != 'success':
                logger.debug(f"[{symbol}] API returned non-success status: {data.get('message', 'Unknown error')}")
                return pd.DataFrame()
            
            # Extract stock data from response
            if 'data' not in data or not data['data']:
                logger.debug(f"[{symbol}] No data in API response")
                return pd.DataFrame()
            
            stock_data = data['data'].get(formatted_symbol)
            if not stock_data:
                logger.debug(f"[{symbol}] No data for {formatted_symbol} in response")
                return pd.DataFrame()
            
            logger.debug(f"[{symbol}] stock_data type: {type(stock_data)}, repr: {str(stock_data)[:100]}")
            
            # Handle different response formats
            # The M.Stock API might return:
            # - A single dict with keys: instrument_token, last_price, ohlc
            # - A list of dicts (when get_historical returns multiple candles)
            # - A list of dicts each with instrument_token, last_price, ohlc
            
            records = []
            
            if isinstance(stock_data, dict):
                # Check if this is a single quote (has instrument_token, last_price, ohlc)
                if 'instrument_token' in stock_data and 'ohlc' in stock_data:
                    logger.debug(f"[{symbol}] Single quote format detected")
                    ohlc = stock_data.get('ohlc', {})
                    records.append({
                        'Open': ohlc.get('o') or ohlc.get('open'),
                        'High': ohlc.get('h') or ohlc.get('high'),
                        'Low': ohlc.get('l') or ohlc.get('low'),
                        'Close': ohlc.get('c') or ohlc.get('close'),
                        'Volume': stock_data.get('volume') or ohlc.get('v'),
                        'Time': stock_data.get('ts') or stock_data.get('timestamp') or int(pd.Timestamp.now().timestamp()),
                    })
                # Otherwise treat as a flat dict with OHLC fields
                else:
                    logger.debug(f"[{symbol}] Flat dict format detected")
                    records.append({
                        'Open': stock_data.get('o') or stock_data.get('open'),
                        'High': stock_data.get('h') or stock_data.get('high'),
                        'Low': stock_data.get('l') or stock_data.get('low'),
                        'Close': stock_data.get('c') or stock_data.get('close'),
                        'Volume': stock_data.get('v') or stock_data.get('volume'),
                        'Time': stock_data.get('ts') or stock_data.get('timestamp'),
                    })
                    
            elif isinstance(stock_data, list):
                logger.debug(f"[{symbol}] List format with {len(stock_data)} elements detected")
                for i, record in enumerate(stock_data):
                    if isinstance(record, dict):
                        # Check if this record has nested ohlc
                        if 'ohlc' in record:
                            ohlc = record['ohlc']
                            records.append({
                                'Open': ohlc.get('o') or ohlc.get('open'),
                                'High': ohlc.get('h') or ohlc.get('high'),
                                'Low': ohlc.get('l') or ohlc.get('low'),
                                'Close': ohlc.get('c') or ohlc.get('close'),
                                'Volume': record.get('volume') or ohlc.get('v'),
                                'Time': record.get('ts') or record.get('timestamp'),
                            })
                        else:
                            # Flat structure
                            records.append({
                                'Open': record.get('o') or record.get('open'),
                                'High': record.get('h') or record.get('high'),
                                'Low': record.get('l') or record.get('low'),
                                'Close': record.get('c') or record.get('close'),
                                'Volume': record.get('v') or record.get('volume'),
                                'Time': record.get('ts') or record.get('timestamp'),
                            })
            else:
                logger.error(f"[{symbol}] Unknown stock_data type: {type(stock_data)}")
                return pd.DataFrame()
            
            if not records:
                logger.debug(f"[{symbol}] No records extracted from stock_data")
                return pd.DataFrame()
                
            df = pd.DataFrame(records)
            
            if df.empty:
                logger.debug(f"[{symbol}] DataFrame is empty after conversion")
                return pd.DataFrame()
            
            logger.debug(f"[{symbol}] DataFrame shape: {df.shape}, columns: {list(df.columns)}, first row: {df.iloc[0].to_dict() if len(df) > 0 else 'N/A'}")
            
            # Verify required columns exist
            required_cols = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"[{symbol}] Missing columns in M.Stock response: {missing_cols}. Available: {list(df.columns)}")
                return pd.DataFrame()
            
            # Convert Time to datetime and set as index
            df['Time'] = pd.to_datetime(df['Time'], errors='coerce', unit='s')  # M.Stock uses unix timestamp
            df.set_index('Time', inplace=True)
            
            # Drop rows with NaT index
            df = df[~df.index.isna()]
            
            if df.empty:
                return pd.DataFrame()
            
            # Ensure numeric columns
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Drop any remaining NaN rows in OHLCV columns
            df = df.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
            
            logger.debug(f"[{symbol}] Parsed {len(df)} records from M.Stock API")
            return df if not df.empty else pd.DataFrame()
            
        except Exception as e:
            logger.error(f"[{symbol}] M.Stock get_ohlc failed: {type(e).__name__}: {str(e)}")
            return pd.DataFrame()
    
    def fetch_daily_data(self, symbol: str, lookback_days: int = 365) -> pd.DataFrame:
        """
        Fetch daily historical data from M.Stock API
        
        Args:
            symbol: Stock symbol
            lookback_days: Historical lookback period
        
        Returns:
            DataFrame with DatetimeIndex (IST), OHLCV columns
        """
        try:
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"[{symbol}] Fetching daily data from M.Stock: {lookback_days}d")
            
            with _mstock_lock:
                df = self._call_mstock_api(
                    symbol=symbol,
                    interval='1d',
                    start_date=start_date,
                    end_date=end_date
                )
            
            if df is None or df.empty:
                logger.warning(f"[{symbol}] No daily data from M.Stock")
                return pd.DataFrame()
            
            is_valid, df = self.validate_columns(df)
            if not is_valid:
                return pd.DataFrame()
            
            if df.index.tz is None:
                df.index = df.index.tz_localize('Asia/Kolkata', ambiguous='NaT', nonexistent='NaT')
            
            if not df.index.is_monotonic_increasing:
                df = df.sort_index()
            
            logger.info(f"[{symbol}] ✓ Fetched {len(df)} daily candles from M.Stock")
            return df
            
        except Exception as e:
            logger.error(f"[{symbol}] Daily fetch failed: {type(e).__name__}: {str(e)[:100]}")
            return pd.DataFrame()
    
    @staticmethod
    def _filter_nse_hours(df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame to NSE market hours (09:15-15:30 IST)
        
        Args:
            df: DataFrame with DatetimeIndex (IST)
        
        Returns:
            Filtered DataFrame
        """
        try:
            if df.empty or not isinstance(df.index, pd.DatetimeIndex):
                return df
            
            # Extract hour and minute
            hours = df.index.hour
            minutes = df.index.minute
            times = hours + minutes / 60.0
            
            # NSE hours: 09:15 = 9.25, 15:30 = 15.5
            market_open = 9 + 15 / 60.0
            market_close = 15 + 30 / 60.0
            
            mask = (times >= market_open) & (times <= market_close)
            filtered = df[mask]
            
            if len(filtered) < len(df):
                logger.debug(f"NSE hours filter: {len(df)} -> {len(filtered)} candles")
            
            return filtered
            
        except Exception as e:
            logger.warning(f"NSE hours filtering failed: {e}")
            return df
