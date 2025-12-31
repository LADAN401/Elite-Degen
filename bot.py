#!/usr/bin/env python3
import os
import time
import re
import requests
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEX = os.getenv("DEXSCREENER_BASE_URL", "https://api.dexscreener.com")
REF = "https://t.me/based_eth_bot?start=r_Elite_xyz_b_"

CA_REGEX = re.compile(r"0x[a-fA-F0-9]{40}")

# ---------------- HELPERS ----------------

def fmt(n):
    try:
        n = float(n)
    except:
        return "0"
    for u in ["", "K", "M", "B"]:
        if abs(n) < 1000:
            return f"{n:.1f}{u}"
        n /= 1000
    return f"{n:.1f}T"

def ago(ms):
    s = int(time.time() - ms / 1000)
    if s < 3600:
        return f"{s//60}m"
    if s < 86400:
        return f"{s//3600}h"
    return f"{s//86400}d"

# ---------------- DEX DATA ----------------

def dex_search(ca):
    try:
        r = requests.get(f"{DEX}/latest/dex/search?q={ca}", timeout=10).json()
        pairs = r.get("pairs", [])
        if not pairs:
            return None
        # Pick pair with highest liquidity
        pairs.sort(key=lambda x: x.get("liquidity", {}).get("usd", 0), reverse=True)
        return pairs[0]
    except:
        return None

def dex_paid(chain, ca):
    try:
        r = requests.get(f"{DEX}/orders/v1/{chain}/{ca}", timeout=10).json()
        if r:
            ts = r[0].get("createdAt")
            return f"🟢 Dex Paid ({ago(ts)} ago)" if ts else "🟢 Dex Paid"
    except:
        pass
    return "🔴 Dex Not Paid"

def get_profile(ca):
    banner = None
    socials = []
    try:
        r = requests.get(f"{DEX}/token-profiles/latest/v1", timeout=10).json()
        for x in r:
            if x.get("tokenAddress", "").lower() == ca.lower():
                banner = x.get("headerImage")
                socials = x.get("links", [])
                break
    except:
        pass
    return banner, socials

def is_cto(ca):
    try:
        r = requests.get(f"{DEX}/community-takeovers/latest/v1", timeout=10).json()
        for x in r:
            if x.get("tokenAddress", "").lower() == ca.lower():
                return True
    except:
        pass
    return False

def boost_count(ca):
    try:
        r = requests.get(f"{DEX}/token-boosts/latest/v1", timeout=10).json()
        return sum(1 for x in r if x.get("tokenAddress", "").lower() == ca.lower())
    except:
        return 0

def get_token_details(chain, ca):
    try:
        r = requests.get(f"{DEX}/tokens/v1/{chain}/{ca}", timeout=10).json()
        return r
    except:
        return {}

def risk_score(lp, mc, paid, created, socials):
    risks = []
    if lp < 10000:
        risks.append("Low liquidity")
    if mc < lp*2:
        risks.append("Low MC")
    if "🔴" in paid:
        risks.append("Dex Not Paid")
    if int(time.time()*1000) - created < 2*3600*1000:
        risks.append("Fresh token")
    if not socials:
        risks.append("No socials")
    return risks if risks else ["Low risk"]

def render_socials(links):
    if not links:
        return ""
    out = "\n🔗 Socials\n └ "
    items = []
    for l in links:
        t = l.get("type", "").upper()
        u = l.get("url", "")
        if t and u:
            items.append(f"[{t}]({u})")
    return out + " • ".join(items)

# ---------------- SCAN CORE ----------------

async def scan_and_send(ca, send):
    pair = dex_search(ca)
    if not pair:
        await send("❌ Token not found on DexScreener")
        return

    chain = pair["chainId"]
    dex = pair["dexId"]
    token = pair["baseToken"]
    name = token.get("name", "")
    sym = token.get("symbol", "")
    price = float(pair.get("priceUsd", 0))
    mc = float(pair.get("fdv", 0))
    vol = float(pair.get("volume", {}).get("h24", 0))
    lp = float(pair.get("liquidity", {}).get("usd", 0))
    ch1h = pair.get("priceChange", {}).get("h1", 0)
    created = pair.get("pairCreatedAt", int(time.time()*1000))

    paid = dex_paid(chain, ca)
    banner, socials = get_profile(ca)
    cto = "🤝 CTO Detected" if is_cto(ca) else ""
    boosts = boost_count(ca)
    details = get_token_details(chain, ca)
    ath = details.get("allTimeHigh", {}).get("priceUsd", 0)
    drawdown = ((price - ath)/ath*100) if ath else 0
    risks = risk_score(lp, mc, paid, created, socials)

    text = (
        f"🔵 *{name}* (${sym})\n"
        f"├ `{ca}`\n"
        f"└ #{chain.upper()} ({dex}) | 🌱 {ago(created)} | 👁️ {pair.get('holders', '0')}\n\n"
        f"📊 Stats\n"
        f" ├ USD   ${price}\n"
        f" ├ MC    {fmt(mc)}\n"
        f" ├ Vol   {fmt(vol)}\n"
        f" ├ LP    {fmt(lp)}\n"
        f" ├ 1H    {ch1h}%\n"
        f" └ ATH   ${ath} ({drawdown:.1f}% drawdown)\n\n"
        f"🔒 Security\n"
        f" ├ {paid}\n"
        f" ├ Boosts     {boosts}\n"
        f" ├ Risk      {' + '.join(risks)}\n"
    )
    if cto:
        text += f" ├ {cto}\n"
    text += render_socials(socials)
    text += "\n\n🦅 Elite Degen Scanner"

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"r|{ca}"),
            InlineKeyboardButton("🟢 Buy with BaseBot", url=f"{REF}{ca}")
        ]
    ])

    if banner:
        await send(banner)
    await send(text, kb)

# ---------------- TELEGRAM ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🦅 Elite Degen Online\nSend any token CA")

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    found = CA_REGEX.findall(update.message.text)
    if found:
        ca = found[0]
        await scan_and_send(
            ca,
            lambda m, k=None: update.message.reply_text(
                m, parse_mode="Markdown", reply_markup=k
            )
        )

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ca = q.data.split("|")[1]
    await scan_and_send(
        ca,
        lambda m, k=None: q.edit_message_text(
            m, parse_mode="Markdown", reply_markup=k
        )
    )

# ---------------- RUN ----------------

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
app.add_handler(CallbackQueryHandler(refresh, pattern="^r\\|"))

print("🦅 Elite Degen Bot LIVE")
app.run_polling()
