"""
YFinance Data Provider
Stable interim backend for development and validation
Fetches 5-minute NSE data with proper timezone and index handling

✓ Features:
- 5-minute interval data (interval='5m')
- DatetimeIndex preservation (not reset_index)
- IST timezone localization
- NSE market hours filtering (09:15-15:30)
- Thread-safe concurrent access with locks
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from threading import Lock
from src.logger import logger
from .base import DataProviderBase

# IST timezone for Indian Stock Market
IST = pytz.timezone('Asia/Kolkata')

# Thread lock for yfinance (not thread-safe by default)
_yfinance_lock = Lock()


class YFinanceProvider(DataProviderBase):
    """
    YFinance-based data provider for NSE stocks
    
    Safe for concurrent access with automatic locking
    Fetches 5-minute candles with proper indexing
    """
    
    def __init__(self):
        """Initialize YFinance provider"""
        self.provider_name = "YFinance"
        logger.info(f"Initialized {self.provider_name} provider")
    
    def fetch_5min_data(self, symbol: str, lookback_days: int = 90) -> pd.DataFrame:
        """
        Fetch 5-minute historical data from YFinance
        
        ✓ CRITICAL FIXES APPLIED:
        1. interval='5m' to fetch 5-minute candles (not daily)
        2. DatetimeIndex preserved (not reset_index)
        3. IST timezone conversion applied
        4. Thread-safe with locks for concurrent access
        5. ⚠️ YFinance 5-min data limited to 60 days (API constraint)
        
        Args:
            symbol: Stock symbol without .NS suffix (e.g., 'RELIANCE')
            lookback_days: Historical lookback period
        
        Returns:
            DataFrame with DatetimeIndex (IST), OHLCV columns
        """
        try:
            yf_symbol = f"{symbol}.NS"
            
            # ⚠️ CRITICAL: YFinance API LIMITATION
            # 5-minute data is only available for the last 60 days
            # Requesting beyond 60 days returns: "5m data not available for startTime=... 
            # The requested range must be within the last 60 days."
            # Cap the TOTAL lookback (including buffer) to 60 days maximum
            MAX_5MIN_DAYS = 60
            
            # Calculate buffer for indicator warmup
            buffer_days = int(lookback_days * self.BUFFER_RATIO) + self.BUFFER_DAYS
            total_needed = lookback_days + buffer_days
            
            # If total exceeds 60, reduce the data lookback proportionally
            if total_needed > MAX_5MIN_DAYS:
                # Scale down the lookback to fit within the 60-day window
                effective_lookback = max(30, MAX_5MIN_DAYS - buffer_days)
                adjusted_lookback = effective_lookback + buffer_days
            else:
                effective_lookback = lookback_days
                adjusted_lookback = total_needed
            
            # Final cap: never exceed 60 days
            adjusted_lookback = min(adjusted_lookback, MAX_5MIN_DAYS)
            
            logger.info(f"[{symbol}] Fetching 5-min data: {effective_lookback}d (adjusted: {adjusted_lookback}d, YFinance 60-day limit)")
            
            # Date range
            start_date = (datetime.now() - timedelta(days=adjusted_lookback)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # ✓ CRITICAL: yfinance is NOT thread-safe
            # Multiple concurrent downloads without locking can return wrong data
            # Use lock to serialize access
            with _yfinance_lock:
                df = yf.download(
                    yf_symbol, 
                    start=start_date, 
                    end=end_date,
                    interval='5m',  # ✓ CRITICAL FIX: 5-minute intervals
                    progress=False
                )
            
            if df.empty:
                logger.warning(f"[{symbol}] No data from YFinance")
                return pd.DataFrame()
            
            df = df.copy()
            
            # ✓ CRITICAL: Handle MultiIndex columns from yfinance
            # yfinance returns MultiIndex for single symbol downloads
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # ✓ CRITICAL: Preserve DatetimeIndex instead of resetting
            # The index is already DatetimeIndex from yfinance
            if isinstance(df.index, pd.DatetimeIndex):
                df.index.name = 'Time'
            else:
                # Fallback: make index a column and convert to datetime
                df = df.reset_index()
                df = df.rename(columns={'Date': 'Time', 'Datetime': 'Time'})
                df['Time'] = pd.to_datetime(df['Time'])
                df.set_index('Time', inplace=True)
            
            # Remove duplicate columns if any
            if df.columns.duplicated().any():
                df = df.loc[:, ~df.columns.duplicated(keep='first')]
            
            # Ensure all OHLCV columns exist and are numeric
            is_valid, df = self.validate_columns(df)
            if not is_valid:
                logger.error(f"[{symbol}] Column validation failed")
                return pd.DataFrame()
            
            # ✓ CRITICAL: Convert timezone to IST
            # yfinance returns UTC or naive timestamps
            if df.index.tz is None:
                # Localize to UTC, then convert to IST
                df.index = df.index.tz_localize('UTC', ambiguous='NaT', nonexistent='NaT')
            
            # Check timezone and convert if not IST
            # Handle both pytz and datetime.timezone objects
            current_tz = str(df.index.tz) if df.index.tz else None
            if current_tz != 'Asia/Kolkata':
                df.index = df.index.tz_convert(IST)
            
            # Ensure sorted chronologically
            if not df.index.is_monotonic_increasing:
                df = df.sort_index()
            
            # ✓ CRITICAL: Filter to NSE market hours (09:15-15:30 IST)
            # This removes any pre/post-market data
            df = self._filter_nse_hours(df)
            
            if df.empty:
                logger.warning(f"[{symbol}] No data within NSE market hours")
                return pd.DataFrame()
            
            # Check data sufficiency
            if not self.check_data_sufficiency(symbol, len(df)):
                if len(df) < self.FALLBACK_MIN_POINTS:
                    return pd.DataFrame()
            
            logger.info(f"[{symbol}] ✓ Fetched {len(df)} candles (5-min), IST timezone, DatetimeIndex preserved")
            return df
            
        except Exception as e:
            logger.error(f"[{symbol}] Fetch failed: {type(e).__name__}: {str(e)[:100]}")
            return pd.DataFrame()
    
    def fetch_daily_data(self, symbol: str, lookback_days: int = 365) -> pd.DataFrame:
        """
        Fetch daily historical data from YFinance
        
        Args:
            symbol: Stock symbol without .NS suffix
            lookback_days: Historical lookback period
        
        Returns:
            DataFrame with daily OHLCV data, DatetimeIndex (IST)
        """
        try:
            yf_symbol = f"{symbol}.NS"
            
            logger.info(f"[{symbol}] Fetching daily data: {lookback_days}d")
            
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            with _yfinance_lock:
                df = yf.download(
                    yf_symbol,
                    start=start_date,
                    end=end_date,
                    progress=False
                )
            
            if df.empty:
                logger.warning(f"[{symbol}] No daily data from YFinance")
                return pd.DataFrame()
            
            df = df.copy()
            
            # Handle MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Preserve DatetimeIndex
            if isinstance(df.index, pd.DatetimeIndex):
                df.index.name = 'Time'
            else:
                df = df.reset_index()
                df = df.rename(columns={'Date': 'Time'})
                df['Time'] = pd.to_datetime(df['Time'])
                df.set_index('Time', inplace=True)
            
            # Validate columns
            is_valid, df = self.validate_columns(df)
            if not is_valid:
                return pd.DataFrame()
            
            # Convert timezone
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            
            # Check timezone and convert if not IST
            # Handle both pytz and datetime.timezone objects
            current_tz = str(df.index.tz) if df.index.tz else None
            if current_tz != 'Asia/Kolkata':
                df.index = df.index.tz_convert(IST)
            
            # Sort
            if not df.index.is_monotonic_increasing:
                df = df.sort_index()
            
            # Check sufficiency
            if not self.check_data_sufficiency(symbol, len(df)):
                if len(df) < self.FALLBACK_MIN_POINTS:
                    return pd.DataFrame()
            
            logger.info(f"[{symbol}] ✓ Fetched {len(df)} daily candles (IST, DatetimeIndex)")
            return df
            
        except Exception as e:
            logger.error(f"[{symbol}] Daily fetch failed: {type(e).__name__}: {e}")
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
