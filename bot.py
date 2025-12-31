import os
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

ALCHEMY_API = os.getenv("ALCHEMY_API")
ANKR_RPC = os.getenv("ANKR_RPC")
ETHERSCAN_API = os.getenv("ETHERSCAN_API")

DEX = "https://api.dexscreener.com"
REF = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

# -------- HELPERS --------

def short_usd(val):
    if not val:
        return "0"
    if val >= 1_000_000:
        return f"${val/1_000_000:.1f}M"
    if val >= 1_000:
        return f"${val/1_000:.1f}k"
    return f"${val:.2f}"

def risk_level(liq):
    if liq < 10_000:
        return "High risk"
    if liq < 50_000:
        return "Low liquidity"
    return "Healthy"

# -------- COMMANDS --------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🦅 *Elite Degen Scanner*\n\n"
        "Send a token CA to scan.\n"
        "Fast • Brutal • Onchain",
        parse_mode="Markdown"
    )

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ca = update.message.text.strip()

    if not (ca.startswith("0x") and len(ca) == 42):
        return

    try:
        # Base chain scan
        r = requests.get(f"{DEX}/tokens/v1/base/{ca}", timeout=10)
        pairs = r.json()

        if not pairs:
            await update.message.reply_text("❌ Token not found on Base.")
            return

        p = pairs[0]

        name = p["baseToken"]["name"]
        symbol = p["baseToken"]["symbol"]
        price = p.get("priceUsd", "0")
        liq = p.get("liquidity", {}).get("usd", 0)
        mc = p.get("fdv", 0)

        vol1h = p.get("volume", {}).get("h1", 0)
        vol_prev = p.get("volume", {}).get("h6", 0)
        vol_change = "+∞%" if vol_prev == 0 else f"+{int((vol1h/vol_prev)*100)}%"

        # Dex Paid check
        paid = False
        try:
            paid_check = requests.get(
                f"{DEX}/orders/v1/base/{ca}", timeout=5
            ).json()
            if paid_check:
                paid = True
        except:
            pass

        boosts = p.get("boosts", 0)

        text = (
            f"🦅 *ELITE DEGEN SCAN*\n\n"
            f"*Token:* {name} ({symbol})\n"
            f"*Price:* ${price}\n"
            f"*MC:* {short_usd(mc)}\n"
            f"*Liquidity:* {short_usd(liq)}\n\n"
            f"{'🟢 Dex Paid' if paid else '🔴 Dex Not Paid'}\n"
            f"🔥 *Boosts:* {boosts}\n"
            f"📈 *Volume 1h:* {vol_change}\n"
            f"⚠️ *Risk:* {risk_level(liq)}"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Buy with BaseBot", url=f"{REF}{ca}")]
        ])

        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        await update.message.reply_text("⚠️ Scan failed. Try again.")

# -------- APP --------

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, scan))

print("🦅 Elite Degen Bot LIVE")
app.run_polling()
