"""
Utility Functions for Trading Terminal
- Output formatting
- Data validation
- Signal filtering
"""

import pandas as pd
from src.logger import logger

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False
    print("Note: tabulate not installed. Using basic formatting.")


class OutputFormatter:
    """Format scanner results for terminal display"""
    
    @staticmethod
    def display_dual_results(bullish_results, bearish_results, threshold=65):
        """
        Display side-by-side comparison of bullish and bearish candidates
        """
        print("\n" + "="*120)
        print(f"{'DUAL-DIRECTIONAL TRADING SIGNALS':^120}")
        print("="*120)
        
        # Split screen - Left for Bullish, Right for Bearish
        bull_df = pd.DataFrame(bullish_results)
        bear_df = pd.DataFrame(bearish_results)
        
        # Format bullish table
        if not bull_df.empty or not bear_df.empty:
            print(f"\n{'BULLISH SIGNALS (CALLS/CE)':^55} | {'BEARISH SIGNALS (PUTS/PE)':^60}")
            print("-" * 120)
            
            if HAS_TABULATE:
                bull_table = tabulate(
                    bull_df[['Symbol', 'bullish', 'rsi', 'close']].head(10) if not bull_df.empty else [],
                    headers=['Symbol', 'Score', 'RSI', 'LTP'],
                    tablefmt='grid',
                    floatfmt=".2f",
                    showindex=False
                )
                
                bear_table = tabulate(
                    bear_df[['Symbol', 'bearish', 'rsi', 'close']].head(10) if not bear_df.empty else [],
                    headers=['Symbol', 'Score', 'RSI', 'LTP'],
                    tablefmt='grid',
                    floatfmt=".2f",
                    showindex=False
                )
                
                # Print side by side
                bull_lines = bull_table.split('\n') if not bull_df.empty else []
                bear_lines = bear_table.split('\n') if not bear_df.empty else []
                
                max_lines = max(len(bull_lines), len(bear_lines))
                
                for i in range(max_lines):
                    bull_line = bull_lines[i] if i < len(bull_lines) else ""
                    bear_line = bear_lines[i] if i < len(bear_lines) else ""
                    print(f"{bull_line:<58} | {bear_line}")
            else:
                # Basic formatting without tabulate
                if not bull_df.empty:
                    for idx, row in bull_df.head(10).iterrows():
                        print(f"  {row['Symbol']:<10} {row['bullish']:>5.0f}  {row['rsi']:>6.1f}  {row['close']:>8.2f}")
        else:
            print("\nNo bullish or bearish signals meeting threshold.")
        
        print("\n" + "="*120)
    
    @staticmethod
    def display_scan_summary(results, scan_type="Live Scan"):
        """Display summary statistics of the scan"""
        print(f"\n{scan_type} Summary:")
        print("-" * 60)
        
        if results:
            bullish = [r for r in results if r['bullish'] >= 65]
            bearish = [r for r in results if r['bearish'] >= 65]
            
            print(f"Total Stocks Analyzed: {len(results)}")
            print(f"Bullish Signals (≥65): {len(bullish)}")
            print(f"Bearish Signals (≥65): {len(bearish)}")
            print(f"Neutral (both <65):    {len(results) - len(bullish) - len(bearish)}")
        else:
            print("No results available.")
    
    @staticmethod
    def format_signal_row(symbol, bullish_score, bearish_score, metrics):
        """Format a single signal row"""
        rsi = metrics.get('rsi', 0)
        close = metrics.get('close', 0)
        
        return {
            'Symbol': symbol,
            'Bullish': f"{bullish_score}/100",
            'Bearish': f"{bearish_score}/100",
            'RSI': f"{rsi:.1f}" if rsi else "N/A",
            'Close': f"{close:.2f}"
        }


class SignalFilter:
    """Filter and validate trading signals"""
    
    @staticmethod
    def filter_by_threshold(results, threshold=65):
        """Filter results above threshold"""
        bullish = [r for r in results if r['bullish'] >= threshold]
        bearish = [r for r in results if r['bearish'] >= threshold]
        return bullish, bearish
    
    @staticmethod
    def rank_by_score(results, direction='bullish'):
        """Sort results by score descending"""
        return sorted(results, key=lambda x: x[direction], reverse=True)


class DataValidator:
    """Validate data quality before scoring"""
    
    @staticmethod
    def validate_dataframe(df):
        """Check if DataFrame has required columns"""
        required = ['Close', 'High', 'Low', 'Volume', 'EMA_20', 'EMA_50', 'RSI', 'VWAP']
        missing = [col for col in required if col not in df.columns]
        return len(missing) == 0, missing
    
    @staticmethod
    def has_valid_data(df):
        """Check if DataFrame has sufficient valid data"""
        if df.empty or len(df) < 20:
            return False
        return True
