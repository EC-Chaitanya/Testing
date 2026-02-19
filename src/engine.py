import pandas as pd
import pandas_ta as ta
import numpy as np
from src.logger import logger
# pd is available for use in this file

class ScoringEngine:
    @staticmethod
    # def calculate_full_score(df):
    #     # """
    #     # Master function used by the LiveScanner.
        
    #     # ⚠️ CRITICAL: Caller must ensure df has 20+ candles
    #     # This function assumes data is already validated
    #     # """
    #     # results = ScoringEngine.get_bullish_pullback_score(df)
    #     # return {
    #     #     'total_score': results['score'],
    #     #     'signal': results['signal'],
    #     #     'confidence': results['confidence'],
    #     #     'reasons': results['reasons']
    #     # }
    #     """
    #     Sirf sabse latest candle (current price) par focus karne ke liye update.
    #     """
    #     try:
    #         if df.empty or len(df) < 20:
    #             return {'score': 0, 'signal': False, 'confidence': 0, 'reasons': ['Insufficient data']}

    #         # Sabse aakhri (latest) candle ko select karein
    #         last = df.iloc[-1]
            
    #         score = 0
    #         reasons = []

    #         # 1. Latest SuperTrend Signal check karein
    #         if last.get('SuperTrend_Signal') == 1:
    #             score += 50
    #             reasons.append("SuperTrend (20,2) is Bullish ✅")
            
    #         # 2. Latest Price vs VWAP pullback check karein
    #         if 'VWAP' in last and last['Close'] < last['VWAP']:
    #             score += 50
    #             reasons.append(f"Price (${last['Close']:.2f}) is below VWAP (${last['VWAP']:.2f}) ✅")
            
    #         # Final Signal: Dono conditions abhi (latest candle mein) true honi chahiye
    #         signal = (score == 100)
            
    #         return {
    #             'total_score': score,
    #             'signal': signal,
    #             'confidence': score,
    #             'reasons': reasons
    #         }
    #     except Exception as e:
    #         return {'score': 0, 'signal': False, 'confidence': 0, 'reasons': [str(e)]}
    # src/engine.py ko update karein
    @staticmethod
    def calculate_full_score(df):
        try:
            if df.empty or len(df) < 30:
                return {'total_score': 0, 'signal': False, 'side': None, 'reasons': []}

            last = df.iloc[-1]
            score = 0
            reasons = []
            side = None

            # --- 🟢 BUY LOGIC (Price < VWAP) ---
            buy_score = 0
            # 1. SuperTrend Bullish
            if last.get('SuperTrend_Signal') == 1:
                buy_score += 35
                reasons.append("ST Bullish ✅")
            
            # 2. MACD Bullish Crossover (Pichle 5 candles)
            if any(df['MACD_Cross'].tail(4) == 1):
                buy_score += 30
                reasons.append("MACD Bullish ✅")
                
            # 3. Pullback Check: Price MUST be BELOW VWAP for Buy
            vwap_dist_pct = ((last['VWAP'] - last['Close']) / last['VWAP']) * 100
            if 0.3 <= vwap_dist_pct <= 2.0:
                buy_score += 35
                reasons.append("Price Below VWAP (Pullback) ✅")

            # --- 🔴 SELL LOGIC (Price > VWAP) ---
            sell_score = 0
            # 1. SuperTrend Bearish
            if last.get('SuperTrend_Signal') == -1:
                sell_score += 35
            
            # 2. MACD Bearish Crossover (Pichle 5 candles)
            if any(df['MACD_Cross'].tail(4) == -1):
                sell_score += 30
            
            # 3. Pullback Check: Price MUST be ABOVE VWAP for Sell
            sell_vwap_dist = ((last['Close'] - last['VWAP']) / last['VWAP']) * 100
            if 0.3 <= sell_vwap_dist <= 2.0:
                sell_score += 35

            # --- FINAL DECISION ---
            if buy_score >= 70:
                score = buy_score
                side = 'BUY'
            elif sell_score >= 70:
                score = sell_score
                side = 'SELL'
                reasons = ["Bearish Setup Confirmed ❌"] # Reasons updated for Sell
            
            # caluate stop loss and target 1:2
            stop_loss = round(float(last['SuperTrend']), 2)
            risk = abs(last['Close'] - stop_loss)
            target = round(float(last['Close'] + (risk * 2) if side == 'BUY' else last['Close'] - (risk * 2)), 2)

            return {
                'total_score': score,
                'signal': score >= 70, 
                'side': side,
                'reasons': reasons,
                'close': float(last['Close']),
                'stop_loss': stop_loss,
                'target_1_2': target
            }
        except Exception as e:
            return {'total_score': 0, 'signal': False, 'side': None, 'reasons': [str(e)]}

    @staticmethod
    def get_bullish_pullback_score(df_5m):
        """Calculate bullish pullback score."""
        score = 0
        reasons = []
        
        try:
            if df_5m.empty:
                return {'score': 0, 'signal': False, 'confidence': 0, 'reasons': ['Empty DataFrame']}
            
            last = df_5m.iloc[-1]
            
            # ✅ CRITICAL: Validate minimum data BEFORE any calculation
            MIN_CANDLES = 20
            if len(df_5m) < MIN_CANDLES:
                reasons.append(f"Insufficient data: {len(df_5m)}/{MIN_CANDLES} candles")
                return {
                    'score': 0,
                    'signal': False,
                    'confidence': 0,
                    'reasons': reasons
                }
            
            # ✅ Check all required columns exist and are not NaN
            required_cols = ['SuperTrend_Signal', 'VWAP', 'Close']
            missing = [col for col in required_cols if col not in df_5m.columns]
            
            if missing:
                reasons.append(f"Missing columns: {missing}")
                return {'score': 0, 'signal': False, 'confidence': 0, 'reasons': reasons}
            
            # ✅ Check for NaN in critical cells
            if pd.isna(last.get('SuperTrend_Signal')) or pd.isna(last.get('VWAP')):
                reasons.append("Indicators contain NaN (insufficient data for calculation)")
                return {'score': 0, 'signal': False, 'confidence': 0, 'reasons': reasons}
            
            # 1. SuperTrend (20, 2) Positive Signal Check
            if last.get('SuperTrend_Signal') == 1:
                score += 50
                reasons.append("SuperTrend (20,2) is Bullish ✅")
            else:
                reasons.append(f"SuperTrend signal: {last.get('SuperTrend_Signal')} (not bullish)")
            
            # 2. Current Price below VWAP (Pullback)
            if 'VWAP' in last and 'Close' in last and last['Close'] < last['VWAP']:
                score += 50
                reasons.append(f"Price (${last['Close']:.2f}) is below VWAP (${last['VWAP']:.2f}) ✅")
            else:
                vwap_val = last.get('VWAP', 0)
                close_val = last.get('Close', 0)
                reasons.append(f"Price ${close_val:.2f} >= VWAP ${vwap_val:.2f}")
            
            # Final Signal: Both conditions must match (Score = 100)
            signal = score == 100
            
            return {
                'score': score,
                'signal': signal,
                'confidence': score,
                'reasons': reasons
            }
        except Exception as e:
            logger.debug(f"Exception in get_bullish_pullback_score: {e}")
            return {'score': 0, 'signal': False, 'confidence': 0, 'reasons': [str(e)]}

    @staticmethod
    def get_dual_scores(df):
        """Required for compatibility with older scanner versions."""
        res = ScoringEngine.get_bullish_pullback_score(df)
        last = df.iloc[-1]
        return {
            'bullish': res['score'],
            'bearish': 0,
            'signal': res['signal'],
            'confidence': res['confidence'],
            'close': float(last['Close']),
            'rsi': float(last['RSI']) if 'RSI' in df.columns else None,
            'vwap': float(last['VWAP']) if 'VWAP' in df.columns else None
        }
    
