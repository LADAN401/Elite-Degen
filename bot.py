import os
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ANKR_RPC = os.getenv("ANKR_RPC")
DEXSCREENER_BASE_URL = os.getenv("DEXSCREENER_BASE_URL")
REFERRAL_LINK_BASE = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Elite Degen Bot is online! ✅ Send a Base token CA to scan.")

# Dex Paid checker
def get_dex_paid_status(token_address: str) -> str:
    try:
        url = f"{DEXSCREENER_BASE_URL}/orders/v1/base/{token_address}"
        r = requests.get(url, timeout=5)
        data = r.json()
        if "orders" in data and len(data["orders"]) > 0:
            ts = data["orders"][0].get("timestamp")
            if ts:
                paid_time = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                return f"Dex Paid 🟢 ({paid_time})"
        return "Dex Paid 🔴"
    except Exception:
        return "Dex Paid 🔴"

# Message handler for scanning
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("0x") and len(text) == 42:
        token_address = text.lower()
        dex_status = get_dex_paid_status(token_address)
        keyboard = [
            [InlineKeyboardButton("Buy with BaseBot", url=f"{REFERRAL_LINK_BASE}{token_address}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Scanned Token: {token_address}\n{dex_status}", reply_markup=reply_markup)

# Build application
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, scan))

print("Elite Degen Bot is online! ✅")
app.run_polling()
