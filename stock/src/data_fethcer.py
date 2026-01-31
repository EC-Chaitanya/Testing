import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import pytz
from src.logger import logger
from typing import Tuple, Optional
from src.data_providers import get_data_provider, DataProviderBase

# Timezone for Indian Stock Market
IST = pytz.timezone('Asia/Kolkata')


class DataFetcher:
    """
    Stock data fetching with MStock provider
    
    ✓ PRODUCTION ARCHITECTURE:
    - MStock API only (no fallbacks)
    - Provider instance-based (no static methods that hide provider)
    - Fail-fast on configuration errors
    - Thread-safe concurrent fetching
    
    ✓ ALL CRITICAL FIXES PRESERVED:
    - 5-minute interval data (not daily)
    - DatetimeIndex preservation
    - IST timezone localization
    - NSE market hours filtering (09:15-15:30)
    - VWAP daily reset logic (in indicators.py)
    """
    
    def __init__(self, provider: str = 'mstock', api_key: str = None, session=None):
        """
        Initialize DataFetcher with MStock provider
        
        Args:
            provider: Provider identifier (must be 'mstock')
            api_key: M.Stock API key (optional if session provided)
            session: Authenticated MConnect session object (optional if api_key provided)
        
        Raises:
            ValueError: If neither api_key nor session provided, or provider invalid
        """
        if provider != 'mstock':
            raise ValueError(
                f"Unsupported provider: {provider}\n"
                f"Only 'mstock' is allowed (YFinance limited to 60 days)."
            )
        
        # If session provided, use it
        if session:
            self.provider: DataProviderBase = get_data_provider(provider, session=session)
            logger.info(f"DataFetcher initialized with {self.provider} (authenticated session)")
            return
        
        # Otherwise try to get API key from parameter or config
        if api_key is None:
            try:
                from config import API_KEY
                api_key = API_KEY
            except ImportError:
                raise ValueError(
                    "MStock requires either API_KEY or authenticated session.\n"
                    "Set API_KEY in config.py or pass session=get_session(...)\n"
                )
        
        self.provider: DataProviderBase = get_data_provider(provider, api_key=api_key)
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
