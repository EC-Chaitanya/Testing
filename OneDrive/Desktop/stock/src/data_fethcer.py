import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import pytz
from src.logger import logger
from typing import Tuple, Optional
from src.data_providers import get_data_provider, DataProviderBase

# Timezone for Indian Stock Market
IST = pytz.timezone('Asia/Kolkata')

# Default instance for backward compatibility with static calls
_default_fetcher = None


def _get_default_fetcher():
    """Get or create default DataFetcher instance (yfinance)"""
    global _default_fetcher
    if _default_fetcher is None:
        _default_fetcher = DataFetcher(provider='yfinance')
    return _default_fetcher


class DataFetcher:
    """
    Stock data fetching with provider abstraction
    
    ✓ ARCHITECTURE IMPROVEMENTS:
    - Provider-agnostic: swap yfinance for Kite/Shoonya/m.Stock anytime
    - Clean separation of concerns: DataFetcher routes, providers fetch
    - Broker-independent trading logic
    
    ✓ ALL CRITICAL FIXES PRESERVED:
    - 5-minute interval data (not daily)
    - DatetimeIndex preservation
    - IST timezone localization
    - NSE market hours filtering (09:15-15:30)
    - VWAP daily reset logic (in indicators.py)
    """
    
    def __init__(self, provider: str = 'yfinance'):
        """
        Initialize DataFetcher with a data provider
        
        Args:
            provider: Provider identifier ('yfinance', 'kite', 'shoonya', etc.)
        """
        self.provider: DataProviderBase = get_data_provider(provider)
        logger.info(f"DataFetcher initialized with {self.provider}")
    
    def fetch_5min_data(self, symbol: str, lookback_days: int = 90) -> pd.DataFrame:
        """
        Fetch 5-minute historical data using configured provider
        
        ✓ ALL CRITICAL FIXES APPLIED:
        1. 5-minute intervals (not daily) - via provider's interval='5m'
        2. DatetimeIndex preserved (not reset)
        3. IST timezone localized
        4. NSE market hours filtered (09:15-15:30)
        5. Thread-safe concurrent access
        
        Args:
            symbol: Stock symbol without .NS suffix (e.g., 'RELIANCE')
            lookback_days: Historical lookback period
        
        Returns:
            DataFrame with DatetimeIndex (IST), OHLCV columns
        """
        return self.provider.fetch_5min_data(symbol, lookback_days)
    
    def fetch_daily_data(self, symbol: str, lookback_days: int = 365) -> pd.DataFrame:
        """
        Fetch daily historical data using configured provider
        
        Args:
            symbol: Stock symbol
            lookback_days: Historical lookback period
        
        Returns:
            DataFrame with DatetimeIndex (IST), OHLCV columns
        """
        return self.provider.fetch_daily_data(symbol, lookback_days)
    
    @staticmethod
    def _process_quote_data(symbol: str, quote_data: dict) -> pd.DataFrame:
        """
        Process live quote data with timezone handling
        
        Converts quote dict to IST-localized DataFrame
        """
        try:
            if not quote_data:
                return pd.DataFrame()
            
            now_ist = datetime.now(IST)
            
            df = pd.DataFrame([{
                'Time': now_ist,
                'Open': quote_data.get('open', 0),
                'High': quote_data.get('dayHigh', quote_data.get('high', 0)),
                'Low': quote_data.get('dayLow', quote_data.get('low', 0)),
                'Close': quote_data.get('lastPrice', quote_data.get('close', 0)),
                'Volume': quote_data.get('totalTradedVolume', 0)
            }])
            
            # Set Time as DatetimeIndex
            df.set_index('Time', inplace=True)
            
            logger.info(f"{symbol}: Quote data processed (IST, DatetimeIndex)")
            return df
            
        except Exception as e:
            logger.error(f"{symbol}: Quote processing failed - {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_csv_data(file_path: str) -> pd.DataFrame:
        """
        Load data from local CSV file with validation
        
        Loads CSV and converts Time column to IST DatetimeIndex
        """
        try:
            df = pd.read_csv(file_path)
            logger.info(f"CSV loaded: {file_path} ({len(df)} records)")
            
            # Validate columns using provider's validation
            is_valid, df = DataProviderBase.validate_columns(df)
            if not is_valid:
                return pd.DataFrame()
            
            # Convert timezone if Time column exists
            if 'Time' in df.columns:
                df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
                if df['Time'].dt.tz is None:
                    df['Time'] = df['Time'].dt.tz_localize('UTC', ambiguous='NaT', nonexistent='NaT')
                df['Time'] = df['Time'].dt.tz_convert(IST)
                df.set_index('Time', inplace=True)
            
            logger.info(f"CSV validated: {len(df)} records (IST, DatetimeIndex)")
            return df
            
        except FileNotFoundError:
            logger.error(f"CSV not found: {file_path}")
        except Exception as e:
            logger.error(f"CSV loading failed: {type(e).__name__}: {e}")
        
        return pd.DataFrame()


# ============================================================================
# MODULE-LEVEL BACKWARD COMPATIBILITY FUNCTIONS
# ============================================================================
# These functions provide backward compatibility for code that calls:
#   DataFetcher.get_5min_data('SYMBOL')  - as a static method
# Without causing recursion issues with instance methods

def _fetch_5min_data_default(symbol: str, lookback_days: int = 90) -> pd.DataFrame:
    """Backward compatibility wrapper using default yfinance provider"""
    return _get_default_fetcher().fetch_5min_data(symbol, lookback_days)


def _fetch_daily_data_default(symbol: str, lookback_days: int = 365) -> pd.DataFrame:
    """Backward compatibility wrapper using default yfinance provider"""
    return _get_default_fetcher().fetch_daily_data(symbol, lookback_days)


# Make static methods available at class level for backward compatibility
DataFetcher.get_5min_data = staticmethod(_fetch_5min_data_default)
DataFetcher.get_daily_data = staticmethod(_fetch_daily_data_default)
