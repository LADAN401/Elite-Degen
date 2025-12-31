#!/usr/bin/env python3
"""
Elite Degen Bot - Base Token Scanner for Telegram
Deployment ready for Bothost
"""

import os
import logging
import re
from datetime import datetime

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Load environment variables (Bothost will inject these)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ANKR_RPC = os.environ.get("ANKR_RPC")
DEXSCREENER_BASE_URL = os.environ.get("DEXSCREENER_BASE_URL", "https://api.dexscreener.com/orders/v1/base/")

# Configure logging for Bothost compatibility
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Regex pattern to detect Base token contract addresses (0x + 40 hex chars)
TOKEN_ADDRESS_PATTERN = re.compile(r'^0x[a-fA-F0-9]{40}$')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    welcome_message = "Elite Degen Bot is online! ✅ Send a Base token CA to scan."
    await update.message.reply_text(welcome_message)

async def handle_token_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Process token contract addresses sent by users.
    Checks DexScreener status and provides referral link.
    """
    # Get the message text and remove any whitespace
    message_text = update.message.text.strip()
    
    # Validate it's a proper Ethereum/Base address
    if not TOKEN_ADDRESS_PATTERN.match(message_text):
        await update.message.reply_text("❌ Invalid format. Please send a valid Base token contract address (0x...).")
        return
    
    token_address = message_text.lower()  # Use lowercase for consistency
    
    try:
        # Fetch DexScreener data
        dex_status, timestamp = await check_dex_paid_status(token_address)
        
        # Prepare response message
        response_message = f"🔍 *Token Scan Results*\n\n"
        response_message += f"• *Contract:* `{token_address}`\n"
        response_message += f"• *Network:* Base ✅\n"
        response_message += f"• *Dex Paid:* {dex_status}\n"
        
        # Generate dynamic referral URL
        referral_url = f"https://t.me/based_eth_bot?start=r_Elite_xyz_b_{token_address}"
        
        # Create inline keyboard with referral button
        keyboard = [
            [InlineKeyboardButton("Buy with BaseBot", url=referral_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send response with button
        await update.message.reply_text(
            response_message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error processing token {token_address}: {e}")
        await update.message.reply_text(
            "⚠️ Error scanning token. Please try again later or verify the contract address."
        )

async def check_dex_paid_status(token_address: str):
    """
    Check if token has paid for DexScreener listing.
    Returns: (status_text, timestamp_or_none)
    """
    try:
        # Construct API URL
        api_url = f"{DEXSCREENER_BASE_URL.rstrip('/')}/{token_address}"
        
        # Make API request with timeout
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes
        
        data = response.json()
        
        # Check if paid status exists in response
        # Note: DexScreener API structure may vary - adjust based on actual response
        if isinstance(data, dict):
            # Try different possible response structures
            if data.get("paid") is True:
                timestamp = data.get("timestamp")
                if timestamp:
                    # Convert timestamp to readable format
                    try:
                        dt = datetime.fromtimestamp(timestamp / 1000)
                        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                        return f"🟢 Paid ({formatted_time})", formatted_time
                    except:
                        return f"🟢 Paid", None
                return "🟢 Paid", None
            elif "order" in data and data["order"].get("paid") is True:
                return "🟢 Paid", None
        
        # Default to not paid if not found or false
        return "🔴 Not Paid", None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"DexScreener API error: {e}")
        return "❌ API Error", None
    except (KeyError, ValueError) as e:
        logger.error(f"Error parsing DexScreener response: {e}")
        return "🔴 Not Paid", None

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors and handle exceptions gracefully"""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Optionally send error message to user (uncomment if needed)
    # if update and update.effective_message:
    #     await update.effective_message.reply_text(
    #         "❌ An error occurred. Please try again."
    #     )

def main():
    """Main function to start the bot"""
    
    # Validate environment variables
    required_vars = ["BOT_TOKEN", "ANKR_RPC"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.info("Bothost deployment requires these environment variables to be set:")
        logger.info("1. BOT_TOKEN: Your Telegram bot token from @BotFather")
        logger.info("2. ANKR_RPC: Your Ankr RPC URL for Base network")
        logger.info("3. DEXSCREENER_BASE_URL: (Optional) DexScreener API base URL")
        return
    
    # Create Application instance
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    
    # Register message handler for token addresses
    # Filters text messages that match Ethereum address pattern
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_token_address
    ))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Starting Elite Degen Bot...")
    print("✅ Bot is running. Press Ctrl+C to stop.")
    
    # Run bot until stopped
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
