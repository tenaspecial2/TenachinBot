"""
Standalone Vercel webhook handler for Tena Special Bot.
Uses Telegram Bot API directly via HTTP (no aiogram dependency chain).
Uses Supabase for data persistence.
"""
import json
import os
import hashlib
import hmac
import logging
from http.server import BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
ADMIN_IDS      = [int(x) for x in os.getenv("ADMIN_IDS", "501384766,5872954068").split(",")]
SUPABASE_URL   = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY   = os.getenv("SUPABASE_SERVICE_KEY", "")
WEBSITE_URL    = "https://healthlink-gate-main-nine.vercel.app/"
SUPPORT_PHONE  = "+251 90 834 3267"
FREE_CHANNEL   = "https://t.me/tenachinfree"
PREMIUM_CHANNEL= "https://t.me/tenachinpremium"

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── Telegram API helpers ───────────────────────────────────────────

def tg_post(method: str, payload: dict) -> dict:
    url = f"{TG_API}/{method}"
    data = json.dumps(payload).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except URLError as e:
        logger.error(f"Telegram API error: {e}")
        return {}

def send_message(chat_id: int, text: str, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_post("sendMessage", payload)

def answer_callback(callback_id: str, text: str = ""):
    tg_post("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})

def inline_keyboard(rows: list[list[dict]]) -> dict:
    return {"inline_keyboard": rows}

# ── Supabase helpers ───────────────────────────────────────────────

def sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

def sb_get(table: str, params: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    req = Request(url, headers=sb_headers())
    try:
        with urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.error(f"Supabase GET error: {e}")
        return []

def sb_post(table: str, body: dict) -> dict:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    data = json.dumps(body).encode()
    req = Request(url, data=data, headers={**sb_headers(), "Prefer": "return=representation"})
    try:
        with urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.error(f"Supabase POST error: {e}")
        return {}

def sb_patch(table: str, query: str, body: dict) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{table}?{query}"
    data = json.dumps(body).encode()
    headers = {**sb_headers(), "Prefer": "return=minimal"}
    req = Request(url, data=data, headers=headers, method="PATCH")
    try:
        with urlopen(req, timeout=8) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        logger.error(f"Supabase PATCH error: {e}")
        return False

# ── Bot Handlers ───────────────────────────────────────────────────

def handle_start(chat_id: int, user: dict, payload: str = ""):
    name = user.get("first_name", "there")
    is_admin = user.get("id") in ADMIN_IDS

    # Handle login token from website
    if payload.startswith("login_"):
        token = payload[6:]
        handle_login_token(chat_id, user, token)
        return

    text = (
        f"👋 Welcome to <b>Tena Special</b>, {name}!\n\n"
        "🏥 Connect with verified specialist doctors for private online consultations.\n\n"
        f"🌐 <a href='{WEBSITE_URL}'>Visit our website</a>"
    )

    buttons = [
        [{"text": "🌐 Open Website", "web_app": {"url": WEBSITE_URL}}],
        [{"text": "👨‍⚕️ Browse Doctors", "callback_data": "browse_doctors"}],
        [{"text": "📋 My Consultations", "callback_data": "my_consultations"}],
        [{"text": "📞 Support", "callback_data": "support"}],
    ]
    if is_admin:
        buttons.append([{"text": "⚙️ Admin Panel", "callback_data": "admin_panel"}])

    send_message(chat_id, text, reply_markup=inline_keyboard(buttons))


def handle_login_token(chat_id: int, user: dict, token: str):
    """Verify login token from website and update Supabase."""
    telegram_id = str(user.get("id", ""))
    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    username = user.get("username", "")

    updated = sb_patch(
        "login_tokens",
        f"token=eq.{token}&used=eq.false",
        {
            "telegram_id": telegram_id,
            "telegram_name": name,
            "telegram_username": username,
        }
    )

    if updated:
        send_message(
            chat_id,
            f"✅ <b>Login confirmed!</b>\n\nGo back to the website — you'll be logged in automatically, {name}! 🚀"
        )
    else:
        send_message(chat_id, "❌ This login link has expired or already been used.\nPlease go back to the website and try again.")



def handle_browse_doctors(chat_id: int):
    doctors = sb_get("public_doctor_profiles", "select=full_name,specialty,consultation_fee&is_verified=eq.true")
    if not doctors:
        send_message(chat_id, "No verified doctors available yet. Check back soon!")
        return

    text = "👨‍⚕️ <b>Available Doctors</b>\n\n"
    buttons = []
    for doc in doctors[:8]:
        name = doc.get("full_name", "Unknown")
        spec = doc.get("specialty", "General")
        fee  = doc.get("consultation_fee", "N/A")
        text += f"• <b>{name}</b> — {spec} ({fee} ETB)\n"
        buttons.append([{"text": f"🩺 {name}", "callback_data": f"doctor_{name}"}])

    buttons.append([{"text": "⬅️ Back", "callback_data": "back_main"}])
    send_message(chat_id, text, reply_markup=inline_keyboard(buttons))


def handle_support(chat_id: int):
    text = (
        "📞 <b>Support</b>\n\n"
        f"Phone: {SUPPORT_PHONE}\n"
        f"Free Channel: {FREE_CHANNEL}\n"
        f"Premium Channel: {PREMIUM_CHANNEL}"
    )
    buttons = [[{"text": "⬅️ Back", "callback_data": "back_main"}]]
    send_message(chat_id, text, reply_markup=inline_keyboard(buttons))


def handle_admin_panel(chat_id: int, user_id: int):
    if user_id not in ADMIN_IDS:
        send_message(chat_id, "⛔ Access denied.")
        return
    text = "⚙️ <b>Admin Panel</b>\n\nManage the platform:"
    buttons = [
        [{"text": "📊 View Consultations", "callback_data": "admin_consultations"}],
        [{"text": "👨‍⚕️ Manage Doctors", "callback_data": "admin_doctors"}],
        [{"text": "⬅️ Back", "callback_data": "back_main"}],
    ]
    send_message(chat_id, text, reply_markup=inline_keyboard(buttons))


def handle_back_main(chat_id: int, user: dict):
    handle_start(chat_id, user)


# ── Update Router ──────────────────────────────────────────────────

def process_update(update: dict):
    # Handle messages
    if "message" in update:
        msg     = update["message"]
        chat_id = msg["chat"]["id"]
        user    = msg.get("from", {})
        text    = msg.get("text", "")

        if text.startswith("/start"):
            parts = text.split(" ", 1)
            payload = parts[1].strip() if len(parts) > 1 else ""
            handle_start(chat_id, user, payload)
        elif text.startswith("/help"):
            handle_support(chat_id)
        else:
            send_message(chat_id, "Use the menu below 👇", reply_markup=inline_keyboard([
                [{"text": "🏠 Main Menu", "callback_data": "back_main"}]
            ]))

    # Handle callback queries
    elif "callback_query" in update:
        cb      = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        user    = cb.get("from", {})
        data    = cb.get("data", "")

        answer_callback(cb["id"])

        if data == "browse_doctors":
            handle_browse_doctors(chat_id)
        elif data == "support":
            handle_support(chat_id)
        elif data == "admin_panel":
            handle_admin_panel(chat_id, user.get("id", 0))
        elif data == "back_main":
            handle_back_main(chat_id, user)
        elif data == "my_consultations":
            send_message(chat_id, f"📋 View your consultations on our website:\n{WEBSITE_URL}")
        else:
            send_message(chat_id, "Coming soon! 🚧")


# ── Vercel Handler ─────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Tena Special Bot is active.")

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            update = json.loads(body)
            process_update(update)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            self.send_response(200)  # Always return 200 to Telegram
            self.end_headers()
            self.wfile.write(b'{"ok":false}')
