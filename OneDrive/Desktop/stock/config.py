
NIFTY_50_STOCKS = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN", "BHARTIARTL"]

# MSTCOK api using
API_KEY = "X4+gKPbsg2GLYXMLw5afn005kw86ldhx5xO+VZ6TVuk="

# Weighted Scoring Logic (Total 100)
WEIGHTS = {
    "trend": 30,      # Above/Below EMAs
    "momentum": 30,   # RSI and MACD
    "vwap": 20,       # Price vs VWAP
    "structure": 20   # Day High/Low position
}

THRESHOLD = 65  