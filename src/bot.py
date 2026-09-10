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
COST_CREDICUOTAS = 12
DB_FILE = "users.json"

# KEY PERU
API_KEY_DECOLECTA = "sk_19272.V8Z6VdfAkdjg5teDriucciqmHRi9rbkK"

COUNTRIES = {
    "CO": {"name": "🇨🇴 COLOMBIA"},
    "MX": {"name": "🇲🇽 MEXICO"},
    "EC": {"name": "🇪🇨 ECUADOR"},
    "VE": {"name": "🇻🇪 VENEZUELA"},
    "PE": {"name": "🇵🇪 PERU"},
    "AR": {"name": "🇦🇷 ARGENTINA"},
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

# ================= API CREDICUOTAS (ARGENTINA) =================
def consulta_credicuotas(documento=None, telefono=None, customer_id=None):
    url = "https://clientes.credicuotas.com.ar/v1/onboarding/resolvecustomers/"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://clientes.credicuotas.com.ar",
        "Referer": "https://clientes.credicuotas.com.ar/",
    }
    
    payload = {}
    if documento:
        payload["document"] = str(documento).strip()
    if telefono:
        payload["phone"] = str(telefono).strip()
    if customer_id:
        payload["customerId"] = str(customer_id).strip()
    
    if not payload:
        return {"error": "Debes proporcionar al menos un parámetro (documento, teléfono o customerId)"}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json()
            }
        else:
            return {
                "success": False,
                "status_code": response.status_code,
                "error": "Error en la consulta",
                "data": response.text
            }
            
    except Exception as e:
        return {"error": str(e)}

# ================= SETUP COMMANDS =================
async def setup_commands(app: Application):
    user_commands = [
        BotCommand("start", "Acceso principal"),
        BotCommand("sys", "Panel por paises"),
        BotCommand("mycoins", "Ver saldo"),
        BotCommand("sisben", "Consultar SISBEN"),
        BotCommand("runt", "Consultar RUNT (solo placa)"),
        BotCommand("ruc", "Consultar RUC PE 🇵🇪"),
        BotCommand("dnipe", "Consultar DNI PE 🇵🇪"),
        BotCommand("credicuotas", "Consultar Credicuotas 🇦🇷"),
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
         InlineKeyboardButton("🇦🇷 ARGENTINA", callback_data="country_AR")],
        [InlineKeyboardButton("🌎 OTROS", callback_data="country_OT")],
    ]
    await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb))

# --- SISBEN (CON CEDULA) ---
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

# --- RUNT SOLO PLACA ---
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

# --- RUC PE ---
async def do_ruc(target, user_id, ruc):
    if not can_afford(user_id, COST_RUC):
        await target.message.reply_text(f"[ SIN COINS ] Necesitas {COST_RUC} coins")
        return
    await target.message.reply_text(f"[ RUC PE ] Consultando {ruc}... ⏳")
    data = consulta_ruc_pe(ruc)
    if data.get("error"):
        await target.message.reply_text(f"[ RUC - {ruc} ] ❌ {data.get('error')}")
        return
    if not data.get("razon_social") and not data.get("numero"):
        await target.message.reply_text(f"[ RUC - {ruc} ] ❌ No encontrado\n{json.dumps(data)[:800]}")
        return
    deduct(user_id, COST_RUC)
    txt = f"[ RUC - {ruc} ] ✅\n━━━━━━━━━━━━━━━\n🏢 {data.get('razon_social','N/A')}\n📊 ESTADO: {data.get('estado','N/A')}\n📋 CONDICION: {data.get('condicion','N/A')}\n📍 {data.get('direccion','N/A')}\n━━━━━━━━━━━━━━━"
    await target.message.reply_text(txt[:4000])

async def ruc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        context.user_data['awaiting']='ruc'
        await update.message.reply_text(f"🇵🇪 RUC ({COST_RUC} coins)\nEnviame RUC\nEj: 20601030013")
        return
    await do_ruc(update, update.effective_user.id, context.args[0])

# --- DNI PE ---
async def do_dnipe(target, user_id, dni):
    if not can_afford(user_id, COST_DNIPE):
        await target.message.reply_text(f"[ SIN COINS ] Necesitas {COST_DNIPE} coins")
        return
    await target.message.reply_text(f"[ DNI PE ] Consultando {dni}... ⏳")
    data = consulta_dni_pe(dni)
    if data.get("error") or (not data.get("nombres") and not data.get("nombre_completo")):
        await target.message.reply_text(f"[ DNI PE - {dni} ] ❌ {data.get('error') or 'No encontrado'}\n{str(data)[:800]}")
        return
    deduct(user_id, COST_DNIPE)
    completo = data.get("nombre_completo") or f"{data.get('nombres','')} {data.get('apellido_paterno','')} {data.get('apellido_materno','')}"
    txt = f"[ DNI PE - {dni} ] ✅\n━━━━━━━━━━━━━━━\n👤 {completo}\n🪪 DNI: {dni}\n━━━━━━━━━━━━━━━"
    await target.message.reply_text(txt[:4000])

async def dnipe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        context.user_data['awaiting']='dnipe'
        await update.message.reply_text(f"🇵🇪 DNI PE ({COST_DNIPE} coins)\nEnviame DNI\nEj: 12345678")
        return
    await do_dnipe(update, update.effective_user.id, context.args[0])

# --- CREDICUOTAS AR (CORREGIDO) ---
async def do_credicuotas(target, user_id, documento):
    if not can_afford(user_id, COST_CREDICUOTAS):
        await target.message.reply_text(f"[ SIN COINS ] Necesitas {COST_CREDICUOTAS} coins")
        return
    
    await target.message.reply_text(f"[ CREDICUOTAS ] Consultando {documento}... ⏳")
    
    result = consulta_credicuotas(documento=documento)
    
    if result.get("error"):
        await target.message.reply_text(f"[ CREDICUOTAS - {documento} ] ❌\n{result.get('error')}")
        return
    
    if not result.get("success") or result.get("status_code") != 200:
        await target.message.reply_text(f"[ CREDICUOTAS - {documento} ] ❌\nStatus: {result.get('status_code')}\nNo encontrado")
        return
    
    data = result.get("data", [])
    
    # Si devuelve lista vacía
    if not data or len(data) == 0:
        await target.message.reply_text(f"[ CREDICUOTAS - {documento} ] ❌\nNo se encontraron datos")
        return
    
    deduct(user_id, COST_CREDICUOTAS)
    
    # Formatear cada resultado (puede devolver múltiples)
    for item in data:
        cuit = item.get("cuit", "N/A")
        nombre = item.get("nombrecompleto", "N/A")
        dni = item.get("dni", "N/A")
        fecha_nac = item.get("fechanacimiento", "N/A")
        sexo = item.get("sexo", "N/A")
        
        # Calcular edad si hay fecha
        edad = "N/A"
        if fecha_nac and fecha_nac != "N/A":
            try:
                fecha = datetime.strptime(fecha_nac, "%Y-%m-%d")
                hoy = datetime.now()
                edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
            except:
                pass
        
        sexo_icon = "👩" if sexo == "F" else "👨" if sexo == "M" else "👤"
        
        txt = f"[ 🇦🇷 CREDICUOTAS - {dni} ] ✅\n"
        txt += f"━━━━━━━━━━━━━━━\n"
        txt += f"{sexo_icon} Nombre: {nombre}\n"
        txt += f"🪪 DNI: {dni}\n"
        txt += f"🏢 CUIT: {cuit}\n"
        txt += f"📅 Nacimiento: {fecha_nac}"
        if edad != "N/A":
            txt += f" ({edad} años)"
        txt += f"\n⚧ Sexo: {'Femenino' if sexo == 'F' else 'Masculino' if sexo == 'M' else sexo}\n"
        txt += f"━━━━━━━━━━━━━━━"
        
        await target.message.reply_text(txt[:4000])

async def credicuotas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        context.user_data['awaiting']='credicuotas'
        await update.message.reply_text(f"🇦🇷 CREDICUOTAS ({COST_CREDICUOTAS} coins)\n━━━━━━━━━━━━━━━\nEnviame DNI, teléfono o ID de cliente\nEj: 12345678")
        return
    await do_credicuotas(update, update.effective_user.id, " ".join(context.args))

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
        elif code=="AR":
            txt=f"[ 🇦🇷 ARGENTINA ]\n━━━━━━━━━━━━━━━\nCoins: {d['coins']}\n━━━━━━━━━━━━━━━\n1 módulo"
            kb=[
                [InlineKeyboardButton(f"› CREDICUOTAS ({COST_CREDICUOTAS})", callback_data="ask_credicuotas")],
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
             InlineKeyboardButton("🇦🇷 ARGENTINA", callback_data="country_AR")],
            [InlineKeyboardButton("🌎 OTROS", callback_data="country_OT")],
        ]
        await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb))
    elif data=="ask_sisben":
        context.user_data['awaiting']='sisben'
        await q.edit_message_text(f"🇨🇴 SISBEN ({COST_SISBEN} coins)\nEnviame cedula", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("‹ Volver", callback_data="country_CO")]]))
    elif data=="ask_runt":
        context.user_data['awaiting']='runt'
 
