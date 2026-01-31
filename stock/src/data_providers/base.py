"""
Abstract Data Provider Interface
Allows swapping between different data sources (yfinance, Kite, Shoonya, m.Stock, etc.)
without changing the core trading logic.
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Tuple
from src.logger import logger


class DataProviderBase(ABC):
    """
    Abstract base class for stock data providers
    
    All providers must implement these methods to fetch OHLCV data
    with proper timezone handling and validation.
    """
    
    # Constants (shared across all providers)
    MIN_DATA_POINTS = 100
    FALLBACK_MIN_POINTS = 20
    BUFFER_RATIO = 0.1
    BUFFER_DAYS = 10
    
    @abstractmethod
    def fetch_5min_data(self, symbol: str, lookback_days: int = 90) -> pd.DataFrame:
        """
        Fetch 5-minute historical data for a symbol
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE', 'TCS', 'INFY')
            lookback_days: Historical lookback period
        
        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
            Index: DatetimeIndex with IST timezone
            Name: 'Time'
        
        Contract:
            - Must return DatetimeIndex (not reset to integer index)
            - Must be timezone-aware (IST)
            - Must be sorted chronologically
            - Must contain only NSE market hours (09:15-15:30)
            - Empty DataFrame if fetch fails
        """
        pass
    
    @abstractmethod
    def fetch_daily_data(self, symbol: str, lookback_days: int = 365) -> pd.DataFrame:
        """
        Fetch daily historical data for a symbol
        
        Args:
            symbol: Stock symbol
            lookback_days: Historical lookback period
        
        Returns:
            DataFrame with OHLCV data, DatetimeIndex (IST), sorted
        """
        pass
    
    @staticmethod
    def validate_columns(df: pd.DataFrame) -> Tuple[bool, pd.DataFrame]:
        """
        Validate and extract required OHLCV columns
        
        Args:
            df: DataFrame to validate
        
        Returns:
            Tuple: (is_valid, df_cleaned)
        """
        if df is None or df.empty:
            return False, df
        
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            logger.error(f"Missing columns: {missing}")
            return False, df
        
        # Convert to numeric and remove NaN
        for col in required_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna(subset=required_cols)
        
        return True, df
    
    @staticmethod
    def check_data_sufficiency(symbol: str, data_count: int) -> bool:
        """
        Check if data is sufficient for analysis
        
        Args:
            symbol: Stock symbol (for logging)
            data_count: Number of data points
        
        Returns:
            Boolean: True if sufficient, False if critically insufficient
        """
        if data_count < DataProviderBase.FALLBACK_MIN_POINTS:
            logger.error(
                f"{symbol}: Insufficient data ({data_count} < {DataProviderBase.FALLBACK_MIN_POINTS})"
            )
            return False
        
        if data_count < DataProviderBase.MIN_DATA_POINTS:
            logger.warning(
                f"{symbol}: Data stabilization warning. "
                f"Got {data_count} periods, need {DataProviderBase.MIN_DATA_POINTS} for optimal indicators."
            )
        
        return True
    
    def __repr__(self):
        return f"{self.__class__.__name__}()"
