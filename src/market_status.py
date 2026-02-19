"""
Market Status Checks for NSE Trading
Prevents trading outside market hours, weekends, and holidays
"""

from datetime import datetime, date, time
import pytz
from src.logger import logger

IST = pytz.timezone('Asia/Kolkata')

# NSE Market Hours (strict IST)
NSE_OPEN_TIME = time(9, 15)    # 09:15 IST
NSE_CLOSE_TIME = time(15, 30)  # 15:30 IST

# NSE Holidays 2026 (Update quarterly)
NSE_HOLIDAYS = {
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 8),    # Mahashivratri
    date(2026, 3, 29),   # Holi
    date(2026, 4, 2),    # Good Friday
    date(2026, 8, 15),   # Independence Day
    date(2026, 8, 21),   # Janmashtami
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 11, 1),   # Diwali (estimated)
    date(2026, 12, 25),  # Christmas
}


def is_market_hours() -> bool:
    """
    Check if NSE is currently open (9:15-15:30 IST)
    
    Returns:
        bool: True if trading hours, False otherwise
    """
    now = datetime.now(IST)
    current_time = now.time()
    
    # Must be weekday (Mon-Fri = 0-4)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    
    # Must be within market hours
    return NSE_OPEN_TIME <= current_time <= NSE_CLOSE_TIME


def is_trading_day(check_date: date = None) -> bool:
    """
    Check if date is a trading day (not weekend or holiday)
    
    Args:
        check_date: Date to check (default: today)
    
    Returns:
        bool: True if trading day, False if weekend/holiday
    """
    if check_date is None:
        check_date = datetime.now(IST).date()
    
    # Skip weekends
    if check_date.weekday() >= 5:
        return False
    
    # Skip holidays
    if check_date in NSE_HOLIDAYS:
        return False
    
    return True


def can_scan_now() -> tuple:
    """
    Complete gate: Can we run a scan right now?
    
    Returns:
        tuple: (bool: can_scan, str: reason)
    """
    now = datetime.now(IST)
    
    # Check if trading day
    if not is_trading_day(now.date()):
        reason = f"Not a trading day ({now.strftime('%A, %b %d')})"
        return False, reason
    
    # Check if market hours
    if not is_market_hours():
        current_time = now.strftime('%H:%M:%S')
        return False, f"Outside market hours: {current_time} (need 9:15-15:30 IST)"
    
    return True, "Market is open and trading"


def next_trading_day() -> date:
    """Get next trading day after today"""
    check_date = datetime.now(IST).date()
    
    while True:
        check_date = date(check_date.year, check_date.month, check_date.day + 1)
        if is_trading_day(check_date):
            return check_date


def time_to_market_open() -> int:
    """
    Get seconds until market opens
    
    Returns:
        int: Seconds until 9:15 AM IST
    """
    now = datetime.now(IST)
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    
    if now.time() < NSE_OPEN_TIME:
        # Market hasn't opened yet today
        delta = (market_open - now).total_seconds()
        return max(0, int(delta))
    else:
        # Market already closed today, open tomorrow
        tomorrow = now.date()
        if is_trading_day(tomorrow):
            market_open_tomorrow = datetime.combine(tomorrow, NSE_OPEN_TIME)
            market_open_tomorrow = IST.localize(market_open_tomorrow)
            delta = (market_open_tomorrow - now).total_seconds()
            return max(0, int(delta))
        else:
            # Tomorrow is not trading day, find next trading day
            next_day = next_trading_day()
            market_open_next = datetime.combine(next_day, NSE_OPEN_TIME)
            market_open_next = IST.localize(market_open_next)
            delta = (market_open_next - now).total_seconds()
            return max(0, int(delta))
