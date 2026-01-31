from src.auth import get_session
import config
from datetime import datetime, timedelta

session = get_session(config.API_KEY, config.USER_ID, config.PASSWORD, config.DOB)

# Test 1: Try get_historical
try:
    end = datetime.now()
    start = end - timedelta(days=5)
    
    response = session.get_historical(
        segment='E',
        security_id='RELIANCE',
        interval='5',
        from_date=start.strftime('%Y-%m-%d'),
        to_date=end.strftime('%Y-%m-%d')
    )
    
    data = response.json() if hasattr(response, 'json') else response
    print("get_historical response:", data)
    
except Exception as e:
    print("get_historical ERROR:", str(e))

# Test 2: Try get_ohlc (this should work)
try:
    response = session.get_ohlc(ohlc_input=["NSE:RELIANCE"])
    data = response.json() if hasattr(response, 'json') else response
    print("\nget_ohlc response:", data)
    
except Exception as e:
    print("get_ohlc ERROR:", str(e))