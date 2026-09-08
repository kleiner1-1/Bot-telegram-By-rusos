import os, threading, requests, urllib3, json
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot vivo"
def run_flask(): flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
urllib3.disable_warnings()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    msg = f"""
╔══════════════════════╗
   🧬 𝗦𝗬𝗦𝗧𝗘𝗠 𝗩𝟯 - 𝗔𝗖𝗘𝗦𝗢 𝗖𝗢𝗡𝗖𝗘𝗗𝗜𝗗𝗢
╚══════════════════════╝
👤 𝗨𝗦𝗨𝗔𝗥𝗜𝗢: @{u.Lowwsad or 'anon'} 
🆔 𝗜𝗗: `{u.id}`
💎 𝗥𝗔𝗡𝗚𝗢: `FREE // VERIFIED`
━━━━━━━━━━━━━━━━━━━━━━
⚡ 𝗠𝗢𝗗𝗨𝗟𝗢𝗦 𝗔𝗖𝗧𝗜𝗩𝗢𝗦:
🇨🇴 [ RUI / SISBEN ] → /sisben
🚗 [ RUNT HISTORIAL ] → /runt
🧩 [ PANEL ] → /sys
━━━━━━━━━━━━━━━━━━━━━━
📡 𝗦𝗧𝗔𝗧𝗨𝗦: `ONLINE 🟢`
"""
    await update.message.reply_text(msg, parse_mode="Markdown")

async def sys_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🇨🇴 CONSULTAR SISBEN / RUI", callback_data="ask_sisben")],
        [InlineKeyboardButton("🚗 CONSULTAR RUNT", callback_data="ask_runt")],
        [InlineKeyboardButton("📞 SOPORTE", callback_data="soporte")]
    ]
    await update.message.reply_text("⚙️ **PANEL DE CONSULTAS**\nToca una opción:",
