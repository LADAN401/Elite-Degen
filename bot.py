#!/usr/bin/env python3
"""
Elite Degen Bot - Pro Edition (2025)
- Real-time Dex Paid Status via DexScreener Orders API
- Tappable CA for instant copying
- Multi-chain support with specific emojis
- Ticker search ($EXAMPLE) support
"""

import os
import re
import requests
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ---------------- CONFIGURATION ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DEX_SEARCH_API = "https://api.dexscreener.com/latest/dex/search?q="
DEX_ORDERS_API = "https://api.dexscreener.com/orders/v1"
REF_URL = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

# Regex for CA (0x...) or Ticker ($TICKER)
SCAN_REGEX = re.compile(r"(0x[a-fA-F0-9]{40})|(\$[a-zA-Z0-9]+)")

# ---------------- FORMATTING HELPERS ----------------
def fmt_num(n):
    if n is None: return "0"
    try:
        n = float(n)
    except: return "0"
    if n >= 1e9: return f"${n/1e9:.2f}B"
    if n >= 1e6: return f"${n/1e6:.2f}M"
    if n >= 1e3: return f"${n/1e3:.2f}K"
    return f"${n:.2f}"

def get_ago(ts_ms):
    """Human readable time from milliseconds timestamp"""
    if not ts_ms: return None
    now = datetime.now(timezone.utc).timestamp()
    diff = int(now - (ts_ms / 1000))
    if diff < 60: return f"{diff}s"
    if diff < 3600: return f"{diff//60}m"
    if diff < 86400: return f"{diff//3600}h"
    return f"{diff//86400}d"

def get_chain_emoji(chain_id):
    """Maps chain IDs to your specific requested emojis"""
    mapping = {
        "base": "🔵",
        "ethereum": "🔷",
        "bsc": "🔶",
        "solana": "💊"
    }
    return mapping.get(chain_id.lower(), "🌐")

# ---------------- DATA FETCHING ----------------
def fetch_token_data(query):
    clean_query = query.replace('$', '')
    try:
        r = requests.get(f"{DEX_SEARCH_API}{clean_query}", timeout=10).json()
        pairs = r.get("pairs", [])
        if not pairs: return None
        # Primary pair = highest liquidity
        pairs.sort(key=lambda x: float(x.get("liquidity", {}).get("usd", 0)), reverse=True)
        return pairs[0]
    except Exception:
        return None

def check_dex_paid(chain, ca):
    """Fetches real order data from DexScreener to check if paid"""
    try:
        # Endpoint: /orders/v1/{chainId}/{tokenAddress}
        url = f"{DEX_ORDERS_API}/{chain}/{ca}"
        r = requests.get(url, timeout=5).json()
        
        # If the API returns a list of orders
        if isinstance(r, list) and len(r) > 0:
            # Get the most recent payment timestamp
            latest_order = r[0]
            payment_ts = latest_order.get("paymentTimestamp") or latest_order.get("createdAt")
            time_ago = get_ago(payment_ts)
            return f"Dex paid 🟢 ({time_ago} ago)" if time_ago else "Dex paid 🟢"
    except Exception as e:
        print(f"Order API error: {e}")
        
    return "Dex not paid 🔴"

# ---------------- UI BUILDER ----------------
def build_ui(data):
    base = data.get("baseToken", {})
    chain = data.get("chainId", "unknown")
    ca = base.get("address", "N/A")
    price_change = data.get("priceChange", {})
    
    emoji = get_chain_emoji(chain)
    paid_status = check_dex_paid(chain, ca)
    
    # Message Construction
    msg = (
        f"{emoji} **{base.get('name')} (${base.get('symbol')})**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📑 **Tap to Copy CA:**\n`{ca}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        f"💰 **Price:** `${data.get('priceUsd', '0')}`\n"
        f"💎 **MC:** `{fmt_num(data.get('fdv'))}`\n"
        f"💦 **Liq:** `{fmt_num(data.get('liquidity', {}).get('usd', 0))}`\n\n"
        
        f"📊 **Price Action**\n"
        f"├ 5m: `{price_change.get('m5', 0)}%` | 1h: `{price_change.get('h1', 0)}%` \n"
        f"└ 6h: `{price_change.get('h6', 0)}%` | 24h: `{price_change.get('h24', 0)}%` \n\n"
        
        f"📢 **Marketing**\n"
        f"└ {paid_status}\n\n"
        f"🦅 _Elite Degen Scanner_"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{ca}"),
            InlineKeyboardButton("📊 Chart", url=data.get("url"))
        ],
        [InlineKeyboardButton("🟢 Buy on BaseBot", url=f"{REF_URL}{ca}")]
    ])
    
    return msg, kb

# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦅 **Elite Degen Bot**\n\nSend a **Contract Address** or **$TICKER** to scan.\n"
        "Supports: 🔷 ETH, 🔵 Base, 🔶 BSC, 💊 SOL",
        parse_mode="Markdown"
    )

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = SCAN_REGEX.search(text)
    if not match: return

    load_msg = await update.message.reply_text("🔍 *Scanning Blockchain...*", parse_mode="Markdown")
    
    data = fetch_token_data(text)
    if not data:
        await load_msg.edit_text("❌ Token not found on DexScreener.")
        return

    msg, kb = build_ui(data)
    await load_msg.delete()
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

async def handle_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ca = query.data.split("_")[1]
    
    data = fetch_token_data(ca)
    if data:
        msg, kb = build_ui(data)
        try:
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=kb)
        except:
            await query.answer("No changes yet.")
    else:
        await query.answer("Error fetching data.")

# ---------------- MAIN ----------------
def main():
    if not BOT_TOKEN:
        print("Set BOT_TOKEN environment variable!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, scan))
    app.add_handler(CallbackQueryHandler(handle_refresh, pattern="^refresh_"))
    
    print("🦅 Bot online...")
    app.run_polling()

if __name__ == "__main__":
    main()
 
