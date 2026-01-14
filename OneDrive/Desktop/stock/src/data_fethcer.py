import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
from src.logger import logger

class DataFetcher:
    @staticmethod
    def get_5min_data(symbol, lookback_days=90):
        """
        Fetch historical data using yfinance API
        Returns daily OHLCV data for the specified lookback period
        """
        try:
            # Format symbol for yfinance (add .NS for NSE India stocks)
            yf_symbol = f"{symbol}.NS"
            
            logger.info(f"Fetching data for {symbol} from yfinance: {lookback_days} days lookback")
            
            # Download historical data from yfinance
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            df = yf.download(yf_symbol, start=start_date, end=end_date, progress=False)
            
            if df.empty:
                logger.warning(f"{symbol}: No data returned from yfinance")
                return pd.DataFrame()
            
            # Make a copy
            df = df.copy()
            
            # Handle MultiIndex columns - extract just the price type (first level)
            if isinstance(df.columns, pd.MultiIndex):
                # df.columns is like [('Close', 'RELIANCE.NS'), ('High', 'RELIANCE.NS'), ...]
                # We want to extract just ['Close', 'High', ...]
                df.columns = df.columns.get_level_values(0)
            
            # Reset the index to convert Date from index to column
            df = df.reset_index()
            
            # Create a clean dataframe
            result = pd.DataFrame()
            result['Time'] = df['Date']
            result['Open'] = pd.to_numeric(df['Open'], errors='coerce')
            result['High'] = pd.to_numeric(df['High'], errors='coerce')
            result['Low'] = pd.to_numeric(df['Low'], errors='coerce')
            result['Close'] = pd.to_numeric(df['Close'], errors='coerce')
            result['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
            
            # Remove rows with any NaN in OHLCV columns
            result = result.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
            
            # Reset index
            result = result.reset_index(drop=True)
            
            logger.info(f"{symbol}: Got {len(result)} records from yfinance")
            
            if len(result) < 20:
                logger.warning(f"{symbol}: Insufficient data ({len(result)} < 20)")
                return pd.DataFrame()
            
            return result
            
        except Exception as e:
            logger.error(f"{symbol}: yfinance fetch failed - {type(e).__name__}: {e}")
            logger.debug(f"{symbol}: Exception details: {str(e)}")
            return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"DataFetcher error for {symbol}: {e}", exc_info=True)
            return pd.DataFrame()
    
    @staticmethod
    def _process_quote_data(symbol, quote_data):
        """Process live quote data into a DataFrame"""
        try:
            # Create a single row DataFrame from quote data
            row = {
                'Time': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
                'Open': quote_data.get('open', 0),
                'High': quote_data.get('dayHigh', quote_data.get('high', 0)),
                'Low': quote_data.get('dayLow', quote_data.get('low', 0)),
                'Close': quote_data.get('lastPrice', quote_data.get('close', 0)),
                'Volume': quote_data.get('totalTradedVolume', 0)
            }
            df = pd.DataFrame([row])
            logger.info(f"{symbol}: Created DataFrame from quote data")
            return df
        except Exception as e:
            logger.error(f"Error processing quote data for {symbol}: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_csv_data(file_path):
        """
        Load data from local CSV file for testing
        Columns: Time, Open, High, Low, Close, Volume
        """
        try:
            df = pd.read_csv(file_path)
            logger.info(f"Loaded CSV: {file_path} with {len(df)} records")
            
            # Ensure numeric columns
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna()
            logger.info(f"After cleanup: {len(df)} records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {e}")
            return pd.DataFrame()