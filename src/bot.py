import os, threading, requests, urllib3, json
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
    await update.message.reply_text(
        f"ID: {update.effective_user.id}\n\nComandos:\n/sys - menu\n/sisben 1005190841\n/runt ABC123 1005190841"
    )

async def sys_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🇨🇴 Sisben / RUI", callback_data="co")],
        [InlineKeyboardButton("🚗 RUNT Historial", callback_data="runt")]
    ]
    await update.message.reply_text("Menu:", reply_markup=InlineKeyboardMarkup(kb))

async def sisben_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /sisben 1005190841")
        return
    cedula = context.args[0]
    await update.message.reply_text(f"Consultando RUI {cedula}...")
    try:
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://ventanillasocial.dnp.gov.co/"})
        url = "https://ventanillasocial.dnp.gov.co/Home/ObtenerDatosRUI"
        data = {"pNumDoc": cedula, "pTipDoc": "3"}
        r = s.post(url, data=data, verify=False, timeout=30)
        await update.message.reply_text(f"RUI {cedula}:\n{r.text[:4000]}")
    except Exception as e:
        await update.message.reply_text(f"Error Sisben (bloqueo IP Render): {e}\nUsa proxy colombiano.")

# --- NUEVO COMANDO RUNT ---
async def runt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Uso: /runt PLACA CEDULA\nEj: /runt ABC123 1005190841")
        return

    placa = context.args[0].upper().strip()
    cedula = context.args[1].strip()

    await update.message.reply_text(f"Consultando historial RUNT {placa} - {cedula}...")

    try:
        url = f"https://historialrunt.org/api/consultar.php?placa={placa}&documento={cedula}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.get(url, headers=headers, timeout=30)

        # mostrar codigo http
        if r.status_code!= 200:
            await update.message.reply_text(f"RUNT respondió con código {r.status_code}:\n{r.text[:2000]}")
            return

        try:
            data = r.json()
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
            await update.message.reply_text(f"🚗 RUNT {placa}:\n\n{pretty[:4000]}")
        except:
            # si no es json, manda texto plano
            await update.message.reply_text(f"🚗 RUNT {placa}:\n\n{r.text[:4000]}")

    except Exception as e:
        await update.message.reply_text(f"Error RUNT: {e}")

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "runt":
        await q.edit_message_text("Usa:\n/runt PLACA CEDULA\nEj: /runt ABC123 1005190841")
    else:
        await q.edit_message_text("Usa /sisben <cedula> o /runt <placa> <cedula>")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sys", sys_cmd))
    app.add_handler(CommandHandler("sisben", sisben_cmd))
    app.add_handler(CommandHandler("runt", runt_cmd))
    print("Bot iniciado con /runt")
    app.run_polling()

if __name__ == "__main__":
    main()
