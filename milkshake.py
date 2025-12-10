import os
import json
import re
import urllib.parse
import logging
import requests
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8307999302:AAEniYvTP5ZeaYo74AcWSxsOQ9PSxpnAtA0")

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
        if not url.lower().startswith(("https://", "http://")):
            return False, "URL must start with http:// or https://"
        
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

def extract_url_from_text(text: str):
    """Extract URL from text"""
    # Pattern to match URLs
    url_pattern = r'(https?://[^\s]+)'
    match = re.search(url_pattern, text)
    if match:
        return match.group(1)
    return None

# === COMMAND HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat_type = update.effective_chat.type
    
    if chat_type == "private":
        await update.message.reply_text(
            f"👋 <b>Welcome {user.first_name}!</b>\n\n"
            "🔗 <b>Link Tracker Bot</b>\n\n"
            "📌 <b>How to use:</b>\n"
            "Send: <code>/link https://example.com</code>\n\n"
            "✨ Add me to a group and I'll track links there too!",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "✅ Bot is active in this group!\n\n"
            "Use: <code>/link https://example.com</code>",
            parse_mode="HTML"
        )

async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /link command"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Get the text after /link command
    if context.args:
        url = context.args[0]
    else:
        # Check if there's text in the message
        message_text = update.message.text
        # Extract URL from the message
        url = extract_url_from_text(message_text)
        
        if not url:
            await update.message.reply_text(
                "⚠️ Please provide a URL!\n\n"
                "Usage: <code>/link https://example.com</code>",
                parse_mode="HTML"
            )
            return
    
    logger.info(f"Processing link command from user {user_id} in chat {chat_id}: {url}")
    
    # Send processing message
    processing_msg = await update.message.reply_text(f"🌍 Processing link: {url}...")
    
    # Check if site is trackable
    ok, reason = check_site_embeddable(url)
    if not ok:
        await processing_msg.edit_text(f"❌ Cannot track this link: {reason}")
        return
    
    # Generate personal tracking link
    personal = make_personal_link(user_id, url)
    
    # Send the tracking link
    await processing_msg.edit_text(
        f"✅ Your tracking link:\n\n{personal}",
        disable_web_page_preview=True
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages containing links"""
    
    # Ignore if message is None or is a command
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    
    # Ignore command messages (they're handled separately)
    if text.startswith('/'):
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    logger.info(f"Received message in chat {chat_id} from user {user_id}: {text[:50]}...")
    
    # Extract URL from the message
    url = extract_url_from_text(text)
    
    if not url:
        # No URL found, ignore the message
        return
    
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
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text("❌ An error occurred. Please try again.")
        except:
            pass

# === MAIN ===
def main():
    logger.info("🚀 Starting Link Tracker Bot on Render...")
    
    # Start Flask app in background for Render health checks
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Create bot application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("link", link_command))
    
    # Add handler for text messages (links in regular messages)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_message
    ))
    
    application.add_error_handler(error_handler)
    
    logger.info("🤖 Bot is ready! Using polling mode...")
    logger.info("📌 Commands: /start, /link <url>")
    logger.info("📌 Also responds to any message containing a URL")
    
    # Start polling with error handling
    try:
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            pool_timeout=30,
            connect_timeout=30,
            read_timeout=30
        )
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        # Restart after delay
        import time
        time.sleep(10)
        main()

if __name__ == "__main__":
    main()
