import os, time, requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEX = "https://api.dexscreener.com"
REF = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

# ---------- HELPERS ----------

def fmt(n):
    if not n: return "0"
    n = float(n)
    for unit in ["", "K", "M", "B"]:
        if abs(n) < 1000:
            return f"{n:.1f}{unit}"
        n /= 1000
    return f"{n:.1f}T"

def ago(ms):
    diff = int(time.time() - ms / 1000)
    if diff < 3600: return f"{diff//60}m"
    if diff < 86400: return f"{diff//3600}h"
    return f"{diff//86400}d"

# ---------- CORE ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🦅 Elite Degen Scanner\nSend token CA")

async def scan(ca, send):
    pairs = requests.get(f"{DEX}/tokens/v1/base/{ca}", timeout=10).json()
    if not pairs:
        await send("❌ Token not found on Base")
        return

    p = pairs[0]
    name = p["baseToken"]["name"]
    sym = p["baseToken"]["symbol"]
    price = p.get("priceUsd", 0)
    mc = p.get("fdv", 0)
    vol = p.get("volume", {}).get("h24", 0)
    lp = p.get("liquidity", {}).get("usd", 0)
    ch1h = p.get("priceChange", {}).get("h1", 0)
    created = p.get("pairCreatedAt", int(time.time() * 1000))

    # Dex Paid
    paid = "🔴 Dex Not Paid"
    try:
        orders = requests.get(f"{DEX}/orders/v1/base/{ca}", timeout=5).json()
        if orders:
            paid = f"🟢 Dex Paid ({ago(orders[0]['createdAt'])} ago)"
    except:
        pass

    # Banner
    banner = ""
    try:
        prof = requests.get(f"{DEX}/token-profiles/latest/v1", timeout=5).json()
        for x in prof:
            if x.get("tokenAddress", "").lower() == ca.lower():
                banner = x.get("headerImage", "")
                break
    except:
        pass

    text = (
        f"🔵 *{name}* (${sym})\n"
        f"├ `{ca}`\n"
        f"└ #Base | Uniswap | 🌱 {ago(created)}\n\n"
        f"📊 *Stats*\n"
        f" ├ USD   ${price}\n"
        f" ├ MC    {fmt(mc)}\n"
        f" ├ Vol   {fmt(vol)}\n"
        f" ├ LP    {fmt(lp)}\n"
        f" └ 1H    {ch1h}%\n\n"
        f"{paid}\n\n"
        f"🦅 Elite Degen Scanner"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"r|{ca}"),
            InlineKeyboardButton("🟢 Buy with BaseBot", url=f"{REF}{ca}")
        ]
    ])

    if banner:
        await send(banner)
    await send(text, kb)

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ca = update.message.text.strip()
    if ca.startswith("0x") and len(ca) == 42:
        await scan(ca, lambda m, k=None: update.message.reply_text(
            m, parse_mode="Markdown", reply_markup=k
        ))

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ca = q.data.split("|")[1]
    await scan(ca, lambda m, k=None: q.edit_message_text(
        m, parse_mode="Markdown", reply_markup=k
    ))

# ---------- RUN ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
app.add_handler(CallbackQueryHandler(refresh, pattern="^r\\|"))

print("🦅 Elite Degen LIVE")
app.run_polling()
