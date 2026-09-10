import os
import sqlite3
import threading
import time
import requests
import urllib3

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

TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_KEY_DECOLECTA = os.getenv("DECOLECTA_API_KEY", "").strip()

OWNER_ID = int(os.getenv("OWNER_ID", "8768048667"))
PORT = int(os.getenv("PORT", "10000"))
DB_FILE = os.getenv("DB_FILE", "users.db")

COST_RUC = int(os.getenv("COST_RUC", "10"))
COST_TC = int(os.getenv("COST_TC", "2"))
COST_TCHIST = int(os.getenv("COST_TCHIST", "3"))

DECOLECTA_BASE = "https://api.decolecta.com"

urllib3.disable_warnings()

if not TOKEN:
    raise RuntimeError(
        "Falta BOT_TOKEN en las variables de entorno."
    )

if not API_KEY_DECOLECTA:
    raise RuntimeError(
        "Falta DECOLECTA_API_KEY en las variables de entorno."
    )


# =========================================================
# FLASK
# =========================================================

flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return "Bot Telegram activo"


def run_flask():
    flask_app.run(
        host="0.0.0.0",
        port=PORT
    )


# =========================================================
# DATABASE
# =========================================================

def db_connect():
    conn = sqlite3.connect(
        DB_FILE,
        timeout=20,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = db_connect()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            coins INTEGER DEFAULT 0,
            vip_until REAL DEFAULT 0,
            created_at REAL DEFAULT 0,
            updated_at REAL DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            operation TEXT NOT NULL,
            cost INTEGER DEFAULT 0,
            success INTEGER DEFAULT 0,
            created_at REAL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# USERS
# =========================================================

def ensure_user(
    user_id,
    username="",
    first_name=""
):

    conn = db_connect()

    now = time.time()

    if user_id == OWNER_ID:
        initial_coins = 999999
        initial_vip = 9999999999
    else:
        initial_coins = 0
        initial_vip = 0

    conn.execute("""
        INSERT INTO users (
            user_id,
            username,
            first_name,
            coins,
            vip_until,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name,
            updated_at=excluded.updated_at
    """, (
        user_id,
        username or "",
        first_name or "",
        initial_coins,
        initial_vip,
        now,
        now
    ))

    conn.commit()
    conn.close()


def get_user(user_id):

    ensure_user(user_id)

    conn = db_connect()

    row = conn.execute("""
        SELECT *
        FROM users
        WHERE user_id=?
    """, (user_id,)).fetchone()

    conn.close()

    if not row:
        return None

    return dict(row)


def is_vip(user):

    if not user:
        return False

    return (
        float(user.get("vip_until", 0))
        > time.time()
    )


def can_afford(user_id, cost):

    if user_id == OWNER_ID:
        return True

    user = get_user(user_id)

    if not user:
        return False

    if is_vip(user):
        return True

    return int(user["coins"]) >= cost


def deduct(user_id, cost):

    if user_id == OWNER_ID:
        return True

    conn = db_connect()

    now = time.time()

    row = conn.execute("""
        SELECT coins, vip_until
        FROM users
        WHERE user_id=?
    """, (user_id,)).fetchone()

    if not row:
        conn.close()
        return False

    if float(row["vip_until"]) > now:
        conn.close()
        return True

    result = conn.execute("""
        UPDATE users
        SET
            coins = coins - ?,
            updated_at = ?
        WHERE
            user_id = ?
            AND coins >= ?
    """, (
        cost,
        now,
        user_id,
        cost
    ))

    conn.commit()

    success = result.rowcount == 1

    conn.close()

    return success


def add_coins(user_id, amount):

    ensure_user(user_id)

    conn = db_connect()

    conn.execute("""
        UPDATE users
        SET
            coins = coins + ?,
            updated_at = ?
        WHERE user_id = ?
    """, (
        amount,
        time.time(),
        user_id
    ))

    conn.commit()
    conn.close()


def add_vip(user_id, days):

    ensure_user(user_id)

    conn = db_connect()

    now = time.time()

    row = conn.execute("""
        SELECT vip_until
        FROM users
        WHERE user_id=?
    """, (user_id,)).fetchone()

    current = float(
        row["vip_until"]
    ) if row else 0

    base = max(
        now,
        current
    )

    new_vip = (
        base +
        (days * 86400)
    )

    conn.execute("""
        UPDATE users
        SET
            vip_until = ?,
            updated_at = ?
        WHERE user_id = ?
    """, (
        new_vip,
        now,
        user_id
    ))

    conn.commit()
    conn.close()


def remove_vip(user_id):

    ensure_user(user_id)

    conn = db_connect()

    conn.execute("""
        UPDATE users
        SET
            vip_until = 0,
            updated_at = ?
        WHERE user_id = ?
    """, (
        time.time(),
        user_id
    ))

    conn.commit()
    conn.close()


# =========================================================
# LOG
# =========================================================

def log_operation(
    user_id,
    operation,
    cost,
    success
):

    conn = db_connect()

    conn.execute("""
        INSERT INTO operations (
            user_id,
            operation,
            cost,
            success,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        operation,
        cost,
        1 if success else 0,
        time.time()
    ))

    conn.commit()
    conn.close()


# =========================================================
# DECOLECTA
# =========================================================

def decolecta_get(
    endpoint,
    params=None
):

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": (
            f"Bearer {API_KEY_DECOLECTA}"
        ),
        "User-Agent": "TelegramBot/2.0"
    }

    try:

        response = requests.get(
            DECOLECTA_BASE + endpoint,
            headers=headers,
            params=params or {},
            timeout=20
        )

    except requests.RequestException as e:

        raise RuntimeError(
            f"Error de conexión: {e}"
        )

    if response.status_code == 401:

        raise RuntimeError(
            "La API key de Decolecta no es válida."
        )

    if response.status_code == 429:

        raise RuntimeError(
            "Decolecta indicó límite de solicitudes."
        )

    if response.status_code >= 400:

        try:
            error = response.json()
        except Exception:
            error = response.text[:300]

        raise RuntimeError(
            f"API HTTP {response.status_code}: {error}"
        )

    try:

        return response.json()

    except Exception:

        raise RuntimeError(
            "Decolecta devolvió una respuesta inválida."
        )


# =========================================================
# RUC
# =========================================================

def consulta_ruc_pe(ruc):

    ruc = str(ruc).strip()

    return decolecta_get(
        "/v1/sunat/ruc/full",
        {
            "numero": ruc
        }
    )


def format_ruc(data):

    if not isinstance(data, dict):
        return (
            "🇵🇪 RUC PERÚ\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "Respuesta inválida."
        )

    fields = [
        ("RUC", ["ruc", "numero", "document_number"]),
        ("Razón social", ["razon_social", "nombre_o_razon_social"]),
        ("Estado", ["estado"]),
        ("Condición", ["condicion"]),
        ("Dirección", ["direccion"]),
        ("Departamento", ["departamento"]),
        ("Provincia", ["provincia"]),
        ("Distrito", ["distrito"]),
    ]

    lines = [
        "🇵🇪 RUC PERÚ",
        "━━━━━━━━━━━━━━━━"
    ]

    for label, keys in fields:

        value = None

        for key in keys:

            if key in data:
                value = data.get(key)
                break

        if value not in (
            None,
            "",
            "null"
        ):

            lines.append(
                f"🔹 {label}: {value}"
            )

    if len(lines) == 2:

        lines.append(
            "No se encontraron datos."
        )

    lines.append(
        "━━━━━━━━━━━━━━━━"
    )

    return "\n".join(lines)[:4000]


# =========================================================
# TIPO DE CAMBIO SUNAT
# =========================================================

def consulta_tc_sunat(
    fecha=None,
    mes=None,
    anio=None
):

    params = {}

    if fecha:
        params["date"] = fecha

    if mes is not None:
        params["month"] = mes

    if anio is not None:
        params["year"] = anio

    return decolecta_get(
        "/v1/tipo-cambio/sunat",
        params
    )


def format_tc(
    data,
    title="💱 TIPO DE CAMBIO SUNAT"
):

    if isinstance(data, list):

        if not data:

            return (
                f"{title}\n\n"
                "No se encontraron resultados."
            )

        output = [
            title,
            "━━━━━━━━━━━━━━━━"
        ]

        for item in data[:20]:

            output.append(
                f"📅 Fecha: "
                f"{item.get('date', 'N/A')}\n"
                f"💰 Compra: "
                f"{item.get('buy_price', 'N/A')}\n"
                f"💰 Venta: "
                f"{item.get('sell_price', 'N/A')}\n"
                "──────────────"
            )

        return "\n".join(output)[:4000]

    if not isinstance(data, dict):

        return (
            f"{title}\n\n"
            "Respuesta inválida."
        )

    return (
        f"{title}\n"
        "━━━━━━━━━━━━━━━━\n"
        f"💵 Compra: "
        f"{data.get('buy_price', 'N/A')}\n"
        f"💵 Venta: "
        f"{data.get('sell_price', 'N/A')}\n"
        f"💱 Moneda: "
        f"{data.get('base_currency', 'USD')}/"
        f"{data.get('quote_currency', 'PEN')}\n"
        f"📅 Fecha: "
        f"{data.get('date', 'N/A')}\n"
        "━━━━━━━━━━━━━━━━"
    )


# =========================================================
# COMMANDS
# =========================================================

async def setup_commands(app):

    user_commands = [

        BotCommand(
            "start",
            "Acceso principal"
        ),

        BotCommand(
            "sys",
            "Panel principal"
        ),

        BotCommand(
            "mycoins",
            "Ver saldo"
        ),

        BotCommand(
            "myinfo",
            "Mi información"
        ),

        BotCommand(
            "ruc",
            "Consultar RUC Perú"
        ),

        BotCommand(
            "tc",
            "Tipo de cambio SUNAT"
        ),

        BotCommand(
            "tcfecha",
            "TC SUNAT por fecha"
        ),

        BotCommand(
            "tcmes",
            "TC SUNAT mensual"
        ),
    ]

    await app.bot.set_my_commands(
        user_commands
    )

    admin_commands = user_commands + [

        BotCommand(
            "addcoins",
            "Dar coins"
        ),

        BotCommand(
            "addvip",
            "Dar VIP"
        ),

        BotCommand(
            "remvip",
            "Quitar VIP"
        ),

        BotCommand(
            "users",
            "Ver usuarios"
        ),

        BotCommand(
            "stats",
            "Estadísticas"
        ),
    ]

    await app.bot.set_my_commands(
        admin_commands,
        scope=BotCommandScopeChat(
            chat_id=OWNER_ID
        )
    )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    ensure_user(
        user.id,
        user.username,
        user.first_name
    )

    data = get_user(user.id)

    if user.id == OWNER_ID:

        plan = "OWNER ∞"
        coins = "ILIMITADO"

    else:

        plan = (
            "VIP"
            if is_vip(data)
            else "FREE"
        )

        coins = data["coins"]

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🌎 Abrir panel",
                callback_data="panel"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 Mi saldo",
                callback_data="mycoins"
            ),

            InlineKeyboardButton(
                "👤 Mi info",
                callback_data="myinfo"
            )
        ]

    ])

    await update.message.reply_text(

        "╭━━━━━━━━━━━━━━━━╮\n"
        "      🤖 TELEGRAM BOT\n"
        "╰━━━━━━━━━━━━━━━━╯\n\n"

        f"👤 ID: {user.id}\n"
        f"⭐ PLAN: {plan}\n"
        f"🪙 COINS: {coins}\n\n"

        "Selecciona una opción:",

        reply_markup=keyboard
    )


# =========================================================
# MYCOINS
# =========================================================

async def mycoins_cmd(
    update,
    context
):

    user_id = update.effective_user.id

    data = get_user(user_id)

    if user_id == OWNER_ID:

        await update.message.reply_text(
            "╭━━━━━━━━━━━━━━╮\n"
            "       👑 OWNER\n"
            "╰━━━━━━━━━━━━━━╯\n\n"
            "🪙 Coins: ILIMITADOS ∞"
        )

        return

    await update.message.reply_text(

        "╭━━━━━━━━━━━━━━╮\n"
        "       💰 SALDO\n"
        "╰━━━━━━━━━━━━━━╯\n\n"

        f"⭐ Plan: "
        f"{'VIP' if is_vip(data) else 'FREE'}\n"
        f"🪙 Coins: {data['coins']}"
    )


# =========================================================
# MYINFO
# =========================================================

async def myinfo_cmd(
    update,
    context
):

    user = update.effective_user

    data = get_user(user.id)

    if user.id == OWNER_ID:
        plan = "OWNER ∞"
    else:
        plan = (
            "VIP"
            if is_vip(data)
            else "FREE"
        )

    await update.message.reply_text(

        "╭━━━━━━━━━━━━━━━━╮\n"
        "       👤 MI INFO\n"
        "╰━━━━━━━━━━━━━━━━╯\n\n"

        f"🆔 ID: {user.id}\n"
        f"👤 Nombre: "
        f"{user.first_name or 'N/A'}\n"
        f"🔹 Username: "
        f"@{user.username if user.username else 'N/A'}\n"
        f"⭐ Plan: {plan}\n"
        f"🪙 Coins: {data['coins']}"
    )


# =========================================================
# ADD COINS
# =========================================================

async def addcoins_cmd(
    update,
    context
):

    if update.effective_user.id != OWNER_ID:

        await update.message.reply_text(
            "❌ Solo el OWNER puede usar este comando."
        )

        return

    if len(context.args) != 2:

        await update.message.reply_text(
            "Uso:\n"
            "/addcoins ID CANTIDAD\n\n"
            "Ejemplo:\n"
            "/addcoins 123456789 50"
        )

        return

    try:

        user_id = int(
            context.args[0]
        )

        amount = int(
            context.args[1]
        )

        if amount <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ ID o cantidad inválida."
        )

        return

    add_coins(
        user_id,
        amount
    )

    data = get_user(user_id)

    await update.message.reply_text(

        "✅ COINS ACTUALIZADOS\n"
        "━━━━━━━━━━━━━━━━\n\n"

        f"🆔 ID: {user_id}\n"
        f"➕ Añadidos: {amount}\n"
        f"💰 Saldo: {data['coins']}"
    )


# =========================================================
# ADD VIP
# =========================================================

async def addvip_cmd(
    update,
    context
):

    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) != 2:

        await update.message.reply_text(
            "Uso:\n"
            "/addvip ID DIAS"
        )

        return

    try:

        user_id = int(
            context.args[0]
        )

        days = int(
            context.args[1]
        )

        if days <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Datos inválidos."
        )

        return

    add_vip(
        user_id,
        days
    )

    await update.message.reply_text(

        "✅ VIP ACTUALIZADO\n"
        "━━━━━━━━━━━━━━━━\n\n"

        f"🆔 ID: {user_id}\n"
        f"⭐ Días añadidos: {days}"
    )


# =========================================================
# REMOVE VIP
# =========================================================

async def remvip_cmd(
    update,
    context
):

    if update.effective_user.id != OWNER_ID:
        return

    if len(context.args) != 1:

        await update.message.reply_text(
            "Uso:\n"
            "/remvip ID"
        )

        return

    try:

        user_id = int(
            context.args[0]
        )

    except ValueError:

        await update.message.reply_text(
            "❌ ID inválido."
        )

        return

    remove_vip(user_id)

    await update.message.reply_text(

        "✅ VIP ELIMINADO\n"
        "━━━━━━━━━━━━━━━━\n\n"

        f"🆔 ID: {user_id}"
    )


# =========================================================
# USERS
# =========================================================

async def users_cmd(
    update,
    context
):

    if update.effective_user.id != OWNER_ID:
        return

    conn = db_connect()

    total = conn.execute(
        "SELECT COUNT(*) AS c FROM users"
    ).fetchone()["c"]

    rows = conn.execute("""
        SELECT
            user_id,
            username,
            coins,
            vip_until
        FROM users
        ORDER BY updated_at DESC
        LIMIT 20
    """).fetchall()

    conn.close()

    text = (
        f"👥 USUARIOS: {total}\n"
        "━━━━━━━━━━━━━━━━\n"
    )

    for row in rows:

        vip = (
            "VIP"
            if float(row["vip_until"]) > time.time()
            else "FREE"
        )

        username = (
            f"@{row['username']}"
            if row["username"]
            else "sin_username"
        )

        text += (
            f"🆔 {row['user_id']}\n"
            f"👤 {username}\n"
            f"⭐ {vip} | "
            f"🪙 {row['coins']}\n"
            "──────────────\n"
        )

    await update.message.reply_text(
        text[:4000]
    )


# =========================================================
# STATS
# =========================================================

async def stats_cmd(
    update,
    context
):

