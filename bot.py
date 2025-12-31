
import os
import requests
from datetime import datetime
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALCHEMY_API = os.getenv("ALCHEMY_API")
ANKR_RPC = os.getenv("ANKR_RPC")
ETHERSCAN_API = os.getenv("ETHERSCAN_API")
DEXSCREENER_BASE_URL = os.getenv("DEXSCREENER_BASE_URL")

# Referral BaseBot link
REFERRAL_LINK_BASE = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

# Initialize bot
bot = Bot(BOT_TOKEN)
updater = Updater(BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

def get_dex_paid_status(token_address: str):
    """
    Check Dex Paid status via DexScreener orders endpoint.
    Returns string with green/red circle and timestamp if available.
    """
    try:
        url = f"{DEXSCREENER_BASE_URL}/orders/v1/base/{token_address}"
        r = requests.get(url)
        data = r.json()
        if "orders" in data and len(data["orders"]) > 0:
            last_paid_ts = data["orders"][0].get("timestamp")
            if last_paid_ts:
                paid_time = datetime.utcfromtimestamp(last_paid_ts).strftime("%Y-%m-%d %H:%M:%S")
                return f"Dex Paid 🟢 ({paid_time})"
        return "Dex Paid 🔴"
    except Exception:
        return "Dex Paid 🔴"

def scan(update: Update, context: CallbackContext):
    text = update.message.text
    if text.startswith("0x") and len(text) == 42:  # Simple CA detection
        token_address = text.lower()
        dex_status = get_dex_paid_status(token_address)

        # Create "Buy with BaseBot" button
        keyboard = [
            [InlineKeyboardButton("Buy with BaseBot", url=f"{REFERRAL_LINK_BASE}{token_address}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Reply with details
        update.message.reply_text(
            f"Scanned Token: {token_address}\n{dex_status}",
            reply_markup=reply_markup
        )

# Add message handler
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, scan))

# Start polling
updater.start_polling()
updater.idle()
