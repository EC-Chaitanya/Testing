import yfinance as yf
import pandas as pd

df = yf.download('RELIANCE.NS', start='2025-10-16', end='2026-01-14', progress=False)
print("DataFrame type:", type(df))
print("Columns:", df.columns.tolist())
print("Column names detailed:")
for col in df.columns:
    print(f"  {repr(col)}")
print("\nFirst row:")
print(df.iloc[0])
print("\nData types:")
print(df.dtypes)
print("\nIndex type:", type(df.index))
print("Index name:", df.index.name)
