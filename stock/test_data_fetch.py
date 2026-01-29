"""
Quick test to verify DataFetcher is working
"""
import sys
import pandas as pd
from datetime import datetime, timedelta
from src.logger import logger

# Mock session class to test without authentication
class MockSession:
    def get_historical(self, segment, security_id, interval, from_date, to_date):
        """Mock get_historical that returns realistic data"""
        print(f"✓ get_historical called with interval={interval}, dates={from_date} to {to_date}")
        
        # Return mock historical data
        dates = pd.date_range(start=from_date, end=to_date, freq='5min')
        # Filter to market hours only (09:15 to 15:30 IST)
        dates = [d for d in dates if 9 <= d.hour < 16]
        
        if len(dates) == 0:
            # If no market hours, at least return some test data
            base_date = pd.to_datetime(from_date)
            dates = [base_date + timedelta(minutes=5*i) for i in range(1, 25)]
        
        data = {
            security_id: [
                {
                    'o': 2500.0 + i*5,
                    'h': 2505.0 + i*5,
                    'l': 2495.0 + i*5,
                    'c': 2502.0 + i*5,
                    'v': 1000000 + i*100000,
                    'ts': int(d.timestamp())
                }
                for i, d in enumerate(dates)
            ]
        }
        
        response = MockResponse({'status': 'success', 'data': data})
        return response

class MockResponse:
    def __init__(self, data):
        self.data = data
    
    def json(self):
        return self.data

def test_data_fetcher():
    """Test that DataFetcher properly fetches 20+ candles"""
    print("=" * 60)
    print("Testing DataFetcher with mock M.Stock session")
    print("=" * 60)
    
    try:
        from src.data_fethcer import DataFetcher
        
        # Create mock session
        mock_session = MockSession()
        
        # Initialize DataFetcher with mock session
        data_fetcher = DataFetcher(provider='mstock', session=mock_session)
        print(f"✓ DataFetcher initialized")
        
        # Fetch 5-minute data
        df = data_fetcher.fetch_5min_data('RELIANCE', lookback_days=5)
        
        print(f"\n✓ DataFetcher returned {len(df)} candles")
        print(f"  Columns: {list(df.columns)}")
        
        if len(df) >= 20:
            print(f"\n✅ SUCCESS: Got {len(df)} candles (required: 20+)")
            print(f"   First candle: {df.index[0]} - Close: {df['Close'].iloc[0]:.2f}")
            print(f"   Last candle:  {df.index[-1]} - Close: {df['Close'].iloc[-1]:.2f}")
            return True
        else:
            print(f"\n❌ FAILED: Only got {len(df)} candles (required: 20+)")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_data_fetcher()
    sys.exit(0 if success else 1)
