import os
import asyncio
import threading
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# --- Servidor web para que funcione GRATIS en Render ---
app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Bot activo 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)
# -------------------------------------------------------

# Configura tus contactos de venta
CONTACTO_1 = "@Sumersion"
CONTACTO_2 = "@Indolido"

SECCIONES = {
    "archivos": {
        "nombre": "📁 Archivos", 
        "comandos": ["📤 /subir - Subir archivo", "📂 /misarchivos - Ver mis archivos"]
    },
    "herramientas": {
        "nombre": "🛠️ Herramientas", 
        "comandos": ["🌤️ /clima - Ver clima", "🌐 /traducir - Traducir texto"]
    },
    "utilidades": {
        "nombre": "⚙️ Utilidades", 
        "comandos": ["ℹ️ /info - Info del bot", "🆘 /ayuda - Ayuda"]
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nombre = user.username if user.username else user.first_name
    
    texto = (
        f"**BOT DE CONSULTAS MULTI-PAÍS**\n\n"
        f"SISTEMA ENFOCADO EN CONSULTAS RÁPIDAS Y ORGANIZADAS DE INFORMACIÓN EN DISTINTOS PAÍSES.\n\n"
        f"**TU INFORMACIÓN**\n\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"👤 **USUARIO:** {nombre}\n"
        f"🎭 **ROL:** `FREE`\n"
        f"💳 **CRÉDITOS:** `0`\n"
        f"👑 **PREMIUM:** ❌\n\n"
        f"USA /sys PARA VER LOS COMANDOS DISPONIBLES PARA TI.\n\n"
        f"**COMPRA DE CRÉDITOS**\n"
        f"PARA COMPRAR CRÉDITOS CONTACTAR CON:\n"
        f"{CONTACTO_1}  {CONTACTO_2}"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")

async def sys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(SECCIONES["archivos"]["nombre"], callback_data="seccion_archivos")],
        [InlineKeyboardButton(SECCIONES["herramientas"]["nombre"], callback_data="seccion_herramientas")],
        [InlineKeyboardButton(SECCIONES["utilidades"]["nombre"], callback_data="seccion_utilidades")],
    ]
    await update.message.reply_text(
        "👋 **Bienvenido al Menú Principal**\n\nSelecciona una sección:", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def boton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("seccion_"):
        key = data.replace("seccion_", "")
        seccion = SECCIONES.get(key)
        texto = "\n".join(seccion["comandos"])
        keyboard = [[InlineKeyboardButton("⬅️ Volver al Menú", callback_data="volver_menu")]]
