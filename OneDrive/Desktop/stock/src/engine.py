# src/engine.py
"""
Professional Trading Engine for NIFTY 50 Pullback-in-Uptrend Strategy
Based on institutional trading principles with proper multi-timeframe confirmation
"""
import pandas as pd
import pandas_ta as ta
import numpy as np
from src.logger import logger


class TradingSignal:
    """Represents a complete trading signal with rules"""
    def __init__(self, symbol, signal_type, entry_price, stop_loss, target, 
                 risk_reward_ratio, confidence, reasons):
        self.symbol = symbol
        self.signal_type = signal_type  # 'BUY' or 'SELL'
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.target = target
        self.risk = abs(entry_price - stop_loss)
        self.reward = abs(target - entry_price)
        self.risk_reward_ratio = risk_reward_ratio
        self.confidence = confidence  # 0-100%
        self.reasons = reasons  # List of confirmation reasons


class ScoringEngine:
    """
    Professional Pullback-in-Uptrend Trading Engine
    Multi-timeframe confirmation with volume & reversal validation
    """
    
    @staticmethod
    def is_reversal_candle(df, lookback=3):
        """
        Detect reversal candles indicating end of pullback
        
        Patterns:
        1. Hammer: Long lower wick, small body
        2. Lower low with higher close: Bottoming pattern
        3. Volume spike on reversal
        
        Args:
            df: OHLCV DataFrame
            lookback: Number of candles to check for pattern
        
        Returns:
            Boolean: True if reversal pattern detected
        """
        try:
            if len(df) < lookback + 1:
                return False
            
            current = df.iloc[-1]
            prev_rows = df.iloc[-(lookback+1):-1]
            
            # Pattern 1: Hammer/Reversal candle
            body_size = abs(current['Close'] - current['Open'])
            lower_wick = current['Open'] - current['Low'] if current['Open'] > current['Close'] else current['Close'] - current['Low']
            
            # Hammer: wick is 2x+ body size
            if lower_wick > body_size * 2:
                return True
            
            # Pattern 2: Lower low but higher close than previous candle
            prev_low = prev_rows['Low'].min()
            if current['Low'] < prev_low and current['Close'] > current['Open']:
                return True
            
            # Pattern 3: Higher close than previous with strong body
            if current['Close'] > prev_rows['Close'].iloc[-1]:
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error detecting reversal candle: {e}")
            return False
    
    @staticmethod
    def is_volume_confirming(df, multiplier=1.5):
        """
        Check if volume confirms the reversal/pullback
        
        Requirements:
        - Current volume > 80% of 20-candle average
        - Volume spike on reversal (> 1.5x average)
        
        Args:
            df: OHLCV DataFrame
            multiplier: Volume spike multiplier (default: 1.5x average)
        
        Returns:
            Boolean: True if volume confirms move
        """
        try:
            if len(df) < 20:
                return True  # Can't validate, assume ok
            
            current_vol = df.iloc[-1]['Volume']
            avg_vol_20 = df.iloc[-20:-1]['Volume'].mean()
            
            # Volume must be meaningful (> 80% of average)
            if current_vol < avg_vol_20 * 0.8:
                return False  # Low volume = not confirmed
            
            # For reversal, prefer volume spike (> 1.5x average)
            return current_vol > avg_vol_20 * multiplier
            
        except Exception as e:
            logger.warning(f"Error checking volume confirmation: {e}")
            return True  # Fail open if error


    @staticmethod
    def check_multi_timeframe_filter(df_1h=None, df_daily=None, signal_type='BUY'):
        """
        Filter signals against bigger timeframe trends
        
        Rules:
        - Only take BUY signals if 1-hour trend is BULLISH
        - Only take BUY signals if daily price > 50-EMA (not deep downtrend)
        
        Args:
            df_1h: 1-hour DataFrame with SuperTrend_Signal
            df_daily: Daily DataFrame with EMA_50
            signal_type: 'BUY' or 'SELL'
        
        Returns:
            Tuple: (is_valid, reason)
        """
        try:
            if signal_type == 'BUY':
                # Check 1-hour trend
                if df_1h is not None and len(df_1h) > 0:
                    if 'SuperTrend_Signal' in df_1h.columns:
                        if df_1h.iloc[-1]['SuperTrend_Signal'] != 1:  # Not bullish
                            return False, "1-hour trend not bullish"
                
                # Check daily trend
                if df_daily is not None and len(df_daily) > 0:
                    if 'EMA_50' in df_daily.columns:
                        daily_close = df_daily.iloc[-1]['Close']
                        daily_ema50 = df_daily.iloc[-1]['EMA_50']
                        if daily_close < daily_ema50:  # Price below 50-EMA = downtrend
                            return False, "Daily trend bearish (price below 50-EMA)"
            
            return True, "Multi-timeframe filter OK"
            
        except Exception as e:
            logger.warning(f"Error in multi-timeframe filter: {e}")
            return True, "Filter check skipped due to error"
    
    @staticmethod
    def calculate_trade_rules(entry_price, pullback_low, recent_high, signal_type='BUY'):
        """
        Calculate professional stop loss and profit targets
        
        Stop Loss:
        - BUY: Below pullback low (with buffer)
        - SELL: Above pullback high (with buffer)
        
        Profit Target:
        - Use 1:2 or 1:3 risk/reward ratio
        
        Args:
            entry_price: Actual entry price
            pullback_low: Lowest point in pullback
            recent_high: Recent resistance/previous high
            signal_type: 'BUY' or 'SELL'
        
        Returns:
            Dict: {stop_loss, target_1, target_2, risk, reward, risk_reward}
        """
        try:
            if signal_type == 'BUY':
                stop_loss = pullback_low - 0.5  # 0.5 point buffer below low
                risk = entry_price - stop_loss
                
                # Target 1: 1:2 risk/reward
                target_1 = entry_price + (risk * 2)
                
                # Target 2: Previous high or 1:3 risk/reward (whichever is closer)
                target_2 = max(recent_high, entry_price + (risk * 3))
                
                reward = target_1 - entry_price
                risk_reward = reward / risk if risk > 0 else 0
                
            else:  # SELL
                stop_loss = pullback_low + 0.5  # 0.5 point buffer above high
                risk = stop_loss - entry_price
                
                target_1 = entry_price - (risk * 2)
                target_2 = min(recent_high, entry_price - (risk * 3))
                
                reward = entry_price - target_1
                risk_reward = reward / risk if risk > 0 else 0
            
            return {
                'stop_loss': round(stop_loss, 2),
                'target_1': round(target_1, 2),
                'target_2': round(target_2, 2),
                'risk': round(risk, 2),
                'reward': round(reward, 2),
                'risk_reward_ratio': round(risk_reward, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating trade rules: {e}")
            return None
    
    @staticmethod
    def get_bullish_pullback_score(df_5m, df_1h=None):
        """
        CORRECTED: Calculate score for PULLBACK-IN-UPTREND strategy (not momentum chase)
        
        Professional Rules:
        1. 1-hour SuperTrend must be BULLISH (trend confirmation) ✓
        2. 5-min price must be BELOW VWAP (pullback) ✓
        3. 5-min shows reversal candle ✓
        4. Volume confirms reversal ✓
        
        Returns:
            Dict with signal, confidence, and trade rules
        """
        score = 0
        reasons = []
        
        try:
            if df_5m.empty or len(df_5m) < 20:
                return {'score': 0, 'signal': False, 'confidence': 0, 'reasons': ['Insufficient data']}
            
            last_5m = df_5m.iloc[-1]
            
            # 1. TREND CONFIRMATION (1-hour SuperTrend bullish) - PRIMARY FILTER
            # Note: If df_1h not provided, we use 5m SuperTrend as fallback
            trend_ok = False
            if df_1h is not None and len(df_1h) > 0:
                if 'SuperTrend_Signal' in df_1h.columns:
                    if df_1h.iloc[-1]['SuperTrend_Signal'] == 1:
                        score += 30
                        reasons.append("1-hour SuperTrend bullish")
                        trend_ok = True
            else:
                # Fallback: Use 5-min with careful interpretation
                if 'SuperTrend_Signal' in df_5m.columns and last_5m['SuperTrend_Signal'] == 1:
                    score += 20  # Lower confidence without 1-hour confirmation
                    reasons.append("5-min SuperTrend bullish (no 1-hour data)")
                    trend_ok = True
            
            if not trend_ok:
                return {'score': 0, 'signal': False, 'confidence': 0, 
                       'reasons': ['Trend not bullish - primary filter failed']}
            
            # 2. PULLBACK DETECTION (Price below VWAP) - SECONDARY FILTER
            pullback_ok = False
            if pd.notna(last_5m['Close']) and pd.notna(last_5m['VWAP']):
                if last_5m['Close'] < last_5m['VWAP']:
                    score += 25
                    reasons.append(f"Price below VWAP (${last_5m['Close']:.2f} < ${last_5m['VWAP']:.2f})")
                    pullback_ok = True
            
            if not pullback_ok:
                return {'score': score, 'signal': False, 'confidence': score/100*100, 
                       'reasons': reasons + ['Price not below VWAP - no pullback detected']}
            
            # 3. REVERSAL CONFIRMATION (Candle pattern + volume)
            if ScoringEngine.is_reversal_candle(df_5m):
                score += 20
                reasons.append("Reversal candle detected (hammer/bottoming pattern)")
            else:
                score -= 10  # Penalty: no confirmation yet
                reasons.append("No reversal candle - still in pullback phase")
            
            # 4. VOLUME CONFIRMATION
            if ScoringEngine.is_volume_confirming(df_5m):
                score += 15
                reasons.append("Volume confirms reversal")
            else:
                score -= 5
                reasons.append("Volume not confirming (low volume pullback)")
            
            # 5. RSI CHECK (Not overbought)
            if pd.notna(last_5m['RSI']):
                if last_5m['RSI'] < 75:  # Not overbought
                    score += 5
                    reasons.append("RSI not overbought")
                else:
                    score -= 10
                    reasons.append("RSI overbought - caution advised")
            
            # Calculate confidence (score as percentage)
            confidence = min(100, max(0, score))  # Clamp 0-100
            
            # Signal threshold: Need at least 60 points for HIGH confidence signal
            signal = score >= 60
            
            return {
                'score': score,
                'signal': signal,
                'confidence': confidence,
                'reasons': reasons
            }
            
        except Exception as e:
            logger.error(f"Error calculating bullish pullback score: {e}")
            return {'score': 0, 'signal': False, 'confidence': 0, 'reasons': [f'Error: {str(e)}']}
    
    @staticmethod
    
    @staticmethod
    def get_dual_scores(df):
        """
        Calculate both Bullish and Bearish scores simultaneously
        Returns: (bullish_score, bearish_score, last_close, rsi, ema20, ema50, vwap)
        """
        bullish = ScoringEngine.get_bullish_pullback_score(df)
        
        try:
            last = df.iloc[-1]
            return {
                'bullish': bullish['score'],
                'bearish': 0,  # Deprecated
                'signal': bullish['signal'],
                'confidence': bullish['confidence'],
                'close': float(last['Close']),
                'rsi': float(last['RSI']) if pd.notna(last['RSI']) else None,
                'ema20': float(last['EMA_20']) if pd.notna(last['EMA_20']) else None,
                'ema50': float(last['EMA_50']) if pd.notna(last['EMA_50']) else None,
                'vwap': float(last['VWAP']) if pd.notna(last['VWAP']) else None,
                'reasons': bullish['reasons']
            }
        except Exception as e:
            logger.error(f"Error in get_dual_scores: {e}")
            return None