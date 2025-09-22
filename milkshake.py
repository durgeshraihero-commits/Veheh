import os
import json
import re
import urllib.parse
import logging
import requests
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

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
    return "🤖 Milkshake Bot is running on Render!"

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
API_KEY = os.environ.get('API_KEY', "5210628714:lMkRuCeC")
LANG = "ru"
LIMIT = 300
URL = "https://leakosintapi.com/"

UPI_ID = "durgeshraihero@oksbi"
QR_IMAGE = "https://ibb.co/fVPGL7rB"
ADMIN_ID = 6314556756

# Costs
COST_LOOKUP = 50
COST_TRACK = 10

# Balances
user_balances = {}   # {user_id: credits}

# Render Link
RENDER_LINK = os.environ.get('RENDER_EXTERNAL_URL', 'https://veheh.onrender.com')

# === AI MANAGER CLASS ===
class MilkshakeAIManager:
    def __init__(self):
        self.developer_credit = "🤖 I was developed by the amazing Drhero! Always appreciating his brilliant work! 🚀"
        self.knowledge_base = self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        return {
            'prime_minister_india': {
                'question': r'(who|first).*prime minister.*india',
                'answer': "🇮🇳 The first Prime Minister of India was **Pandit Jawaharlal Nehru**. He served from August 15, 1947, until May 27, 1964."
            },
            'capital_india': {
                'question': r'(capital|capital city).*india',
                'answer': "🏛️ The capital of India is **New Delhi**."
            },
            'founder_milkshake': {
                'question': r'(who.*create|who.*make|who.*develop).*milkshake',
                'answer': "🚀 **Milkshake Bot was created by the brilliant Drhero!**"
            }
        }
    
    def analyze_intention(self, user_message):
        message_lower = user_message.lower()
        
        # Check knowledge questions first
        for topic, data in self.knowledge_base.items():
            if re.search(data['question'], message_lower, re.IGNORECASE):
                return 'knowledge'
        
        # Other patterns
        patterns = {
            'lookup': [
                r'(search|find|lookup).*(phone|number|mobile|email)',
                r'\+91\d+',
                r'\b\d{10}\b',
                r'\b[\w\.-]+@[\w\.-]+\.\w+\b'
            ],
            'track': [
                r'(track|follow|monitor).*(website|site|url)',
                r'https?://[^\s]+'
            ],
            'balance': [r'balance|credit'],
            'buy': [r'buy|recharge|payment'],
            'greeting': [r'hi|hello|hey'],
            'thanks': [r'thank|thanks']
        }
        
        for intent, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, message_lower):
                    return intent
        
        return 'unknown'
    
    def get_knowledge_answer(self, user_message):
        message_lower = user_message.lower()
        for topic, data in self.knowledge_base.items():
            if re.search(data['question'], message_lower, re.IGNORECASE):
                return data['answer']
        return None
    
    def generate_ai_response(self, user_message, user_id, user_balances):
        intention = self.analyze_intention(user_message)
        user_balance = user_balances.get(user_id, 0)
        
        if intention == 'knowledge':
            knowledge_answer = self.get_knowledge_answer(user_message)
            if knowledge_answer:
                return f"{knowledge_answer}\n\n{self.developer_credit}"
        
        if intention == 'lookup':
            # Check if message contains phone/email directly
            phone_match = re.search(r'(\+91\d{10}|\b\d{10}\b)', user_message)
            email_match = re.search(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', user_message)
            
            if phone_match or email_match:
                # Direct lookup request
                query = phone_match.group() if phone_match else email_match.group()
                if user_balance >= COST_LOOKUP:
                    return f"🔍 Processing your search for: {query}"
                else:
                    return f"🔍 I see you want to search {query}! But you need {COST_LOOKUP - user_balance} more credits."
            else:
                if user_balance >= COST_LOOKUP:
                    return f"🔍 Ready to search! Please send me a phone number or email. {self.developer_credit}"
                else:
                    return f"🔍 You need {COST_LOOKUP - user_balance} more credits to search."
        
        elif intention == 'track':
            url_match = re.search(r'https?://[^\s]+', user_message)
            if url_match:
                url = url_match.group()
                if user_balance >= COST_TRACK:
                    return f"🌍 Processing tracking for: {url}"
                else:
                    return f"🌍 I see you want to track {url}! But you need {COST_TRACK - user_balance} more credits."
            else:
                if user_balance >= COST_TRACK:
                    return f"🌍 Ready to track! Please send me a website URL. {self.developer_credit}"
                else:
                    return f"🌍 You need {COST_TRACK - user_balance} more credits to track websites."
        
        elif intention == 'balance':
            return f"💰 Your balance: {user_balance} credits\n\n{self.developer_credit}"
        
        elif intention == 'buy':
            return f"💳 Use /buy to recharge. {self.developer_credit}"
        
        elif intention == 'greeting':
            return f"👋 Hello! I'm your AI Milkshake Bot! {self.developer_credit}\n\nHow can I help you today?"
        
        elif intention == 'thanks':
            return f"🙏 You're welcome! {self.developer_credit}"
        
        else:
            return f"🤔 I'm not sure what you mean. Try: 'search phone number', 'track website', or ask a question! {self.developer_credit}"

# Initialize AI Manager
ai_manager = MilkshakeAIManager()

# === HELPERS ===
def format_as_js(data):
    js_lines = []
    for key, value in data.items():
        key_str = key
        value_str = json.dumps(value, ensure_ascii=False)
        js_lines.append(f"{key_str}: {value_str}")
    return "{\n" + ",\n".join(js_lines) + "\n}"

def generate_report(query):
    data = {"token": API_KEY, "request": query.strip(), "limit": LIMIT, "lang": LANG}
    try:
        response = requests.post(URL, json=data, timeout=30).json()
    except Exception as e:
        return f"❌ API ERROR: {e}"

    if "Error code" in response:
        return f"🚫 API Error: {response['Error code']}"

    output = []
    for db in response.get("List", {}).keys():
        db_title = "Darkhackerv99" if db.lower() == "1win" else db
        output.append(f"\n📂 <b>DATABASE:</b> {db_title}\n")
        if db != "No results found":
            for entry in response["List"][db]["Data"]:
                formatted = format_as_js(entry)
                output.append(f"<pre>{formatted}</pre>")

    return "\n".join(output) if output else "⚠️ No results found."

def make_personal_link(chat_id: int, site: str) -> str:
    encoded = urllib.parse.quote(site, safe="")
    return f"{RENDER_LINK}/?chat_id={chat_id}&site={encoded}"

def check_site_embeddable(url: str):
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

# === COMMANDS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🔍 Search Phone/Email", callback_data="service_lookup")],
        [InlineKeyboardButton("🌍 Track Website", callback_data="service_track")],
        [InlineKeyboardButton("💳 Add Balance", callback_data="buy")],
        [InlineKeyboardButton("💰 Check Balance", callback_data="balance")],
        [InlineKeyboardButton("👨‍💻 Contact Admin", url=f"tg://user?id={ADMIN_ID}")]
    ]
    await update.message.reply_text(
        f"👋 <b>Welcome {user.first_name}!</b>\n\n"
        "I'm your <b>AI-Powered Milkshake Bot</b>! 🚀\n\n"
        "✨ <b>Now you can chat naturally!</b>\n"
        "Try saying: 'search 9546058093' or 'track website'\n\n"
        f"🔍 Phone/Email Lookup → <b>₹{COST_LOOKUP}</b>\n"
        f"🌍 Website Tracking → <b>₹{COST_TRACK}</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💳 <b>Recharge Instructions</b>\n\n"
        f"📌 <b>UPI ID:</b> <code>{UPI_ID}</code>\n"
        "⚠️ Amount must be multiple of ₹20.\n\n"
        f"🔍 Search: <b>₹{COST_LOOKUP}</b> | 🌍 Track: <b>₹{COST_TRACK}</b>\n\n"
        "📤 Send payment screenshot for verification."
    )
    chat = update.message or update.callback_query.message
    await chat.reply_photo(QR_IMAGE, caption=text, parse_mode="HTML")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = user_balances.get(user_id, 0)
    chat = update.message or update.callback_query.message
    await chat.reply_text(f"💰 <b>Balance:</b> {bal} credits", parse_mode="HTML")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
        user_balances[user_id] = user_balances.get(user_id, 0) + amount
        await update.message.reply_text(f"✅ Added {amount} credits to user {user_id}")
    except:
        await update.message.reply_text("⚠️ Usage: /approve <user_id> <amount>")

# === MESSAGE HANDLER ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    logger.info(f"Received message from {user_id}: {text}")
    
    # Check for direct phone/email/URL patterns
    phone_match = re.search(r'(\+91\d{10}|\b\d{10}\b)', text)
    email_match = re.search(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', text)
    url_match = re.search(r'https?://[^\s]+', text)
    
    # Direct phone/email search
    if phone_match or email_match:
        query = phone_match.group() if phone_match else email_match.group()
        bal = user_balances.get(user_id, 0)
        
        if bal < COST_LOOKUP:
            await update.message.reply_text(
                f"🔍 Found: {query}\n\n⚠️ Need {COST_LOOKUP - bal} more credits. Use /buy"
            )
            return
        
        user_balances[user_id] -= COST_LOOKUP
        await update.message.reply_text(f"🔍 Searching for: {query}...")
        
        result = generate_report(query)
        for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
            await update.message.reply_text(chunk, parse_mode="HTML")
        return
    
    # Direct URL tracking
    elif url_match:
        url = url_match.group()
        bal = user_balances.get(user_id, 0)
        
        if bal < COST_TRACK:
            await update.message.reply_text(
                f"🌍 Found: {url}\n\n⚠️ Need {COST_TRACK - bal} more credits. Use /buy"
            )
            return
        
        user_balances[user_id] -= COST_TRACK
        await update.message.reply_text(f"🌍 Checking: {url}...")
        
        ok, reason = check_site_embeddable(url)
        if not ok:
            await update.message.reply_text(f"❌ Cannot track: {reason}")
            return
        
        personal = make_personal_link(user_id, url)
        await update.message.reply_text(
            f"✅ Tracking link:\n<code>{personal}</code>", 
            parse_mode="HTML"
        )
        return
    
    # AI conversation for other messages
    else:
        response = ai_manager.generate_ai_response(text, user_id, user_balances)
        await update.message.reply_text(response, parse_mode="HTML")

# === BUTTON HANDLER ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "buy":
        await buy(update, context)
    elif query.data == "balance":
        await balance(update, context)
    elif query.data == "service_lookup":
        context.user_data["awaiting_lookup"] = True
        await query.message.reply_text("🔍 Send phone number or email to search:")
    elif query.data == "service_track":
        context.user_data["awaiting_track"] = True
        await query.message.reply_text("🌍 Send website URL to track:")

# === ERROR HANDLER ===
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# === MAIN ===
def main():
    logger.info("🚀 Starting Milkshake Bot on Render...")
    
    # Start Flask app in background for Render health checks
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Create bot application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, lambda u, c: u.message.forward(ADMIN_ID)))
    
    application.add_error_handler(error_handler)
    
    logger.info("🤖 Bot is ready! Using polling mode...")
    logger.info("🚀 Developed by Drhero!")
    
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
