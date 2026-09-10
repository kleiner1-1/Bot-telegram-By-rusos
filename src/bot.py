import os, threading, requests, json, time, re
from html import unescape
from datetime import datetime
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeChat
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
API_KEY_DECOLECTA = os.getenv("DECOLECTA_API_KEY")
OWNER_ID = 8768048667
COST_RUNT = 10
COST_RUC = 10
DB_FILE = "users.json"
db_lock = threading.Lock()

COUNTRIES = {
    "CO": {"name": "🇨🇴 COLOMBIA"},
    "MX": {"name": "🇲🇽 MEXICO"},
    "EC": {"name": "🇪🇨 ECUADOR"},
    "VE": {"name": "🇻🇪 VENEZUELA"},
    "PE": {"name": "🇵🇪 PERU"},
    "OT": {"name": "🌎 OTROS"},
}

flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return f"Bot vivo - Owner {OWNER_ID}"
def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_db(data):
    with db_lock:
        with open(DB_FILE, 'w') as f: json.dump(data, f, indent=2)

def get_user(user_id):
    db = load_db()
    uid = str(user_id)
    if uid not in db:
        db[uid] = {"coins": 9999 if int(uid)==OWNER_ID else 0, "vip_until": 9999999999 if int(uid)==OWNER_ID else 0}
        save_db(db)
    return db[uid]

def is_vip(d): return d.get("vip_until",0) > time.time()
def can_afford(uid, cost):
    if uid==OWNER_ID: return True
    d=get_user(uid)
    if is_vip(d): return True
    return d.get("coins",0)>=cost
def deduct(uid, cost):
    if uid==OWNER_ID: return True
    db=load_db()
    suid=str(uid)
    if suid not in db: return False
    if is_vip(db[suid]): return True
    if db[suid]["coins"]>=cost:
        db[suid]["coins"]-=cost
        save_db(db)
        return True
    return False

# ================= API PERU =================
def consulta_ruc_pe(ruc):
    url = "https://api.decolecta.com/v1/sunat/ruc/full"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {API_KEY_DECOLECTA}"}
    try:
        r = requests.get(url, headers=headers, params={"numero": str(ruc).strip()}, timeout=25)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ================= SETUP COMMANDS =================
async def setup_commands(app: Application):
    user_commands = [
        BotCommand("start", "Acceso principal"),
        BotCommand("sys", "Panel por paises"),
        BotCommand("mycoins", "Ver saldo"),
        BotCommand("ruc", "Consultar RUC PE"),
        BotCommand("runt", "Consultar RUNT"),
    ]
    await app.bot.set_my_commands(user_commands)
    admin_commands = user_commands + [
        BotCommand("addcoins", "Dar coins [OWNER]"),
        BotCommand("addvip", "Dar VIP [OWNER]"),
        BotCommand("remvip", "Quitar VIP [OWNER]"),
        BotCommand("users", "Ver usuarios [OWNER]"),
    ]
    await app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=OWNER_ID))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d=get_user(update.effective_user.id)
    plan = "OWNER ∞" if update.effective_user.id==OWNER_ID else ("VIP" if is_vip(d) else "FREE")
    await update.message.reply_text(f"[ ACCESS GRANTED ]\nID : {update.effective_user.id}\nPLAN : {plan}\nCOINS : {d['coins']}\n> /sys panel por paises")

async def mycoins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d=get_user(update.effective_user.id)
    if update.effective_user.id==OWNER_ID:
        await update.message.reply_text(f"[ OWNER {OWNER_ID} ]\nCoins: ILIMITADO ∞")
    else:
        await update.message.reply_text(f"[ SALDO ] Plan: {'VIP' if is_vip(d) else 'FREE'} | Coins: {d['coins']}")

async def sys_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d=get_user(update.effective_user.id)
    txt=f"[ PANEL POR PAISES ]\nUSER: {update.effective_user.id} | Coins: {d['coins']}\nSelecciona país"
    kb=[
        [InlineKeyboardButton("🇨🇴 COLOMBIA", callback_data="country_CO"),
         InlineKeyboardButton("🇵🇪 PERU", callback_data="country_PE")],
        [InlineKeyboardButton("🇲🇽 MEXICO", callback_data="country_MX"),
         InlineKeyboardButton("🇪🇨 ECUADOR", callback_data="country_EC")],
    ]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb))

# --- Handlers RUC / RUNT (sin datos personales) ---
async def do_ruc(target, user_id, ruc):
    if not can_afford(user_id, COST_RUC):
        await target.message.reply_text(f"[ SIN COINS ] Necesitas {COST_RUC}")
        return
    await target.message.reply_text(f"[ RUC PE ] Consultando {ruc}... ⏳")
    data = consulta_ruc_pe(ruc)
    if data.get("error") or not data.get("razon_social"):
        await target.message.reply_text(f"[ RUC - {ruc} ] ❌ No encontrado")
        return
    deduct(user_id, COST_RUC)
    txt = f"[ RUC - {ruc} ] ✅\n🏢 {data.get('razon_social','N/A')}\n📊 {data.get('estado','N/A')}\n📍 {data.get('direccion','N/A')}"
    await target.message.reply_text(txt[:4000])

async def ruc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"🇵🇪 RUC ({COST_RUC} coins)\nEnviame RUC")
        return
    await do_ruc(update, update.effective_user.id, context.args[0])

async def addcoins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=OWNER_ID: return
    if len(context.args)<2: return
    db=load_db()
    tid, amt = context.args[0], int(context.args[1])
    if tid not in db: db[tid]={"coins":0,"vip_until":0}
    db[tid]["coins"]+=amt
    save_db(db)
    await update.message.reply_text(f"[ OK ] ID {tid} +{amt}")

async def addvip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=OWNER_ID: return
    db=load_db()
    tid, dias = context.args[0], int(context.args[1])
    if tid not in db: db[tid]={"coins":0,"vip_until":0}
    base=max(time.time(), db[tid].get("vip_until",0))
    db[tid]["vip_until"]=base+dias*86400
    save_db(db)
    await update.message.reply_text(f"[ VIP ] {tid} -> {dias} dias")

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    data=q.data
    if data.startswith("country_"):
        code=data.split("_")[1]
        await q.edit_message_text(f"Seleccionaste {COUNTRIES[code]['name']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Volver", callback_data="back")]]))
    elif data=="back":
        await sys_cmd(q, context)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app=Application.builder().token(TOKEN).post_init(setup_commands).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sys", sys_cmd))
    app.add_handler(CommandHandler("mycoins", mycoins_cmd))
    app.add_handler(CommandHandler("addcoins", addcoins_cmd))
    app.add_handler(CommandHandler("addvip", addvip_cmd))
    app.add_handler(CommandHandler("ruc", ruc_cmd))
    app.add_handler(CallbackQueryHandler(btn))
    print(f"Bot iniciado OWNER {OWNER_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
