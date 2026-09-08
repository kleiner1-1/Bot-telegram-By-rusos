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
def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    txt = (
        "╔══════════════════════╗\n"
        " SYSTEM V3 - ACCESO CONCEDIDO\n"
        "╚══════════════════════╝\n\n"
        f"Usuario: @{u.username or 'anon'}\n"
        f"ID: {u.id}\n"
        "Rango: FREE // VERIFIED\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "MODULOS ACTIVOS:\n"
        " [RUI/SISBEN] -> /sisben\n"
        " [RUNT] -> /runt\n"
        " [PANEL] -> /sys\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "STATUS: ONLINE\n"
    )
    await update.message.reply_text(txt)

async def sys_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("CONSULTAR SISBEN / RUI", callback_data="ask_sisben")],
        [InlineKeyboardButton("CONSULTAR RUNT", callback_data="ask_runt")],
    ]
    await update.message.reply_text("PANEL DE CONSULTAS\nToca una opcion:", reply_markup=InlineKeyboardMarkup(kb))

async def do_sisben(target, cedula):
    try:
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://ventanillasocial.dnp.gov.co/"})
        r = s.post("https://ventanillasocial.dnp.gov.co/Home/ObtenerDatosRUI",
                   data={"pNumDoc": cedula, "pTipDoc": "3"}, verify=False, timeout=30)
        await target.message.reply_text(f"RUI {cedula}:\n{r.text[:4000]}")
    except Exception as e:
        await target.message.reply_text(f"Error Sisben: {e}")

async def sisben_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        context.user_data['awaiting'] = 'sisben'
        await update.message.reply_text("Uso: /sisben CEDULA\nEj: /sisben 1005190841")
        return
    await do_sisben(update, context.args[0])

async def do_runt(target, placa, cedula):
    try:
        url = f"https://historialrunt.org/api/consultar.php?placa={placa.upper()}&documento={cedula}"
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=30)
        try:
            data = r.json()
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
            await target.message.reply_text(f"RUNT {placa}:\n{pretty[:4000]}")
        except:
            await target.message.reply_text(f"RUNT {placa}:\n{r.text[:4000]}")
    except Exception as e:
        await target.message.reply_text(f"Error RUNT: {e}")

async def runt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        context.user_data['awaiting'] = 'runt'
        await update.message.reply_text("Uso: /runt PLACA CEDULA\nEj: /runt ABC123 1005190841")
        return
    await do_runt(update, context.args[0], context.args[1])

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "ask_sisben":
        context.user_data['awaiting'] = 'sisben'
        kb = [[InlineKeyboardButton("Volver", callback_data="back")]]
        await q.edit_message_text("SISBEN / RUI\nEnviame solo la cedula:\nEj: 1005190841", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data == "ask_runt":
        context.user_data['awaiting'] = 'runt'
        kb = [[InlineKeyboardButton("Volver", callback_data="back")]]
        await q.edit_message_text("RUNT HISTORIAL\nEnviame: PLACA CEDULA\nEj: ABC123 1005190841", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data == "back":
        kb = [
            [InlineKeyboardButton("CONSULTAR SISBEN / RUI", callback_data="ask_sisben")],
            [InlineKeyboardButton("CONSULTAR RUNT", callback_data="ask_runt")],
        ]
        await q.edit_message_text("PANEL DE CONSULTAS\nToca una opcion:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting = context.user_data.get('awaiting')
    text = update.message.text.strip()
    if not awaiting:
        return
    if awaiting == 'sisben':
        context.user_data['awaiting'] = None
        await do_sisben(update, text)
    elif awaiting == 'runt':
        parts = text.split()
        if len(parts) >= 2:
            context.user_data['awaiting'] = None
            await do_runt(update, parts[0], parts[1])
        else:
            await update.message.reply_text("Formato mal. Enviame: PLACA CEDULA")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sys", sys_cmd))
    app.add_handler(CommandHandler("sisben", sisben_cmd))
    app.add_handler(CommandHandler("runt", runt_cmd))
    app.add_handler(CallbackQueryHandler(btn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot iniciado")
    app.run_polling()

if __name__ == "__main__":
    main()
