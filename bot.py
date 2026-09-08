import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

SECCIONES = {
    "archivos": {
        "nombre": "📁 Archivos",
        "comandos": [
            "/subir - Subir archivo grande",
            "/misarchivos - Ver mis archivos",
            "/descargar - Descargar por ID"
        ]
    },
    "herramientas": {
        "nombre": "🛠️ Herramientas",
        "comandos": [
            "/clima - Ver clima",
            "/traducir - Traducir texto",
            "/qr - Crear QR"
        ]
    },
    "utilidades": {
        "nombre": "⚙️ Utilidades",
        "comandos": [
            "/info - Info del bot",
            "/ayuda - Ayuda general",
            "/contacto - Contacto"
        ]
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(SECCIONES["archivos"]["nombre"], callback_data="seccion_archivos")],
        [InlineKeyboardButton(SECCIONES["herramientas"]["nombre"], callback_data="seccion_herramientas")],
        [InlineKeyboardButton(SECCIONES["utilidades"]["nombre"], callback_data="seccion_utilidades")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 *Bienvenido al Menú Principal*\n\nSelecciona una sección:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def boton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("seccion_"):
        key = data.replace("seccion_", "")
        seccion = SECCIONES.get(key)
        texto_comandos = "\n".join(seccion["comandos"])
        mensaje = f"{seccion['nombre']}\n\n*Comandos disponibles:*\n{texto_comandos}"
        keyboard = [[InlineKeyboardButton("⬅️ Volver al Menú", callback_data="volver_menu")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "volver_menu":
        keyboard = [
            [InlineKeyboardButton(SECCIONES["archivos"]["nombre"], callback_data="seccion_archivos")],
            [InlineKeyboardButton(SECCIONES["herramientas"]["nombre"], callback_data="seccion_herramientas")],
            [InlineKeyboardButton(SECCIONES["utilidades"]["nombre"], callback_data="seccion_utilidades")],
        ]
        await query.edit_message_text(
            "👋 *Bienvenido al Menú Principal*\n\nSelecciona una sección:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

def main():
    if not TOKEN:
        print("ERROR: No hay BOT_TOKEN en .env")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(boton_callback))
    print("Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
