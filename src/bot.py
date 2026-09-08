import os, threading, asyncio
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "Bot vivo"
def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# DEFINIDOS LOS 2 - ESTO ERA LO QUE FALTABA
CONTACTO_1 = "@Lowwsad"
CONTACTO_2 = "@Lowwsad"

SECCIONES = {
    "co": {"nombre": "🇨🇴 Colombia", "comandos": ["/co"]},
    "ve": {"nombre": "🇻🇪 Venezuela", "comandos": ["/ve"]},
    "ec": {"nombre": "🇪🇨 Ecuador", "comandos": ["/ec"]},
}

async def set_commands(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "Ver mi informacion y creditos"),
        BotCommand("sys", "Ver menu de comandos"),
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    name = u.username or u.first_name
    txt = (
        f"**BOT DE DOXEO MULTI-PAÍS**\n\n"
        f"SISTEMA ENFOCADO EN CONSULTAS RÁPIDAS Y ORGANIZADAS DE INFORMACIÓN EN DISTINTOS PAÍSES.\n\n"
        f"**TU INFORMACIÓN**\n\n"
        f"🆔 **ID:** `{u.id}`\n"
        f"👤 **USUARIO:** {name}\n"
        f"🎭 **ROL:** `FREE`\n"
        f"💳 **CRÉDITOS:** `0`\n"
        f"👑 **PREMIUM:** ❌\n\n"
        f"USA /sys PARA VER LOS COMANDOS DISPONIBLES PARA TI.\n\n"
        f"**COMPRA DE CRÉDITOS**\n"
        f"PARA COMPRAR CRÉDITOS CONTACTAR CON:\n"
        f"{CONTACTO_1} {CONTACTO_2}"
    )
    await update.message.reply_text(txt, parse_mode="Markdown")

async def sys_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton(v["nombre"], callback_data=f"s_{k}")] for k,v in SECCIONES.items()]
    await update.message.reply_text("👋 **Menú Principal**", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data.startswith("s_"):
        k = q.data.replace("s_","")
        kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="back")]]
        await q.edit_message_text(f"{SECCIONES[k]['nombre']}", reply_markup=InlineKeyboardMarkup(kb))
    else:
        kb = [[InlineKeyboardButton(v["nombre"], callback_data=f"s_{k}")] for k,v in SECCIONES.items()]
        await q.edit_message_text("👋 **Menú Principal**", reply_markup=InlineKeyboardMarkup(kb))

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if not TOKEN:
        print("ERROR: BOT_TOKEN no existe")
        return
    app = Application.builder().token(TOKEN).post_init(set_commands).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sys", sys_cmd))
    app.add_handler(CallbackQueryHandler(btn))
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()
