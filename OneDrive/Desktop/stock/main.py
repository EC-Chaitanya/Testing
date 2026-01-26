"""
NIFTY 50 Dual-Directional Trading Terminal
CLI Gatekeeper for Live Scanner and Historical Backtest Modes
"""

import sys
from datetime import datetime

from src.logger import logger
from src.live_scanner import LiveScanner
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
        
        elif choice == "0":
            print("\n" + "="*65)
            print("Exiting Trading Terminal. Thank you!")
            print("="*65)
            logger.info("Trading Terminal Shutdown")
            break
        
        else:
            print("\n✗ Invalid option. Please select 0 or 1.")
        
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