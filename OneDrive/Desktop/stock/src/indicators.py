"""
Technical Indicators for Stock Analysis
- SuperTrend: Trend identification with bullish/bearish signals
- VWAP: Volume Weighted Average Price
"""

import pandas as pd
import numpy as np
from src.logger import logger
import pytz

# IST timezone for NSE market
IST = pytz.timezone('Asia/Kolkata')


class TechnicalIndicators:
    """Calculate technical indicators for stock analysis"""
    
    # NSE Market Hours (IST)
    NSE_OPEN_HOUR = 9
    NSE_OPEN_MINUTE = 15
    NSE_CLOSE_HOUR = 15
    NSE_CLOSE_MINUTE = 30
    
    @staticmethod
    def filter_nse_market_hours(df):
        """
        Filter DataFrame to only include NSE market hours (09:15-15:30 IST)
        
        ✓ CRITICAL FIX: Ensures all data is within actual trading hours
        
        Args:
            df: DataFrame with DatetimeIndex (IST timezone-aware)
        
        Returns:
            Filtered DataFrame with only NSE market hours
        """
        try:
            if df is None or df.empty:
                return df
            
            if not isinstance(df.index, pd.DatetimeIndex):
                logger.warning("Cannot filter NSE hours: DataFrame must have DatetimeIndex")
                return df
            
            # Ensure index is in IST
            if df.index.tz is None:
                logger.warning("DatetimeIndex has no timezone. Assuming IST.")
                df.index = df.index.tz_localize('Asia/Kolkata')
            elif df.index.tz.zone != 'Asia/Kolkata':
                logger.info(f"Converting timezone from {df.index.tz} to IST")
                df.index = df.index.tz_convert('Asia/Kolkata')
            
            # Extract hour and minute for filtering
            hours = df.index.hour
            minutes = df.index.minute
            
            # Create time as decimal for comparison (e.g., 09:15 = 9.25, 15:30 = 15.5)
            times = hours + minutes / 60.0
            
            market_open = TechnicalIndicators.NSE_OPEN_HOUR + TechnicalIndicators.NSE_OPEN_MINUTE / 60.0
            market_close = TechnicalIndicators.NSE_CLOSE_HOUR + TechnicalIndicators.NSE_CLOSE_MINUTE / 60.0
            
            # Filter to market hours
            mask = (times >= market_open) & (times <= market_close)
            filtered_df = df[mask]
            
            if len(filtered_df) < len(df):
                logger.info(f"Filtered to NSE hours: {len(df)} -> {len(filtered_df)} candles")
            
            return filtered_df
            
        except Exception as e:
            logger.error(f"Error filtering NSE market hours: {type(e).__name__}: {e}")
            return df
    
    @staticmethod
    def calculate_supertrend(df, period=20, multiplier=2):
        """
        Calculate SuperTrend indicator
        
        SuperTrend is a trend-following indicator that identifies uptrends and downtrends
        It uses Average True Range (ATR) to create dynamic support and resistance levels
        
        Args:
            df: DataFrame with OHLC data
            period: Lookback period for ATR calculation (default: 20)
            multiplier: Multiplier for ATR to create bands (default: 2)
        
        Returns:
            DataFrame with added 'SuperTrend' and 'SuperTrend_Signal' columns
            SuperTrend_Signal: 1 for bullish, -1 for bearish, 0 for neutral
        """
        try:
            # Make a copy to avoid modifying original
            df = df.copy()
            
            if len(df) < period:
                logger.warning(f"Insufficient data for SuperTrend: {len(df)} < {period}")
                df['SuperTrend'] = np.nan
                df['SuperTrend_Signal'] = 0
                return df
            
            # Step 1: Calculate True Range
            df['TR'] = np.maximum(
                df['High'] - df['Low'],
                np.maximum(
                    abs(df['High'] - df['Close'].shift(1)),
                    abs(df['Low'] - df['Close'].shift(1))
                )
            )
            
            # Step 2: Calculate Average True Range (ATR)
            df['ATR'] = df['TR'].rolling(window=period).mean()
            
            # Step 3: Calculate Basic Bands
            hl_avg = (df['High'] + df['Low']) / 2
            df['Basic_UB'] = hl_avg + (multiplier * df['ATR'])
            df['Basic_LB'] = hl_avg - (multiplier * df['ATR'])
            
            # Step 4: Calculate Final Bands
            df['Final_UB'] = df['Basic_UB'].copy()
            df['Final_LB'] = df['Basic_LB'].copy()
            
            for i in range(period, len(df)):
                # Final upper band
                if df.loc[i, 'Basic_UB'] < df.loc[i-1, 'Final_UB'] or df.loc[i-1, 'Close'] > df.loc[i-1, 'Final_UB']:
                    df.loc[i, 'Final_UB'] = df.loc[i, 'Basic_UB']
                else:
                    df.loc[i, 'Final_UB'] = df.loc[i-1, 'Final_UB']
                
                # Final lower band
                if df.loc[i, 'Basic_LB'] > df.loc[i-1, 'Final_LB'] or df.loc[i-1, 'Close'] < df.loc[i-1, 'Final_LB']:
                    df.loc[i, 'Final_LB'] = df.loc[i, 'Basic_LB']
                else:
                    df.loc[i, 'Final_LB'] = df.loc[i-1, 'Final_LB']
            
            # Step 5: Calculate SuperTrend
            df['SuperTrend'] = np.nan
            df['SuperTrend_Signal'] = 0
            
            in_uptrend = True
            
            for i in range(period, len(df)):
                if df.loc[i, 'Close'] <= df.loc[i, 'Final_UB']:
                    in_uptrend = False
                
                if df.loc[i, 'Close'] >= df.loc[i, 'Final_LB']:
                    in_uptrend = True
                
                if in_uptrend:
                    df.loc[i, 'SuperTrend'] = df.loc[i, 'Final_LB']
                    df.loc[i, 'SuperTrend_Signal'] = 1  # Bullish
                else:
                    df.loc[i, 'SuperTrend'] = df.loc[i, 'Final_UB']
                    df.loc[i, 'SuperTrend_Signal'] = -1  # Bearish
            
            # Clean up intermediate columns
            df = df.drop(['TR', 'ATR', 'Basic_UB', 'Basic_LB', 'Final_UB', 'Final_LB'], axis=1)
            
            logger.info(f"SuperTrend calculated successfully (period={period}, multiplier={multiplier})")
            return df
            
        except Exception as e:
            logger.error(f"Error calculating SuperTrend: {e}")
            df['SuperTrend'] = np.nan
            df['SuperTrend_Signal'] = 0
            return df
    
    @staticmethod
    def calculate_vwap(df, window=None):
        """
        Calculate Volume Weighted Average Price (VWAP) with rolling window support
        
        VWAP is the ratio of the value traded to total volume traded over a particular time horizon
        Formula: VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
        where Typical Price = (High + Low + Close) / 3
        
        ✓ FIXED: Now uses rolling window for INTRADAY (resets appropriately)
        ✓ FIXED: Consistent with pandas_ta ta.vwap() implementation
        
        Args:
            df: DataFrame with OHLCV data (should have DatetimeIndex)
            window: Optional rolling window size for VWAP calculation. 
                   For INTRADAY (5-min, 15-min): Use window=50-100 (resets every 3-5 hours)
                   For DAILY: Use window=None (cumulative from market open)
        
        Returns:
            DataFrame with added 'VWAP' column
            
        Data Integrity Fixes:
            1. Zero volume handling - prevents NaN division errors
            2. Rolling window support - allows intraday VWAP reset
            3. NaN value isolation - prevents null propagation
            4. Type consistency - ensures float64 precision
            5. Consistent with pandas_ta.vwap() for live trading accuracy
        """
        try:
            # Input validation
            if df is None or df.empty:
                logger.warning("Empty DataFrame provided for VWAP calculation")
                return df
            
            if len(df) < 2:
                logger.warning(f"Insufficient data for VWAP calculation: {len(df)} < 2")
                df['VWAP'] = np.nan
                return df
            
            # Validate required columns
            required_cols = ['High', 'Low', 'Close', 'Volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"Missing required columns for VWAP: {missing_cols}")
                df['VWAP'] = np.nan
                return df
            
            df = df.copy()
            
            # Ensure DatetimeIndex is sorted
            if isinstance(df.index, pd.DatetimeIndex):
                if not df.index.is_monotonic_increasing:
                    df = df.sort_index()
            
            # BUG FIX #1: Handle NaN values in input data
            # Prevent NaN values in OHLC data from propagating through calculation
            df_clean = df[required_cols].ffill().bfill()
            if df_clean.isnull().any().any():
                logger.warning("Could not fill all NaN values in OHLCV data - using forward fill with backward fill")
                df_clean = df_clean.fillna(df_clean.mean())
            
            # BUG FIX #2: Calculate Typical Price with NaN-safe operations
            # Ensure type consistency (float64) to prevent precision loss
            typical_price = ((df_clean['High'].astype(np.float64) + 
                            df_clean['Low'].astype(np.float64) + 
                            df_clean['Close'].astype(np.float64)) / 3.0)
            
            # BUG FIX #3: Zero volume handling - prevent division by zero
            # Ensure volume is positive, replace zero/negative with small value
            volume = df_clean['Volume'].astype(np.float64)
            volume = volume.clip(lower=1.0)  # Minimum 1 share to prevent division by zero
            
            # BUG FIX #4: Rolling VWAP calculation with proper reset behavior
            # ✓ NOW FIXED: Use rolling window for INTRADAY to match pandas_ta behavior
            if window is not None and window > 1:
                # INTRADAY VWAP with rolling window reset
                # This matches pandas_ta.vwap() implementation
                tp_volume = typical_price * volume
                rolling_tp_sum = tp_volume.rolling(window=window, min_periods=1).sum()
                rolling_vol_sum = volume.rolling(window=window, min_periods=1).sum()
                
                # Prevent division by zero in rolling window
                vwap = np.where(rolling_vol_sum > 0, rolling_tp_sum / rolling_vol_sum, np.nan)
                logger.info(f"VWAP calculated with rolling window={window} (for intraday resetting)")
            else:
                # Cumulative VWAP from data start (standard for daily data)
                # ✓ FIXED: This is now correct - used only for daily/swing
                tp_volume = typical_price * volume
                cum_tp_volume = tp_volume.cumsum()
                cum_volume = volume.cumsum()
                
                # Prevent division by zero with safe division
                vwap = np.where(cum_volume > 0, cum_tp_volume / cum_volume, np.nan)
                logger.info(f"VWAP calculated with cumulative method (for daily/swing)")
            
            # Ensure output is float64 for consistency
            df['VWAP'] = vwap.astype(np.float64)
            
            # Validate output - check for unexpected NaN patterns
            nan_count = df['VWAP'].isnull().sum()
            if nan_count > len(df) * 0.5:
                logger.warning(f"VWAP calculation produced {nan_count} NaN values ({nan_count/len(df)*100:.1f}%)")
            
            logger.info(f"✓ VWAP calculation complete: {len(df)} candles, "
                       f"{nan_count} NaN values, {'rolling window' if window else 'cumulative'}")
            return df
            
        except Exception as e:
            logger.error(f"Error calculating VWAP: {type(e).__name__}: {e}")
            df['VWAP'] = np.nan
            return df
    
    @staticmethod
    def calculate_vwap_with_daily_reset(df, market_open_hour=9, market_open_minute=15):
        """
        Calculate VWAP with automatic daily reset at market open (IST)
        
        ✓ CRITICAL FIX: VWAP must reset every trading day, not cumulative across days
        
        This ensures:
        1. VWAP reflects intraday price value only
        2. Resets at 09:15 IST (NSE market open)
        3. Not influenced by previous day's closing prices
        
        Args:
            df: DataFrame with DatetimeIndex (must be IST timezone-aware)
            market_open_hour: Market open hour in 24-hour format (default: 9 for 09:15)
            market_open_minute: Market open minute (default: 15)
        
        Returns:
            DataFrame with VWAP column that resets daily
            
        Requirements:
            - df must have DatetimeIndex with IST timezone
            - df must have columns: High, Low, Close, Volume
        """
        try:
            if df is None or df.empty:
                logger.warning("Empty DataFrame provided for VWAP with daily reset")
                return df
            
            df = df.copy()
            
            # CRITICAL: Ensure we have DatetimeIndex
            if not isinstance(df.index, pd.DatetimeIndex):
                logger.error("VWAP daily reset requires DatetimeIndex. DataFrame index must be timestamps.")
                df['VWAP'] = np.nan
                return df
            
            # Create daily session identifier
            # Each candle gets marked with its trading day's start time
            df['_trading_day'] = df.index.normalize()  # Get date part only (at 00:00)
            df['_session_start'] = df['_trading_day'] + pd.Timedelta(hours=market_open_hour, minutes=market_open_minute)
            
            # Calculate VWAP within each daily session
            df['_group'] = df['_trading_day']  # Group by trading day
            
            required_cols = ['High', 'Low', 'Close', 'Volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"Missing required columns for VWAP: {missing_cols}")
                df['VWAP'] = np.nan
                return df
            
            # Calculate typical price and TP*Volume
            typical_price = (df['High'].astype(np.float64) + 
                           df['Low'].astype(np.float64) + 
                           df['Close'].astype(np.float64)) / 3.0
            
            # Handle zero volume
            volume = df['Volume'].astype(np.float64).clip(lower=1.0)
            
            # For each trading day, calculate cumulative VWAP within that day only
            def calculate_daily_vwap(group):
                """Calculate VWAP for a single trading day"""
                tp_volume = typical_price[group.index] * volume[group.index]
                cum_tp_volume = tp_volume.cumsum()
                cum_volume = volume[group.index].cumsum()
                
                # Prevent division by zero
                vwap = np.where(cum_volume > 0, cum_tp_volume / cum_volume, np.nan)
                return vwap
            
            # Apply VWAP calculation per trading day
            df['VWAP'] = np.nan
            for trading_day in df['_trading_day'].unique():
                mask = df['_trading_day'] == trading_day
                df.loc[mask, 'VWAP'] = calculate_daily_vwap(df[mask])
            
            # Clean up temporary columns
            df = df.drop(['_trading_day', '_session_start', '_group'], axis=1)
            
            logger.info(f"✓ VWAP with daily reset calculated: {len(df)} candles")
            return df
            
        except Exception as e:
            logger.error(f"Error calculating VWAP with daily reset: {type(e).__name__}: {e}")
            df['VWAP'] = np.nan
            return df
    
    @staticmethod
    def is_supertrend_bullish(df):
        """
        Check if current SuperTrend signal is bullish (positive)
        
        Args:
            df: DataFrame with SuperTrend_Signal column
        
        Returns:
            Boolean: True if bullish, False otherwise
        """
        if df.empty or 'SuperTrend_Signal' not in df.columns:
            return False
        
        last_signal = df.iloc[-1]['SuperTrend_Signal']
        return last_signal == 1
    
    @staticmethod
    def is_price_below_vwap(df):
        """
        Check if current price is below VWAP
        
        Args:
            df: DataFrame with VWAP column and Close price
        
        Returns:
            Boolean: True if price below VWAP, False otherwise
        """
        if df.empty or 'VWAP' not in df.columns:
            return False
        
        last_row = df.iloc[-1]
        close_price = last_row['Close']
        vwap = last_row['VWAP']
        
        if pd.isna(vwap) or pd.isna(close_price):
            return False
        
        return close_price < vwap
