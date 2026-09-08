import os
import asyncio
import threading
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Mini servidor web para que Render Gratis no se apague
app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Bot activo 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)

SECCIONES = {
    "archivos": {"nombre": "📁 Archivos", "comandos": ["/subir", "/misarchivos", "/descargar"]},
    "herramientas": {"nombre": "🛠️ Herramientas", "comandos": ["/clima", "/traducir", "/qr"]},
    "utilidades": {"nombre": "⚙️ Utilidades", "comandos": ["/info", "/ayuda", "/contacto"]}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(SECCIONES["archivos"]["nombre"], callback_data="seccion_archivos")],
        [InlineKeyboardButton(SECCIONES["herramientas"]["nombre"], callback_data="seccion_herramientas")],
        [InlineKeyboardButton(SECCIONES["utilidades"]["nombre"], callback_data="seccion_utilidades")],
    ]
    await update.message.reply_text("👋 *Bienvenido al Menú Principal*\n\nSelecciona una sección:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def boton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("seccion_"):
        key = data.replace("seccion_", "")
        seccion = SECCIONES.get(key)
        texto = "\n".join(seccion["comandos"])
        keyboard = [[InlineKeyboardButton("⬅️ Volver al Menú", callback_data="volver_menu")]]
        await query.edit_message_text(f"{seccion['nombre']}\n\n{texto}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif data == "volver_menu":
        keyboard = [
            [InlineKeyboardButton(SECCIONES["archivos"]["nombre"], callback_data="seccion_archivos")],
            [InlineKeyboardButton(SECCIONES["herramientas"]["nombre"], callback_data="seccion_herramientas")],
            [InlineKeyboardButton(SECCIONES["utilidades"]["nombre"], callback_data="seccion_utilidades")],
        ]
        await query.edit_message_text("👋 *Bienvenido al Menú Principal*\n\nSelecciona una sección:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(boton_callback))
    print("Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    main()
