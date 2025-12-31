#!/usr/bin/env python3
"""
Elite Degen Token Scanner Bot - Base token only
"""

import os
import re
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------- CONFIG ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DEXSCREENER_API = os.environ.get("DEXSCREENER_BASE_URL", "https://api.dexscreener.com")
REF_BASEBOT = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")

# ---------------- HELPERS ----------------
def format_number(n):
    try:
        n = float(n)
    except:
        return str(n)
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    elif n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    else:
        return str(n)

def get_token_profile(token_address_or_symbol):
    """
    Fetch token profile from DexScreener
    """
    # If user sends ticker ($EXAMPLE), search for it
    if token_address_or_symbol.startswith("$"):
        symbol = token_address_or_symbol[1:]
        search_url = f"{DEXSCREENER_API}/latest/dex/search?query={symbol}"
        try:
            resp = requests.get(search_url, timeout=10)
            data = resp.json()
            pairs = data.get("pairs", [])
            if not pairs:
                return None
            token_address = pairs[0].get("baseToken", {}).get("address")
        except:
            return None
    else:
        token_address = token_address_or_symbol

    try:
        url = f"{DEXSCREENER_API}/tokens/v1/base/{token_address}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data
    except Exception as e:
        logger.error(f"DexScreener fetch error: {e}")
        return None

def get_dex_paid_status(token_address):
    try:
        url = f"{DEXSCREENER_API}/orders/v1/base/{token_address}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        for order in data.get("orders", []):
            if order.get("paid"):
                return "🟢 Paid"
        return "🔴 Not Paid"
    except:
        return "❌ API Error"

# ---------------- TELEGRAM HANDLERS ----------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦅 Elite Degen Token Scanner!\n"
        "Use /scan <CA or $SYMBOL> to get token info."
    )

async def scan_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip().split()
    if len(msg) < 2:
        return await update.message.reply_text("Usage: /scan <CA or $SYMBOL>")

    token_input = msg[1]
    info = get_token_profile(token_input)
    if not info:
        return await update.message.reply_text("❌ Token not found on DexScreener.")

    pair = info.get("pairs", [{}])[0]
    base_token = pair.get("baseToken", {})
    name = base_token.get("name", "Unknown")
    symbol = base_token.get("symbol", "UNK")
    token_address = base_token.get("address")
    price = base_token.get("priceUsd", 0)
    mc = base_token.get("marketCap", 0)
    liquidity = base_token.get("liquidity", 0)
    holders = base_token.get("holders", 0)
    boosts = pair.get("boosts", 0)
    banner = info.get("banner")

    dex_paid = get_dex_paid_status(token_address)

    text = ""
    if banner:
        text += f"{banner}\n"
    text += f"🦅 ELITE DEGEN SCAN\n"
    text += f"{name} ({symbol})\n"
    text += f"Contract: `{token_address}`\n"
    text += f"Price: ${float(price):.8f}\nMC: {format_number(mc)}\nLiquidity: {format_number(liquidity)}\nHolders: {format_number(holders)}\n"
    text += f"Boosts: {boosts}\n"
    text += f"{dex_paid}\n"

    # Show social links if present
    socials = info.get("socials", [])
    if socials:
        text += "Socials:\n"
        for s in socials:
            text += f"• {s.get('type')}: {s.get('url')}\n"

    # Button
    keyboard = [[InlineKeyboardButton("Buy with BaseBot", url=REF_BASEBOT + token_address)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

# ---------------- MAIN ----------------
async def main_async():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_token))
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main_async()) 
