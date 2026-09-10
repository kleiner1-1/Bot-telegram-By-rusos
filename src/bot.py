# bot.py - TODO EN UNO - COLOMBIA / ARGENTINA / PERU
import os
import json
import time
import requests
import urllib3
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = os.getenv("BOT_TOKEN") or "TU_TOKEN_AQUI"
API_KEY_DECOLECTA = "sk_19272.V8Z6VdfAkdjg5teDriucciqmHRi9rbkK"

# COSTOS
COST_CEDULA = 5
COST_RUNT = 8
COST_PADRON = 5
COST_RUC = 10
COST_DNIPE = 8

# SISTEMA DE COINS SIMPLE (usa tu sistema real si ya tienes)
coins_db = {}

def can_afford(uid, cost):
    return coins_db.get(uid, 100) >= cost

def deduct(uid, cost):
    coins_db[uid] = coins_db.get(uid, 100) - cost

def get_coins(uid):
    return coins_db.get(uid, 100)

# ================= FUNCIONES API =================

def consulta_runt(placa, documento):
    placa = placa.upper().strip()
    documento = documento.strip()
    url = f"https://historialrunt.org/api/consultar.php?placa={placa}&documento={documento}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://historialrunt.org/"
    }
    for intento in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=30, verify=False)
            data = r.json()
            if "captcha" in str(data).lower():
                time.sleep(2)
                continue
            return data
        except Exception as e:
            time.sleep(1)
            continue
    return {"success": False, "error": "RUNT captcha caído, intenta en 1 min"}

def consulta_padron_ar(dni, sexo):
    dni = str(dni).strip()
    sexo = sexo.upper()[0]
    url = f"https://integrandosalud.com/src/InterfazJs/buscarPadronMinisterio.php?dni={dni}&sexo={sexo}"
    headers = {
        "Accept": "application/json, text/javascript, */*",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://integrandosalud.com/",
        "X-Requested-With": "XMLHttpRequest"
    }
    try:
        r = requests.get(url, headers=headers, timeout=20, verify=False)
        try:
            return r.json(), sexo
        except:
            if len(r.text.strip()) > 10:
                return {"raw": r.text}, sexo
            return None, sexo
    except:
        return None, sexo

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

# ================= COMANDOS =================

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = f"""👋 Bienvenido {update.effective_user.first_name}
💰 Coins: {get_coins(update.effective_user.id)}

🇨🇴 /cedula 123456 - Cedula Colombia
🇨🇴 /runt OMG650 1002345678 - RUNT placa+cedula

🇦🇷 /padron 40123456 - Padron AR (auto M/F)

🇵🇪 /ruc 20601030013 - RUC SUNAT
🇵🇪 /dnipe 12345678 - DNI RENIEC

💳 /coins - Ver coins
"""
    await update.message.reply_text(txt)

async def coins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💰 Tus coins: {get_coins(update.effective_user.id)}")

async def runt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("🇨🇴 Uso: /runt PLACA CEDULA\nEj: /runt OMG650 1023456789")
        return
    placa = context.args[0]
    doc = context.args[1]
    uid = update.effective_user.id
    if not can_afford(uid, COST_RUNT):
        await update.message.reply_text(f"❌ Necesitas {COST_RUNT} coins")
        return
    await update.message.reply_text(f"[ RUNT ] Consultando {placa}... ⏳")
    data = consulta_runt(placa, doc)
    if not data.get("success", False):
        # Si la API devuelve success false pero tiene datos, igual mostrar
        if "captcha" in str(data.get("error","")).lower():
            await update.message.reply_text(f"[ RUNT ] 🚧 Captcha caído, intenta en 1 min\n{data.get('error')}")
            return
        # Si no es success pero tiene error real
        if not data.get("placa") and not data.get("marca"):
            await update.message.reply_text(f"[ RUNT - {placa} ] ❌ {data.get('error','No encontrado')}")
            return
    deduct(uid, COST_RUNT)
    txt = f"[ RUNT - {placa.upper()} ] ✅\n━━━━━━━━━━━━━━━\n{json.dumps(data, indent=2, ensure_ascii=False)[:3500]}"
    await update.message.reply_text(txt[:4000])

async def padron_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🇦🇷 Uso: /padron DNI\nEj: /padron 40123456\nPrueba M y F auto")
        return
    dni = context.args[0]
    uid = update.effective_user.id
    if not can_afford(uid, COST_PADRON):
        await update.message.reply_text(f"❌ Necesitas {COST_PADRON} coins")
        return
    await update.message.reply_text(f"[ PADRON AR ] Buscando {dni} M/F... ⏳")
    encontrado = None
    sexo_ok = None
    for sexo in ["M","F"]:
        data, s = consulta_padron_ar(dni, sexo)
        if data and len(str(data)) > 15:
            if "raw" in data and len(data["raw"]) < 15:
                continue
            encontrado = data
            sexo_ok = s
            break
    if not encontrado:
        await update.message.reply_text(f"[ PADRON - {dni} ] ❌ No encontrado M/F")
        return
    deduct(uid, COST_PADRON)
    await update.message.reply_text(f"[ PADRON - {dni} {sexo_ok} ] ✅\n━━━━━━━━━━━━━━━\n{json.dumps(encontrado, indent=2, ensure_ascii=False)[:3500]}")

async def ruc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🇵🇪 Uso: /ruc RUC\nEj: /ruc 20601030013")
        return
    ruc = context.args[0]
    uid = update.effective_user.id
    if not can_afford(uid, COST_RUC):
        await update.message.reply_text(f"❌ Necesitas {COST_RUC} coins")
        return
    await update.message.reply_text(f"[ RUC ] Consultando {ruc}... ⏳")
    data = consulta_ruc_pe(ruc)
    if data.get("error") or data.get("message") and "razon" not in str(data).lower():
        await update.message.reply_text(f"[ RUC - {ruc} ] ❌ {data.get('error') or data.get('message')}")
        return
    deduct(uid, COST_RUC)
    razon = data.get('razon_social') or data.get('nombre_o_razon_social') or 'N/A'
    txt = f"[ RUC - {ruc} ] ✅\n━━━━━━━━━━━━━━━\n🏢 {razon}\n📊 {data.get('estado','')}\n📍 {data.get('direccion','')}\n━━━━━━━━━━━━━━━\n{json.dumps(data, indent=2, ensure_ascii=False)[:2500]}"
    await update.message.reply_text(txt[:4000])

async def dnipe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🇵🇪 Uso: /dnipe DNI\nEj: /dnipe 12345678")
        return
    dni = context.args[0]
    uid = update.effective_user.id
    if not can_afford(uid, COST_DNIPE):
        await update.message.reply_text(f"❌ Necesitas {COST_DNIPE} coins")
        return
    await update.message.reply_text(f"[ DNI PE ] Consultando {dni}... ⏳")
    data = consulta_dni_pe(dni)
    if data.get("error") or (not data.get("nombres") and not data.get("nombre_completo")):
        await update.message.reply_text(f"[ DNI PE - {dni} ] ❌ {data.get('error') or 'No encontrado'}\n{str(data)[:500]}")
        return
    deduct(uid, COST_DNIPE)
    completo = data.get("nombre_completo") or f"{data.get('nombres','')} {data.get('apellido_paterno','')} {data.get('apellido_materno','')}"
    txt = f"[ DNI PE - {dni} ] ✅\n━━━━━━━━━━━━━━━\n👤 {completo}\n🪪 DNI: {dni}\n━━━━━━━━━━━━━━━\n{json.dumps(data, indent=2, ensure_ascii=False)[:3000]}"
    await update.message.reply_text(txt[:4000])

# ================= MAIN =================

async def setup_commands(app):
    cmds = [
        BotCommand("start", "Inicio"),
        BotCommand("coins", "Ver coins"),
        BotCommand("runt", "RUNT Colombia 🇨🇴"),
        BotCommand("padron", "Padron AR 🇦🇷"),
        BotCommand("ruc", "RUC Peru 🇵🇪"),
        BotCommand("dnipe", "DNI Peru 🇵🇪"),
    ]
    await app.bot.set_my_commands(cmds)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("coins", coins_cmd))
    app.add_handler(CommandHandler("runt", runt_cmd))
    app.add_handler(CommandHandler("padron", padron_cmd))
    app.add_handler(CommandHandler("ruc", ruc_cmd))
    app.add_handler(CommandHandler("dnipe", dnipe_cmd))
    app.add_handler(CommandHandler("dniperu", dnipe_cmd))
    app.add_handler(CommandHandler("dnic", dnipe_cmd)) # alias

    app.job_queue.run_once(setup_commands, 1)
    print("Bot iniciado... ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
