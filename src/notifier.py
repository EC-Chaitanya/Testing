# import requests
# from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

# def send_telegram_msg(stock_name, price, stoploss):
#     """
#     Sends a formatted buy alert to your Telegram.
#     """
#     emoji = "🟢" if side == 'BUY' else "🔴"
#     action = "BULLISH" if side == 'BUY' else "BEARISH"
    
#     message = (
#         f"{emoji} *{action} SIGNAL ALERT*\n\n"
#         f"📈 *Stock:* {stock_name}\n"
#         f"💰 *Entry:* ₹{price:.2f}\n"
#         f"🛡️ *SL:* ₹{stoploss:.2f}\n"
#         f"🎯 *Target (1:2):* ₹{target:.2f}\n"
#         f"📊 *Logic:* Strategy 100% Matched"
#     )
#     # message = (
#     #     f"🚀 *BULLISH PULLBACK ALERT*\n\n"
#     #     f"📈 *Stock:* {stock_name}\n"
#     #     f"💰 *Entry Price:* ₹{price}\n"
#     #     f"🛡️ *Stop-Loss:* ₹{stoploss}\n"
#     #     f"📊 *Signal:* STRATEGY MATCHED"
#     # )
    
#     url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
#     payload = {
#         "chat_id": TELEGRAM_CHAT_ID,
#         "text": message,
#         "parse_mode": "Markdown"
#     }
    
#     try:
#         response = requests.post(url, data=payload)
#         if response.status_code == 200:
#             print(f"✅ Alert sent for {stock_name}")
#         else:
#             print(f"❌ Failed to send alert: {response.text}")
#     except Exception as e:
#         print(f"⚠️ Notifier Error: {e}")
import requests
from src.logger import logger
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_msg(stock_name, price, stoploss, target, side='BUY'):
    """
    Final fixed notifier to handle Target and Side arguments.
    """
    try:
        # Side ke basis par emoji aur label set karein
        emoji = "🟢" if side == 'BUY' else "🔴"
        action = "BULLISH" if side == 'BUY' else "BEARISH"
        
        # Message template aapki strategy ke mutabiq
        message = (
            f"{emoji} *{action} SIGNAL ALERT*\n\n"
            f"📈 *Stock:* {stock_name}\n"
            f"💰 *Entry:* ₹{price:.2f}\n"
            f"🛡️ *Stop-Loss:* ₹{stoploss:.2f}\n"
            f"🎯 *Target (1:2):* ₹{target:.2f}\n\n"
            f"📊 *Strategy:* ST + VWAP Balanced Match"
        )
        
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            logger.error(f"Telegram API Error: {response.text}")
            
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")