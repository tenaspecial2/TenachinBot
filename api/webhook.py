"""
Tena Special Bot — Full Vercel Webhook Handler
Dynamic doctors from Supabase, full Amharic UI, FSM via Supabase,
profit tracking for doctors, admin group notifications.
"""
import json
import os
import logging
from http.server import BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
ADMIN_GROUP     = int(os.getenv("ADMIN_GROUP_ID", "0"))  # Telegram group chat ID (negative number)
SUPABASE_URL    = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY    = os.getenv("SUPABASE_SERVICE_KEY", "")
WEBSITE_URL     = "https://healthlink-gate-main-nine.vercel.app/"
SUPPORT_PHONE_1 = "+251 90 834 3267"
SUPPORT_PHONE_2 = "0967449552"
SUPPORT_USERNAME= "@tenachinbottelemedicine"
FREE_CHANNEL    = "https://t.me/tenachinfree"
PREMIUM_CHANNEL = "https://t.me/tenachinpremium"
FREE_GROUP      = "https://t.me/+UXHaDU3GIudlY2U0"
COMMISSION_PCT  = 10.0

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── Telegram API ───────────────────────────────────────────────────

def tg(method: str, payload: dict) -> dict:
    url  = f"{TG_API}/{method}"
    data = json.dumps(payload).encode()
    req  = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except URLError as e:
        logger.error(f"TG {method} error: {e}")
        return {}

def send(chat_id, text, markup=None, parse_mode="HTML"):
    p = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if markup:
        p["reply_markup"] = markup
    return tg("sendMessage", p)

def edit_text(chat_id, message_id, text, markup=None):
    p = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    tg("editMessageText", p)

def edit_caption(chat_id, message_id, caption):
    tg("editMessageCaption", {"chat_id": chat_id, "message_id": message_id,
                               "caption": caption, "parse_mode": "HTML"})

def answer_cb(cb_id, text=""):
    tg("answerCallbackQuery", {"callback_query_id": cb_id, "text": text})

def fwd_photo(chat_id, file_id, caption, markup=None):
    p = {"chat_id": chat_id, "photo": file_id, "caption": caption, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    tg("sendPhoto", p)

def fwd_doc(chat_id, file_id, caption, markup=None):
    p = {"chat_id": chat_id, "document": file_id, "caption": caption, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    tg("sendDocument", p)

def copy_msg(to_id, from_id, msg_id):
    tg("copyMessage", {"chat_id": to_id, "from_chat_id": from_id, "message_id": msg_id})

def notify_admin(file_id: str, caption: str, markup, is_photo: bool):
    """Forward a receipt/notification to the admin group."""
    if not ADMIN_GROUP:
        logger.warning("ADMIN_GROUP_ID not set in environment variables.")
        return
    (fwd_photo if is_photo else fwd_doc)(ADMIN_GROUP, file_id, caption, markup=markup)

# ── Keyboards ─────────────────────────────────────────────────────

def rk(*rows):
    return {"keyboard": [[{"text": t} for t in row] for row in rows],
            "resize_keyboard": True}

def ik(*rows):
    return {"inline_keyboard": list(rows)}

def btn(text, cb=None, url=None):
    if url:   return {"text": text, "url": url}
    return {"text": text, "callback_data": cb}

MAIN_MENU = rk(
    ["👨‍⚕️ ስፔሻሊስት ለማማከር"],
    ["📚 የጤና ትምህርቶች"],
    ["👥 የቡድን ህክምና ምክክሮች"],
    ["🏠 የቤት ለቤት ህክምና & 🚨 ድንገተኛ አደጋ"],
    ["📞 እርዳታና ድጋፍ (Help)"],
    ["💰 የምክክር ዋጋዬን ማስተካከያ", "📊 የኔ ትርፍ (Earnings)"],
)

SPEC_SUB = ik(
    [btn("👤 ታካሚ/ጠያቂ ነኝ", cb="spec_patient")],
    [btn("👨‍⚕️ ጠቅላላ ሀኪም (GP) ነኝ", cb="spec_gp")],
    [btn("📝 የስፔሻሊስት/ዶክተር ምዝገባ", cb="start_doc_reg")],
    [btn("⬅️ ተመለስ", cb="back_main")],
)

SPECIALTIES_KB = ik(
    [btn("🩺 የውስጥ ደዌ (Internal Medicine)", cb="dept_internal")],
    [btn("🧠 የነርቭ ስፔሻሊስት (Neurology)",    cb="dept_neuro")],
    [btn("👶 የህፃናት ስፔሻሊስት (Pediatrics)",  cb="dept_peds")],
    [btn("🫀 የልብ ስፔሻሊስት (Cardiology)",    cb="dept_cardio")],
    [btn("🤰 የማህፀንና ፅንስ (OBGYN)",          cb="dept_obgyn")],
    [btn("⬅️ ተመለስ", cb="back_to_spec_choice")],
)

EDU_MENU = ik(
    [btn("🎁 ነፃ የጤና ትምህርቶች (Free Channel)", url=FREE_CHANNEL)],
    [btn("💎 ፕሪሚየም ቻናል (24 ETB/ወር)", cb="buy_premium_channel")],
    [btn("🩺 የውስጥ ደዌ መጻሕፍት (Internal Med)", cb="store_dept_internal")],
    [btn("🤰 የማህፀን መጻሕፍት (OBGYN)",          cb="store_dept_obgyn")],
    [btn("👶 የሕፃናት ህክምና (Pediatrics)",       cb="store_dept_peds")],
    [btn("⬅️ ተመለስ", cb="back_main")],
)

GROUP_MENU = ik(
    [btn("👥 ነፃ የቡድን ውይይት (Free Group)", url=FREE_GROUP)],
    [btn("🔒 ፕሪሚየም የቪዲዮ/ድምፅ ውይይት", cb="group_premium")],
    [btn("⬅️ ተመለስ", cb="back_main")],
)

HOMECARE_MENU = ik(
    [btn("🏠 የቤት ለቤት ህክምና ስልክ", cb="homecare_info")],
    [btn("🚨 ድንገተኛ አደጋ (Emergency)", cb="emergency_alert")],
    [btn("⬅️ ተመለስ", cb="back_main")],
)

def digital_products_kb(dept):
    if dept == "internal":
        return ik(
            [btn("📘 የደም ግፊት መከላከያ - 200 ETB", cb="buy_prod_HTN Book_200_pdf")],
            [btn("📙 የስኳር በሽታ አያያዝ - 300 ETB",  cb="buy_prod_DM Book_300_pdf")],
            [btn("⬅️ ተመለስ", cb="back_to_edu_menu")],
        )
    elif dept == "obgyn":
        return ik(
            [btn("📗 OBGYN Guide (PDF) - 300 ETB",   cb="buy_prod_OBGYN Guide_300_pdf")],
            [btn("🎬 OBGYN Video Lecture - 500 ETB", cb="buy_prod_OBGYN Video_500_video")],
            [btn("📘 የእርግዝና እንክብካቤ - 250 ETB",    cb="buy_prod_Pregnancy Care_250_pdf")],
            [btn("⬅️ ተመለስ", cb="back_to_edu_menu")],
        )
    else:  # peds
        return ik(
            [btn("📘 የሕፃናት ምግብና እድገት - 200 ETB", cb="buy_prod_Child Health_200_pdf")],
            [btn("⬅️ ተመለስ", cb="back_to_edu_menu")],
        )

def admin_approve_kb(approve_cb, reject_user_id):
    return ik([btn("✅ Approve", cb=approve_cb),
               btn("❌ Reject",  cb=f"reject_{reject_user_id}")])

def rating_kb(doctor_id):
    return ik([
        btn("⭐ 1",       cb=f"rate_1_{doctor_id}"),
        btn("⭐⭐ 2",    cb=f"rate_2_{doctor_id}"),
        btn("⭐⭐⭐ 3", cb=f"rate_3_{doctor_id}"),
        btn("⭐⭐⭐⭐ 4", cb=f"rate_4_{doctor_id}"),
        btn("⭐⭐⭐⭐⭐ 5", cb=f"rate_5_{doctor_id}"),
    ])

def end_consultation_kb(other_user_id):
    return ik([btn("🛑 End Consultation", cb=f"confirm_end_{other_user_id}")])

# ── Supabase helpers ───────────────────────────────────────────────

def _sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

def sb_get(table, params=""):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    req = Request(url, headers=_sb_headers())
    try:
        with urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.error(f"sb_get {table}: {e}")
        return []

def sb_post(table, body):
    url  = f"{SUPABASE_URL}/rest/v1/{table}"
    data = json.dumps(body).encode()
    req  = Request(url, data=data,
                   headers={**_sb_headers(), "Prefer": "return=minimal"})
    try:
        with urlopen(req, timeout=8):
            return True
    except Exception as e:
        logger.error(f"sb_post {table}: {e}")
        return False

def sb_patch(table, query, body):
    url     = f"{SUPABASE_URL}/rest/v1/{table}?{query}"
    data    = json.dumps(body).encode()
    headers = {**_sb_headers(), "Prefer": "return=minimal"}
    req     = Request(url, data=data, headers=headers, method="PATCH")
    try:
        with urlopen(req, timeout=8) as r:
            return r.status in (200, 204)
    except Exception as e:
        logger.error(f"sb_patch {table}: {e}")
        return False

def sb_delete(table, query):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{query}"
    req = Request(url, headers=_sb_headers(), method="DELETE")
    try:
        with urlopen(req, timeout=8):
            return True
    except Exception as e:
        logger.error(f"sb_delete {table}: {e}")
        return False

# ── Dynamic doctor helpers ─────────────────────────────────────────

def get_doctors_list(dept: str = "") -> list:
    try:
        docs = sb_get("public_doctor_profiles",
                      "select=full_name,specialty,telegram_id")
        if dept:
            dept_map = {
                "internal": "Internal",
                "neuro":    "Neurol",
                "peds":     "Pediatr",
                "cardio":   "Cardiol",
                "obgyn":    "OBGYN",
            }
            kw = dept_map.get(dept, "")
            if kw:
                docs = [d for d in docs
                        if kw.lower() in (d.get("specialty") or "").lower()]
        return [d for d in docs if d.get("telegram_id")]
    except Exception as e:
        logger.error(f"get_doctors_list: {e}")
        return []

def is_doctor(uid: int) -> bool:
    try:
        rows = sb_get("public_doctor_profiles",
                      f"telegram_id=eq.{uid}&select=telegram_id")
        return bool(rows)
    except Exception:
        return False

def get_doctor_name_by_tid(telegram_id: int) -> str:
    try:
        rows = sb_get("public_doctor_profiles",
                      f"telegram_id=eq.{telegram_id}&select=full_name")
        if rows:
            return rows[0].get("full_name", f"Doctor ({telegram_id})")
    except Exception:
        pass
    return f"Doctor ({telegram_id})"

def get_doctor_online(telegram_id: int) -> bool:
    rows = sb_get("doctor_consultation_fees",
                  f"telegram_id=eq.{telegram_id}&select=is_online")
    return rows[0].get("is_online", False) if rows else False

def doctors_kb(dept: str):
    rows = []
    for d in get_doctors_list(dept):
        tid    = int(d["telegram_id"])
        name   = d.get("full_name", "Doctor")
        online = get_doctor_online(tid)
        status = "🟢 Online" if online else "🔴 Offline"
        rows.append([btn(f"{name} ({status})", cb=f"select_doc_{tid}_{name}")])
    if not rows:
        rows.append([btn("❌ ምንም ዶክተር አልተገኘም", cb="back_to_depts")])
    rows.append([btn("⬅️ ተመለስ", cb="back_to_depts")])
    return {"inline_keyboard": rows}

# ── Doctor fee / online helpers ────────────────────────────────────

def get_doctor_fees(doctor_id: int) -> dict:
    rows = sb_get("doctor_consultation_fees",
                  f"telegram_id=eq.{doctor_id}&select=text_fee,voice_fee,video_fee")
    if rows:
        return {"text":  rows[0].get("text_fee", 100),
                "voice": rows[0].get("voice_fee", 200),
                "video": rows[0].get("video_fee", 300)}
    return {"text": 100, "voice": 200, "video": 300}

def set_doctor_fees(doctor_id: int, text_fee, voice_fee, video_fee):
    body = {"telegram_id": doctor_id, "text_fee": text_fee,
            "voice_fee": voice_fee, "video_fee": video_fee}
    if not sb_patch("doctor_consultation_fees", f"telegram_id=eq.{doctor_id}", body):
        sb_post("doctor_consultation_fees", body)

def toggle_online(doctor_id: int) -> bool:
    current = get_doctor_online(doctor_id)
    new_val = not current
    body = {"telegram_id": doctor_id, "is_online": new_val}
    if not sb_patch("doctor_consultation_fees", f"telegram_id=eq.{doctor_id}", body):
        sb_post("doctor_consultation_fees", body)
    return new_val

def call_type_kb(doctor_id, doctor_name):
    fees = get_doctor_fees(doctor_id)
    return ik(
        [btn(f"💬 Text Chat - {fees['text']} ETB",
             cb=f"call_{doctor_id}_text_{fees['text']}_{doctor_name}")],
        [btn(f"🎙️ Voice Call - {fees['voice']} ETB",
             cb=f"call_{doctor_id}_voice_{fees['voice']}_{doctor_name}")],
        [btn(f"📹 Video Call - {fees['video']} ETB",
             cb=f"call_{doctor_id}_video_{fees['video']}_{doctor_name}")],
        [btn("⬅️ ተመለስ", cb="back_to_depts")],
    )

# ── Earnings helpers ───────────────────────────────────────────────

def get_doctor_earnings(telegram_id: int) -> dict:
    try:
        rows = sb_get("bot_transactions",
                      f"doctor_telegram_id=eq.{telegram_id}"
                      f"&select=price,commission,net_amount,item_title,created_at"
                      f"&order=created_at.desc")
        total  = sum(r.get("price", 0) or 0 for r in rows)
        commis = sum(r.get("commission", 0) or 0 for r in rows)
        net    = sum(r.get("net_amount", 0) or 0 for r in rows)
        return {"total": total, "commission": commis, "net": net,
                "count": len(rows), "recent": rows[:5]}
    except Exception as e:
        logger.error(f"get_doctor_earnings: {e}")
        return {"total": 0, "commission": 0, "net": 0, "count": 0, "recent": []}

def record_transaction(doctor_telegram_id: int, doctor_name: str,
                       item_type: str, item_title: str, price: float, user_id: int):
    commission = round(price * COMMISSION_PCT / 100, 2)
    net        = round(price - commission, 2)
    sb_post("bot_transactions", {
        "doctor_telegram_id": doctor_telegram_id,
        "doctor_name":   doctor_name,
        "item_type":     item_type,
        "item_title":    item_title,
        "price":         price,
        "commission":    commission,
        "net_amount":    net,
        "user_id":       user_id,
    })

# ── FSM helpers ────────────────────────────────────────────────────

def get_state(user_id: int) -> dict:
    rows = sb_get("bot_fsm_states", f"user_id=eq.{user_id}&select=state,data")
    if rows:
        return {"state": rows[0].get("state", ""), "data": rows[0].get("data") or {}}
    return {"state": "", "data": {}}

def set_state(user_id: int, state: str, data: dict = None):
    body = {"user_id": user_id, "state": state, "data": data or {}}
    url  = f"{SUPABASE_URL}/rest/v1/bot_fsm_states?user_id=eq.{user_id}"
    d    = json.dumps(body).encode()
    req  = Request(url, data=d,
                   headers={**_sb_headers(), "Prefer": "resolution=merge-duplicates"},
                   method="PATCH")
    try:
        with urlopen(req, timeout=8) as r:
            if r.status not in (200, 204):
                sb_post("bot_fsm_states", body)
    except Exception:
        sb_post("bot_fsm_states", body)

def clear_state(user_id: int):
    sb_delete("bot_fsm_states", f"user_id=eq.{user_id}")

def update_state_data(user_id: int, extra: dict):
    s = get_state(user_id)
    s["data"].update(extra)
    set_state(user_id, s["state"], s["data"])

def start_session(patient_id: int, doctor_id: int, call_type: str):
    set_state(patient_id, "in_session", {"partner_id": doctor_id, "call_type": call_type})
    set_state(doctor_id,  "in_session", {"partner_id": patient_id, "call_type": call_type})

def end_session_state(user_id: int, partner_id: int):
    clear_state(user_id)
    clear_state(partner_id)

# ── Bot handlers ───────────────────────────────────────────────────

def handle_start(chat_id: int, user: dict, payload: str = ""):
    if payload.startswith("login_"):
        handle_login_token(chat_id, user, payload[6:])
        return
    clear_state(chat_id)
    send(chat_id,
         "👋 <b>እንኳን ወደ ጤናችን (Tenachin) የህክምና ማማከሪያ ቦት በደህና መጡ!</b>\n\n"
         "እባክዎ የሚፈልጉትን አገልግሎት ከታች ካለው ሜኑ ይምረጡ፦",
         markup=MAIN_MENU)

def handle_login_token(chat_id: int, user: dict, token: str):
    tg_id    = str(user.get("id", ""))
    name     = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    username = user.get("username", "")
    ok = sb_patch("login_tokens", f"token=eq.{token}&used=eq.false",
                  {"telegram_id": tg_id, "telegram_name": name,
                   "telegram_username": username})
    if ok:
        send(chat_id,
             f"✅ <b>Login confirmed!</b>\n\nGo back to the website — "
             f"you'll be logged in automatically, {name}! 🚀")
    else:
        send(chat_id, "❌ This login link expired or was already used.\nPlease go back and try again.")

def handle_set_fees_start(chat_id: int, user: dict):
    uid = user.get("id", 0)
    if not is_doctor(uid):
        send(chat_id, "⛔ ይህ አገልግሎት ለስፔሻሊስት ሀኪሞች ብቻ ነው።")
        return
    fees   = get_doctor_fees(uid)
    online = get_doctor_online(uid)
    status_label = "🟢 Online" if online else "🔴 Offline"
    send(chat_id,
         f"💰 <b>የምክክር ዋጋ ማስተካከያ</b>\n\n"
         f"💬 Text Chat:  <b>{fees['text']} ETB</b>\n"
         f"🎙️ Voice Call: <b>{fees['voice']} ETB</b>\n"
         f"📹 Video Call: <b>{fees['video']} ETB</b>\n\n"
         f"📶 አሁኑ ሁኔታ: <b>{status_label}</b>",
         markup=ik(
             [btn("💬 Text Chat ዋጋ ለመለወጥ",   cb="set_fee_text")],
             [btn("🎙️ Voice Call ዋጋ ለመለወጥ", cb="set_fee_voice")],
             [btn("📹 Video Call ዋጋ ለመለወጥ", cb="set_fee_video")],
             [btn("🔴 Go Offline" if online else "🟢 Go Online", cb="toggle_online")],
             [btn("⬅️ ወደ ሜኑ", cb="back_main")],
         ))

def handle_earnings(chat_id: int, user: dict):
    uid = user.get("id", 0)
    if not is_doctor(uid):
        send(chat_id,
             "📊 <b>Earnings Tracker</b>\n\n"
             "ይህ አገልግሎት ለስፔሻሊስት ሀኪሞች ብቻ ነው።\n\n"
             f"ዶክተር ለመመዝገብ: {WEBSITE_URL}")
        return
    e = get_doctor_earnings(uid)
    text = (
        f"📊 <b>የኔ ትርፍ (My Earnings)</b>\n\n"
        f"💵 <b>ጠቅላላ ክፍያ:</b>   {e['total']:.0f} ETB\n"
        f"🏛 <b>Commission (10%):</b> {e['commission']:.0f} ETB\n"
        f"✅ <b>ለኔ የሚደርሰኝ:</b>  {e['net']:.0f} ETB\n"
        f"📋 <b>ጠቅላላ ግብይቶች:</b> {e['count']}\n"
    )
    if e["recent"]:
        text += "\n<b>ቅርብ ጊዜ ግብይቶች:</b>\n"
        for r in e["recent"]:
            d   = (r.get("created_at") or "")[:10]
            t   = r.get("item_title", "—")
            amt = r.get("price", 0)
            text += f"  • {d} | {t} | {amt} ETB\n"
    send(chat_id, text, markup=MAIN_MENU)

# ── Menu text button handlers ──────────────────────────────────────

MENU_HANDLERS = {
    "👨‍⚕️ ስፔሻሊስት ለማማከር": lambda cid, _: send(
        cid, "👨‍⚕️ <b>የስፔሻሊስት ማማከሪያ ክፍል</b>\n\nእባክዎ ማንነትዎን ይምረጡ፦",
        markup=SPEC_SUB),
    "📚 የጤና ትምህርቶች": lambda cid, _: send(
        cid, "📚 <b>የጤና ትምህርቶች እና ዲጂታል Store</b>\n\nእባክዎ ይምረጡ፦",
        markup=EDU_MENU),
    "👥 የቡድን ህክምና ምክክሮች": lambda cid, _: send(
        cid, "👥 <b>የቡድን ህክምና ውይይቶች</b>\n\nእባክዎ ይምረጡ፦",
        markup=GROUP_MENU),
    "🏠 የቤት ለቤት ህክምና & 🚨 ድንገተኛ አደጋ": lambda cid, _: send(
        cid, "🏠 <b>የቤት ለቤት ህክምና እና ድንገተኛ አደጋ</b>\n\nእባክዎ ይምረጡ፦",
        markup=HOMECARE_MENU),
    "📞 እርዳታና ድጋፍ (Help)": lambda cid, _: send(
        cid,
        f"📞 <b>Support Center</b>\n\n"
        f"• ስልክ: <code>{SUPPORT_PHONE_1}</code> / <code>{SUPPORT_PHONE_2}</code>\n"
        f"• Telegram: {SUPPORT_USERNAME}\n"
        f"• Website: {WEBSITE_URL}"),
    "💰 የምክክር ዋጋዬን ማስተካከያ": lambda cid, user: handle_set_fees_start(cid, user),
    "📊 የኔ ትርፍ (Earnings)":    lambda cid, user: handle_earnings(cid, user),
}

# ── Callback handler ───────────────────────────────────────────────

def handle_callback(cb: dict):
    data = cb.get("data", "")
    cid  = cb["message"]["chat"]["id"]
    mid  = cb["message"]["message_id"]
    user = cb.get("from", {})
    uid  = user.get("id", 0)

    answer_cb(cb["id"])

    # Fee / online toggle
    if data in ("set_fee_text", "set_fee_voice", "set_fee_video"):
        if not is_doctor(uid):
            send(cid, "⛔ ይህ አገልግሎት ለስፔሻሊስቶች ብቻ ነው።")
            return
        fee_type = data.split("_")[2]
        labels   = {"text": "Text Chat", "voice": "Voice Call", "video": "Video Call"}
        set_state(uid, f"setting_fee_{fee_type}", {})
        send(cid, f"💰 <b>አዲስ {labels[fee_type]} ዋጋ ያስገቡ (ETB):</b>\n\nምሳሌ: 150")
        return

    if data == "toggle_online":
        if not is_doctor(uid):
            send(cid, "⛔ ይህ አገልግሎት ለስፔሻሊስቶች ብቻ ነው።")
            return
        new_status = toggle_online(uid)
        label = "🟢 Online" if new_status else "🔴 Offline"
        send(cid, f"✅ ሁኔታዎ ወደ <b>{label}</b> ተቀይሯል!", markup=MAIN_MENU)
        return

    # Navigation
    if data == "back_main":
        clear_state(uid)
        send(cid, "👋 እባክዎ ከሜኑ ይምረጡ፦", markup=MAIN_MENU)
    elif data == "back_to_spec_choice":
        edit_text(cid, mid, "👨‍⚕️ <b>ስፔሻሊስት ማማከሪያ</b>\n\nማንነትዎን ይምረጡ፦", markup=SPEC_SUB)
    elif data == "back_to_depts":
        edit_text(cid, mid, "🩺 <b>የስፔሻሊቲ ዘርፍ ይምረጡ፦</b>", markup=SPECIALTIES_KB)
    elif data == "back_to_edu_menu":
        edit_text(cid, mid, "📚 <b>የጤና ትምህርቶች Store</b>", markup=EDU_MENU)

    # Specialist sub-menu
    elif data in ("spec_patient", "spec_gp"):
        role = "Patient" if data == "spec_patient" else "GP"
        update_state_data(uid, {"user_role": role})
        edit_text(cid, mid, "🩺 <b>የስፔሻሊቲ ዘርፍ ይምረጡ፦</b>", markup=SPECIALTIES_KB)

    # Specialty → Doctors
    elif data.startswith("dept_"):
        dept = data.split("_")[1]
        edit_text(cid, mid, "👨‍⚕️ <b>ስፔሻሊስት ይምረጡ፦</b>", markup=doctors_kb(dept))

    # Doctor selected
    elif data.startswith("select_doc_"):
        parts = data.split("_")
        did   = int(parts[2])
        dname = "_".join(parts[3:])
        edit_text(cid, mid,
                  f"👨‍⚕️ <b>{dname}</b>\n\nየምክክር አይነት ይምረጡ፦",
                  markup=call_type_kb(did, dname))

    # Call type → payment
    elif data.startswith("call_"):
        parts  = data.split("_")
        did    = int(parts[1])
        ctype  = parts[2]
        price  = float(parts[3])
        dname  = "_".join(parts[4:])
        role   = get_state(uid)["data"].get("user_role", "Patient")

        if role == "GP":
            set_state(uid, "waiting_for_gp_case",
                      {"doctor_id": did, "doctor_name": dname,
                       "price": price, "call_type": ctype})
            send(cid,
                 f"👨‍⚕️ <b>ለ {dname} — Case Details</b>\n\n"
                 "የካርድ/የታካሚ ታሪክ በአንድ መልእክት ጽፈው ይላኩ፦")
        else:
            set_state(uid, "waiting_for_receipt",
                      {"doctor_id": did, "doctor_name": dname,
                       "price": price, "call_type": ctype})
            send(cid,
                 f"📋 <b>የምክክር ጥያቄ ለ {dname}</b>\n\n"
                 f"📞 <b>ዓይነት:</b> {ctype.upper()} Consultation\n"
                 f"💰 <b>ክፍያ:</b> {price} ETB\n\n"
                 "ክፍያ ቦታ፦\n"
                 "• <b>CBE:</b> <code>1000255631865</code> (Tazebachew Wudie)\n"
                 "• <b>Telebirr:</b> <code>0908343267</code>\n\n"
                 "<b>ደረሰኙን (Screenshot) ይላኩ፦</b>")

    # Doctor registration start
    elif data == "start_doc_reg":
        set_state(uid, "doc_reg_name", {})
        send(cid, "📝 <b>ዶክተር ምዝገባ</b>\n\nሙሉ ስምዎን ያስገቡ (ምሳሌ: Dr. Abebe Kebede):")

    # Education store
    elif data.startswith("store_dept_"):
        dept = data.split("_")[2]
        edit_text(cid, mid, "📚 <b>ምርጫዎን ያድርጉ፦</b>",
                  markup=digital_products_kb(dept))

    elif data.startswith("buy_prod_"):
        parts      = data.split("_")
        prod_name  = parts[2]
        prod_price = float(parts[3])
        file_type  = parts[4]
        set_state(uid, "waiting_for_store_receipt",
                  {"item_name": prod_name, "item_price": prod_price, "file_type": file_type})
        send(cid,
             f"📖 <b>{prod_name} ለመግዛት</b>\n\n"
             f"💳 <b>ዋጋ:</b> {prod_price} ETB\n\n"
             "ክፍያ ቦታ፦\n"
             "• <b>CBE:</b> <code>1000255631865</code>\n"
             "• <b>Telebirr:</b> <code>0908343267</code>\n\n"
             "<b>ደረሰኙን ፎቶ ወይም ዶኩሜንት አድርጎ ይላኩ፦</b>")

    # Premium channel
    elif data == "buy_premium_channel":
        set_state(uid, "waiting_for_premium_receipt", {})
        send(cid,
             "💎 <b>ፕሪሚየም ቻናል አባልነት (24 ETB/ወር)</b>\n\n"
             "ክፍያ ቦታ፦\n"
             "• <b>CBE:</b> <code>1000255631865</code>\n"
             "• <b>Telebirr:</b> <code>0908343267</code>\n\n"
             "<b>ደረሰኙን (Screenshot) ይላኩ፦</b>")

    # Info
    elif data == "group_premium":
        send(cid, f"🔒 <b>ፕሪሚየም ቪዲዮ/ድምፅ ውይይት</b>\n\nወርሃዊ ክፍያ: 150 ETB\nአድሚን: {SUPPORT_USERNAME}")
    elif data == "homecare_info":
        send(cid, f"🏠 <b>የቤት ለቤት ህክምና</b>\n\n📞 <code>{SUPPORT_PHONE_1}</code> / <code>{SUPPORT_PHONE_2}</code>")
    elif data == "emergency_alert":
        send(cid, "🚨 <b>ድንገተኛ አደጋ</b>\n\nወደ አቅራቢያ ሆስፒታል ሄዱ!\n📞 <b>907</b> (ቀይ መስቀል)")

    # Admin: Approve consultation
    elif data.startswith("approve_") and not data.startswith(
            ("approve_prem_", "approve_doc_", "approve_store_")):
        parts    = data.split("_")
        pat_id   = int(parts[1])
        doc_id   = int(parts[2])
        price    = float(parts[3]) if len(parts) > 3 else 300.0
        doc_name = "_".join(parts[4:]) if len(parts) > 4 else get_doctor_name_by_tid(doc_id)
        ctype    = "text" if price <= 100 else ("voice" if price <= 200 else "video")
        is_online = get_doctor_online(doc_id)

        record_transaction(doc_id, doc_name, "Consultation",
                           f"1-on-1 {ctype.upper()}", price, pat_id)

        if is_online:
            start_session(pat_id, doc_id, ctype)
            send(pat_id,
                 f"🟢 <b>ክፍያዎ ጸድቋል! ሀኪሙ Online ናቸው!</b>\n\n"
                 f"ከ {doc_name} ጋር ምስጢራዊ ምክክር ተጀምሯል።",
                 markup=end_consultation_kb(doc_id))
            send(doc_id,
                 f"👨‍⚕️ <b>አዲስ ታካሚ ተመድቦልዎታል!</b>\n\n"
                 f"👤 ታካሚ ID: <code>{pat_id}</code>\n💬 ዓይነት: {ctype.upper()}",
                 markup=end_consultation_kb(pat_id))
        else:
            send(pat_id,
                 f"🔴 <b>{doc_name} አሁን Offline ናቸው።</b>\n\n"
                 "ሀኪሙ ሰዓቱን ሲያሳውቁ መልእክት ይደርስዎታል!")
            send(doc_id,
                 f"🚨 <b>አዲስ ክፍያ ደርሷል!</b>\n\n"
                 f"👤 ታካሚ ID: <code>{pat_id}</code>\n📞 {ctype.upper()}\n\nሰዓቱን ይጠቁሙ:",
                 markup=ik([btn("🕒 ሰዓት ለመወሰን", cb=f"set_time_{pat_id}_{ctype}")]))

        edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n✅ <b>APPROVED</b>")

    elif data.startswith("approve_prem_"):
        pat_id = int(data.split("_")[2])
        send(pat_id, f"🎉 <b>ፕሪሚየም ክፍያዎ ጸድቋል!</b>\n\n🔗 {PREMIUM_CHANNEL}")
        edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n✅ PREMIUM APPROVED")

    elif data.startswith("approve_doc_"):
        doc_id = int(data.split("_")[2])
        send(doc_id,
             "🎉 <b>ምዝገባዎ ጸድቋል!</b>\n\nአሁን ከሲስተሙ ጋር ተቀላቅለዋል።")
        edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n✅ DOCTOR APPROVED")

    elif data.startswith("approve_store_"):
        parts     = data.split("_")
        pat_id    = int(parts[2])
        file_type = parts[3]
        price     = float(parts[4])
        item_name = "_".join(parts[5:]) if len(parts) > 5 else "Digital Product"
        record_transaction(0, "Admin", file_type.upper(), item_name, price, pat_id)
        send(pat_id, f"🎉 <b>ክፍያዎ ጸድቋል!</b>\n\n{item_name} ({file_type.upper()}) ቶሎ ይደርስዎታል!")
        edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n✅ APPROVED")

    elif data.startswith("reject_"):
        pat_id = int(data.split("_")[1])
        send(pat_id, "❌ <b>ደረሰኝዎ ውድቅ ተደርጓል!</b>\n\nትክክለኛ ደረሰኝ ይላኩ ወይም አድሚን ያናግሩ።")
        edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n❌ REJECTED")

    # Doctor scheduling
    elif data.startswith("set_time_"):
        parts  = data.split("_")
        pat_id = int(parts[2])
        ctype  = parts[3]
        set_state(uid, "doc_scheduling",
                  {"target_patient_id": pat_id, "scheduled_call_type": ctype})
        send(cid, "✍️ <b>ነፃ ሰዓቱን ይጻፉ (ምሳሌ: ነገ ከቀኑ 8:00):</b>")

    # End consultation
    elif data.startswith("confirm_end_"):
        other = int(data.split("_")[2])
        send(cid, "⚠️ <b>ምክክሩን ማጠናቀቅ ይፈልጋሉ?</b>",
             markup=ik([btn("✅ አዎ ጨርስ", cb=f"end_session_{other}"),
                        btn("❌ አይ ቀጥል", cb=f"cancel_end_{other}")]))

    elif data.startswith("cancel_end_"):
        tg("deleteMessage", {"chat_id": cid, "message_id": mid})

    elif data.startswith("end_session_"):
        other = int(data.split("_")[2])
        end_session_state(uid, other)
        edit_text(cid, mid, "🔴 <b>ምክክሩ ተጠናቋል።</b> አመሰግናለን!")
        send(other, "🔴 <b>ምክክሩ ተጠናቋል።</b> አመሰግናለን!")
        uid_is_doc = is_doctor(uid)
        patient_id = other if uid_is_doc else uid
        doc_id2    = uid  if uid_is_doc else other
        send(patient_id, "⭐ <b>ሀኪምዎን አገልግሎት ይመዝኑ፦</b>", markup=rating_kb(doc_id2))
        set_state(patient_id, "waiting_for_rating", {"rating_doctor_id": doc_id2})

    # Rating
    elif data.startswith("rate_"):
        parts   = data.split("_")
        score   = parts[1]
        doc_id2 = parts[2]
        update_state_data(uid, {"rating_score": score, "rating_doctor_id": doc_id2})
        set_state(uid, "waiting_for_feedback_comment", get_state(uid)["data"])
        edit_text(cid, mid,
                  f"⭐ ደረጃ ስለሰጡ አመሰግናለን ({score}/5)!\n\n"
                  "ተጨማሪ አስተያየት ካለ ጻፉ (ካለለዎት 'የለኝም' ይጻፉ):")


# ── Message dispatcher ─────────────────────────────────────────────

def handle_message(msg: dict):
    cid   = msg["chat"]["id"]
    user  = msg.get("from", {})
    uid   = user.get("id", 0)
    text  = msg.get("text", "")
    photo = msg.get("photo")
    doc   = msg.get("document")

    if text.startswith("/start"):
        parts   = text.split(" ", 1)
        payload = parts[1].strip() if len(parts) > 1 else ""
        handle_start(cid, user, payload)
        return

    if text.startswith("/help"):
        send(cid,
             f"📞 ስልክ: <code>{SUPPORT_PHONE_1}</code>\n"
             f"Telegram: {SUPPORT_USERNAME}")
        return

    for key, fn in MENU_HANDLERS.items():
        if text == key:
            fn(cid, user)
            return

    fsm   = get_state(uid)
    state = fsm["state"]
    data  = fsm["data"]

    # Payment receipt
    if state == "waiting_for_receipt" and (photo or doc):
        doc_name = data.get("doctor_name", "Specialist")
        doc_id   = data.get("doctor_id", 0)
        price    = data.get("price", 0)
        caption  = (
            f"🧾 <b>አዲስ ክፍያ ደረሰኝ!</b>\n\n"
            f"👤 ታካሚ: {user.get('first_name', '')} (<code>{uid}</code>)\n"
            f"👨‍⚕️ ሀኪም: {doc_name} (<code>{doc_id}</code>)\n"
            f"💳 ክፍያ: {price} ETB"
        )
        fid = photo[-1]["file_id"] if photo else doc["file_id"]
        notify_admin(fid, caption,
                     admin_approve_kb(f"approve_{uid}_{doc_id}_{price}_{doc_name}", uid),
                     is_photo=bool(photo))
        clear_state(uid)
        send(cid, "✅ ደረሰኝዎ ለአድሚን ቡድን ተልኳል። ክፍያው ሲረጋገጥ ከሀኪሙ ጋር ይገናኛሉ።")
        return

    # GP Case details
    if state == "waiting_for_gp_case" and text:
        data["case_details"] = text
        set_state(uid, "waiting_for_gp_receipt", data)
        send(cid,
             f"✅ <b>Case details ተመዝግቧል!</b>\n\n💳 ክፍያ: {data.get('price', 0)} ETB\n\n"
             "ክፍያ ቦታ፦\n• <b>CBE:</b> <code>1000255631865</code>\n"
             "• <b>Telebirr:</b> <code>0908343267</code>\n\n<b>ደረሰኙን ይላኩ፦</b>")
        return

    if state == "waiting_for_gp_receipt" and (photo or doc):
        doc_name = data.get("doctor_name", "Specialist")
        doc_id   = data.get("doctor_id", 0)
        price    = data.get("price", 0)
        caption  = (
            f"🧾 <b>GP ማማከር ደረሰኝ!</b>\n\n"
            f"👤 GP: {user.get('first_name', '')} (<code>{uid}</code>)\n"
            f"👨‍⚕️ ስፔሻሊስት: {doc_name} (<code>{doc_id}</code>)\n"
            f"💳 {price} ETB\n\n📝 Case:\n{data.get('case_details', '')}"
        )
        fid = photo[-1]["file_id"] if photo else doc["file_id"]
        notify_admin(fid, caption,
                     admin_approve_kb(f"approve_{uid}_{doc_id}_{price}_{doc_name}", uid),
                     is_photo=bool(photo))
        clear_state(uid)
        send(cid, "✅ ደረሰኝዎ ለአድሚን ቡድን ተልኳል። ከስፔሻሊስቱ ጋር ይገናኛሉ።")
        return

    # Store receipt
    if state == "waiting_for_store_receipt" and (photo or doc):
        item_name  = data.get("item_name", "Product")
        item_price = data.get("item_price", 0)
        file_type  = data.get("file_type", "pdf")
        caption = (
            f"🛒 <b>Digital Product ክፍያ!</b>\n\n"
            f"👤 ገዢ: {user.get('first_name', '')} (<code>{uid}</code>)\n"
            f"📦 ምርት: {item_name} ({file_type.upper()})\n💳 {item_price} ETB"
        )
        fid = photo[-1]["file_id"] if photo else doc["file_id"]
        notify_admin(fid, caption,
                     admin_approve_kb(f"approve_store_{uid}_{file_type}_{item_price}_{item_name}", uid),
                     is_photo=bool(photo))
        clear_state(uid)
        send(cid, "✅ ደረሰኝዎ ለአድሚን ቡድን ተልኳል። ፋይሉ ቶሎ ይደርስዎታል!")
        return

    # Premium receipt
    if state == "waiting_for_premium_receipt" and (photo or doc):
        caption = (
            f"💎 <b>Premium Channel ክፍያ!</b>\n\n"
            f"👤 {user.get('first_name', '')} (<code>{uid}</code>)\n💳 24 ETB/ወር"
        )
        fid = photo[-1]["file_id"] if photo else doc["file_id"]
        notify_admin(fid, caption,
                     admin_approve_kb(f"approve_prem_{uid}", uid),
                     is_photo=bool(photo))
        clear_state(uid)
        send(cid, "✅ ደረሰኝዎ ለአድሚን ቡድን ተልኳል! ቻናሉ ሊንክ ይደርስዎታል።")
        return

    # Doctor registration
    if state == "doc_reg_name" and text:
        set_state(uid, "doc_reg_specialty", {"reg_name": text})
        send(cid, "🩺 ስፔሻሊቲ ዘርፍዎን ያስገቡ (ምሳሌ: Internal Medicine):")
        return
    if state == "doc_reg_specialty" and text:
        data["reg_specialty"] = text
        set_state(uid, "doc_reg_institution", data)
        send(cid, "🏥 ስራ ቦታ/ሆስፒታሉን ያስገቡ:")
        return
    if state == "doc_reg_institution" and text:
        data["reg_institution"] = text
        set_state(uid, "doc_reg_fee", data)
        send(cid, "💳 ለአንድ ታካሚ የህክምና ክፍያ ስንት ነው (ETB)?:")
        return
    if state == "doc_reg_fee" and text:
        data["reg_fee"] = text
        set_state(uid, "doc_reg_license", data)
        send(cid,
             "📄 የህክምና ፈቃድዎን (Professional License) ፎቶ ወይም Document ይላኩ፦\n\n"
             f"<b>ወይም ሙሉ ምዝገባ ለማድረግ ወደ ድረ-ገጻችን ሄዱ:</b>\n{WEBSITE_URL}")
        return
    if state == "doc_reg_license" and (photo or doc):
        caption = (
            f"📝 <b>አዲስ ዶክተር ምዝገባ!</b>\n\n"
            f"👤 ስም: {data.get('reg_name')}\n"
            f"🆔 Telegram ID: <code>{uid}</code>\n"
            f"🩺 ስፔሻሊቲ: {data.get('reg_specialty')}\n"
            f"🏥 ተቋም: {data.get('reg_institution')}\n"
            f"💳 ክፍያ: {data.get('reg_fee')} ETB"
        )
        fid = photo[-1]["file_id"] if photo else doc["file_id"]
        notify_admin(fid, caption,
                     admin_approve_kb(f"approve_doc_{uid}", uid),
                     is_photo=bool(photo))
        clear_state(uid)
        send(cid, "✅ ምዝገባ ጥያቄዎ ለአድሚን ቡድን ተልኳል! ሲጸድቅ ማሳወቂያ ይደርስዎታል!")
        return

    # Doctor fee update
    if state and state.startswith("setting_fee_") and text:
        fee_type = state.split("_")[2]
        try:
            new_fee = float(text.replace(" ETB", "").replace(",", "").strip())
            if new_fee <= 0: raise ValueError
        except (ValueError, TypeError):
            send(cid, "❌ ትክክለኛ ቁጥር ያስገቡ (ምሳሌ: 150)")
            return
        fees = get_doctor_fees(uid)
        fees[fee_type] = new_fee
        set_doctor_fees(uid, fees["text"], fees["voice"], fees["video"])
        clear_state(uid)
        labels = {"text": "Text Chat", "voice": "Voice Call", "video": "Video Call"}
        send(cid,
             f"✅ <b>{labels[fee_type]} ዋጋ ወደ {new_fee} ETB ተቀይሯል!</b>\n\n"
             f"💬 Text:  {fees['text']} ETB\n"
             f"🎙️ Voice: {fees['voice']} ETB\n"
             f"📹 Video: {fees['video']} ETB",
             markup=MAIN_MENU)
        return

    # Doctor scheduling
    if state == "doc_scheduling" and text:
        pat_id = data.get("target_patient_id")
        ctype  = data.get("scheduled_call_type", "")
        if pat_id:
            send(int(pat_id),
                 f"🗓️ <b>ቀጠሮ ሰዓት ተቆርጧል!</b>\n\n"
                 f"👨‍⚕️ ሀኪም: {user.get('first_name', '')}\n"
                 f"🕒 ሰዓት: {text}\n📞 ዓይነት: {ctype.upper()}")
            send(cid, "✅ ሰዓቱ ለታካሚው ተልኳል!")
        clear_state(uid)
        return

    # Feedback
    if state == "waiting_for_feedback_comment" and text:
        doc_id2 = data.get("rating_doctor_id")
        score   = data.get("rating_score", "?")
        if doc_id2:
            send(int(doc_id2),
                 f"🌟 <b>አዲስ Feedback!</b>\n\n⭐ ደረጃ: {score}/5\n💬 አስተያየት: {text}")
        clear_state(uid)
        send(cid, "🙏 ለሰጡን አስተያየት እናመሰግናለን! ጤና ይስጥልን።", markup=MAIN_MENU)
        return

    # Active session relay
    if state == "in_session":
        partner = data.get("partner_id")
        if partner:
            copy_msg(int(partner), cid, msg["message_id"])
        return

    send(cid, "የተላከውን ማስተናገድ አልተቻለም። ከሜኑ ይምረጡ፦", markup=MAIN_MENU)


# ── Update router ──────────────────────────────────────────────────

def process_update(update: dict):
    if "message" in update:
        handle_message(update["message"])
    elif "callback_query" in update:
        handle_callback(update["callback_query"])


# ── Vercel handler ─────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
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
        except Exception as e:
            logger.error(f"Webhook error: {e}")
        finally:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
