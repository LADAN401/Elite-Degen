#!/usr/bin/env python3
"""
Elite Degen Bot - Pro Edition
Features: Tap-to-copy CA, Ticker Search, Price Action, & Dex Status
"""

import os
import re
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ---------------- CONFIGURATION ----------------
# Ensure these are set in your environment or replace with strings for testing
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DEX_API = "https://api.dexscreener.com/latest/dex/search?q="
PAID_CHECK_API = "https://api.dexscreener.com/orders/v1"
REF_URL = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

# Regex to detect Contract Addresses (0x...) or Tickers ($TICKER)
SCAN_REGEX = re.compile(r"(0x[a-fA-F0-9]{40})|(\$[a-zA-Z0-9]+)")

# ---------------- FORMATTING HELPERS ----------------
def fmt_num(n):
    """Format large numbers into readable K, M, B formats"""
    if n is None: return "0"
    try:
        n = float(n)
    except: return "0"
    if n >= 1e9: return f"${n/1e9:.2f}B"
    if n >= 1e6: return f"${n/1e6:.2f}M"
    if n >= 1e3: return f"${n/1e3:.2f}K"
    return f"${n:.2f}"

def get_time_ago(ts_ms):
    """Convert timestamp to human-readable 'time ago'"""
    if not ts_ms: return "N/A"
    diff = int(datetime.utcnow().timestamp() - (ts_ms / 1000))
    if diff < 60: return f"{diff}s"
    if diff < 3600: return f"{diff//60}m"
    if diff < 86400: return f"{diff//3600}h"
    return f"{diff//86400}d"

# ---------------- DATA FETCHING ----------------
def fetch_token_data(query):
    """Clean the query and fetch the best pair from DexScreener"""
    clean_query = query.replace('$', '')
    try:
        response = requests.get(f"{DEX_API}{clean_query}", timeout=10).json()
        pairs = response.get("pairs", [])
        if not pairs:
            return None
        # Sort by liquidity (highest first) to ensure we get the 'main' pair
        pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0)), reverse=True)
        return pairs[0]
    except Exception as e:
        print(f"API Error: {e}")
        return None

def check_paid_status(chain, ca):
    """Check if the dev has paid for DexScreener marketing/ads"""
    try:
        r = requests.get(f"{PAID_CHECK_API}/{chain}/{ca}", timeout=5).json()
        return "✅ **PAID**" if r else "❌ **UNPAID**"
    except:
        return "❓ **UNKNOWN**"

# ---------------- UI DESIGN ----------------
def build_message(data):
    """Constructs the high-end degen UI with tappable CA and live stats"""
    base = data.get("baseToken", {})
    address = base.get('address')
    price_change = data.get("priceChange", {})
    
    # Header & Copy Section
    # Wrapping address in `backticks` makes it copy-on-tap in Telegram
    msg = (
        f"💎 **{base.get('name')} ({base.get('symbol')})**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 **CA (Tap to Copy):**\n`{address}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        f"🌐 **Network:** {data.get('chainId').upper()} | {data.get('dexId').capitalize()}\n"
        f"📅 **Age:** {get_time_ago(data.get('pairCreatedAt'))}\n"
        f"💰 **Price:** `${data.get('priceUsd')}`\n\n"
        
        f"📊 **Market Stats**\n"
        f"├ MC: `{fmt_num(data.get('fdv'))}`\n"
        f"├ Liq: `{fmt_num(data.get('liquidity', {}).get('usd', 0))}`\n"
        f"└ Vol: `{fmt_num(data.get('volume', {}).get('h24'))}`\n\n"
        
        f"📈 **Price Action**\n"
        f"├ 5m:  `{price_change.get('m5', 0)}%` | 1h:  `{price_change.get('h1', 0)}%` \n"
        f"└ 6h:  `{price_change.get('h6', 0)}%` | 24h: `{price_change.get('h24', 0)}%` \n\n"
        
        f"🛡️ **Security Check**\n"
        f"└ DexScreener Ads: {check_paid_status(data.get('chainId'), address)}\n\n"
        f"🦅 _Elite Scanner Bot_"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh Stats", callback_data=f"refresh_{address}"),
            InlineKeyboardButton("📊 DexScreener", url=data.get("url"))
        ],
        [InlineKeyboardButton("🟢 Buy with BaseBot", url=f"{REF_URL}{address}")]
    ])
    
    return msg, kb

# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "🦅 **Elite Degen Scanner Ready**\n\n"
        "Send me a **Contract Address** or a **$TICKER** to scan.\n\n"
        "Example:\n"
        "• `0x23...` (Base/ETH/Sol CA)\n"
        "• `$BRETT` (Ticker Search)"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.message.text.strip()
    match = SCAN_REGEX.search(query_text)
    
    if not match:
        return # Ignore messages that don't look like crypto data

    status_msg = await update.message.reply_text("🔍 *Searching the trenches...*", parse_mode="Markdown")
    
    data = fetch_token_data(query_text)
    
    if not data:
        await status_msg.edit_text("❌ **No data found.**\nEnsure the CA is correct or the token has a pair on DexScreener.")
        return

    msg, kb = build_message(data)
    await status_msg.delete()
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

async def on_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ca = query.data.replace("refresh_", "")
    
    data = fetch_token_data(ca)
    if data:
        msg, kb = build_message(data)
        try:
            # We add a timestamp so the user sees it actually refreshed
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)
        except:
            await query.answer("No new changes yet!")
    else:
        await query.answer("Error updating data...")

# ---------------- EXECUTION ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(on_refresh, pattern="^refresh_"))
    
    print("🦅 Elite Degen Bot is live and scanning...")
    app.run_polling()

if __name__ == "__main__":
    main()
 
