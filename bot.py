#!/usr/bin/env python3
"""
Elite Degen Bot - Token Scanner + Wallet Tracker
Features:
1. Token scanning with DexScreener data
2. Dex Paid status, social links, banners
3. Wallet tracking with instant alerts
4. BaseBot referral link integration
Deployment ready for Bothost
"""

import os
import re
import json
import asyncio
import logging
from datetime import datetime
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)
from websockets import connect

# -------------------- CONFIG --------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ALCHEMY_WS = os.environ.get("ALCHEMY_API")  # wss://base-mainnet.g.alchemy.com/v2/KEY
DEXSCREENER_API = os.environ.get("DEXSCREENER_BASE_URL", "https://api.dexscreener.com")
REF_BASEBOT = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Regex patterns
WALLET_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")
TOKEN_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")

# In-memory storage
tracked_wallets = {}  # { user_id: [ {"address": "...", "nickname": "..."} ] }

# -------------------- HELPERS --------------------
def format_number(n):
    """Convert numbers to 1.5K / 2.3M / 1.2B style"""
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

def get_dexscreener_token_info(token_address):
    """Fetch token info from DexScreener"""
    try:
        url = f"{DEXSCREENER_API}/tokens/v1/base/{token_address}"
        resp = requests.get(url, timeout=10)
        return resp.json()
    except Exception as e:
        logger.error(f"DexScreener token fetch error: {e}")
        return {}

def get_dex_paid_status(token_address):
    """Check Dex paid orders"""
    try:
        url = f"{DEXSCREENER_API}/orders/v1/base/{token_address}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        # Check if any order shows paid
        for order in data.get("orders", []):
            if order.get("paid"):
                ts = order.get("timestamp")
                if ts:
                    dt = datetime.fromtimestamp(ts / 1000)
                    return f"🟢 Paid ({dt.strftime('%Y-%m-%d %H:%M:%S UTC')})"
                return "🟢 Paid"
        return "🔴 Not Paid"
    except:
        return "❌ API Error"

# -------------------- TELEGRAM HANDLERS --------------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦅 Elite Degen Bot Online!\n"
        "Commands:\n"
        "/scan <token_address> - Scan token\n"
        "/add <wallet> <nickname> - Track wallet\n"
        "/remove <wallet> - Stop tracking\n"
        "/list - List tracked wallets"
    )

async def scan_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan token and show info"""
    msg = update.message.text.strip().split()
    if len(msg) < 2:
        return await update.message.reply_text("Usage: /scan <token_address>")

    token_address = msg[1].lower()
    if not TOKEN_REGEX.match(token_address):
        return await update.message.reply_text("❌ Invalid token address")

    info = get_dexscreener_token_info(token_address)
    pair = info.get("pairs", [{}])[0]
    base_token = pair.get("baseToken", {})
    name = base_token.get("name", "Unknown")
    symbol = base_token.get("symbol", "UNK")
    price = base_token.get("priceUsd", 0)
    mc = base_token.get("marketCap", 0)
    liquidity = base_token.get("liquidity", 0)
    holders = base_token.get("holders", 0)
    banner = info.get("banner")

    dex_paid = get_dex_paid_status(token_address)

    # Format message
    text = ""
    if banner:
        text += f"{banner}\n"
    text += f"🦅 ELITE DEGEN SCAN\n"
    text += f"Token: {name} ({symbol})\n"
    text += f"Price: ${float(price):.8f}\n"
    text += f"MC: {format_number(mc)}\nLiquidity: {format_number(liquidity)}\nHolders: {format_number(holders)}\n"
    text += f"{dex_paid}\n"

    # Inline button
    keyboard = [[InlineKeyboardButton("Buy with BaseBot", url=REF_BASEBOT + token_address)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def add_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add wallet to tracking"""
    msg = update.message.text.strip().split()
    if len(msg) < 2:
        return await update.message.reply_text("Usage: /add <wallet> <nickname>")

    wallet = msg[1].lower()
    nickname = " ".join(msg[2:]) if len(msg) > 2 else wallet[:6]

    if not WALLET_REGEX.match(wallet):
        return await update.message.reply_text("❌ Invalid Base wallet address.")

    uid = update.message.from_user.id
    tracked_wallets.setdefault(uid, [])

    for w in tracked_wallets[uid]:
        if w["address"] == wallet:
            return await update.message.reply_text("Wallet already tracked.")

    tracked_wallets[uid].append({"address": wallet, "nickname": nickname})
    await update.message.reply_text(f"✅ Now tracking {wallet} as {nickname}")

async def remove_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip().split()
    if len(msg) < 2:
        return await update.message.reply_text("Usage: /remove <wallet>")
    wallet = msg[1].lower()
    uid = update.message.from_user.id
    if uid in tracked_wallets:
        tracked_wallets[uid] = [w for w in tracked_wallets[uid] if w["address"] != wallet]
        await update.message.reply_text(f"Removed {wallet} from tracking.")

async def list_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if uid not in tracked_wallets or not tracked_wallets[uid]:
        return await update.message.reply_text("No wallets tracked.")
    msg = "Tracked wallets:\n"
    for w in tracked_wallets[uid]:
        msg += f"• {w['nickname']}: {w['address']}\n"
    await update.message.reply_text(msg)

# -------------------- WEBSOCKET LISTENER --------------------
async def alchemy_listener(application):
    """Listen to all pending transactions on Base via Alchemy WS"""
    subscribe_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "alchemy_pendingTransactions",
        "params": [{}]
    }

    async with connect(ALCHEMY_WS) as ws:
        logger.info("Connected to Alchemy WebSocket")
        await ws.send(json.dumps(subscribe_payload))

        async for message in ws:
            try:
                data = json.loads(message)
                tx = data.get("params", {}).get("result")
                if not tx:
                    continue

                frm = tx.get("from", "").lower()
                to = tx.get("to", "").lower()

                for uid, wallets in tracked_wallets.items():
                    for w in wallets:
                        addr = w["address"]
                        if frm == addr or to == addr:
                            await send_wallet_alert(application, uid, tx, w)

            except Exception as e:
                logger.error(f"WS parse error: {e}")

async def send_wallet_alert(application, user_id, tx, wallet_obj):
    """Format and send wallet transaction alert"""
    tx_hash = tx.get("hash")
    frm = tx.get("from")
    to = tx.get("to")

    msg = (
        f"#{wallet_obj['nickname']}\n"
        f"🟢 New Tx detected!\n"
        f"Tx: {tx_hash}\nFrom: {frm}\nTo: {to}\n"
        f"View: https://base.etherscan.io/tx/{tx_hash}"
    )

    try:
        await application.bot.send_message(chat_id=user_id, text=msg)
    except Exception as e:
        logger.error(f"Failed to send wallet alert: {e}")

# -------------------- MAIN --------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("scan", scan_token))
    app.add_handler(CommandHandler("add", add_wallet))
    app.add_handler(CommandHandler("remove", remove_wallet))
    app.add_handler(CommandHandler("list", list_wallets))

    # Run WebSocket listener in background
    asyncio.get_event_loop().create_task(alchemy_listener(app))

    # Start bot
    logger.info("Elite Degen Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
