import os, json, time, re, threading, logging, tempfile, requests, random
from datetime import datetime, timedelta
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
BOT_NAME = "DOXCOL"
BONUS_FIRST = 3
BONUS_REF = 1
DAILY_MIN, DAILY_MAX = 1, 5
DB_FILE = "users.json"
COST_RUNT, COST_RUC = 10, 10
FREE_DAILY_LIMIT = 3
CACHE_HOURS = 24
db_lock = threading.RLock()
cache = {} # {key: (data, timestamp)}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COUNTRIES = {"CO":"🇨🇴 COLOMBIA","PE":"🇵🇪 PERÚ","MX":"🇲🇽 MÉXICO","AR":"🇦🇷 ARGENTINA","CL":"🇨🇱 CHILE","EC":"🇪🇨 ECUADOR","VE":"🇻🇪 VENEZUELA","BO":"🇧🇴 BOLIVIA","BR":"🇧🇷 BRASIL","UY":"🇺🇾 URUGUAY","PY":"🇵🇾 PARAGUAY","PA":"🇵🇦 PANAMÁ","CR":"🇨🇷 COSTA RICA","DO":"🇩🇴 DOMINICANA","GT":"🇬🇹 GUATEMALA","HN":"🇭🇳 HONDURAS","SV":"🇸🇻 SALVADOR"}
ACTIVE_COUNTRIES = ["CO","PE"]

flask_app = Flask(__name__)
@flask_app.route("/")
def home(): return f"{BOT_NAME} activo"
def run_flask(): flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)), debug=False, use_reloader=False)

def load_db():
    with db_lock:
        if not os.path.exists(DB_FILE): return {}
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f: return json.load(f)
        except: return {}

def save_db(data):
    with db_lock:
        try:
            fd, tp = tempfile.mkstemp(dir=".", prefix="users_", suffix=".tmp")
            with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(data,f,indent=2,ensure_ascii=False)
            os.replace(tp, DB_FILE)
        except: logger.exception("save fail")

def get_user(uid):
    uid=str(uid); db=load_db()
    if uid not in db:
        db[uid]={"coins":9999 if int(uid)==OWNER_ID else 0,"vip_until":9999999999 if int(uid)==OWNER_ID else 0,"bonus_claimed":True if int(uid)==OWNER_ID else False,"first_seen":time.time(),"daily_last":0,"streak":0,"referrals":0,"referred_by":None,"daily_count":0,"daily_date":str(datetime.now().date()),"history":[]}
        save_db(db)
    return db[uid].copy()

def update_user(uid, fn):
    with db_lock:
        db=load_db(); uid=str(uid)
        if uid not in db: db[uid]={"coins":0,"vip_until":0,"bonus_claimed":True,"first_seen":time.time(),"daily_last":0,"streak":0,"referrals":0,"referred_by":None,"daily_count":0,"daily_date":str(datetime.now().date()),"history":[]}
        fn(db[uid]); save_db(db)

def is_vip(d): return d.get("vip_until",0) > time.time()
def get_plan(uid, d=None):
    if int(uid)==OWNER_ID: return "OWNER 👑"
    if d is None: d=get_user(uid)
    return "VIP 💎" if is_vip(d) else "FREE"

def can_afford(uid, cost):
    if int(uid)==OWNER_ID: return True
    d=get_user(uid)
    if is_vip(d): return True
    return d.get("coins",0) >= cost

def deduct(uid, cost):
    if int(uid)==OWNER_ID: return True
    ok=False
    def fn(u):
        nonlocal ok
        if is_vip(u): ok=True; return
        if u.get("coins",0) >= cost: u["coins"]-=cost; ok=True
    update_user(uid, fn); return ok

def add_history(uid, txt):
    def fn(u):
        h=u.get("history",[]); h.insert(0,f"{datetime.now().strftime('%d/%m %H:%M')} - {txt}"); u["history"]=h[:10]
    update_user(uid, fn)

def check_daily_limit(uid):
    d=get_user(uid)
    if is_vip(d) or int(uid)==OWNER_ID: return True
    today=str(datetime.now().date())
    if d.get("daily_date")!=today:
        update_user(uid, lambda u: (u.update({"daily_date":today,"daily_count":0})))
        return True
    return d.get("daily_count",0) < FREE_DAILY_LIMIT

def inc_daily_count(uid):
    def fn(u):
        today=str(datetime.now().date())
        if u.get("daily_date")!=today: u["daily_date"]=today; u["daily_count"]=0
        u["daily_count"]=u.get("daily_count",0)+1
    update_user(uid, fn)

def main_keyboard(uid):
    buy=f"https://t.me/{OWNER_USERNAME}"
    d=get_user(uid); coins="∞" if int(uid)==OWNER_ID else d.get("coins",0)
    kb=[
        [InlineKeyboardButton("🔍 Consultas", callback_data="panel")],
        [InlineKeyboardButton(f"💰 {coins}", callback_data="coins"), InlineKeyboardButton("💎 Plan", callback_data="plan")],
        [InlineKeyboardButton("🎁 Daily", callback_data="daily"), InlineKeyboardButton("👥 Referidos", callback_data="ref")],
        [InlineKeyboardButton("🛒 Comprar", url=buy), InlineKeyboardButton("📢 Canal", url=CHANNEL_LINK)],
    ]
    if int(uid)==OWNER_ID: kb.append([InlineKeyboardButton("⚙️ Owner", callback_data="owner")])
    return InlineKeyboardMarkup(kb)

def countries_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇨🇴 Colombia ✅", callback_data="country_CO"), InlineKeyboardButton("🇵🇪 Perú ✅", callback_data="country_PE")],
        [InlineKeyboardButton("🇲🇽 México 🚧", callback_data="country_MX"), InlineKeyboardButton("🇦🇷 Argentina 🚧", callback_data="country_AR")],
        [InlineKeyboardButton("🇨🇱 Chile 🚧", callback_data="country_CL"), InlineKeyboardButton("🇪🇨 Ecuador 🚧", callback_data="country_EC")],
        [InlineKeyboardButton("🇻🇪 Venezuela 🚧", callback_data="country_VE"), InlineKeyboardButton("🇧🇴 Bolivia 🚧", callback_data="country_BO")],
        [InlineKeyboardButton("⬅️ Inicio", callback_data="home")]
    ])

def country_keyboard(code):
    if code not in ACTIVE_COUNTRIES:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔔 Avísame", url=CHANNEL_LINK)],[InlineKeyboardButton("⬅️ Países", callback_data="panel")]])
    b=[]
    if code=="CO": b.append([InlineKeyboardButton(f"🚗 RUNT • {COST_RUNT}c", callback_data="runt_info")])
    if code=="PE": b.append([InlineKeyboardButton(f"🏢 RUC • {COST_RUC}c", callback_data="ruc_info")])
    b.append([InlineKeyboardButton("⬅️ Países", callback_data="panel")])
    return InlineKeyboardMarkup(b)

async def check_channel(context, uid):
    try:
        m=await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=uid)
        return m.status in ["member","administrator","creator"]
    except: return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user=update.effective_user
    if not user: return
    args=context.args
    uid=str(user.id)
    db=load_db()
    is_new=uid not in db
    # Referido
    if is_new and args and args[0].startswith("ref"):
        try:
            ref_id=args[0].replace("ref","")
            if ref_id!=uid and ref_id in db:
                update_user(uid, lambda u: u.update({"referred_by":ref_id}))
                update_user(ref_id, lambda u: (u.update({"coins":u.get("coins",0)+BONUS_REF,"referrals":u.get("referrals",0)+1})))
                await context.bot.send_message(int(ref_id), f"👥 ¡Nuevo referido! +{BONUS_REF} coin de {user.first_name} ({uid})")
        except: pass

    data=get_user(uid)
    if is_new and not data.get("bonus_claimed"):
        if not await check_channel(context, user.id):
            kb=[[InlineKeyboardButton("📢 Unirme", url=CHANNEL_LINK)],[InlineKeyboardButton(f"✅ Verificar +{BONUS_FIRST} coins", callback_data="check_join")]]
            await update.message.reply_text(f"<b>Hola {user.first_name} 👋</b>\nPara activar <b>{BOT_NAME}</b> únete a {CHANNEL_ID}\n\n🎁 <b>+{BONUS_FIRST} coins gratis</b>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(kb))
            return
        else:
            update_user(uid, lambda u: (u.update({"coins":u.get("coins",0)+BONUS_FIRST,"bonus_claimed":True})) if int(uid)!=OWNER_ID else u.update({"bonus_claimed":True}))

    data=get_user(uid)
    plan=get_plan(uid,data)
    coins="∞" if int(uid)==OWNER_ID else data.get('coins',0)
    ref_link=f"https://t.me/{context.bot.username}?start=ref{uid}"
    text=(f"<b>{BOT_NAME}</b>\n"
          f"Hola, {user.first_name} 👋\n"
          f"━━━━━━━━━━━━━━━\n"
          f"🆔 <code>{uid}</code> | 💎 {plan}\n"
          f"💰 Saldo: <b>{coins}</b> | 👥 Refs: {data.get('referrals',0)}\n"
          f"━━━━━━━━━━━━━━━\n"
          f"🔗 Tu link referido:\n<code>{ref_link}</code>\n"
          f"<i>Gana {BONUS_REF} coin por amigo</i>")
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=main_keyboard(user.id))

async def daily_cmd(update, context):
    uid=str(update.effective_user.id)
    d=get_user(uid)
    now=time.time()
    if now - d.get("daily_last",0) < 86400:
        left=86400-(now-d.get("daily_last",0))
        h=int(left//3600)
        await update.message.reply_text(f"⏳ Ya reclamaste hoy. Vuelve en {h}h")
        return
    win=random.randint(DAILY_MIN,DAILY_MAX)
    def fn(u):
        u["coins"]=u.get("coins",0)+win
        u["daily_last"]=now
        u["streak"]=u.get("streak",0)+1
    update_user(uid, fn)
    await update.message.reply_text(f"🎰 <b>RULETA DIARIA</b>\n\n¡Ganaste <b>{win} coins</b>! 🎉\nRacha: {d.get('streak',0)+1} días\n\nVuelve mañana.", parse_mode='HTML', reply_markup=main_keyboard(update.effective_user.id))

async def mycoins_cmd(update, context):
    d=get_user(update.effective_user.id); c="∞" if update.effective_user.id==OWNER_ID else d.get('coins',0)
    await update.message.reply_text(f"💰 Tienes <b>{c} coins</b>", parse_mode='HTML', reply_markup=main_keyboard(update.effective_user.id))

async def myplan_cmd(update, context):
    uid=update.effective_user.id; d=get_user(uid); plan=get_plan(uid,d)
    vip_txt="Activo ilimitado" if is_vip(d) else "No eres VIP - Límite 3/día"
    if d.get('vip_until',0)>time.time(): vip_txt=f"Expira {datetime.fromtimestamp(d['vip_until']).strftime('%d/%m/%Y')}"
    txt=(f"👤 <b>MI PLAN</b>\n━━━━━━━━━━━━━━━\n"
         f"🆔 <code>{uid}</code>\n💎 {plan}\n📅 {vip_txt}\n💰 {d.get('coins',0) if uid!=OWNER_ID else '∞'} coins\n👥 Referidos: {d.get('referrals',0)}\n"
         f"📊 Hoy: {d.get('daily_count',0)}/{FREE_DAILY_LIMIT} consultas\n"
         f"━━━━━━━━━━━━━━━\n<b>Historial:</b>\n" + ("\n".join(d.get('history',[])[:5]) or "Sin consultas"))
    await update.message.reply_text(txt, parse_mode='HTML', reply_markup=main_keyboard(uid))

async def sys_cmd(update, context):
    d=get_user(update.effective_user.id)
    text=(f"🌎 <b>{BOT_NAME} — PANEL</b>\n━━━━━━━━━━━━━━━\n"
          f"💎 {get_plan(update.effective_user.id,d)} | 💰 {d.get('coins',0) if update.effective_user.id!=OWNER_ID else '∞'}\n"
          f"✅ Disponible | 🚧 Próximamente\n"
          f"Selecciona país:")
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=countries_keyboard())

async def buy_cmd(update, context):
    buy=f"https://t.me/{OWNER_USERNAME}"
    await update.message.reply_text(f"🛒 <b>COMPRAR</b>\n50c=$5 | 150c=$10 | VIP 30d=$15\nTu ID: <code>{update.effective_user.id}</code>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Owner", url=buy)]]))

def get_cache(k):
    if k in cache:
        data, ts = cache[k]
        if time.time()-ts < CACHE_HOURS*3600: return data
        del cache[k]
    return None

def consulta_ruc_pe(ruc):
    ck=get_cache(f"ruc_{ruc}")
    if ck: return ck
    if not API_KEY_DECOLECTA: return None
    try:
        r=requests.get("https://api.decolecta.com/v1/sunat/ruc/full", headers={"Authorization": f"Bearer {API_KEY_DECOLECTA}"}, params={"numero": ruc}, timeout=20)
        if r.status_code==200:
            cache[f"ruc_{ruc}"]=(r.json(), time.time())
            return r.json()
    except: pass
    return None

def consulta_runt(placa):
    ck=get_cache(f"runt_{placa}")
    if ck: return ck
    try:
        r=requests.get("https://api.historialrunt.org/v2/consulta", params={"placa": placa}, timeout=20)
        if r.status_code==200:
            cache[f"runt_{placa}"]=(r.json(), time.time())
            return r.json()
    except: pass
    return None

async def do_ruc(target, uid, ruc):
    if not re.fullmatch(r"\d{11}", ruc): await target.message.reply_text("❌ RUC 11 dígitos"); return
    if not check_daily_limit(uid): await target.message.reply_text("🔒 Límite FREE 3/día alcanzado. Compra VIP /buy"); return
    if not can_afford(uid, COST_RUC): await target.message.reply_text(f"🔒 Necesitas {COST_RUC}c /buy"); return
    msg=await target.message.reply_text(f"🔎 RUC {ruc}...")
    data=consulta_ruc_pe(ruc)
    if not data or not data.get("razon_social"): await msg.edit_text("❌ No encontrado"); return
    if not deduct(uid, COST_RUC): await msg.edit_text("❌ Error coins"); return
    inc_daily_count(uid); add_history(uid, f"RUC {ruc}")
    await msg.edit_text(f"🏢 <b>RUC {ruc}</b>\n📌 {data.get('razon_social')}\n📊 {data.get('estado')}\n📍 {data.get('direccion','')}")

async def do_runt(target, uid, placa):
    placa=placa.upper()
    if not check_daily_limit(uid): await target.message.reply_text("🔒 Límite FREE 3/día alcanzado. /buy VIP"); return
    if not can_afford(uid, COST_RUNT): await target.message.reply_text(f"🔒 Necesitas {COST_RUNT}c /buy"); return
    msg=await target.message.reply_text(f"🚗 {placa}...")
    data=consulta_runt(placa)
    if not data or data.get("error"): await msg.edit_text("❌ No encontrado"); return
    if not deduct(uid, COST_RUNT): await msg.edit_text("❌ Error"); return
    inc_daily_count(uid); add_history(uid, f"RUNT {placa}")
    await msg.edit_text(f"🚗 <b>{placa}</b>\nMarca: {data.get('marca')} | Modelo: {data.get('modelo')}")

async def ruc_cmd(update, context):
    if not context.args: await update.message.reply_text("Uso: /ruc 20123456789"); return
    await do_ruc(update, update.effective_user.id, context.args[0])
async def runt_cmd(update, context):
    if not context.args: await update.message.reply_text("Uso: /runt ABC123"); return
    await do_runt(update, update.effective_user.id, context.args[0])

async def addcoins_cmd(update, context):
    if update.effective_user.id!=OWNER_ID: return
    try:
        tid, amt = str(int(context.args[0])), int(context.args[1])
    except: await update.message.reply_text("Uso: /addcoins ID CANT"); return
    update_user(tid, lambda u: u.update({"coins":u.get("coins",0)+amt}))
    await update.message.reply_text(f"✅ +{amt} a {tid}")

async def addvip_cmd(update, context):
    if update.effective_user.id!=OWNER_ID: return
    try: tid, days = str(int(context.args[0])), int(context.args[1])
    except: await update.message.reply_text("Uso: /addvip ID DIAS"); return
    def fn(u):
        base=max(time.time(), u.get("vip_until",0))
        u["vip_until"]=base+days*86400
    update_user(tid, fn)
    await update.message.reply_text(f"💎 VIP {tid} {days}d")

async def remvip_cmd(update, context):
    if update.effective_user.id!=OWNER_ID: return
    update_user(context.args[0], lambda u: u.update({"vip_until":0}))
    await update.message.reply_text("VIP removido")

async def users_cmd(update, context):
    if update.effective_user.id!=OWNER_ID: return
    db=load_db(); total=len(db)
    await update.message.reply_text(f"👥 {total} usuarios\nVIP: {sum(1 for v in db.values() if v.get('vip_until',0)>time.time())}")

async def btn(update, context):
    q=update.callback_query; await q.answer(); data=q.data
    if data=="panel":
        await q.edit_message_text(f"🌎 <b>{BOT_NAME} — Países</b>\n✅=Disponible 🚧=Pronto", parse_mode='HTML', reply_markup=countries_keyboard())
    elif data=="coins":
        d=get_user(q.from_user.id); c="∞" if q.from_user.id==OWNER_ID else d.get('coins',0)
        await q.edit_message_text(f"💰 {c} coins", reply_markup=main_keyboard(q.from_user.id))
    elif data=="plan":
        uid=q.from_user.id; d=get_user(uid); await q.edit_message_text(f"💎 Plan: {get_plan(uid,d)}\n💰 {d.get('coins',0)}c\nHoy: {d.get('daily_count',0)}/{FREE_DAILY_LIMIT}", reply_markup=main_keyboard(uid))
    elif data=="daily":
        await daily_cmd(q, context)
    elif data=="ref":
        uid=str(q.from_user.id); link=f"https://t.me/{context.bot.username}?start=ref{uid}"; d=get_user(uid)
        await q.edit_message_text(f"👥 <b>REFERIDOS</b>\nGanas {BONUS_REF}c por amigo\nTienes: {d.get('referrals',0)} refs\n\nTu link:\n<code>{link}</code>", parse_mode='HTML', reply_markup=main_keyboard(q.from_user.id))
    elif data=="home":
        d=get_user(q.from_user.id); await q.edit_message_text(f"<b>{BOT_NAME}</b> | 💰 {d.get('coins',0) if q.from_user.id!=OWNER_ID else '∞'}", parse_mode='HTML', reply_markup=main_keyboard(q.from_user.id))
    elif data=="owner":
        await q.edit_message_text("⚙️ <b>OWNER</b>\n/addcoins ID CANT\n/addvip ID DIAS\n/users", parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Inicio", callback_data="home")]]))
    elif data.startswith("country_"):
        code=data.split("_")[1]; name=COUNTRIES.get(code,code)
        if code in ACTIVE_COUNTRIES:
            await q.edit_message_text(f"{name}", reply_markup=country_keyboard(code))
        else:
            await q.edit_message_text(f"{name}\n\n🚧 <b>PRÓXIMAMENTE</b>\nÚnete a {CHANNEL_ID} para aviso.", parse_mode='HTML', reply_markup=country_keyboard(code))
    elif data=="runt_info": await q.edit_message_text(f"🚗 RUNT {COST_RUNT}c\nUsa: /runt PLACA", reply_markup=country_keyboard("CO"))
    elif data=="ruc_info": await q.edit_message_text(f"🏢 RUC {COST_RUC}c\nUsa: /ruc RUC", reply_markup=country_keyboard("PE"))
    elif data=="check_join":
        if await check_channel(context, q.from_user.id):
            update_user(q.from_user.id, lambda u: (u.update({"coins":u.get("coins",0)+BONUS_FIRST,"bonus_claimed":True})) if not u.get("bonus_claimed") else None)
            await q.edit_message_text(f"✅ +{BONUS_FIRST} coins! Usa /start")
        else: await q.answer("❌ Únete primero", show_alert=True)

def main():
    if not TOKEN: print("FALTA TOKEN"); return
    threading.Thread(target=run_flask, daemon=True).start()
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sys", sys_cmd))
    app.add_handler(CommandHandler("daily", daily_cmd))
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
    print("Bot V3 listo")
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__=="__main__": main()
