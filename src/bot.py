import os, threading, asyncio, requests, urllib3
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "Bot vivo"
def run_flask(): app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
CONTACTO_1 = "@Sumersion"
CONTACTO_2 = "@Indolido"
urllib3.disable_warnings()

SECCIONES = {
    "co": {"nombre": "🇨🇴 Colombia - Sisben", "comandos": ["/sisben"]},
}

async def set_commands(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "Ver informacion"),
        BotCommand("sys", "Ver menu"),
        BotCommand("sisben", "Consulta Sisben"),
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    txt = f"**BOT MULTI-PAIS**\n\nID: `{u.id}`\nUSUARIO: {u.username}\nROL: FREE\n\nUsa /sys\nCompra: {CONTACTO_1} {CONTACTO_2}"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def sys_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton(v["nombre"], callback_data=f"s_{k}")] for k,v in SECCIONES.items()]
    await update.message.reply_text("Menu:", reply_markup=InlineKeyboardMarkup(kb))

async def sisben_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /sisben 1005190841")
        return
    cedula = context.args[0]
    await update.message.reply_text(f"Consultando {cedula}...")
    try:
        url = "https://ventanillasocial.dnp.gov.co/Home/ObtenerDatosRUI"
        headers = {"accept": "*/*","content-type": "application/x-www-form-urlencoded","origin": "https://ventanillasocial.dnp.gov.co","referer": "https://ventanillasocial.dnp.gov.co/","user-agent": "Mozilla/5.0"}
        data = {"pNumDoc": cedula, "pTipDoc": "3"}
        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(None, lambda: requests.post(url, headers=headers, data=data, verify=False, timeout=20))
        await update.message.reply_text(f"Resultado {cedula}:\n\n{r.text[:4000]}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "back":
        kb = [[InlineKeyboardButton(v["nombre"], callback_data=f"s_{k}")] for k,v in SECCIONES.items()]
        await q.edit_message_text("Menu:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        k = q.data.replace("s_","")
        kb = [[InlineKeyboardButton("⬅️ Volver", callback_data="back")]]
        await q.edit_message_text(f"{SECCIONES[k]['nombre']}\nUsa /sisben", reply_markup=InlineKeyboardMarkup(kb))

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application.builder().token(TOKEN).post_init(set_commands).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sys", sys_cmd))
    app.add_handler(CommandHandler("sisben", sisben_cmd))
    app.add_handler(CallbackQueryHandler(btn))
    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()
