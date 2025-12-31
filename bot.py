#!/usr/bin/env python3
"""
Elite Degen Bot - Accurate Dex Paid Scanner
Ready for Bothost deployment
"""

import os
import re
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ---------------- VARIABLES ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DEX_API = os.environ.get("DEXSCREENER_BASE_URL", "https://api.dexscreener.com")
REF_URL = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

# Detect token contract addresses
CA_REGEX = re.compile(r"0x[a-fA-F0-9]{40}")

# ---------------- HELPERS ----------------
def fmt(n):
    """Format numbers to 1.5K, 1.5M, 1.5B"""
    try:
        n = float(n)
    except:
        return "0"
    for unit in ["", "K", "M", "B"]:
        if abs(n) < 1000:
            return f"{n:.1f}{unit}"
        n /= 1000
    return f"{n:.1f}T"

def ago(ts_ms):
    """Convert timestamp to human-readable 'Xh ago' format"""
    seconds = int(datetime.utcnow().timestamp()*1000 - ts_ms) / 1000
    if seconds < 3600:
        return f"{int(seconds/60)}m"
    if seconds < 86400:
        return f"{int(seconds/3600)}h"
    return f"{int(seconds/86400)}d"

# ---------------- DEX FUNCTIONS ----------------
def get_token_data(ca):
    """Fetch token info from DexScreener API"""
    try:
        r = requests.get(f"{DEX_API}/latest/dex/search?q={ca}", timeout=10).json()
        pairs = r.get("pairs", [])
        if not pairs:
            return None
        # Pick pair with highest liquidity
        pairs.sort(key=lambda x: x.get("liquidity", {}).get("usd", 0), reverse=True)
        return pairs[0]
    except:
        return None

def dex_paid_status(chain, ca):
    """Check if token has paid for DexScreener listing"""
    try:
        r = requests.get(f"{DEX_API}/orders/v1/{chain}/{ca}", timeout=10).json()
        if isinstance(r, list) and len(r) > 0:
            ts = r[0].get("createdAt")
            return f"🟢 Dex Paid ({ago(ts)} ago)" if ts else "🟢 Dex Paid"
    except:
        pass
    return "🔴 Dex Not Paid"

# ---------------- BOT HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🦅 Elite Degen Bot Online\nSend any Base token contract address to scan.")

async def scan_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    ca_match = CA_REGEX.search(text)
    if not ca_match:
        await update.message.reply_text("❌ Invalid contract address. Please send a valid 0x... Base token CA.")
        return
    ca = ca_match.group(0)

    token_data = get_token_data(ca)
    if not token_data:
        await update.message.reply_text("❌ Token not found on DexScreener")
        return

    chain = token_data.get("chainId", "base")
    dex = token_data.get("dexId", "unknown")
    token = token_data.get("baseToken", {})
    name = token.get("name", "")
    symbol = token.get("symbol", "")
    price = token_data.get("priceUsd", 0)
    mc = token_data.get("fdv", 0)
    vol = token_data.get("volume", {}).get("h24", 0)
    lp = token_data.get("liquidity", {}).get("usd", 0)
    holders = token_data.get("holders", 0)
    created = token_data.get("pairCreatedAt", int(datetime.utcnow().timestamp()*1000))

    paid_status = dex_paid_status(chain, ca)

    msg = (
        f"🔵 {name} (${symbol})\n"
        f"├ {ca}\n"
        f"└ #{chain.upper()} ({dex}) | 🌱 {ago(created)} | 👁️ {holders}\n\n"
        f"📊 Stats\n"
        f" ├ USD   ${price}\n"
        f" ├ MC    {fmt(mc)}\n"
        f" ├ Vol   {fmt(vol)}\n"
        f" ├ LP    {fmt(lp)}\n\n"
        f"🔒 Security\n"
        f" ├ {paid_status}\n\n"
        f"🦅 Elite Degen Scanner"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"r|{ca}"),
            InlineKeyboardButton("🟢 Buy with BaseBot", url=f"{REF_URL}{ca}")
        ]
    ])

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ca = query.data.split("|")[1]
    token_data = get_token_data(ca)
    if not token_data:
        await query.edit_message_text("❌ Token not found on DexScreener")
        return

    chain = token_data.get("chainId", "base")
    dex = token_data.get("dexId", "unknown")
    token = token_data.get("baseToken", {})
    name = token.get("name", "")
    symbol = token.get("symbol", "")
    price = token_data.get("priceUsd", 0)
    mc = token_data.get("fdv", 0)
    vol = token_data.get("volume", {}).get("h24", 0)
    lp = token_data.get("liquidity", {}).get("usd", 0)
    holders = token_data.get("holders", 0)
    created = token_data.get("pairCreatedAt", int(datetime.utcnow().timestamp()*1000))

    paid_status = dex_paid_status(chain, ca)

    msg = (
        f"🔵 {name} (${symbol})\n"
        f"├ {ca}\n"
        f"└ #{chain.upper()} ({dex}) | 🌱 {ago(created)} | 👁️ {holders}\n\n"
        f"📊 Stats\n"
        f" ├ USD   ${price}\n"
        f" ├ MC    {fmt(mc)}\n"
        f" ├ Vol   {fmt(vol)}\n"
        f" ├ LP    {fmt(lp)}\n\n"
        f"🔒 Security\n"
        f" ├ {paid_status}\n\n"
        f"🦅 Elite Degen Scanner"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"r|{ca}"),
            InlineKeyboardButton("🟢 Buy with BaseBot", url=f"{REF_URL}{ca}")
        ]
    ])

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, scan_token))
    app.add_handler(CallbackQueryHandler(refresh, pattern="^r\\|"))
    print("🦅 Elite Degen Bot Running")
    app.run_polling()

if __name__ == "__main__":
    main() 
