import os
import re
import requests
from datetime import datetime, timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackContext

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN missing")
    exit(1)

# Regex for contract addresses (Ethereum style)
CA_REGEX = r"0x[a-fA-F0-9]{40}"

# DexScreener endpoints
DEX_API = "https://api.dexscreener.com"
TOKEN_INFO_ENDPOINT = "/tokens/v1/{chain}/{tokenAddress}"
TOKEN_BOOSTS_ENDPOINT = "/token-boosts/latest/v1"

# Referral link base
BASEBOT_REF = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

# Helper functions
def fetch_token_data(chain: str, ca: str):
    url = f"{DEX_API}/tokens/v1/{chain}/{ca}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if "pairs" in data:
            token = data.get("token", {})
            return token
        return None
    except:
        return None

def fetch_boost_status(ca: str):
    try:
        url = f"{DEX_API}/token-boosts/latest/v1"
        resp = requests.get(url, timeout=10).json()
        for token in resp.get("tokens", []):
            if token.get("address", "").lower() == ca.lower():
                paid = token.get("paid", False)
                timestamp = token.get("paidTimestamp")
                if paid and timestamp:
                    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    return f"🟢 Dex Paid ({dt.strftime('%H:%M UTC')})"
                elif paid:
                    return "🟢 Dex Paid"
                else:
                    return "🔴 Dex Paid"
        return "🔴 Dex Paid"
    except:
        return "🔴 Dex Paid"

def build_message(token, ca):
    # Default safe values
    name = token.get("name", "Unknown")
    symbol = token.get("symbol", "UNK")
    price = token.get("priceUsd", "0")
    mc = token.get("marketCap", "0")
    liquidity = token.get("liquidity", "0")
    holders = token.get("holdersCount", "N/A")
    boosts = token.get("boostCount", 0)
    volume = token.get("volume1h", 0)
    risk = "Low liquidity" if float(liquidity) > 1000 else "High risk"
    dex_paid = fetch_boost_status(ca)

    message = f"""
🦅 ELITE DEGEN SCAN

Token: {name} ({symbol})
Price: ${price}
MC: ${mc}
Liquidity: ${liquidity}
Holders: {holders}

{dex_paid}
🔥 Boosts: {boosts}
📈 Volume 1h: {volume}
⚠️ Risk: {risk}
"""
    return message

def build_buttons(ca):
    buttons = [
        [InlineKeyboardButton("📊 Chart", url=f"https://dexscreener.com/base/{ca}")],
        [InlineKeyboardButton("Buy with BaseBot", url=f"{BASEBOT_REF}{ca}")]
    ]
    return InlineKeyboardMarkup(buttons)

# Telegram handlers
async def handle_message(update: Update, context: CallbackContext.DEFAULT_TYPE):
    text = update.message.text
    matches = re.findall(CA_REGEX, text)
    if not matches:
        return
    chain = "base"  # default chain, can later detect dynamically
    for ca in matches:
        token = fetch_token_data(chain, ca)
        if not token:
            await update.message.reply_text(f"❌ Could not fetch token data for {ca}")
            continue
        message = build_message(token, ca)
        buttons = build_buttons(ca)
        await update.message.reply_text(message, reply_markup=buttons)

# Build and run bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🤖 Elite Degen 🦅 Bot is running...")
app.run_polling()
