import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

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
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    main()
