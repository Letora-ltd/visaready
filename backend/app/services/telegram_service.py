import requests
import logging
from ..core.config import settings

def send_telegram_message(chat_id: str, message: str):
    """
    Sends a message to a Telegram chat via the Bot API.
    """
    if not settings.telegram_bot_token:
        logging.warning("TELEGRAM_BOT_TOKEN not set. Skipping message.")
        return False
    
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")
        return False

def setup_webhook(webhook_url: str):
    """
    Registers the webhook URL with Telegram.
    """
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"
    try:
        resp = requests.post(url, json={"url": webhook_url})
        return resp.json()
    except Exception as e:
        logging.error(f"Failed to set Telegram webhook: {e}")
        return None
