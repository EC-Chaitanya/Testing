
NIFTY_50_STOCKS = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN", "BHARTIARTL"]

# Weighted Scoring Logic (Total 100)
WEIGHTS = {
    "trend": 30,      # Above/Below EMAs
    "momentum": 30,   # RSI and MACD
    "vwap": 20,       # Price vs VWAP
    "structure": 20   # Day High/Low position
}

THRESHOLD = 65  