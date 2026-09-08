import os, threading, requests, urllib3
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "Bot vivo"
def run_flask(): flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

urllib3.disable_warnings()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"ID: {update.effective_user.id}\nUsa /sys y /sisben 1005190841")

async def sys_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🇨🇴 Colombia - Sisben", callback_data="co")]]
    await update.message.reply_text("Menu:", reply_markup=InlineKeyboardMarkup(kb))

async def sisben_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /sisben 1005190841")
        return
    cedula = context.args[0]
    await update.message.reply_text(f"Consultando {cedula}...")
    try:
        url = "https://ventanillasocial.dnp.gov.co/Home/ObtenerDatosRUI"
        headers = {"content-type": "application/x-www-form-urlencoded","origin": "https://ventanillasocial.dnp.gov.co","referer": "https://ventanillasocial.dnp.gov.co/"}
        data = {"pNumDoc": cedula, "pTipDoc": "3"}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=20)
        await update.message.reply_text(f"{cedula}:\n{r.text[:4000]}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("Usa /sisben <cedula>")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sys", sys_cmd))
    app.add_handler(CommandHandler("sisben", sisben_cmd))
    app.add_handler(CallbackQueryHandler(btn))
    print("Bot iniciado")
    app.run_polling()

if __name__ == "__main__":
    main()
