import os
import json
import time
import re
import threading
import logging
import tempfile

import requests
from flask import Flask
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    BotCommandScopeChat,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
API_KEY_DECOLECTA = os.getenv("DECOLECTA_API_KEY")

OWNER_ID = 8768048667

DB_FILE = "users.json"

COST_RUNT = 10
COST_RUC = 10

# RLock evita problemas cuando una función de DB llama a otra.
db_lock = threading.RLock()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# PAISES
# =========================================================

COUNTRIES = {
    "CO": "🇨🇴 COLOMBIA",
    "PE": "🇵🇪 PERÚ",
    "MX": "🇲🇽 MÉXICO",
    "EC": "🇪🇨 ECUADOR",
    "VE": "🇻🇪 VENEZUELA",
    "OT": "🌎 OTROS",
}


# =========================================================
# FLASK / KEEP ALIVE
# =========================================================

flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return "Bot activo"


def run_flask():
    port = int(os.environ.get("PORT", 10000))

    flask_app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
    )


# =========================================================
# BASE DE DATOS
# =========================================================

def load_db():
    with db_lock:

        if not os.path.exists(DB_FILE):
            return {}

        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return {}

            return data

        except (json.JSONDecodeError, OSError):
            logger.exception("No se pudo leer users.json")
            return {}


def save_db(data):
    """
    Guarda de forma atómica para reducir el riesgo
    de dejar users.json corrupto.
    """

    with db_lock:

        directory = os.path.dirname(os.path.abspath(DB_FILE))

        try:
            fd, temp_path = tempfile.mkstemp(
                dir=directory,
                prefix="users_",
                suffix=".tmp",
            )

            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
            ) as f:

                json.dump(
                    data,
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            os.replace(temp_path, DB_FILE)

        except Exception:
            logger.exception("Error guardando la base de datos")

            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

            raise


def get_user(user_id):
    uid = str(user_id)

    with db_lock:

        db = load_db()

        if uid not in db:

            db[uid] = {
                "coins": 9999 if user_id == OWNER_ID else 0,
                "vip_until": 9999999999 if user_id == OWNER_ID else 0,
            }

            save_db(db)

        return db[uid].copy()


def is_vip(data):
    return data.get("vip_until", 0) > time.time()


def get_plan(user_id, data=None):

    if user_id == OWNER_ID:
        return "OWNER ∞"

    if data is None:
        data = get_user(user_id)

    if is_vip(data):
        return "VIP"

    return "FREE"


def can_afford(user_id, cost):

    if user_id == OWNER_ID:
        return True

    data = get_user(user_id)

    if is_vip(data):
        return True

    return data.get("coins", 0) >= cost


def deduct(user_id, cost):

    if user_id == OWNER_ID:
        return True

    with db_lock:

        db = load_db()
        uid = str(user_id)

        if uid not in db:
            return False

        if is_vip(db[uid]):
            return True

        coins = db[uid].get("coins", 0)

        if coins < cost:
            return False

        db[uid]["coins"] = coins - cost

        save_db(db)

        return True


# =========================================================
# TECLADOS
# =========================================================

def main_keyboard(user_id):

    buttons = [
        [
            InlineKeyboardButton(
                "🌎 PANEL",
                callback_data="panel",
            ),
            InlineKeyboardButton(
                "💰 SALDO",
                callback_data="coins",
            ),
        ],
        [
            InlineKeyboardButton(
                "👤 MI PLAN",
                callback_data="plan",
            ),
        ],
    ]

    if user_id == OWNER_ID:

        buttons.append(
            [
                InlineKeyboardButton(
                    "⚙️ OWNER",
                    callback_data="owner",
                )
            ]
        )

    return InlineKeyboardMarkup(buttons)


def countries_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🇨🇴 COLOMBIA",
                    callback_data="country_CO",
                ),
                InlineKeyboardButton(
                    "🇵🇪 PERÚ",
                    callback_data="country_PE",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🇲🇽 MÉXICO",
                    callback_data="country_MX",
                ),
                InlineKeyboardButton(
                    "🇪🇨 ECUADOR",
                    callback_data="country_EC",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🇻🇪 VENEZUELA",
                    callback_data="country_VE",
                ),
                InlineKeyboardButton(
                    "🌎 OTROS",
                    callback_data="country_OT",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏠 INICIO",
                    callback_data="home",
                )
            ],
        ]
    )


def country_keyboard(code):

    buttons = []

    if code == "CO":

        buttons.append(
            [
                InlineKeyboardButton(
                    f"🚗 RUNT — {COST_RUNT} coins",
                    callback_data="runt_info",
                )
            ]
        )

    elif code == "PE":

        buttons.append(
            [
                InlineKeyboardButton(
                    f"🏢 RUC — {COST_RUC} coins",
                    callback_data="ruc_info",
                )
            ]
        )

    else:

        buttons.append(
            [
                InlineKeyboardButton(
                    "🚧 MÓDULO EN DESARROLLO",
                    callback_data="noop",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "‹ PAÍSES",
                callback_data="panel",
            ),
            InlineKeyboardButton(
                "🏠 INICIO",
                callback_data="home",
            ),
        ]
    )

    return InlineKeyboardMarkup(buttons)


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not user:
        return

    data = get_user(user.id)

    plan = get_plan(user.id, data)

    name = user.first_name or "Usuario"

    if user.id == OWNER_ID:

        coins_text = "ILIMITADO ∞"

    else:

        coins_text = str(data.get("coins", 0))

    text = (
        "╔════════════════════╗\n"
        "      🔐 ACCESS CENTER\n"
        "╚════════════════════╝\n\n"

        f"👤 Usuario : {name}\n"
        f"🆔 ID      : {user.id}\n"
        f"💎 Plan    : {plan}\n"
        f"🪙 Coins   : {coins_text}\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"
        "📡 SERVICIOS ACTIVOS\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"🇨🇴 RUNT       → {COST_RUNT} coins\n"
        f"🇵🇪 RUC        → {COST_RUC} coins\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"
        "Selecciona una opción:"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(user.id),
    )


# =========================================================
# SALDO
# =========================================================

async def mycoins_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id
    data = get_user(user_id)

    if user_id == OWNER_ID:

        text = (
            "💰 MI SALDO\n\n"
            "👑 OWNER\n"
            "🪙 Coins: ILIMITADO ∞"
        )

    else:

        plan = get_plan(user_id, data)

        text = (
            "💰 MI SALDO\n\n"
            f"💎 Plan: {plan}\n"
            f"🪙 Coins: {data.get('coins', 0)}"
        )

    await update.message.reply_text(text)


# =========================================================
# PLAN
# =========================================================

async def myplan_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id
    data = get_user(user_id)

    plan = get_plan(user_id, data)

    if user_id == OWNER_ID:

        text = (
            "👑 PLAN OWNER\n\n"
            "Acceso administrativo completo.\n"
            "Coins: ILIMITADO ∞"
        )

    elif is_vip(data):

        remaining = max(
            0,
            int(data.get("vip_until", 0) - time.time()),
        )

        days = remaining // 86400
        hours = (remaining % 86400) // 3600

        text = (
            "💎 PLAN VIP\n\n"
            f"⏳ Tiempo restante: {days} días "
            f"{hours} horas\n\n"
            "Acceso sin descuento de coins "
            "mientras el VIP esté activo."
        )

    else:

        text = (
            "🆓 PLAN FREE\n\n"
            f"🪙 Coins disponibles: {data.get('coins', 0)}"
        )

    await update.message.reply_text(text)


# =========================================================
# PANEL
# =========================================================

async def sys_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    user_id = update.effective_user.id
    data = get_user(user_id)

    text = (
        "╔════════════════════╗\n"
        "       🌎 SYSTEM PANEL\n"
        "╚════════════════════╝\n\n"
        f"🆔 ID: {user_id}\n"
        f"🪙 Coins: {data.get('coins', 0)}\n\n"
        "Selecciona un país:"
    )

    await update.message.reply_text(
        text,
        reply_markup=countries_keyboard(),
    )


# =========================================================
# RUC PERÚ
# =========================================================

def consulta_ruc_pe(ruc):

    if not API_KEY_DECOLECTA:
        logger.error("DECOLECTA_API_KEY no configurada")
        return None

    url = "https://api.decolecta.com/v1/sunat/ruc/full"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {API_KEY_DECOLECTA}",
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params={
                "numero": str(ruc).strip()
            },
            timeout=25,
        )

        if response.status_code != 200:

            logger.warning(
                "Decolecta respondió HTTP %s",
                response.status_code,
            )

            return None

        data = response.json()

        if not isinstance(data, dict):
            return None

        return data

    except requests.RequestException:
        logger.exception("Error consultando RUC")
        return None

    except ValueError:
        logger.exception("Respuesta RUC no válida")
        return None


async def do_ruc(
    target,
    user_id,
    ruc,
):

    ruc = str(ruc).strip()

    if not re.fullmatch(r"\d{11}", ruc):

        await target.message.reply_text(
            "❌ RUC inválido.\n\n"
            "El RUC debe contener exactamente 11 números."
        )

        return

    if not can_afford(user_id, COST_RUC):

        await target.message.reply_text(
            "❌ SIN COINS\n\n"
            f"Necesitas {COST_RUC} coins para consultar un RUC."
        )

        return

    msg = await target.message.reply_text(
        f"🔎 Consultando RUC {ruc}...\n"
        "⏳ Espera un momento."
    )

    data = consulta_ruc_pe(ruc)

    if not data:

        await msg.edit_text(
            "⚠️ No fue posible realizar la consulta.\n\n"
            "El servicio externo no respondió correctamente."
        )

        return

    razon_social = data.get("razon_social")

    if not razon_social:

        await msg.edit_text(
            f"🏢 RUC {ruc}\n\n"
            "❌ No encontrado."
        )

        return

    # SOLO se cobra si la consulta fue válida.
    if not deduct(user_id, COST_RUC):

        await msg.edit_text(
            "❌ No se pudo descontar el saldo."
        )

        return

    estado = data.get("estado", "N/A")
    direccion = data.get("direccion", "N/A")

    text = (
        f"🏢 RUC — {ruc}\n\n"
        f"📌 Razón social:\n{razon_social}\n\n"
        f"📊 Estado: {estado}\n"
        f"📍 Dirección: {direccion}\n\n"
        f"🪙 Costo: {COST_RUC} coins"
    )

    await msg.edit_text(text[:4000])


async def ruc_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.args:

        await update.message.reply_text(
            f"🇵🇪 RUC PERÚ\n\n"
            f"💰 Costo: {COST_RUC} coins\n\n"
            "Uso:\n"
            "/ruc 20123456789"
        )

        return

    await do_ruc(
        update,
        update.effective_user.id,
        context.args[0],
    )


# =========================================================
# RUNT
# =========================================================

def consulta_runt(placa):

    placa = placa.upper().strip()

    url = "https://api.historialrunt.org/v2/consulta"

    try:

        response = requests.get(
            url,
            params={
                "placa": placa
            },
            timeout=25,
        )

        if response.status_code != 200:
            logger.warning(
                "RUNT HTTP %s",
                response.status_code,
            )
            return None

        data = response.json()

        if isinstance(data, dict):
            return data

        return None

    except requests.RequestException:
        logger.exception("Error consultando RUNT")
        return None

    except ValueError:
        logger.exception("Respuesta RUNT no válida")
        return None


async def do_runt(
    target,
    user_id,
    placa,
):

    placa = str(placa).strip().upper()

    # Validación básica de placa.
    if not re.fullmatch(r"[A-Z0-9]{5,7}", placa):

        await target.message.reply_text(
            "❌ PLACA INVÁLIDA\n\n"
            "Usa únicamente letras y números."
        )

        return

    if not can_afford(user_id, COST_RUNT):

        await target.message.reply_text(
            "❌ SIN COINS\n\n"
            f"Necesitas {COST_RUNT} coins para consultar RUNT."
        )

        return

    msg = await target.message.reply_text(
        f"🚗 Consultando placa {placa}...\n"
        "⏳ Espera un momento."
    )

    data = consulta_runt(placa)

    if not data:

        await msg.edit_text(
            "⚠️ No fue posible realizar la consulta RUNT.\n\n"
            "El servicio externo no respondió correctamente."
        )

        return

    # Intentamos detectar una respuesta vacía.
    if data.get("error"):

        await msg.edit_text(
            f"🚗 PLACA {placa}\n\n"
            "❌ No encontrado."
        )

        return

    if not deduct(user_id, COST_RUNT):

        await msg.edit_text(
            "❌ No se pudo descontar el saldo."
        )

        return

    # Campos genéricos para evitar romperse si la API cambia.
    marca = data.get("marca", "N/A")
    modelo = data.get("modelo", "N/A")
    linea = data.get("linea", "N/A")
    estado = data.get("estado", "N/A")

    text = (
        f"🚗 RUNT — {placa}\n\n"
        f"🏷 Marca: {marca}\n"
        f"🚘 Modelo: {modelo}\n"
        f"📋 Línea: {linea}\n"
        f"📊 Estado: {estado}\n\n"
        f"🪙 Costo: {COST_RUNT} coins"
    )

    await msg.edit_text(text[:4000])


async def runt_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.args:

        await update.message.reply_text(
            f"🇨🇴 RUNT\n\n"
            f"💰 Costo: {COST_RUNT} coins\n\n"
            "Uso:\n"
            "/runt ABC123"
        )

        return

    await do_runt(
        update,
        update.effective_user.id,
        context.args[0],
    )


# =========================================================
# OWNER — ADD COINS
# =========================================================

async def addcoins_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) < 2:

        await update.message.reply_text(
            "Uso:\n"
            "/addcoins ID CANTIDAD"
        )

        return

    try:

        target_id = str(int(context.args[0]))
        amount = int(context.args[1])

    except ValueError:

        await update.message.reply_text(
            "❌ ID o cantidad inválida."
        )

        return

    if amount <= 0:

        await update.message.reply_text(
            "❌ La cantidad debe ser mayor que 0."
        )

        return

    with db_lock:

        db = load_db()

        if target_id not in db:

            db[target_id] = {
                "coins": 0,
                "vip_until": 0,
            }

        db[target_id]["coins"] = (
            db[target_id].get("coins", 0)
            + amount
        )

        save_db(db)

        new_balance = db[target_id]["coins"]

    await update.message.reply_text(
        "✅ COINS AGREGADOS\n\n"
        f"🆔 ID: {target_id}\n"
        f"➕ Agregado: {amount}\n"
        f"💰 Nuevo saldo: {new_balance}"
    )


# =========================================================
# OWNER — ADD VIP
# =========================================================

async def addvip_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) < 2:

        await update.message.reply_text(
            "Uso:\n"
            "/addvip ID DIAS"
        )

        return

    try:

        target_id = str(int(context.args[0]))
        days = int(context.args[1])

    except ValueError:

        await update.message.reply_text(
            "❌ ID o días inválidos."
        )

        return

    if days <= 0:

        await update.message.reply_text(
            "❌ Los días deben ser mayores que 0."
        )

        return

    with db_lock:

        db = load_db()

        if target_id not in db:

            db[target_id] = {
                "coins": 0,
                "vip_until": 0,
            }

        base = max(
            time.time(),
            db[target_id].get("vip_until", 0),
        )

        db[target_id]["vip_until"] = (
            base + days * 86400
        )

        save_db(db)

    await update.message.reply_text(
        "💎 VIP ACTIVADO\n\n"
        f"🆔 ID: {target_id}\n"
        f"⏳ Duración agregada: {days} días"
    )


# =========================================================
# OWNER — REMOVE VIP
# ========================
