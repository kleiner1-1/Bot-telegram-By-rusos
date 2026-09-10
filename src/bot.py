import os, json, time, re, threading, logging, tempfile, requests
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
API_KEY_DECOLECTA = os.getenv("DECOLECTA_API_KEY")
OWNER_ID = 8768048667
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "botdoxcol")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@botdoxcol")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/botdoxcol")
BONUS_FIRST = 3
DB_FILE = "users.json"
COST_RUNT, COST_RUC = 10, 10
db_lock = threading.RLock()

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

COUNTRIES = {"CO": "🇨🇴 COLOMBIA", "PE": "🇵🇪 PERÚ"}

flask_app = Flask(__name__)
@flask_app.route("/")
def home(): return "Bot activo @botdoxcol"
def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)), debug=False, use_reloader=False)

def load_db():
    with db_lock:
        if not os.path.exists(DB_FILE): return {}
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except: return {}

def save_db(data):
    with db_lock:
        directory = os.path.dirname(os.path.abspath(DB_FILE)) or "."
        try:
            fd, temp_path = tempfile.mkstemp(dir=directory, prefix="users_", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, DB_FILE)
        except Exception:
            logger.exception("Error guardando DB")

def get_user(user_id):
    uid = str(user_id)
    with db_lock:
        db = load_db()
        if uid not in db:
            db[uid] = {"coins": 9999 if user_id == OWNER_ID else 0, "vip_until": 9999999999 if user_id == OWNER_ID else 0, "bonus_claimed": True if user_id == OWNER_ID else False, "first_seen": time.time()}
            save_db(db)
        return db[uid].copy()

def is_vip(data): return data.get("vip_until", 0) > time.time()
def get_plan(user_id, data=None):
    if user_id == OWNER_ID: return "OWNER ∞"
    if data is None: data = get_user(user_id)
    return "VIP 💎" if is_vip(data) else "FREE"

def can_afford(user_id, cost):
    if user_id == OWNER_ID: return True
    data = get_user(user_id)
    if is_vip(data): return True
    return data.get("coins", 0) >= cost

def deduct(user_id, cost):
    if user_id == OWNER_ID: return True
    with db_lock:
        db = load_db()
        uid = str(user_id)
        if uid not in db or is_vip(db[uid]): return uid in db
        if db[uid].get("coins",0) < cost: return False
        db[uid]["coins"] -= cost
        save_db(db)
        return True

# --- TECLADOS ESTÉTICOS ---
def main_keyboard(user_id):
    buy_url = f"https://t.me/{OWNER_USERNAME}"
    buttons = [
        [InlineKeyboardButton("🌎 PANEL DE CONSULTAS", callback_data="panel")],
        [InlineKeyboardButton("💰 SALDO", callback_data="coins"), InlineKeyboardButton("👤 MI PLAN", callback_data="plan")],
        [InlineKeyboardButton("🛒 COMPRAR COINS / VIP", url=buy_url)],
        [InlineKeyboardButton("📢 CANAL OFICIAL", url=CHANNEL_LINK)]
    ]
    if user_id == OWNER_ID:
        buttons.append([InlineKeyboardButton("⚙️ PANEL OWNER", callback_data="owner")])
    return InlineKeyboardMarkup(buttons)

def countries_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇨🇴 COLOMBIA", callback_data="country_CO"), InlineKeyboardButton("🇵🇪 PERÚ", callback_data="country_PE")],
        [InlineKeyboardButton("🏠 INICIO", callback_data="home")]
    ])

def owner_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 VER USUARIOS", callback_data="owner_users")],
        [InlineKeyboardButton("🏠 INICIO", callback_data="home")]
    ])

def country_keyboard(code):
    buttons = []
    if code == "CO": buttons.append([InlineKeyboardButton(f"🚗 RUNT — {COST_RUNT} coins", callback_data="runt_info")])
    elif code == "PE": buttons.append([InlineKeyboardButton(f"🏢 RUC — {COST_RUC} coins", callback_data="ruc_info")])
    buttons.append([InlineKeyboardButton("‹ PAÍSES", callback_data="panel"), InlineKeyboardButton("🏠 INICIO", callback_data="home")])
    return InlineKeyboardMarkup(buttons)

async def check_channel(context, user_id):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return True

# --- START CON CANAL + 3 COINS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user: return
    db = load_db()
    is_new = str(user.id) not in db
    data = get_user(user.id)

    if is_new and not data.get("bonus_claimed"):
        if not await check_channel(context, user.id):
            kb = [[InlineKeyboardButton(f"📢 Unirse a {CHANNEL_ID}", url=CHANNEL_LINK)],
                  [InlineKeyboardButton(f"✅ Ya me uní - Reclamar {BONUS_FIRST} coins", callback_data="check_join")]]
            await update.message.reply_text(
                f"🔐 <b>ACCESO RESTRINGIDO</b>\n\n"
                f"Para activar tu bot debes seguir nuestro canal oficial\n"
                f"{CHANNEL_ID}\n\n"
                f"🎁 <b>Recompensa:</b> {BONUS_FIRST} coins GRATIS\n\n"
                f"<i>Paso 1:</i> Únete\n<i>Paso 2:</i> Pulsa 'Ya me uní'",
                parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb)
            )
            return
        else:
            with db_lock:
                db = load_db()
                uid = str(user.id)
                if uid in db and not db[uid].get("bonus_claimed"):
                    if user.id!= OWNER_ID:
                        db[uid]["coins"] += BONUS_FIRST
                    db[uid]["bonus_claimed"] = True
                    save_db(db)
            await update.message.reply_text(f"🎉 ¡Bienvenido a @botdoxcol! +{BONUS_FIRST} coins acreditados")

    data = get_user(user.id)
    plan = get_plan(user.id, data)
    coins_text = "ILIMITADO ∞" if user.id == OWNER_ID else str(data.get("coins", 0))
    text = f"┏━━━━━━━━━━━━━━━┓\n┃ <b>@botdoxcol CENTER v2</b> ┃\n┗━━━━━━━━━━━━━━━┛\n\n👤 <b>Usuario:</b> {user.first_name}\n🆔 <b>ID:</b> <code>{user.id}</code>\n💎 <b>Plan:</b> {plan}\n🪙 <b>Saldo:</b> {coins_text}\n━━━━━━━━━━━━━━━━\n📡 Canal: {CHANNEL_ID}"
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=main_keyboard(user.id))

async def mycoins_cmd(update, context):
    data = get_user(update.effective_user.id)
    c = "ILIMITADO ∞" if update.effective_user.id == OWNER_ID else data.get("coins",0)
    await update.message.reply_text(f"💰 <b>Saldo:</b> {c}", parse_mode='HTML')

async def myplan_cmd(update, context):
    data = get_user(update.effective_user.id)
    await update.message.reply_text(f"Plan: {get_plan(update.effective_user.id, data)}")

async def sys_cmd(update, context):
    data = get_user(update.effective_user.id)
    await update.message.reply_text(f"🌎 <b>SYSTEM PANEL @botdoxcol</b>\n🪙 {data.get('coins',0)} coins", parse_mode='HTML', reply_markup=countries_keyboard())

async def buy_cmd(update, context):
    buy_url = f"https://t.me/{OWNER_USERNAME}"
    kb = [[InlineKeyboardButton("💬 HABLAR CON EL OWNER", url=buy_url)]]
    await update.message.reply_text(
        f"🛒 <b>COMPRAR COINS @botdoxcol</b>\n\n"
        f"💰 <b>Precios:</b>\n"
        f"• 50 coins = $5 USD\n"
        f"• 150 coins = $10 USD\n"
        f"• VIP 30 días = $15 USD (ilimitado)\n\n"
        f"📩 Pulsa el botón y te atiendo directo.\n"
        f"Tu ID: <code>{update.effective_user.id}</code>",
        parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb)
    )

def consulta_ruc_pe(ruc):
    if not API_KEY_DECOLECTA: return None
    try:
        r = requests.get("https://api.decolecta.com/v1/sunat/ruc/full", headers={"Accept":"application/json","Authorization": f"Bearer {API_KEY_DECOLECTA}"}, params={"numero": str(ruc).strip()}, timeout=25)
        if r.status_code!= 200: return None
        return r.json()
    except: return None

def consulta_runt(placa):
    try:
        r = requests.get("https://api.historialrunt.org/v2/consulta", params={"placa": placa.upper().strip()}, timeout=25)
        if r.status_code!= 200: return None
        return r.json()
    except: return None

async def do_ruc(target, user_id, ruc):
    ruc = str(ruc).strip()
    if not re.fullmatch(r"\d{11}", ruc):
        await target.message.reply_text("❌ RUC inválido, deben ser 11 números"); return
    if not can_afford(user_id, COST_RUC):
        await target.message.reply_text(f"🔒 Sin coins, necesitas {COST_RUC}. Usa /buy", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 COMPRAR", url=f"https://t.me/{OWNER_USERNAME}")]])); return
    msg = await target.message.reply_text(f"🔎 Consultando RUC {ruc}...")
    data = consulta_ruc_pe(ruc)
    if not data or not data.get("razon_social"):
        await msg.edit_text(f"❌ RUC {ruc} no encontrado"); return
    if not deduct(user_id, COST_RUC):
        await msg.edit_text("❌ Error descontando"); return
    await msg.edit_text(f"┏━━━━ 🏢 RUC {ruc} ━━━━┓\n📌 {data.get('razon_social')}\n📊 {data.get('estado','N/A')}\n📍 {data.get('direccion','N/A')}\n┗━━━━━━━━━━━━━━━┛")

async def do_runt(target, user_id, placa):
    placa = str(placa).strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{5,7}", placa):
        await target.message.reply_text("❌ Placa inválida"); return
    if not can_afford(user_id, COST_RUNT):
        await target.message.reply_text(f"🔒 Sin coins, necesitas {COST_RUNT}. Usa /buy", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 COMPRAR", url=f"https://t.me/{OWNER_USERNAME}")]])); return
    msg = await target.message.reply_text(f"🚗 Consultando {placa}...")
    data = consulta_runt(placa)
    if not data or data.get("error"):
        await msg.edit_text(f"❌ Placa {placa} no encontrada"); return
    if not deduct(user_id, COST_RUNT):
        await msg.edit_text("❌ Error descontando"); return
    await msg.edit_text(f"┏━━━━ 🚗 RUNT {placa} ━━━━┓\n🏷️ Marca: {data.get('marca','N/A')}\n📅 Modelo: {data.get('modelo','N/A')}\n📋 Línea: {data.get('linea','N/A')}\n┗━━━━━━━━━━━━━━━┛")

async def ruc_cmd(update, context):
    if not context.args:
        await update.message.reply_text("Uso: /ruc 20123456789"); return
    await do_ruc(update, update.effective_user.id, context.args[0])

async def runt_cmd(update, context):
    if not context.args:
        await update.message.reply_text("Uso: /runt ABC123"); return
    await do_runt(update, update.effective_user.id, context.args[0])

async def addcoins_cmd(update, context):
    if update.effective_user.id!= OWNER_ID: return
    try:
        tid, amt = str(int(context.args[0])), int(context.args[1])
    except: await update.message.reply_text("Uso: /addcoins ID CANTIDAD"); return
    with db_lock:
        db = load_db()
        if tid not in db: db[tid] = {"coins":0,"vip_until":0,"bonus_claimed":True,"first_seen":time.time()}
        db[tid]["coins"] += amt
        save_db(db)
    await update.message.reply_text(f"✅ +{amt} a <code>{tid}</code>", parse_mode='HTML')

async def addvip_cmd(update, context):
    if update.effective_user.id!= OWNER_ID: return
    try:
        tid, days = str(int(context.args[0])), int(context.args[1])
    except: await update.message.reply_text("Uso: /addvip ID DIAS"); return
    with db_lock:
        db = load_db()
        if tid not in db: db[tid] = {"coins":0,"vip_until":0,"bonus_claimed":True,"first_seen":time.time()}
        base = max(time.time(), db[tid].get("vip_until",0))
        db[tid]["vip_until"] = base + days*86400
        save_db(db)
    await update.message.reply_text(f"💎 VIP {tid} por {days} días")

async def remvip_cmd(update, context):
    if update.effective_user.id!= OWNER_ID: return
    if not context.args: return
    tid = str(context.args[0])
    with db_lock:
        db = load_db()
        if tid in db:
            db[tid]["vip_until"] = 0
            save_db(db)
    await update.message.reply_text(f"VIP removido: {tid}")

async def users_cmd(update, context):
    if update.effective_user.id!= OWNER_ID: return
    db = load_db()
    total=len(db); vip=sum(1 for v in db.values() if v.get("vip_until",0)>time.time()); con_coins=sum(1 for v in db.values() if v.get("coins",0)>0)
    txt = f"📊 <b>BOTDOXCOL STATS</b>\n👥 Total: {total}\n💎 VIP: {vip}\n🪙 Con coins: {con_coins}\n🆓 Gratis: {total-con_coins-vip}\n\n<b>Últimos 20:</b>\n"
    for uid, info in list(db.items())[-20:]: txt += f"<code>{uid}</code> | {info.get('coins',0)}c | {'VIP' if info.get('vip_until',0)>time.time() else 'FREE'}\n"
    await update.message.reply_text(txt, parse_mode='HTML')

async def btn(update, context):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data == "panel":
        await q.edit_message_text("🌎 Selecciona país:", reply_markup=countries_keyboard())
    elif data == "coins":
        d = get_user(q.from_user.id); await q.edit_message_text(f"🪙 Coins: {d.get('coins',0)}", reply_markup=main_keyboard(q.from_user.id))
    elif data.startswith("country_"):
        code = data.split("_")[1]; await q.edit_message_text(f"{COUNTRIES.get(code,code)}", reply_markup=country_keyboard(code))
    elif data == "home":
        d = get_user(q.from_user.id); await q.edit_message_text(f"ID: {q.from_user.id} | Coins: {d.get('coins',0)}", reply_markup=main_keyboard(q.from_user.id))
    elif data == "owner":
        await q.edit_message_text("⚙️ <b>PANEL OWNER</b>\n/addcoins ID CANT\n/addvip ID DIAS\n/remvip ID\n/users\n/buy", parse_mode='HTML', reply_markup=owner_keyboard())
    elif data == "owner_users":
        db=load_db(); total=len(db); await q.edit_message_text(f"👥 {total} usuarios. Usa /users para detalle", reply_markup=owner_keyboard())
    elif data == "runt_info":
        await q.edit_message_text(f"🚗 RUNT {COST_RUNT} coins\nUsa: /runt PLACA", reply_markup=country_keyboard("CO"))
    elif data == "ruc_info":
        await q.edit_message_text(f"🏢 RUC {COST_RUC} coins\nUsa: /ruc RUC", reply_markup=country_keyboard("PE"))
    elif data == "check_join":
        if await check_channel(context, q.from_user.id):
            with db_lock:
                db = load_db(); uid=str(q.from_user.id)
                if uid in db and not db[uid].get("bonus_claimed"):
                    db[uid]["coins"] += BONUS_FIRST; db[uid]["bonus_claimed"]=True; save_db(db)
                    await q.edit_message_text(f"✅ Verificado @botdoxcol | +{BONUS_FIRST} coins. Usa /start")
                else:
                    await q.edit_message_text("✅ Ya reclamaste tu bonus. Usa /start")
        else:
            await q.answer("❌ Aún no te has unido a @botdoxcol", show_alert=True)

def main():
    if not TOKEN:
        print("❌ FALTA BOT_TOKEN en Environment de Render")
        return
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sys", sys_cmd))
    app.add_handler(CommandHandler("mycoins", mycoins_cmd))
    app.add_handler(CommandHandler("myplan", myplan_cmd))
    app.add_handler(CommandHandler("buy", buy_cmd))
    app.add_handler(CommandHandler("ruc", ruc_cmd))
    app.add_handler(CommandHandler("runt", runt_cmd))
    app.add_handler(CommandHandler("addcoins", addcoins_cmd))
    app.add_handler(CommandHandler("addvip", addvip_cmd))
    app.add_handler(CommandHandler("remvip", remvip_cmd))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CallbackQueryHandler(btn))
    print(f"Bot @botdoxcol iniciado OWNER {OWNER_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
