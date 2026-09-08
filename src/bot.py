import os
import threading
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "Bot activo 24/7"
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)

CONTACTO_1 = "@Lowwsad"

SECCIONES = {
    "archivos": {"nombre": "📁 Archivos", "comandos": ["📤 /subir", "📂 /misarchivos"]},
    "herramientas": {"nombre": "🛠️ Herramientas", "comandos": ["🌤️ /clima", "🌐 /traducir"]},
    "utilidades": {"nombre": "⚙️ Utilidades", "comandos": ["ℹ️ /info", "🆘 /ayuda"]}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nombre = user.username or user.first_name
    texto = f"**BOT DE CONSULTAS MULTI-PAÍS**\n\nSISTEMA ENFOCADO EN CONSULTAS RÁPIDAS Y ORGANIZADAS DE INFORMACIÓN EN DISTINTOS PAÍSES.\n\n**TU INFORMACIÓN**\n\n🆔 **ID:** `{user.id}`\n👤 **USUARIO:** {nombre}\n🎭 **ROL:** `FREE`\n💳 **CRÉDITOS:** `0`\n👑 **PREMIUM:** ❌\n\nUSA /sys PARA VER LOS COMANDOS DISPONIBLES PARA TI.\n\n**COMPRA DE CRÉDITOS**\nPARA COMPRAR CRÉDITOS CONTACTAR CON:\n{CONTACTO_1} {CONTACTO_2}"
    await update.message.reply_text(texto, parse_mode="Markdown")

async def sys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(v["nombre"], callback_data=f"seccion_{k}")] for k,v in SECCIONES.items()]
    await update.message.reply_text("👋 **Menú Principal**\n\nSelecciona una sección:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def boton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("seccion_"):
        key = data.replace("seccion_", "")
        texto = "\n".join(SECCIONES[key]["comandos"])
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data="volver")]]
        await query.edit_message_text(f"{SECCIONES[key]['nombre']}\n\n{texto}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data == "volver":
        keyboard = [[InlineKeyboardButton(v["nombre"], callback_data=f"seccion_{k}")] for k,v in SECCIONES.items()]
        await query.edit_message_text("👋 **Menú Principal**\n\nSelecciona una sección:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def main():
    print(f"Token cargado: {'SI' if TOKEN else 'NO - FALTA BOT_TOKEN EN RENDER'}")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sys", sys_command))
    app.add_handler(CallbackQueryHandler(boton_callback))
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()
