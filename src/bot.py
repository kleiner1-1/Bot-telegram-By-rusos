import os, threading, requests, urllib3, json, time, re
from html import unescape
from datetime import datetime
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeChat
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

OWNER_ID = 8768048667
COST_SISBEN = 5
COST_RUNT = 10
COST_RUC = 10
COST_DNIPE = 8
DB_FILE = "users.json"

API_KEY_DECOLECTA = "sk_19272.V8Z6VdfAkdjg5teDriucciqmHRi9rbkK"

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
def home(): return f"Bot vivo - Owner {OWNER_ID}"
def run_flask(): flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
urllib3.disable_warnings()

def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except: return {}
def save_db(data):
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

def consulta_dni_pe(dni):
    url = "https://api.decolecta.com/v1/reniec/dni"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {API_KEY_DECOLECTA}"}
    try:
        r = requests.get(url, headers=headers, params={"numero": str(dni).strip()}, timeout=25)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

async def setup_commands(app: Application):
    user_commands = [
        BotCommand("start", "Acceso principal"),
        BotCommand("sys", "Panel por paises"),
        BotCommand("mycoins", "Ver saldo"),
        BotCommand("sisben", "Consultar SISBEN"),
        BotCommand("runt", "Consultar RUNT (solo placa)"),
        BotCommand("ruc", "Consultar RUC PE 🇵🇪"),
        BotCommand("dnipe", "Consultar DNI PE 🇵🇪"),
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
    await update.message.reply_text(f"[ ACCESS GRANTED ]\n━━━━━━━━━━━━━━━\nID : {update.effective_user.id}\nPLAN : {plan}\nCOINS : {d['coins']}\n━━━━━━━━━━━━━━━\n> /sys panel por paises")

async def mycoins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d=get_user(update.effective_user.id)
    if update.effective_user.id==OWNER_ID:
        await update.message.reply_text(f"[ OWNER {OWNER_ID} ]\nCoins: ILIMITADO ∞")
    else:
        await update.message.reply_text(f"[ SALDO ] Plan: {'VIP' if is_vip(d) else 'FREE'} | Coins: {d['coins']}")

async def addcoins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=OWNER_ID:
        await update.message.reply_text("[ DENIED ] Solo OWNER")
        return
    if len(context.args)<2:
        await update.message.reply_text("Uso obligatorio con ID:\n/addcoins ID CANTIDAD\nEj: /addcoins 123456 50")
        return
    db=load_db()
    tid, amt = context.args[0], int(context.args[1])
    if tid not in db: db[tid]={"coins":0,"vip_until":0}
    db[tid]["coins"]+=amt
    save_db(db)
    await update.message.reply_text(f"[ OK ] ID {tid} +{amt} coins\nNuevo saldo: {db[tid]['coins']}")

async def addvip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=OWNER_ID: return
    if len(context.args)<2:
        await update.message.reply_text("Uso: /addvip ID DIAS")
        return
    db=load_db()
    tid, dias = context.args[0], int(context.args[1])
    if tid not in db: db[tid]={"coins":0,"vip_until":0}
    base=max(time.time(), db[tid].get("vip_until",0))
    db[tid]["vip_until"]=base+dias*86400
    save_db(db)
    await update.message.reply_text(f"[ VIP ] {tid} -> {dias} dias")
async def remvip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=OWNER_ID: return
    db=load_db()
    tid=context.args[0]
    if tid in db:
        db[tid]["vip_until"]=0
        save_db(db)
        await update.message.reply_text(f"[ VIP REMOVIDO ] {tid}")
async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!=OWNER_ID: return
    db=load_db()
    txt=f"[ USERS {len(db)} ]\n"
    for uid,info in list(db.items())[-15:]:
        txt+=f"{uid} | {info['coins']} coins\n"
    await update.message.reply_text(txt)

async def sys_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d=get_user(update.effective_user.id)
    txt=f"[ PANEL POR PAISES ]\n━━━━━━━━━━━━━━━\nUSER: {update.effective_user.id} | Coins: {d['coins']}\n━━━━━━━━━━━━━━━\nSelecciona país"
    kb=[
        [InlineKeyboardButton("🇨🇴 COLOMBIA", callback_data="country_CO"),
         InlineKeyboardButton("🇵🇪 PERU", callback_data="country_PE")],
        [InlineKeyboardButton("🇲🇽 MEXICO", callback_data="country_MX"),
         InlineKeyboardButton("🇪🇨 ECUADOR", callback_data="country_EC")],
        [InlineKeyboardButton("🇻🇪 VENEZUELA", callback_data="country_VE"),
         InlineKeyboardButton("🌎 OTROS", callback_data="country_OT")],
    ]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb))

# --- SISBEN ---
async def do_sisben(target, user_id, cedula):
    if not can_afford(user_id, COST_SISBEN):
        await target.message.reply_text(f"[ SIN COINS ] Necesitas {COST_SISBEN}")
        return
    try:
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0","Referer":"https://ventanillasocial.dnp.gov.co/"})
        r=s.post("https://ventanillasocial.dnp.gov.co/Home/ObtenerDatosRUI", data={"pNumDoc":cedula,"pTipDoc":"3"}, verify=False, timeout=30)
        deduct(user_id, COST_SISBEN)
        await target.message.reply_text(f"[ SISBEN ] {cedula}\n━━━━━━━━━━━━━━━\n{r.text[:3000]}")
    except Exception as e:
        await target.message.reply_text(f"Error: {e}")
async def sisben_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        context.user_data['awaiting']='sisben'
        await update.message.reply_text(f"SISBEN {COST_SISBEN} coins\nEnviame cedula")
        return
    await do_sisben(update, update.effective_user.id, context.args[0])

# --- RUNT ---
async def do_runt(target, user_id, placa):
    if not can_afford(user_id, COST_RUNT):
        await target.message.reply_text(f"[ SIN COINS ] Necesitas {COST_RUNT} coins")
        return
    placa = placa.upper().strip()
    await target.message.reply_text(f"[ RUNT ] Consultando {placa}... ⏳")
    try:
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0","Referer":"https://www.runt.com.co/"})
        url=f"https://api.historialrunt.org/v2/consulta?placa={placa}"
        r=s.get(url, timeout=20)
        if r.status_code==200:
            try:
                data=r.json()
                if data.get("success")==True or "marca" in r.text.lower():
                    deduct(user_id, COST_RUNT)
                    txt=f"[ RUNT - {placa} ]\n━━━━━━━━━━━━━━━\nPlaca: {data.get('placa',placa)}\nMarca: {data.get('marca','N/A')}\nLinea: {data.get('linea','N/A')}\nModelo: {data.get('modelo','N/A')}\nColor: {data.get('color','N/A')}\nEstado: {data.get('estado','N/A')}"
                    await target.message.reply_text(txt)
                    return
            except:
                pass
        url2=f"https://www.runt.com.co/consultaCiudadana/consultaVehiculo.php?placa={placa}"
        r2=s.get(url2, timeout=20, verify=False)
        if len(r2.text)>200:
            deduct(user_id, COST_RUNT)
            clean=re.sub('<[^<]+?>', '\n', r2.text)
            clean=unescape(clean)
            clean="\n".join([l.strip() for l in clean.splitlines() if len(l.strip())>2])[:3500]
            await target.message.reply_text(f"[ RUNT - {placa} ]\n━━━━━━━━━━━━━━━\n{clean}")
            return
    except Exception as e:
        await target.message.reply_text(f"Error RUNT: {e}")
        return
    await target.message.reply_text(f"[ RUNT ] {placa}\n━━━━━━━━━━━━━━━\nNo se encontró o RUNT caído")

async def runt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args)<1:
        context.user_data['awaiting']='runt'
        await update.message.reply_text(f"🇨🇴 RUNT ({COST_RUNT} coins)\n━━━━━━━━━━━━━━━\nSolo enviame la PLACA\nEj: OMG650")
        return
    await do_runt(update, update.effective_user.id, context.args[0])

# --- RUC PE CORREGIDO ---
async def do_ruc(target, user_id, ruc):
    if not can_afford(user_id, COST_RUC):
        await target.message.reply_text(f"[ SIN COINS ] Necesitas {COST_RUC} coins")
        return
    await target.message.reply_text(f"[ RUC PE ] Consultando {ruc}... ⏳")
    data = consulta_ruc_pe(ruc)
    if data.get("error"):
        await target.message.reply_text(f"[ RUC - {ruc} ] ❌ {data.get('error')}")
        return
    razon = data.get('razon_social') or data.get('nombre_o_razon_social') or data.get('company_name')
    if not razon:
        await target.message.reply_text(f"[ RUC - {ruc} ] ❌ No encontrado\n{json.dumps(data)[:800]}")
        return
    deduct(user_id, COST_RUC)
    txt = f"""[ RUC - {ruc} ] ✅
━━━━━━━━━━━━━━━
🏢 RAZÓN: {razon}
📄 RUC: {data.get('numero', ruc)}
📊 ESTADO: {data.get('estado', 'N/A')}
📋 CONDICIÓN: {data.get('condicion', 'N/A')}
📍 DIR: {data.get('direccion', 'N/A')}
🗺️ {data.get('departamento','')} - {data.get('provincia','')} - {data.get('distrito','')}
━━━━━━━━━━━━━━━
💼 {data.get('actividad_economica','')}
━━━━━━━━━━━━━━━"""
    await target.message.reply_text(txt[:4000])

async def ruc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        context.user_data['awaiting']='ruc'
        await update.message.reply_text(f"🇵🇪 RUC ({COST_RUC} coins)\nEnviame RUC\nEj: 20601030013")
        return
    await do_ruc(update, update.effective_user.id, context.args[0])

# --- DNI PE CORREGIDO - AHORA SI BONITO ---
async def do_dnipe(target, user_id, dni):
    if not can_afford(user_id, COST_DNIPE):
        await target.message.reply_text(f"[ SIN COINS ] Necesitas {COST_DNIPE} coins")
        return
    await target.message.reply_text(f"[ DNI PE ] Consultando {dni}... ⏳")
    data = consulta_dni_pe(dni)

    # Formato Decollecta real: first_name, first_last_name, second_last_name, full_name
    nombres = data.get("nombres") or data.get("first_name") or ""
    paterno = data.get("apellido_paterno") or data.get("first_last_name") or ""
    materno = data.get("apellido_materno") or data.get("second_last_name") or ""
    completo = data.get("nombre_completo") or data.get("full_name") or f"{paterno} {materno} {nombres}"
    doc_num = data.get("document_number") or data.get("numero") or dni

    if not nombres and "full_name" not in data and "first_name" not in data:
        await target.message.reply_text(f"[ DNI PE - {dni} ] ❌ No encontrado\n{json.dumps(data)[:800]}")
        return

    deduct(user_id, COST_DNIPE)

    txt = f"""[ DNI PE - {doc_num} ] ✅
━━━━━━━━━━━━━━━
👤 NOMBRE COMPLETO: {completo}
📝 NOMBRES: {nombres}
👨 AP. PATERNO: {paterno}
👩 AP. MATERNO: {materno}
🪪 DNI: {doc_num}
━━━━━━━━━━━━━━━
✅ RENIEC VERIFICADO
━━━━━━━━━━━━━━━"""

    await target.message.reply_text(txt[:4000])

async def dnipe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        context.user_data['awaiting']='dnipe'
        await update.message.reply_text(f"🇵🇪 DNI PE ({COST_DNIPE} coins)\nEnviame DNI\nEj: 70985035")
        return
    await do_dnipe(update, update.effective_user.id, context.args[0])

async def btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    data=q.data
    uid=q.from_user.id
    if data.startswith("country_"):
        code=data.split("_")[1]
        d=get_user(uid)
        if code=="CO":
            txt=f"[ 🇨🇴 COLOMBIA ]\n━━━━━━━━━━━━━━━\nCoins: {d['coins']}\n━━━━━━━━━━━━━━━\n2 módulos"
            kb=[
                [InlineKeyboardButton(f"› SISBEN / RUI ({COST_SISBEN})", callback_data="ask_sisben")],
                [InlineKeyboardButton(f"› RUNT - SOLO PLACA ({COST_RUNT})", callback_data="ask_runt")],
                [InlineKeyboardButton("‹ Volver", callback_data="back_countries")],
            ]
        elif code=="PE":
            txt=f"[ 🇵🇪 PERU ]\n━━━━━━━━━━━━━━━\nCoins: {d['coins']}\n━━━━━━━━━━━━━━━\n2 módulos"
            kb=[
                [InlineKeyboardButton(f"› RUC SUNAT ({COST_RUC})", callback_data="ask_ruc")],
                [InlineKeyboardButton(f"› DNI RENIEC ({COST_DNIPE})", callback_data="ask_dnipe")],
                [InlineKeyboardButton("‹ Volver", callback_data="back_countries")],
            ]
        else:
            txt=f"[ {COUNTRIES[code]['name']} ]\n━━━━━━━━━━━━━━━\n🚧 En construcción"
            kb=[[InlineKeyboardButton("‹ Volver", callback_data="back_countries")]]
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif data=="back_countries":
        d=get_user(uid)
        txt=f"[ PANEL POR PAISES ]\n━━━━━━━━━━━━━━━\nUSER: {uid} | Coins: {d['coins']}\n━━━━━━━━━━━━━━━\nSelecciona país"
        kb=[
            [InlineKeyboardButton("🇨🇴 COLOMBIA", callback_data="country_CO"),
             InlineKeyboardButton("🇵🇪 PERU", callback_data="country_PE")],
            [InlineKeyboardButton("🇲🇽 MEXICO", callback_data="country_MX"),
             InlineKeyboardButton("🇪🇨 ECUADOR", callback_data="country_EC")],
            [InlineKeyboardButton("🇻🇪 VENEZUELA", callback_data="country_VE"),
             InlineKeyboardButton("🌎 OTROS", callback_data="country_OT")],
        ]
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif data=="ask_sisben":
        context.user_data['awaiting']='sisben'
        await q.edit_message_text(f"🇨🇴 SISBEN ({COST_SISBEN} coins)\nEnviame cedula", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Volver", callback_data="country_CO")]]))
    elif data=="ask_runt":
        context.user_data['awaiting']='runt'
        await q.edit_message_text(f"🇨🇴 RUNT ({COST_RUNT} coins)\n━━━━━━━━━━━━━━━\nSolo PLACA\nEj: OMG650", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Volver", callback_data="country_CO")]]))
    elif data=="ask_ruc":
        context.user_data['awaiting']='ruc'
        await q.edit_message_text(f"🇵🇪 RUC ({COST_RUC} coins)\nEnviame RUC\nEj: 20601030013", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Volver", callback_data="country_PE")]]))
    elif data=="ask_dnipe":
        context.user_data['awaiting']='dnipe'
        await q.edit_message_text(f"🇵🇪 DNI ({COST_DNIPE} coins)\nEnviame DNI\nEj: 70985035", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Volver", callback_data="country_PE")]]))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting=context.user_data.get('awaiting')
    text=update.message.text.strip()
    if not awaiting: return
    if awaiting=='sisben':
        context.user_data['awaiting']=None
        await do_sisben(update, update.effective_user.id, text)
    elif awaiting=='runt':
        context.user_data['awaiting']=None
        await do_runt(update, update.effective_user.id, text.split()[0])
    elif awaiting=='ruc':
        context.user_data['awaiting']=None
        await do_ruc(update, update.effective_user.id, text.split()[0])
    elif awaiting=='dnipe':
        context.user_data['awaiting']=None
        await do_dnipe(update, update.effective_user.id, text.split()[0])

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app=Application.builder().token(TOKEN).post_init(setup_commands).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sys", sys_cmd))
    app.add_handler(CommandHandler("mycoins", mycoins_cmd))
    app.add_handler(CommandHandler("addcoins", addcoins_cmd))
    app.add_handler(CommandHandler("addvip", addvip_cmd))
    app.add_handler(CommandHandler("remvip", remvip_cmd))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CommandHandler("sisben", sisben_cmd))
    app.add_handler(CommandHandler("runt", runt_cmd))
    app.add_handler(CommandHandler("ruc", ruc_cmd))
    app.add_handler(CommandHandler("dnipe", dnipe_cmd))
    app.add_handler(CommandHandler("dniperu", dnipe_cmd))
    app.add_handler(CallbackQueryHandler(btn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print(f"Bot iniciado OWNER {OWNER_ID} - PERU FIXED")
    app.run_polling()

if __name__=="__main__":
    main()
