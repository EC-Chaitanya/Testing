"""
Real-Time Data Fetcher for Live Trading
Scrapes live prices from multiple free sources without rate limits
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import time
from src.logger import logger
from typing import Dict, Optional

class RealtimeFetcher:
    """Fetch real-time stock prices from free sources"""
    
    # Multiple data sources for reliability
    SOURCES = ['moneycontrol', 'bseindia', 'nseindia', 'yfinance']
    
    @staticmethod
    def get_live_price(symbol: str) -> Optional[Dict]:
        """
        Get current live price for a stock symbol
        Returns: {'symbol': str, 'price': float, 'high': float, 'low': float, 'volume': int, 'timestamp': str}
        """
        
        # Try multiple sources in priority order
        for source in RealtimeFetcher.SOURCES:
            try:
                if source == 'moneycontrol':
                    result = RealtimeFetcher._fetch_moneycontrol(symbol)
                elif source == 'bseindia':
                    result = RealtimeFetcher._fetch_bseindia(symbol)
                elif source == 'nseindia':
                    result = RealtimeFetcher._fetch_nseindia(symbol)
                elif source == 'yfinance':
                    result = RealtimeFetcher._fetch_yfinance_live(symbol)
                
                if result:
                    logger.info(f"✓ {symbol}: Live price fetched from {source} - ₹{result['price']}")
                    return result
                    
            except Exception as e:
                logger.debug(f"{symbol}: {source} failed - {str(e)[:50]}")
                continue
        
        logger.warning(f"❌ {symbol}: Could not fetch live price from any source")
        return None
    
    @staticmethod
    def _fetch_moneycontrol(symbol: str) -> Optional[Dict]:
        """Fetch from Moneycontrol (most reliable free source)"""
        try:
            # Moneycontrol URL pattern
            url = f"https://www.moneycontrol.com/india/stockpricequote/{symbol.lower()}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract price data from Moneycontrol
            # Look for current price in the page
            price_text = soup.find('span', class_='Pd')
            if not price_text:
                price_text = soup.find('span', {'class': 'bsetp'})
            
            if price_text:
                price = float(price_text.text.strip().replace(',', ''))
                
                # Get high/low if available
                high_text = soup.find('span', text='Day High')
                low_text = soup.find('span', text='Day Low')
                
                high = float(high_text.find_next().text.strip().replace(',', '')) if high_text else price
                low = float(low_text.find_next().text.strip().replace(',', '')) if low_text else price
                
                return {
                    'symbol': symbol.upper(),
                    'price': price,
                    'high': high,
                    'low': low,
                    'volume': 0,  # Not easily available
                    'timestamp': datetime.now().isoformat(),
                    'source': 'moneycontrol'
                }
        except Exception as e:
            logger.debug(f"Moneycontrol fetch failed: {e}")
        
        return None
    
    @staticmethod
    def _fetch_bseindia(symbol: str) -> Optional[Dict]:
        """Fetch from BSE India official website"""
        try:
            # BSE API endpoint
            url = f"https://www.bseindia.com/markets/equity/EQReports/StockPriceQuote.aspx?scripcode={symbol}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract current price
            price_elem = soup.find('span', id='ContentPlaceHolder1_lblLTP')
            if price_elem:
                price = float(price_elem.text.strip().replace(',', ''))
                
                # Get high/low
                high_elem = soup.find('span', id='ContentPlaceHolder1_lblHigh')
                low_elem = soup.find('span', id='ContentPlaceHolder1_lblLow')
                
                high = float(high_elem.text.strip().replace(',', '')) if high_elem else price
                low = float(low_elem.text.strip().replace(',', '')) if low_elem else price
                
                # Get volume
                vol_elem = soup.find('span', id='ContentPlaceHolder1_lblVolume')
                volume = int(vol_elem.text.strip().replace(',', '')) if vol_elem else 0
                
                return {
                    'symbol': symbol.upper(),
                    'price': price,
                    'high': high,
                    'low': low,
                    'volume': volume,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'bseindia'
                }
        except Exception as e:
            logger.debug(f"BSE India fetch failed: {e}")
        
        return None
    
    @staticmethod
    def _fetch_nseindia(symbol: str) -> Optional[Dict]:
        """Fetch from NSE India official website"""
        try:
            # NSE API endpoint
            url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data and len(data['data']) > 0:
                quote = data['data'][0]
                
                return {
                    'symbol': symbol.upper(),
                    'price': float(quote.get('lastPrice', 0)),
                    'high': float(quote.get('dayHigh', 0)),
                    'low': float(quote.get('dayLow', 0)),
                    'volume': int(quote.get('totalTradedVolume', 0)),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'nseindia'
                }
        except Exception as e:
            logger.debug(f"NSE India fetch failed: {e}")
        
        return None
    
    @staticmethod
    def _fetch_yfinance_live(symbol: str) -> Optional[Dict]:
        """Fetch live price from yfinance"""
        try:
            import yfinance as yf
            
            yf_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(yf_symbol)
            
            # Get current data
            data = ticker.history(period='1d')
            
            if not data.empty:
                last_row = data.iloc[-1]
                
                return {
                    'symbol': symbol.upper(),
                    'price': float(last_row['Close']),
                    'high': float(last_row['High']),
                    'low': float(last_row['Low']),
                    'volume': int(last_row['Volume']),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'yfinance'
                }
        except ImportError:
            logger.debug("yfinance not installed")
        except Exception as e:
            logger.debug(f"yfinance fetch failed: {e}")
        
        return None
    
    @staticmethod
    def get_batch_live_prices(symbols: list) -> Dict[str, Dict]:
        """
        Get live prices for multiple symbols efficiently
        Returns: {'symbol': price_data, ...}
        """
        results = {}
        
        for symbol in symbols:
            try:
                price_data = RealtimeFetcher.get_live_price(symbol)
                if price_data:
                    results[symbol] = price_data
                time.sleep(0.5)  # Gentle rate limiting
            except Exception as e:
                logger.error(f"Batch fetch error for {symbol}: {e}")
        
        return results
    
    @staticmethod
    def get_realtime_dataframe(symbol: str, lookback_days: int = 30) -> pd.DataFrame:
        """
        Get a DataFrame with recent OHLCV data + current live price
        Useful for calculating indicators with latest data
        """
        try:
            import yfinance as yf
            
            yf_symbol = f"{symbol}.NS"
            
            # Get historical data
            df = yf.download(yf_symbol, period=f"{lookback_days}d", progress=False)
            
            if df.empty:
                logger.warning(f"{symbol}: No historical data from yfinance")
                return pd.DataFrame()
            
            # Get current live price and add as latest candle
            live_price = RealtimeFetcher.get_live_price(symbol)
            
            if live_price:
                # Add current price as latest row if market is open
                latest_date = df.index[-1] + timedelta(days=1)
                new_row = {
                    'Open': live_price['price'],
                    'High': live_price['high'],
                    'Low': live_price['low'],
                    'Close': live_price['price'],
                    'Volume': live_price['volume']
                }
                df.loc[latest_date] = new_row
            
            # Rename columns for consistency
            df = df.rename(columns={
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })
            
            # Convert to numeric
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna()
            
            logger.info(f"{symbol}: Got {len(df)} candles with current price")
            return df
            
        except Exception as e:
            logger.error(f"Error getting realtime dataframe for {symbol}: {e}")
            return pd.DataFrame()


class LivePriceMonitor:
    """Monitor live prices and generate alerts for trading"""
    
    def __init__(self, symbols: list, check_interval: int = 60):
        """
        Initialize live price monitor
        check_interval: seconds between price checks (min 30 seconds for free sources)
        """
        self.symbols = symbols
        self.check_interval = max(check_interval, 30)
        self.price_history = {symbol: [] for symbol in symbols}
        self.alerts = []
        self.running = False
    
    def start_monitoring(self):
        """Start continuous price monitoring"""
        self.running = True
        logger.info(f"Starting live monitoring for {len(self.symbols)} stocks every {self.check_interval}s")
        
        iteration = 0
        while self.running:
            iteration += 1
            try:
                print(f"\n{'='*80}")
                print(f"LIVE MONITORING CYCLE #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*80}\n")
                
                # Fetch all prices
                prices = RealtimeFetcher.get_batch_live_prices(self.symbols)
                
                # Display current prices
                print(f"{'Symbol':<12} {'Price':>12} {'High':>12} {'Low':>12} {'Change':>10}")
                print("-" * 60)
                
                for symbol in self.symbols:
                    if symbol in prices:
                        data = prices[symbol]
                        price = data['price']
                        high = data['high']
                        low = data['low']
                        
                        # Calculate change
                        change = ((price - low) / low * 100) if low > 0 else 0
                        
                        status = "🟢 UP" if change > 0 else "🔴 DOWN" if change < 0 else "⚪ FLAT"
                        
                        print(f"{symbol:<12} ₹{price:>10.2f} ₹{high:>10.2f} ₹{low:>10.2f} {status} {change:>6.2f}%")
                        
                        # Store price history
                        self.price_history[symbol].append({
                            'timestamp': datetime.now(),
                            'price': price,
                            'high': high,
                            'low': low
                        })
                    else:
                        print(f"{symbol:<12} ⚠️  No data available")
                
                # Wait before next check
                print(f"\nNext check in {self.check_interval} seconds...")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                self.stop_monitoring()
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        logger.info("Live monitoring stopped")
    
    def get_price_history(self, symbol: str, minutes: int = 60) -> list:
        """Get price history for the last N minutes"""
        if symbol not in self.price_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [p for p in self.price_history[symbol] if p['timestamp'] > cutoff_time]
