# src/engine.py
import pandas as pd
import pandas_ta as ta

class ScoringEngine:
    """
    Dual-Directional Scoring Engine for NIFTY 50 Quant Scanner
    Calculates both Bullish (CE) and Bearish (PE) signals
    """
    
    @staticmethod
    def get_bullish_score(df):
        """
        Calculate Bullish Score (CE/Call Direction)
        - Trend: Price > EMA20 & EMA50 (30 pts)
        - Momentum: RSI 55-70 (30 pts)
        - VWAP: Price > VWAP (20 pts)
        - Exhaustion Penalty: RSI > 75 (-20 pts)
        """
        score = 0
        last = df.iloc[-1]
        
        try:
            # 1. Trend (30 pts) - Price above both EMAs
            if pd.notna(last['Close']) and pd.notna(last['EMA_20']) and pd.notna(last['EMA_50']):
                if last['Close'] > last['EMA_20'] and last['Close'] > last['EMA_50']:
                    score += 30
                
            # 2. Momentum (30 pts) - Optimal RSI zone
            if pd.notna(last['RSI']):
                if 55 <= last['RSI'] <= 70:
                    score += 30
                # Exhaustion penalty - overbought
                elif last['RSI'] > 75: 
                    score -= 20
                
            # 3. VWAP (20 pts) - Price above volume-weighted average
            if pd.notna(last['Close']) and pd.notna(last['VWAP']):
                if last['Close'] > last['VWAP']:
                    score += 20
            
            return max(0, score)
        except Exception as e:
            return 0
    
    @staticmethod
    def get_bearish_score(df):
        """
        Calculate Bearish Score (PE/Put Direction) - Mirror of Bullish
        - Trend: Price < EMA20 & EMA50 (30 pts)
        - Momentum: RSI 30-45 (30 pts)
        - VWAP: Price < VWAP (20 pts)
        - Exhaustion Penalty: RSI < 25 (-20 pts)
        """
        score = 0
        last = df.iloc[-1]
        
        try:
            # 1. Trend (30 pts) - Price below both EMAs
            if pd.notna(last['Close']) and pd.notna(last['EMA_20']) and pd.notna(last['EMA_50']):
                if last['Close'] < last['EMA_20'] and last['Close'] < last['EMA_50']:
                    score += 30
                
            # 2. Momentum (30 pts) - Optimal RSI zone for bearish
            if pd.notna(last['RSI']):
                if 30 <= last['RSI'] <= 45:
                    score += 30
                # Exhaustion penalty - oversold
                elif last['RSI'] < 25:
                    score -= 20
                
            # 3. VWAP (20 pts) - Price below volume-weighted average
            if pd.notna(last['Close']) and pd.notna(last['VWAP']):
                if last['Close'] < last['VWAP']:
                    score += 20
            
            return max(0, score)
        except Exception as e:
            return 0
    
    @staticmethod
    def get_dual_scores(df):
        """
        Calculate both Bullish and Bearish scores simultaneously
        Returns: (bullish_score, bearish_score, last_close, rsi, ema20, ema50, vwap)
        """
        bullish = ScoringEngine.get_bullish_score(df)
        bearish = ScoringEngine.get_bearish_score(df)
        
        try:
            last = df.iloc[-1]
            return {
                'bullish': bullish,
                'bearish': bearish,
                'close': float(last['Close']),
                'rsi': float(last['RSI']) if pd.notna(last['RSI']) else None,
                'ema20': float(last['EMA_20']) if pd.notna(last['EMA_20']) else None,
                'ema50': float(last['EMA_50']) if pd.notna(last['EMA_50']) else None,
                'vwap': float(last['VWAP']) if pd.notna(last['VWAP']) else None
            }
        except Exception as e:
            return None