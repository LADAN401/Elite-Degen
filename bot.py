import os, requests, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEX = "https://api.dexscreener.com"
REF = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

def k(v): 
    return "0" if not v else f"${v/1_000:.1f}K" if v >= 1_000 else f"${v:.2f}"

def risk(lp):
    return "Low liquidity" if lp < 50_000 else "Healthy"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🦅 Elite Degen Scanner\nSend token CA")

async def scan_ca(ca, send):
    r = requests.get(f"{DEX}/tokens/v1/base/{ca}", timeout=10).json()
    if not r:
        await send("❌ Token not found on Base")
        return

    p = r[0]
    name = p["baseToken"]["name"]
    sym = p["baseToken"]["symbol"]
    price = p.get("priceUsd", "0")
    lp = p.get("liquidity", {}).get("usd", 0)
    mc = p.get("fdv", 0)
    vol = p.get("volume", {}).get("h24", 0)
    vol1h = p.get("priceChange", {}).get("h1", 0)
    boosts = p.get("boosts", 0)

    paid = "🔴"
    try:
        if requests.get(f"{DEX}/orders/v1/base/{ca}", timeout=5).json():
            paid = "🟢"
    except:
        pass

    msg = (
        f"🔵 *{name}* (${sym})\n"
        f"├ `{ca}`\n"
        f"└ #Base | Uniswap\n\n"
        f"📊 *Stats*\n"
        f" ├ USD   ${price}\n"
        f" ├ MC    {k(mc)}\n"
        f" ├ Vol   {k(vol)}\n"
        f" ├ LP    {k(lp)}\n"
        f" └ 1H    {vol1h}%\n\n"
        f"🚀 *Activity*\n"
        f" ├ 🔥 Boosts   {boosts}\n"
        f" └ {paid} Dex Paid\n\n"
        f"⚠️ *Risk*\n"
        f" └ {risk(lp)}\n\n"
        f"🦅 Elite Degen Scanner"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"r|{ca}"),
            InlineKeyboardButton("🟢 Buy with BaseBot", url=f"{REF}{ca}")
        ]
    ])

    await send(msg, kb)

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ca = update.message.text.strip()
    if ca.startswith("0x") and len(ca) == 42:
        await scan_ca(ca, lambda m, k=None: update.message.reply_text(m, parse_mode="Markdown", reply_markup=k))

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ca = q.data.split("|")[1]
    await scan_ca(ca, lambda m, k=None: q.edit_message_text(m, parse_mode="Markdown", reply_markup=k))

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
app.add_handler(CallbackQueryHandler(refresh, pattern="^r\\|"))

print("🦅 Elite Degen LIVE")
app.run_polling() 
