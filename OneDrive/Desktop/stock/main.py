"""
NIFTY 50 Dual-Directional Trading Terminal
CLI Gatekeeper for Live Scanner and Historical Backtest Modes
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from src.logger import logger
from src.live_scanner import LiveScanner
from src.backtest import HistoricalBacktest
from src.realtime_fetcher import RealtimeFetcher, LivePriceMonitor
from config import NIFTY_50_STOCKS


def print_banner():
    """Display application banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║     NIFTY 50 DUAL-DIRECTIONAL TRADING TERMINAL v2.0          ║
    ║     Live Scanner + Historical Backtest Quant System          ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info("Trading Terminal Started")


def print_menu():
    """Display main menu"""
    print("\n" + "="*65)
    print(f"{'MAIN MENU':^65}")
    print("="*65)
    print("\nSelect Operating Mode:\n")
    print("  [1] LIVE SCANNER MODE")
    print("      └─ Real-time NIFTY 50 analysis with 5-min candles")
    print("      └─ Dual-directional scoring (Bullish & Bearish)")
    print("      └─ Continuous monitoring at 5-min intervals")
    print()
    print("  [2] HISTORICAL BACKTEST MODE")
    print("      └─ Analyze historical data for trading signals")
    print("      └─ Data from CSV or NSE historical archive")
    print("      └─ Vectorized signal detection & reporting")
    print()
    print("  [3] LIVE PRICE TRACKER (REAL-TIME)")
    print("      └─ Track live stock prices every 60 seconds")
    print("      └─ Web scraping from free sources")
    print("      └─ Perfect for day trading & price monitoring")
    print()
    print("  [0] EXIT")
    print()
    print("="*65)


def mode_live_scanner():
    """Live Scanner Mode - Real-time NIFTY 50 analysis"""
    print("\n" + "="*65)
    print(f"{'LIVE SCANNER MODE':^65}")
    print("="*65 + "\n")
    
    print("Scanner Mode Options:\n")
    print("  [1] Single Scan (one-time analysis of all stocks)")
    print("  [2] Continuous Scan (repeated scans every 5 minutes)")
    print("  [0] Back to Main Menu")
    print()
    
    choice = input("Select option: ").strip()
    
    try:
        scanner = LiveScanner(threshold=65)
        
        if choice == "1":
            # Single scan
            bullish, bearish, results = scanner.run_single_scan()
            
            print("\n" + "="*65)
            print("Scan Complete. Options:")
            print("  [1] Run another single scan")
            print("  [2] Switch to continuous mode")
            print("  [0] Return to main menu")
            print("="*65)
            
            sub_choice = input("\nSelect: ").strip()
            if sub_choice == "1":
                mode_live_scanner()
            elif sub_choice == "2":
                interval = input("Enter scan interval in minutes (default 5): ").strip()
                try:
                    interval = int(interval) if interval else 5
                    scanner.run_continuous_scan(interval_minutes=interval)
                except ValueError:
                    print("Invalid interval. Using default 5 minutes.")
                    scanner.run_continuous_scan(interval_minutes=5)
        
        elif choice == "2":
            # Continuous scan
            print("\nEnter continuous scan parameters:")
            interval = input("  Scan interval in minutes (default 5): ").strip()
            max_scans = input("  Maximum scans (0 = infinite, default): ").strip()
            
            try:
                interval = int(interval) if interval else 5
                max_scans = int(max_scans) if max_scans and max_scans != "0" else None
            except ValueError:
                interval = 5
                max_scans = None
            
            print(f"\nStarting continuous scanning...")
            print(f"  Interval: {interval} minutes")
            print(f"  Max iterations: {'Infinite' if max_scans is None else max_scans}")
            print("  Press Ctrl+C to stop\n")
            
            scanner.run_continuous_scan(interval_minutes=interval, max_iterations=max_scans)
        
        elif choice != "0":
            print("Invalid option. Returning to main menu...")
    
    except Exception as e:
        logger.error(f"Error in live scanner mode: {e}")
        print(f"✗ Error: {e}")


def mode_backtest():
    """Historical Backtest Mode - Analyze historical data"""
    print("\n" + "="*65)
    print(f"{'HISTORICAL BACKTEST MODE':^65}")
    print("="*65 + "\n")
    
    print("Backtest Options:\n")
    print("  [1] Load from Local CSV File")
    print("  [2] Fetch from NSE Historical Data")
    print("  [0] Back to Main Menu")
    print()
    
    choice = input("Select data source: ").strip()
    
    try:
        backtest = HistoricalBacktest()
        
        if choice == "1":
            # CSV file
            print("\nCSV File Requirements:")
            print("  - Columns: Time, Open, High, Low, Close, Volume")
            print("  - Minimum 50 rows of data")
            print()
            
            file_path = input("Enter CSV file path: ").strip()
            
            if not os.path.exists(file_path):
                print(f"✗ File not found: {file_path}")
                return
            
            signal_df = backtest.run_backtest('CSV', file_path, threshold=65)
            
            if signal_df is not None:
                print("\n✓ Backtest completed successfully!")
                print(f"✓ Report saved with timestamp")
        
        elif choice == "2":
            # NSE Historical Data
            print("\nNSE Historical Data:")
            print("  Available symbols from NIFTY 50:")
            print(f"  {', '.join(NIFTY_50_STOCKS[:5])} ... and more")
            print()
            
            symbol = input("Enter stock symbol (e.g., RELIANCE): ").strip().upper()
            
            days = input("Enter number of days to analyze (default 90): ").strip()
            try:
                days = int(days) if days else 90
            except ValueError:
                days = 90
            
            print(f"\nFetching {days} days of data for {symbol} from NSE...")
            
            signal_df = backtest.run_backtest('NSE', symbol, threshold=65)
            
            if signal_df is not None:
                print("\n✓ Backtest completed successfully!")
        
        elif choice != "0":
            print("Invalid option. Returning to main menu...")
    
    except Exception as e:
        logger.error(f"Error in backtest mode: {e}")
        print(f"✗ Error: {e}")


def mode_realtime_tracker():
    """Real-time Price Tracker Mode - Live Stock Monitoring"""
    print("\n" + "="*65)
    print(f"{'LIVE PRICE TRACKER':^65}")
    print("="*65)
    print("\nReal-time monitoring options:\n")
    print("  [1] Check single stock price")
    print("  [2] Get batch prices for all NIFTY 50 stocks")
    print("  [3] Continuous monitoring (auto-refresh every 60 seconds)")
    print("  [0] Back to Main Menu\n")
    
    choice = input("Select option: ").strip()
    
    try:
        if choice == "1":
            symbol = input("\nEnter stock symbol (e.g., RELIANCE): ").strip().upper()
            if symbol:
                print(f"\n🔄 Fetching live price for {symbol}...")
                price_data = RealtimeFetcher.get_live_price(symbol)
                
                if price_data:
                    print(f"\n{'='*60}")
                    print(f"  {symbol} - LIVE PRICE")
                    print(f"{'='*60}")
                    print(f"  Current Price:  ₹{price_data['price']:.2f}")
                    print(f"  Day High:       ₹{price_data['high']:.2f}")
                    print(f"  Day Low:        ₹{price_data['low']:.2f}")
                    print(f"  Volume:         {price_data['volume']:,}")
                    print(f"  Source:         {price_data['source']}")
                    print(f"  Timestamp:      {price_data['timestamp']}")
                    print(f"  Day Range:      ₹{price_data['high'] - price_data['low']:.2f}")
                    print(f"{'='*60}\n")
                else:
                    print(f"❌ Could not fetch price for {symbol}")
        
        elif choice == "2":
            print(f"\n🔄 Fetching live prices for {len(NIFTY_50_STOCKS)} stocks...")
            print("(This may take 30-60 seconds)\n")
            
            prices = RealtimeFetcher.get_batch_live_prices(NIFTY_50_STOCKS)
            
            if prices:
                print(f"\n{'='*80}")
                print(f"  {'SYMBOL':<12} {'PRICE':>12} {'HIGH':>12} {'LOW':>12} {'RANGE':>10}")
                print(f"{'='*80}")
                
                sorted_prices = sorted(prices.items(), key=lambda x: x[1]['price'], reverse=True)
                
                for symbol, data in sorted_prices:
                    price = data['price']
                    high = data['high']
                    low = data['low']
                    price_range = high - low
                    
                    print(f"  {symbol:<12} ₹{price:>10.2f} ₹{high:>10.2f} ₹{low:>10.2f} ₹{price_range:>8.2f}")
                
                print(f"{'='*80}\n")
                avg_price = sum(p['price'] for p in prices.values()) / len(prices)
                print(f"  Total Stocks:   {len(prices)}")
                print(f"  Average Price:  ₹{avg_price:.2f}\n")
            else:
                print("❌ Could not fetch prices. Check your internet connection.")
        
        elif choice == "3":
            print("\n" + "="*65)
            print("CONTINUOUS MONITORING MODE")
            print("="*65)
            print(f"Stocks: {len(NIFTY_50_STOCKS)} NIFTY 50 stocks")
            print("Check interval: Every 60 seconds")
            print("Press Ctrl+C to stop\n")
            
            input("Press Enter to start monitoring...")
            
            monitor = LivePriceMonitor(NIFTY_50_STOCKS, check_interval=60)
            try:
                monitor.start_monitoring()
            except KeyboardInterrupt:
                print("\n\n❌ Monitoring stopped by user")
                logger.info("Monitoring stopped")
        
        elif choice != "0":
            print("❌ Invalid option. Returning to main menu...")
    
    except Exception as e:
        logger.error(f"Error in real-time tracker: {e}")
        print(f"✗ Error: {e}")


def main():
    """Main CLI Gatekeeper Loop"""
    print_banner()
    
    logger.info("="*65)
    logger.info(f"Terminal Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Configured Stocks: {len(NIFTY_50_STOCKS)} (NIFTY 50)")
    logger.info("="*65)
    
    while True:
        print_menu()
        
        choice = input("Enter your choice: ").strip()
        
        if choice == "1":
            mode_live_scanner()
        
        elif choice == "2":
            mode_backtest()
        
        elif choice == "3":
            mode_realtime_tracker()
        
        elif choice == "0":
            print("\n" + "="*65)
            print("Exiting Trading Terminal. Thank you!")
            print("="*65)
            logger.info("Trading Terminal Shutdown")
            break
        
        else:
            print("\n✗ Invalid option. Please select 0, 1, 2, or 3.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user.")
        logger.info("Program interrupted by user")
    except Exception as e:
        print(f"\n✗ Fatal Error: {e}")
        logger.error(f"Fatal Error: {e}", exc_info=True)
        sys.exit(1)