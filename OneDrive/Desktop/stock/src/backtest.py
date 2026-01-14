"""
Historical Backtest Mode - Analyze historical data for trading signals
Supports CSV files and NSE historical data
"""

import os
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import yfinance as yf

from src.engine import ScoringEngine
from src.logger import logger
from src.utils import OutputFormatter, SignalFilter, DataValidator

class HistoricalBacktest:
    """
    Analyze historical data to identify trading signals
    Supports both local CSV and NSE API data sources
    """
    
    def __init__(self):
        self.logger = logger
        self.results = []
    
    def load_csv_data(self, file_path):
        """Load data from local CSV file"""
        try:
            df = pd.read_csv(file_path)
            
            # Expected columns: Time, Open, High, Low, Close, Volume
            expected_cols = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            
            # Try to rename columns if they have different names
            df.columns = df.columns.str.strip().str.title()
            
            # Ensure numeric columns
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove rows with NaN values
            df = df.dropna()
            
            if len(df) < 50:
                self.logger.warning(f"CSV has only {len(df)} rows. Need minimum 50 for analysis.")
                return None
            
            self.logger.info(f"Loaded CSV with {len(df)} records from {file_path}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading CSV {file_path}: {e}")
            return None
    
    def fetch_nse_history(self, symbol, days=90):
        """Fetch historical data from yfinance API"""
        try:
            yf_symbol = f"{symbol}.NS"
            self.logger.info(f"Fetching {days} days of history for {symbol} using yfinance")
            
            # Download data from yfinance
            df = yf.download(yf_symbol, period=f"{days}d", progress=False)
            
            if df.empty:
                self.logger.warning(f"No data from yfinance for {symbol}")
                return None
            
            # Make a copy
            df = df.copy()
            
            # Handle MultiIndex columns - extract just the price type (first level)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Reset index to make Date a column
            df = df.reset_index()
            
            # Create clean dataframe
            result = pd.DataFrame()
            result['Time'] = df['Date']
            result['Open'] = pd.to_numeric(df['Open'], errors='coerce')
            result['High'] = pd.to_numeric(df['High'], errors='coerce')
            result['Low'] = pd.to_numeric(df['Low'], errors='coerce')
            result['Close'] = pd.to_numeric(df['Close'], errors='coerce')
            result['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
            
            # Remove NaN rows
            result = result.dropna()
            
            if len(result) < 50:
                self.logger.warning(f"yfinance returned only {len(result)} records")
                return None
            
            self.logger.info(f"Fetched {len(result)} records from yfinance for {symbol}")
            return result  # Return all records
            
        except Exception as e:
            self.logger.error(f"Error fetching data from yfinance for {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df):
        """Calculate all technical indicators"""
        try:
            df['EMA_20'] = ta.ema(df['Close'], length=20)
            df['EMA_50'] = ta.ema(df['Close'], length=50)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
            
            # Forward fill NaN values from indicator calculation
            df = df.fillna(method='bfill')
            
            return df
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}")
            return None
    
    def vectorized_score(self, df):
        """
        Apply scoring vectorized across entire DataFrame
        More efficient than row-by-row scoring
        """
        try:
            results = []
            
            for idx in range(len(df)):
                row_df = df.iloc[:idx+1]  # Include all data up to current row
                
                bullish = ScoringEngine.get_bullish_score(row_df)
                bearish = ScoringEngine.get_bearish_score(row_df)
                
                signal_row = df.iloc[idx]
                results.append({
                    'Date': signal_row.get('Time', idx),
                    'Close': float(signal_row['Close']),
                    'RSI': float(signal_row['RSI']) if pd.notna(signal_row['RSI']) else None,
                    'Bullish': bullish,
                    'Bearish': bearish,
                    'Signal': 'BULL' if bullish >= 65 else ('BEAR' if bearish >= 65 else 'NONE')
                })
            
            return pd.DataFrame(results)
            
        except Exception as e:
            self.logger.error(f"Error in vectorized scoring: {e}")
            return None
    
    def run_backtest(self, source_type, symbol_or_path, threshold=65):
        """
        Run backtest on historical data
        source_type: 'CSV' or 'NSE'
        symbol_or_path: Stock symbol for NSE, file path for CSV
        """
        print(f"\n{'='*80}")
        print(f"Historical Backtest Mode")
        print(f"{'='*80}\n")
        
        # Load data
        if source_type.upper() == 'CSV':
            if not os.path.exists(symbol_or_path):
                print(f"✗ File not found: {symbol_or_path}")
                return None
            df = self.load_csv_data(symbol_or_path)
        else:  # NSE
            df = self.fetch_nse_history(symbol_or_path)
        
        if df is None or df.empty:
            print(f"✗ Failed to load data")
            return None
        
        print(f"✓ Loaded {len(df)} records")
        
        # Calculate indicators
        print("Calculating technical indicators...")
        df = self.calculate_indicators(df)
        
        if df is None:
            print("✗ Error calculating indicators")
            return None
        
        print("✓ Indicators calculated")
        
        # Perform vectorized scoring
        print("Performing vectorized analysis...")
        signal_df = self.vectorized_score(df)
        
        if signal_df is None:
            print("✗ Error during scoring")
            return None
        
        print("✓ Analysis complete\n")
        
        # Generate summary report
        self._display_backtest_report(symbol_or_path, signal_df, threshold)
        
        return signal_df
    
    def _display_backtest_report(self, symbol, signal_df, threshold):
        """Display comprehensive backtest report"""
        print(f"\n{'='*80}")
        print(f"BACKTEST REPORT: {symbol}")
        print(f"{'='*80}\n")
        
        # Summary statistics
        total_signals = len(signal_df)
        bullish_signals = len(signal_df[signal_df['Bullish'] >= threshold])
        bearish_signals = len(signal_df[signal_df['Bearish'] >= threshold])
        neutral = total_signals - bullish_signals - bearish_signals
        
        print(f"Total Candles Analyzed: {total_signals}")
        print(f"Bullish Signals (≥{threshold}):  {bullish_signals} ({bullish_signals/total_signals*100:.1f}%)")
        print(f"Bearish Signals (≥{threshold}): {bearish_signals} ({bearish_signals/total_signals*100:.1f}%)")
        print(f"Neutral Signals:            {neutral} ({neutral/total_signals*100:.1f}%)")
        
        # Top signals
        print(f"\n{'-'*80}")
        print(f"Top 10 Bullish Signals:")
        print(f"{'-'*80}\n")
        
        top_bullish = signal_df[signal_df['Bullish'] >= threshold].nlargest(10, 'Bullish')
        if not top_bullish.empty:
            print(top_bullish[['Date', 'Close', 'Bullish', 'RSI']].to_string(index=False))
        else:
            print("No bullish signals found")
        
        print(f"\n{'-'*80}")
        print(f"Top 10 Bearish Signals:")
        print(f"{'-'*80}\n")
        
        top_bearish = signal_df[signal_df['Bearish'] >= threshold].nlargest(10, 'Bearish')
        if not top_bearish.empty:
            print(top_bearish[['Date', 'Close', 'Bearish', 'RSI']].to_string(index=False))
        else:
            print("No bearish signals found")
        
        # Save detailed report
        report_file = f"backtest_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        signal_df.to_csv(report_file, index=False)
        print(f"\n✓ Detailed report saved to: {report_file}")
        
        self.logger.info(f"Backtest complete for {symbol}. Bull={bullish_signals}, Bear={bearish_signals}")
