import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_msg(stock_name, price, stoploss):
    """
    Sends a formatted buy alert to your Telegram.
    """
    message = (
        f"🚀 *BULLISH PULLBACK ALERT*\n\n"
        f"📈 *Stock:* {stock_name}\n"
        f"💰 *Entry Price:* ₹{price}\n"
        f"🛡️ *Stop-Loss:* ₹{stoploss}\n"
        f"📊 *Signal:* STRATEGY MATCHED"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print(f"✅ Alert sent for {stock_name}")
        else:
            print(f"❌ Failed to send alert: {response.text}")
    except Exception as e:
        print(f"⚠️ Notifier Error: {e}")