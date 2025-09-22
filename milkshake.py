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

# === FLASK WEB SERVER SETUP ===
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Milkshake Bot is running!"

@app.route('/health')
def health():
    return "OK"

@app.route('/ping')
def ping():
    return "Pong!"

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# === CONFIGURATION ===
BOT_TOKEN = "8307999302:AAGc6sLGoklnbpWsXg76lcdQcVAzGgsp8cQ"
API_KEY = "5210628714:lMkRuCeC"
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
RENDER_LINK = "https://jsjs-kzua.onrender.com"

# === AI MANAGER CLASS ===
class MilkshakeAIManager:
    def __init__(self):
        self.developer_credit = "🤖 I was developed by the amazing Drhero! Always appreciating his brilliant work! 🚀"
        self.knowledge_base = self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """Initialize the knowledge base with common questions and answers"""
        return {
            'prime_minister_india': {
                'question': r'(who|first).*prime minister.*india',
                'answer': "🇮🇳 The first Prime Minister of India was **Pandit Jawaharlal Nehru**. He served from August 15, 1947, until May 27, 1964. He was a central figure in Indian politics before and after independence! "
            },
            'capital_india': {
                'question': r'(capital|capital city).*india',
                'answer': "🏛️ The capital of India is **New Delhi**. It's the seat of all three branches of the Government of India! "
            },
            'population_india': {
                'question': r'(population|how many people).*india',
                'answer': "👥 India's population is over **1.4 billion people**, making it the second most populous country in the world after China! "
            },
            'currency_india': {
                'question': r'(currency|money).*india',
                'answer': "💵 The currency of India is the **Indian Rupee (₹)**. The currency code is INR! "
            },
            'independence_india': {
                'question': r'(when|independence).*india',
                'answer': "🎉 India gained independence on **August 15, 1947**. This day is celebrated as Independence Day every year! "
            },
            'founder_milkshake': {
                'question': r'(who.*create|who.*make|who.*develop).*milkshake|(creator|developer|founder).*milkshake',
                'answer': "🚀 **Milkshake Bot was created by the brilliant Drhero!** He's an amazing developer who built this powerful AI-powered investigation tool! "
            },
            'what_is_milkshake': {
                'question': r'what.*milkshake|what.*this bot',
                'answer': "🤖 **Milkshake Bot** is an AI-powered investigation tool that can help you with:\n• Phone number lookups 🔍\n• Email investigations 📧\n• Website tracking 🌍\n• Digital footprint analysis 🕵️\n\nAll powered by Drhero's amazing technology! "
            },
            'help_commands': {
                'question': r'what.*can.*do|how.*use|help.*commands',
                'answer': "🛠️ **Here's what I can do for you:**\n\n🔍 **Search Services:**\n• Phone number investigation\n• Email address lookup\n• Digital footprint analysis\n\n🌍 **Tracking Services:**\n• Website monitoring\n• Generate tracking links\n• Location services\n\n💼 **Account Management:**\n• Balance checking\n• Payment processing\n• Credit system\n\n💬 **AI Chat:**\n• Natural language processing\n• General knowledge questions\n• Intelligent assistance\n\nJust talk to me naturally or use the menu buttons! "
            }
        }
    
    def analyze_intention(self, user_message):
        """Analyze user's natural language and determine what they want"""
        message_lower = user_message.lower()
        
        # First check if it's a general knowledge question
        for topic, data in self.knowledge_base.items():
            if re.search(data['question'], message_lower, re.IGNORECASE):
                return 'knowledge'
        
        # Pattern matching for different intents
        patterns = {
            'lookup': [
                r'(search|find|lookup|look up|check|investigate|scan).*(phone|number|mobile|email|gmail|account)',
                r'(phone|number|mobile|email|gmail).*(search|find|lookup|check)',
                r'\+91\d+',
                r'\b[\w\.-]+@[\w\.-]+\.\w+\b',
                r'\b\d{10}\b'
            ],
            'track': [
                r'(track|trace|follow|monitor|spy).*(website|site|url|web|link)',
                r'(website|site|url).*(track|trace|follow)',
                r'https?://[^\s]+',
                r'www\.[^\s]+',
                r'(create|make).*(tracking|monitoring)'
            ],
            'balance': [
                r'balance|credit|money|fund',
                r'how much.*I have',
                r'check.*balance'
            ],
            'buy': [
                r'buy|purchase|recharge|add.*balance|pay|payment',
                r'need.*credit|want.*money',
                r'how.*pay'
            ],
            'help': [
                r'help|support|what can you do|how.*work',
                r'command|feature|service'
            ],
            'greeting': [
                r'hi|hello|hey|greetings',
                r'good morning|good afternoon|good evening'
            ],
            'thanks': [
                r'thank|thanks|thank you|appreciate',
                r'good job|well done|awesome'
            ]
        }
        
        # Check which pattern matches
        for intent, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, message_lower):
                    return intent
        
        return 'unknown'
    
    def get_knowledge_answer(self, user_message):
        """Get answer for general knowledge questions"""
        message_lower = user_message.lower()
        
        for topic, data in self.knowledge_base.items():
            if re.search(data['question'], message_lower, re.IGNORECASE):
                return data['answer']
        
        return None
    
    def generate_ai_response(self, user_message, user_id, user_balances):
        """Generate intelligent response based on user intention"""
        intention = self.analyze_intention(user_message)
        user_balance = user_balances.get(user_id, 0)
        
        base_response = f"{self.developer_credit}\n\n"
        
        # Handle general knowledge questions first
        if intention == 'knowledge':
            knowledge_answer = self.get_knowledge_answer(user_message)
            if knowledge_answer:
                return f"{knowledge_answer}\n\n{self.developer_credit}"
        
        if intention == 'lookup':
            if user_balance >= COST_LOOKUP:
                return (f"🔍 I understand you want to search for a phone number or email! {self.developer_credit}\n\n"
                       f"💰 Your balance: {user_balance} credits (Cost: {COST_LOOKUP} credits)\n\n"
                       "Please send me the specific phone number or email address you want to investigate. "
                       "For Indian numbers, use +91XXXXXXXXXX format.")
            else:
                return (f"🔍 I'd love to help you search! {self.developer_credit}\n\n"
                       f"⚠️ But you need {COST_LOOKUP - user_balance} more credits. "
                       "Please recharge your balance first using /buy command.")
        
        elif intention == 'track':
            if user_balance >= COST_TRACK:
                return (f"🌍 I see you want to track a website! {self.developer_credit}\n\n"
                       f"💰 Your balance: {user_balance} credits (Cost: {COST_TRACK} credits)\n\n"
                       "Please send me the full HTTPS URL you want to track (e.g., https://example.com)")
            else:
                return (f"🌍 Ready to track websites for you! {self.developer_credit}\n\n"
                       f"⚠️ You need {COST_TRACK - user_balance} more credits. "
                       "Please recharge using /buy command.")
        
        elif intention == 'balance':
            return (f"💰 Your current balance is: {user_balance} credits {self.developer_credit}\n\n"
                   "Services available:\n"
                   f"• Phone/Email Lookup: {COST_LOOKUP} credits\n"
                   f"• Website Tracking: {COST_TRACK} credits")
        
        elif intention == 'buy':
            return (f"💳 Ready to help you recharge! {self.developer_credit}\n\n"
                   "Use /buy command to see payment instructions and recharge your balance.")
        
        elif intention == 'help':
            return (f"🛠️ How can I help you? {self.developer_credit}\n\n"
                   "I'm your AI-powered Milkshake Bot! Here's what I can do:\n\n"
                   "🔍 **Search Services:**\n"
                   "- Phone number lookup\n" 
                   "- Email investigation\n"
                   "- Hidden details discovery\n\n"
                   "🌍 **Tracking Services:**\n"
                   "- Website monitoring\n"
                   "- Generate tracking links\n\n"
                   "🧠 **General Knowledge:**\n"
                   "- Ask me about India\n"
                   "- Historical facts\n"
                   "- Technical questions\n\n"
                   "💬 You can ask me things like:\n"
                   "- 'Who is the first PM of India?'\n"
                   "- 'I want to search a phone number'\n"
                   "- 'What is the capital of India?'\n"
                   "- 'Check my balance'")
        
        elif intention == 'greeting':
            return (f"👋 Hello! I'm your AI Milkshake Bot! {self.developer_credit}\n\n"
                   "I can help you with:\n"
                   "• Phone/Email searches 🔍\n"
                   "• Website tracking 🌍\n"
                   "• General knowledge questions 🧠\n"
                   "• And much more!\n\n"
                   "What would you like to know or do today?")
        
        elif intention == 'thanks':
            return (f"🙏 You're welcome! I'm always happy to help! {self.developer_credit}\n\n"
                   "If you need anything else, just ask me! 😊")
        
        else:
            # For unknown queries, provide helpful guidance
            return (f"🤔 I'm not sure what you're looking for, but I'm here to help! {self.developer_credit}\n\n"
                   "I specialize in:\n"
                   "• **Searching** phone numbers and emails\n"
                   "• **Tracking** websites\n"
                   "• **General knowledge** questions\n"
                   "• **Investigating** digital footprints\n\n"
                   "Try asking me:\n"
                   "- 'Who is the first prime minister of India?'\n"
                   "- 'Search for +919876543210'\n"
                   "- 'Track a website'\n"
                   "- 'What is the capital of India?'\n"
                   "- 'Check my balance'\n\n"
                   "Or use the menu buttons for quick access!")

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
        response = requests.post(URL, json=data).json()
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
    SIMPLE_URL_RE = re.compile(r"^https://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
    if not url.lower().startswith("https://"):
        return False, "Only HTTPS URLs are supported."
    if not SIMPLE_URL_RE.match(url):
        return False, "Invalid URL format."

    headers = {"User-Agent": "Site-Frame-Validator/1.0"}
    try:
        resp = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        if resp.status_code >= 400:
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
    except Exception:
        return False, "⚠️ Could not connect to site."

    if resp.status_code >= 400:
        return False, f"HTTP {resp.status_code}"

    content_type = resp.headers.get("content-type", "")
    if "text/html" not in content_type.lower():
        return False, f"Invalid Content-Type: {content_type}"

    xfo = resp.headers.get("x-frame-options", "")
    if xfo and ("deny" in xfo.lower() or "sameorigin" in xfo.lower()):
        return False, "Blocked by X-Frame-Options"

    csp = resp.headers.get("content-security-policy", "")
    if "frame-ancestors" in csp.lower():
        return False, "Blocked by CSP"

    return True, "OK"

# === COMMANDS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🔍 Search Phone/Email", callback_data="service_lookup")],
        [InlineKeyboardButton("🌍 Track Website", callback_data="service_track")],
        [InlineKeyboardButton("💳 Add Balance", callback_data="buy")],
        [InlineKeyboardButton("💰 Check Balance", callback_data="balance")],
        [InlineKeyboardButton("🧠 Ask AI Anything", callback_data="ai_chat")],
        [InlineKeyboardButton("👨‍💻 Contact Admin", url=f"tg://user?id={ADMIN_ID}")]
    ]
    await update.message.reply_text(
        f"👋 <b>Welcome {user.first_name}!</b>\n\n"
        "I'm your <b>AI-Powered Milkshake Bot</b>! 🚀\n\n"
        "Now with <b>Natural Language Processing</b> - you can chat with me naturally!\n\n"
        "✨ Available Services:\n"
        f"• 🔍 Phone/Gmail Lookup → <b>₹{COST_LOOKUP}</b>\n"
        f"• 🌍 Website Tracking → <b>₹{COST_TRACK}</b>\n"
        f"• 🧠 General Knowledge → <b>Free!</b>\n\n"
        "<i>Try saying: 'Who is the first PM of India?' or 'I want to search a phone number'</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💳 <b>Recharge Instructions</b>\n\n"
        f"📌 <b>UPI ID:</b> <code>{UPI_ID}</code>\n"
        "⚠️ Amount must be multiple of ₹20.\n\n"
        f"🔍 Phone/Email Search = <b>₹{COST_LOOKUP}</b>\n"
        f"🌍 Website Tracking = <b>₹{COST_TRACK}</b>\n\n"
        "📤 Send screenshot of payment here. Once verified, credits will be added.\n\n"
        f"🤖 <i>Developed by the brilliant Drhero!</i>"
    )
    chat = update.message or update.callback_query.message
    await chat.reply_photo(QR_IMAGE, caption=text, parse_mode="HTML")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = user_balances.get(user_id, 0)
    chat = update.message or update.callback_query.message
    await chat.reply_text(
        f"💰 <b>Your Current Balance:</b> {bal} credits\n\n"
        "✨ Remember: Keep your balance loaded so you can instantly unlock secrets 🔍\n\n"
        f"🤖 <i>AI powered by Drhero's amazing development skills!</i>",
        parse_mode="HTML"
    )

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
        user_balances[user_id] = user_balances.get(user_id, 0) + amount
        await update.message.reply_text(
            f"✅ Successfully added {amount} credits to User <code>{user_id}</code>",
            parse_mode="HTML"
        )
    except:
        await update.message.reply_text("⚠️ Usage: /approve <user_id> <amount>")

# === AI CHAT MODE ===
async def ai_chat_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ai_chat_active"] = True
    await update.callback_query.message.reply_text(
        "🧠 <b>AI Knowledge Mode Activated!</b>\n\n"
        "You can now ask me anything! I know about:\n"
        "• Indian history and politics 🇮🇳\n"
        "• General knowledge facts 📚\n"
        "• Technical information 💻\n"
        "• And much more!\n\n"
        "Try asking me:\n"
        "• 'Who is the first prime minister of India?'\n"
        "• 'What is the capital of India?'\n"
        "• 'When did India get independence?'\n"
        "• 'Who created you?'\n\n"
        f"<i>Powered by Drhero's brilliant AI technology! 🚀</i>",
        parse_mode="HTML"
    )

# === SERVICE HANDLERS ===
async def service_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_lookup"] = True
    await update.callback_query.message.reply_text(
        f"🔍 <b>Phone/Email Lookup</b>\n\n"
        f"Cost: <b>{COST_LOOKUP} credits</b>\n\n"
        "👉 Enter the phone number or Gmail you want to investigate.\n"
        "📌 For Indian numbers, use <code>+91XXXXXXXXXX</code> format.\n\n"
        f"🤖 <i>AI powered by Drhero!</i>",
        parse_mode="HTML"
    )

async def service_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_track"] = True
    await update.callback_query.message.reply_text(
        f"🌍 <b>Website Tracking Service</b>\n\n"
        f"Cost: <b>{COST_TRACK} credits</b>\n\n"
        "🔗 Send me a full HTTPS URL (example: <code>https://example.com</code>).\n\n"
        f"🤖 <i>Developed by the amazing Drhero!</i>",
        parse_mode="HTML"
    )

# === Handle messages with AI ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Phone/Gmail Lookup (direct mode)
    if context.user_data.get("awaiting_lookup"):
        bal = user_balances.get(user_id, 0)
        if bal < COST_LOOKUP:
            await update.message.reply_text("⚠️ Not enough balance. Please recharge first.")
            return
        user_balances[user_id] -= COST_LOOKUP
        context.user_data["awaiting_lookup"] = False
        result = generate_report(text)
        for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
            await update.message.reply_text(chunk, parse_mode="HTML")
        return

    # Track via Website (direct mode)
    if context.user_data.get("awaiting_track"):
        bal = user_balances.get(user_id, 0)
        if bal < COST_TRACK:
            await update.message.reply_text("⚠️ Not enough balance. Please recharge first.")
            return
        context.user_data["awaiting_track"] = False
        user_balances[user_id] -= COST_TRACK

        await update.message.reply_text("🔎 Checking site compatibility, please wait...")
        try:
            ok, reason = check_site_embeddable(text)
        except:
            await update.message.reply_text("⚠️ Unexpected error while validating site.")
            return

        if not ok:
            await update.message.reply_text(f"❌ Cannot embed site: {reason}")
            return

        personal = make_personal_link(user_id, text)
        await update.message.reply_text(
            f"✅ Site is valid!\n\nHere's your personal tracking link:\n\n<code>{personal}</code>\n\n"
            f"🤖 <i>Tracking technology provided by Drhero!</i>",
            parse_mode="HTML"
        )
        return

    # AI Chat Mode - Process natural language
    if context.user_data.get("ai_chat_active") or not (context.user_data.get("awaiting_lookup") or context.user_data.get("awaiting_track")):
        # Check if it's a direct command pattern (phone/email/URL)
        phone_pattern = r'(\+91\d{10}|\b\d{10}\b)'
        email_pattern = r'\b[\w\.-]+@[\w\.-]+\.\w+\b'
        url_pattern = r'https?://[^\s]+'
        
        if re.search(phone_pattern, text) or re.search(email_pattern, text):
            # Direct phone/email lookup request
            bal = user_balances.get(user_id, 0)
            if bal >= COST_LOOKUP:
                user_balances[user_id] -= COST_LOOKUP
                await update.message.reply_text("🔍 I found a phone/email in your message! Processing search...")
                result = generate_report(text)
                for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
                    await update.message.reply_text(chunk, parse_mode="HTML")
            else:
                await update.message.reply_text(
                    f"🔍 I see you want to search! But you need {COST_LOOKUP - bal} more credits. "
                    f"Please recharge using /buy\n\n🤖 <i>Drhero's AI at your service!</i>",
                    parse_mode="HTML"
                )
            return
        
        elif re.search(url_pattern, text):
            # Direct URL tracking request
            bal = user_balances.get(user_id, 0)
            if bal >= COST_TRACK:
                user_balances[user_id] -= COST_TRACK
                await update.message.reply_text("🌍 I found a URL! Processing website tracking...")
                try:
                    ok, reason = check_site_embeddable(text)
                    if ok:
                        personal = make_personal_link(user_id, text)
                        await update.message.reply_text(
                            f"✅ Tracking link created!\n\n<code>{personal}</code>\n\n"
                            f"🤖 <i>Powered by Drhero's brilliant technology!</i>",
                            parse_mode="HTML"
                        )
                    else:
                        await update.message.reply_text(f"❌ Cannot track this site: {reason}")
                except:
                    await update.message.reply_text("⚠️ Error processing website.")
            else:
                await update.message.reply_text(
                    f"🌍 I see a website! But you need {COST_TRACK - bal} more credits. "
                    f"Please recharge using /buy\n\n🤖 <i>Drhero's AI ready to help!</i>",
                    parse_mode="HTML"
                )
            return
        
        else:
            # General AI conversation including knowledge questions
            ai_response = ai_manager.generate_ai_response(text, user_id, user_balances)
            await update.message.reply_text(ai_response, parse_mode="HTML")
            return

# === Buttons ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "buy":
        await buy(update, context)
    elif query.data == "balance":
        await balance(update, context)
    elif query.data == "service_lookup":
        await service_lookup(update, context)
    elif query.data == "service_track":
        await service_track(update, context)
    elif query.data == "ai_chat":
        await ai_chat_mode(update, context)

# === MAIN ===
def main():
    # Start web server in a separate thread
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()
    
    # Start Telegram bot
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    # forward payment proofs
    application.add_handler(MessageHandler(filters.PHOTO, lambda u, c: u.message.forward(ADMIN_ID)))
    application.add_handler(MessageHandler(filters.Document.ALL, lambda u, c: u.message.forward(ADMIN_ID)))

    print("🤖 AI-Powered Knowledge Bot is running with web server...")
    print("🚀 Developed by the amazing Drhero!")
    application.run_polling()

if __name__ == "__main__":
    main()
