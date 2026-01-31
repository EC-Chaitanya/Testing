# import sys
# from datetime import datetime
# from src.logger import logger
# from src.live_scanner import LiveScanner
# from src.auth import get_session  # We import your new login logic
# import config

# def print_banner():
#     banner = """
#     ╔═══════════════════════════════════════════════════════════════╗
#     ║     NIFTY 50 DUAL-DIRECTIONAL TRADING TERMINAL v2.0          ║
#     ║          LIVE M-STOCK API + QUANT SYSTEM                     ║
#     ╚═══════════════════════════════════════════════════════════════╝
#     """
#     print(banner)

# def print_menu():
#     print("\n" + "="*65)
#     print(f"{'MAIN MENU':^65}")
#     print("="*65)
#     print("\nSelect Operating Mode:\n")
#     print("  [1] LIVE SCANNER MODE (mStock Live Data)")
#     print("  [2] CONTINUOUS SCANNER MODE (mStock Live Data)")
#     print("  [0] EXIT")
#     print("\n" + "="*65)

# def main():
#     print_banner()
    
#     # STEP 1: Beginner-Friendly Login Check
#     print("Connecting to mStock Servers...")
#     session = get_session(config.API_KEY, config.USER_ID, config.PASSWORD, config.DOB)
    
#     if not session:
#         print("❌ Login Failed. Please check your config.py and try again.")
#         sys.exit(1)
        
#     logger.info(f"Terminal Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
#     # STEP 2: Your Original Menu Loop
#     while True:
#         print_menu()
#         choice = input("Enter your choice: ").strip()
        
#         if choice == "1":
#             # We pass the 'session' to the scanner so it can fetch live data
#             try:
#                 scanner = LiveScanner(session=session, threshold=config.THRESHOLD)
#                 scanner.run_single_scan()
#             except Exception as e:
#                 logger.error(f"Error in scanner: {e}")
        
#         elif choice == "0":
#             print("\nExiting Terminal. Goodbye!")
#             break
#         else:
#             print("\n✗ Invalid option.")
            
#         input("\nPress Enter to continue...")

# if __name__ == "__main__":
#     try:
#         main()
#     except KeyboardInterrupt:
#         print("\nProgram stopped by user.")     
import sys
import os
from datetime import datetime
from src.logger import logger
from src.live_scanner import LiveScanner
from src.auth import get_session 
import config

def print_banner():
    """Displays a professional terminal header."""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║     NIFTY 50 DUAL-DIRECTIONAL TRADING TERMINAL v2.0          ║
    ║          LIVE M-STOCK API + QUANT SYSTEM                     ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_menu():
    """Displays the operating mode options."""
    print("\n" + "="*65)
    print(f"{'MAIN MENU':^65}")
    print("="*65)
    print("\nSelect Operating Mode:\n")
    print("  [1] ONE-TIME SCAN (Manual check of all 50 stocks)")
    print("  [2] CONTINUOUS SCANNER (Automated refresh every 5 mins)")
    print("  [0] EXIT")
    print("\n" + "="*65)

def main():
    print_banner()
    
    # STEP 1: Establish API Connection
    print("Connecting to mStock Servers...")
    # This triggers the login and asks for your SMS OTP in the terminal
    session = get_session(
        config.API_KEY, 
        config.USER_ID, 
        config.PASSWORD, 
        config.DOB
    )
    
    if not session:
        print("❌ Login Failed. Please check your credentials in config.py.")
        sys.exit(1)
        
    logger.info(f"Terminal Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀 Connection Active! Ready to scan NIFTY 50.")

    # Initialize the scanner with the authorized session
    scanner = LiveScanner(session=session, threshold=config.THRESHOLD)
    
    # STEP 2: Main Operational Loop
    while True:
        print_menu()
        choice = input("Enter your choice: ").strip()
        
        if choice == "1":
            try:
                # Runs the scan once and returns to menu
                scanner.run_single_scan()
                input("\nScan Complete. Press Enter to return to menu...")
            except Exception as e:
                logger.error(f"Error in manual scan: {e}")
                print(f"⚠️ Scan failed: {e}")
        
        elif choice == "2":
            try:
                # Starts the infinite loop (5-minute intervals)
                # You can stop this by pressing Ctrl+C
               scanner.start_continuous_scanning(interval_minutes=5)
            except Exception as e:
                logger.error(f"Error in continuous mode: {e}")
                print(f"⚠️ Continuous scanner stopped: {e}")

        elif choice == "0":
            print("\nExiting Terminal. Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 0.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Process interrupted by user. Closing...")
        sys.exit(0)