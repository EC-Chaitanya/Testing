"""
Debug script to test the parsing logic with real API response structure
"""
import pandas as pd
import json

# Simulate the real M.Stock API response structure based on the error message
# Available: ['instrument_token', 'last_price', 'ohlc']
api_response_structure = {
    'status': 'success',
    'data': {
        'NSE:RELIANCE': {
            'instrument_token': '2885',
            'last_price': 2500.50,
            'ohlc': {
                'o': 2490.00,
                'h': 2510.00,
                'l': 2485.00,
                'c': 2500.50,
                'v': 5000000,
            },
            'ts': 1706424871  # timestamp
        }
    }
}

# Test if it's a dict with these keys
stock_data = api_response_structure['data']['NSE:RELIANCE']
print(f"stock_data type: {type(stock_data)}")
print(f"stock_data keys: {list(stock_data.keys())}")
print(f"stock_data: {stock_data}")

# Check conditions
print(f"\n'instrument_token' in stock_data: {'instrument_token' in stock_data}")
print(f"'ohlc' in stock_data: {'ohlc' in stock_data}")

# Try the parsing logic
if isinstance(stock_data, dict):
    if 'instrument_token' in stock_data and 'ohlc' in stock_data:
        print("\n✓ Detected as single quote format")
        ohlc = stock_data.get('ohlc', {})
        record = {
            'Open': ohlc.get('o') or ohlc.get('open'),
            'High': ohlc.get('h') or ohlc.get('high'),
            'Low': ohlc.get('l') or ohlc.get('low'),
            'Close': ohlc.get('c') or ohlc.get('close'),
            'Volume': stock_data.get('volume') or ohlc.get('v'),
            'Time': stock_data.get('ts') or stock_data.get('timestamp'),
        }
        print(f"Extracted record: {record}")
        
        df = pd.DataFrame([record])
        print(f"\nDataFrame columns: {list(df.columns)}")
        print(f"DataFrame shape: {df.shape}")
        print(f"DataFrame:\n{df}")
