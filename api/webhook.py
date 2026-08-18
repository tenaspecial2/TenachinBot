"""
Tena Special Bot — Full Vercel Webhook Handler
Standalone implementation with complete Amharic UI from main.py
Uses Supabase bot_fsm_states for FSM and Telegram HTTP API directly.
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
ADMIN_IDS       = [int(x) for x in os.getenv("ADMIN_IDS", "501384766,5872954068").split(",")]
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

SPECIALISTS = {
    "Abebe":       5872954068,
    "Kebede":      8571717581,
    "Tazebachew":  501384766,
}
DOCTOR_STATUS = {
    5872954068: True,
    8571717581: False,
    501384766:  True,
}

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
    tg("editMessageCaption", {"chat_id": chat_id, "message_id": message_id, "caption": caption, "parse_mode": "HTML"})

def answer_cb(cb_id, text=""):
    tg("answerCallbackQuery", {"callback_query_id": cb_id, "text": text})

def fwd_photo(admin_id, file_id, caption, markup=None):
    p = {"chat_id": admin_id, "photo": file_id, "caption": caption, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    tg("sendPhoto", p)

def fwd_doc(admin_id, file_id, caption, markup=None):
    p = {"chat_id": admin_id, "document": file_id, "caption": caption, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    tg("sendDocument", p)

def copy_msg(to_id, from_id, msg_id):
    tg("copyMessage", {"chat_id": to_id, "from_chat_id": from_id, "message_id": msg_id})

# ── Keyboards ─────────────────────────────────────────────────────

def rk(*rows):
    """Reply keyboard"""
    return {"keyboard": [[{"text": t} for t in row] for row in rows], "resize_keyboard": True}

def ik(*rows):
    """Inline keyboard"""
    return {"inline_keyboard": list(rows)}

def btn(text, cb=None, url=None, webapp=None):
    if url:     return {"text": text, "url": url}
    if webapp:  return {"text": text, "web_app": {"url": webapp}}
    return {"text": text, "callback_data": cb}

MAIN_MENU = rk(
    ["👨‍⚕️ ስፔሻሊስት ለማማከር"],
    ["📚 የጤና ትምህርቶች"],
    ["👥 የቡድን ህክምና ምክክሮች"],
    ["🏠 የቤት ለቤት ህክምና & 🚨 ድንገተኛ አደጋ"],
    ["📞 እርዳታና ድጋፍ (Help)"],
    ["💰 የምክክር ዋጋዬን ማስተካከያ"],  # shown to doctors only — harmless for patients
)

SPEC_SUB = ik(
    [btn("👤 ታካሚ/ጠያቂ ነኝ", cb="spec_patient")],
    [btn("👨‍⚕️ ጠቅላላ ሀኪም (GP) ነኝ", cb="spec_gp")],
    [btn("📝 የስፔሻሊስት/ዶክተር ምዝገባ", cb="start_doc_reg")],
    [btn("⬅️ ተመለስ", cb="back_main")],
)

SPECIALTIES_KB = ik(
    [btn("🩺 የውስጥ ደዌ (Internal Medicine)", cb="dept_internal")],
    [btn("🧠 የነርቭ ስፔሻሊስት (Neurology)", cb="dept_neuro")],
    [btn("👶 የህፃናት ስፔሻሊስት (Pediatrics)", cb="dept_peds")],
    [btn("🫀 የልብ ሰብ-ስፔሻሊስት (Cardiology)", cb="dept_cardio")],
    [btn("🤰 የማህፀንና ፅንስ (OBGYN)", cb="dept_obgyn")],
    [btn("⬅️ ተመለስ", cb="back_to_spec_choice")],
)

EDU_MENU = ik(
    [btn("🎁 ነፃ የጤና ትምህርቶች (Free Channel)", url=FREE_CHANNEL)],
    [btn("💎 ፕሪሚየም ቻናል (24 ETB/ወር)", cb="buy_premium_channel")],
    [btn("🩺 የውስጥ ደዌ መጻሕፍት (Internal Med)", cb="store_dept_internal")],
    [btn("🤰 የማህፀን መጻሕፍት (OBGYN)", cb="store_dept_obgyn")],
    [btn("👶 የሕፃናት ህክምና (Pediatrics)", cb="store_dept_peds")],
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

def doctors_kb(dept: str):
    rows = []
    docs = [("Dr. Abebe", SPECIALISTS["Abebe"]), ("Dr. Kebede", SPECIALISTS["Kebede"])]
    if dept == "obgyn":
        docs = [("Dr. Tazebachew", SPECIALISTS["Tazebachew"])]
    for name, did in docs:
        status = "🟢 Online" if DOCTOR_STATUS.get(did) else "🔴 Offline"
        rows.append([btn(f"{name} ({status})", cb=f"select_doc_{did}_{name}")])
    rows.append([btn("⬅️ ተመለስ", cb="back_to_depts")])
    return {"inline_keyboard": rows}

def get_doctor_fees(doctor_id: int) -> dict:
    """Fetch doctor's custom fees from Supabase, fallback to defaults."""
    rows = sb_get("doctor_consultation_fees", f"telegram_id=eq.{doctor_id}&select=text_fee,voice_fee,video_fee")
    if rows:
        return {"text": rows[0].get("text_fee", 100), "voice": rows[0].get("voice_fee", 200), "video": rows[0].get("video_fee", 300)}
    return {"text": 100, "voice": 200, "video": 300}

def set_doctor_fees(doctor_id: int, text_fee, voice_fee, video_fee):
    body = {"telegram_id": doctor_id, "text_fee": text_fee, "voice_fee": voice_fee, "video_fee": video_fee}
    ok = sb_patch("doctor_consultation_fees", f"telegram_id=eq.{doctor_id}", body)
    if not ok:
        sb_post("doctor_consultation_fees", body)

def call_type_kb(doctor_id, doctor_name):
    fees = get_doctor_fees(doctor_id)
    return ik(
        [btn(f"💬 Text Chat - {fees['text']} ETB",  cb=f"call_{doctor_id}_text_{fees['text']}_{doctor_name}")],
        [btn(f"🎙️ Voice Call - {fees['voice']} ETB", cb=f"call_{doctor_id}_voice_{fees['voice']}_{doctor_name}")],
        [btn(f"📹 Video Call - {fees['video']} ETB", cb=f"call_{doctor_id}_video_{fees['video']}_{doctor_name}")],
        [btn("⬅️ ተመለስ", cb="back_to_depts")],
    )

def digital_products_kb(dept):
    abebe = SPECIALISTS["Abebe"]
    taze  = SPECIALISTS["Tazebachew"]
    if dept == "internal":
        return ik(
            [btn("📘 የደም ግፊት መከላከያ - 200 ETB", cb=f"buy_prod_HTN Book_200_pdf_{abebe}")],
            [btn("📙 የስኳር በሽታ አያያዝ - 300 ETB",  cb=f"buy_prod_DM Book_300_pdf_{abebe}")],
            [btn("⬅️ ተመለስ", cb="back_to_edu_menu")],
        )
    elif dept == "obgyn":
        return ik(
            [btn("📗 OBGYN Guide (PDF) - 300 ETB",      cb=f"buy_prod_OBGYN Guide_300_pdf_{taze}")],
            [btn("🎬 OBGYN Video Lecture - 500 ETB",    cb=f"buy_prod_OBGYN Video_500_video_{taze}")],
            [btn("📘 የእርግዝና እንክብካቤ - 250 ETB",       cb=f"buy_prod_Pregnancy Care_250_pdf_{taze}")],
            [btn("⬅️ ተመለስ", cb="back_to_edu_menu")],
        )
    else:  # peds
        return ik(
            [btn("📘 የሕፃናት ምግብና እድገት - 200 ETB", cb=f"buy_prod_Child Health_200_pdf_{abebe}")],
            [btn("⬅️ ተመለስ", cb="back_to_edu_menu")],
        )

def admin_approve_kb(approve_cb, reject_user_id):
    return ik([btn("✅ Approve", cb=approve_cb), btn("❌ Reject", cb=f"reject_{reject_user_id}")])

def rating_kb(doctor_id):
    return ik([
        btn("⭐ 1", cb=f"rate_1_{doctor_id}"),
        btn("⭐ 2", cb=f"rate_2_{doctor_id}"),
        btn("⭐ 3", cb=f"rate_3_{doctor_id}"),
        btn("⭐ 4", cb=f"rate_4_{doctor_id}"),
        btn("⭐ 5", cb=f"rate_5_{doctor_id}"),
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
    req  = Request(url, data=data, headers={**_sb_headers(), "Prefer": "return=minimal"})
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

# ── FSM State helpers ──────────────────────────────────────────────

def get_state(user_id: int) -> dict:
    rows = sb_get("bot_fsm_states", f"user_id=eq.{user_id}&select=state,data")
    if rows:
        d = rows[0].get("data") or {}
        return {"state": rows[0].get("state", ""), "data": d}
    return {"state": "", "data": {}}

def set_state(user_id: int, state: str, data: dict = None):
    body = {"user_id": user_id, "state": state, "data": data or {}}
    # upsert
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

# ── Active Sessions helpers ────────────────────────────────────────

def get_partner(user_id: int):
    rows = sb_get("bot_fsm_states", f"user_id=eq.{user_id}&select=data")
    if rows:
        return rows[0].get("data", {}).get("partner_id")
    return None

def start_session(patient_id: int, doctor_id: int, call_type: str):
    set_state(patient_id, "in_session", {"partner_id": doctor_id, "call_type": call_type})
    set_state(doctor_id,  "in_session", {"partner_id": patient_id, "call_type": call_type})

def end_session_state(user_id: int, partner_id: int):
    clear_state(user_id)
    clear_state(partner_id)

# ── Bot handlers ───────────────────────────────────────────────────

def get_doctor_name(doctor_id: int):
    for name, did in SPECIALISTS.items():
        if did == doctor_id:
            return f"Dr. {name}"
    return f"Dr. Unknown ({doctor_id})"

def handle_set_fees_start(chat_id: int, user: dict):
    uid = user.get("id", 0)
    if uid not in SPECIALISTS.values():
        send(chat_id, "⛔ ይህ አገልግሎት ለስፔሻሊስት ሀኪሞች ብቻ ነው።")
        return
    fees = get_doctor_fees(uid)
    send(chat_id,
         f"💰 <b>የአሁኑ የምክክር ዋጋዎ</b>\n\n"
         f"💬 Text Chat: <b>{fees['text']} ETB</b>\n"
         f"🎙️ Voice Call: <b>{fees['voice']} ETB</b>\n"
         f"📹 Video Call: <b>{fees['video']} ETB</b>\n\n"
         "ዋጋዎን ለማስተካከል ከታች ይምረጡ:",
         markup=ik(
             [btn("💬 Text Chat ዋጋ ለመለወጥ",  cb="set_fee_text")],
             [btn("🎙️ Voice Call ዋጋ ለመለወጥ", cb="set_fee_voice")],
             [btn("📹 Video Call ዋጋ ለመለወጥ", cb="set_fee_video")],
             [btn("⬅️ ወደ ሜኑ", cb="back_main")],
         ))

def handle_start(chat_id: int, user: dict, payload: str = ""):
    name = user.get("first_name", "there")
    if payload.startswith("login_"):
        handle_login_token(chat_id, user, payload[6:])
        return
    clear_state(chat_id)
    text = (
        f"👋 <b>እንኳን ወደ ጤናችን (Tenachin) የህክምና ማማከሪያ ቦት በደህና መጡ!</b>\n\n"
        f"እባክዎ የሚፈልጉትን አገልግሎት ከታች ካለው ሜኑ ይምረጡ፦"
    )
    send(chat_id, text, markup=MAIN_MENU)

def handle_login_token(chat_id: int, user: dict, token: str):
    tg_id    = str(user.get("id", ""))
    name     = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    username = user.get("username", "")
    ok = sb_patch("login_tokens", f"token=eq.{token}&used=eq.false",
                  {"telegram_id": tg_id, "telegram_name": name, "telegram_username": username})
    if ok:
        send(chat_id, f"✅ <b>Login confirmed!</b>\n\nGo back to the website — you'll be logged in automatically, {name}! 🚀")
    else:
        send(chat_id, "❌ This login link expired or was already used.\nPlease go back and try again.")

# ── Menu text triggers ─────────────────────────────────────────────

MENU_HANDLERS = {
    "👨‍⚕️ ስፔሻሊስት ለማማከር": lambda cid, _: send(cid,
        "👨‍⚕️ <b>የስፔሻሊስት ማማከሪያ ክፍል</b>\n\nእባክዎ ማንነትዎን ይምረጡ፦", markup=SPEC_SUB),
    "📚 የጤና ትምህርቶች": lambda cid, _: send(cid,
        "📚 <b>የጤና ትምህርቶች እና ዲጂታል መጻሕፍት Store</b>\n\nእባክዎ የሚፈልጉትን ይምረጡ፦", markup=EDU_MENU),
    "👥 የቡድን ህክምና ምክክሮች": lambda cid, _: send(cid,
        "👥 <b>የቡድን ህክምና ውይይቶች</b>\n\nእባክዎ ይምረጡ፦", markup=GROUP_MENU),
    "🏠 የቤት ለቤት ህክምና & 🚨 ድንገተኛ አደጋ": lambda cid, _: send(cid,
        "🏠 <b>የቤት ለቤት ህክምና እና ድንገተኛ አደጋ አገልግሎት</b>\n\nእባክዎ ይምረጡ፦", markup=HOMECARE_MENU),
    "📞 እርዳታና ድጋፍ (Help)": lambda cid, _: send(cid,
        f"📞 <b>እርዳታና ድጋፍ (Support Center)</b>\n\n"
        f"• ስልክ: <code>{SUPPORT_PHONE_1}</code> / <code>{SUPPORT_PHONE_2}</code>\n"
        f"• Telegram Admin: {SUPPORT_USERNAME}\n"
        f"• Website: {WEBSITE_URL}"),
    "💰 የምክክር ዋጋዬን ማስተካከያ": lambda cid, user: handle_set_fees_start(cid, user),
}

# ── Callback handlers ──────────────────────────────────────────────

def handle_callback(cb: dict):
    data    = cb.get("data", "")
    cid     = cb["message"]["chat"]["id"]
    mid     = cb["message"]["message_id"]
    user    = cb.get("from", {})
    uid     = user.get("id", 0)

    answer_cb(cb["id"])

    # Set fee callbacks (for specialist doctors)
    if data in ("set_fee_text", "set_fee_voice", "set_fee_video"):
        if uid not in SPECIALISTS.values():
            send(cid, "⛔ ይህ አገልግሎት ለስፔሻሊስቶች ብቻ ነው።")
            return
        fee_type = data.split("_")[2]  # text / voice / video
        labels = {"text": "Text Chat", "voice": "Voice Call", "video": "Video Call"}
        set_state(uid, f"setting_fee_{fee_type}", {})
        send(cid, f"💰 <b>አዲስ {labels[fee_type]} ዋጋ ያስገቡ (ETB):</b>\n\nምሳሌ: 150")
        return

    # Navigation
    if data == "back_main":
        clear_state(uid)
        send(cid, "👋 እባክዎ ከታች ካለው ሜኑ ይምረጡ፦", markup=MAIN_MENU)
    elif data == "back_to_spec_choice":
        edit_text(cid, mid, "👨‍⚕️ <b>የስፔሻሊስት ማማከሪያ ክፍል</b>\n\nእባክዎ ማንነትዎን ይምረጡ፦", markup=SPEC_SUB)
    elif data == "back_to_depts":
        edit_text(cid, mid, "🩺 <b>እባክዎ የሚፈልጉትን የስፔሻሊቲ ዘርፍ ይምረጡ፦</b>", markup=SPECIALTIES_KB)
    elif data == "back_to_edu_menu":
        edit_text(cid, mid, "📚 <b>የጤና ትምህርቶች Store</b>\n\nእባክዎ ይምረጡ፦", markup=EDU_MENU)

    # Specialist sub-menu
    elif data in ("spec_patient", "spec_gp"):
        role = "Patient" if data == "spec_patient" else "GP"
        update_state_data(uid, {"user_role": role})
        edit_text(cid, mid, "🩺 <b>እባክዎ የሚፈልጉትን የስፔሻሊቲ ዘርፍ ይምረጡ፦</b>", markup=SPECIALTIES_KB)

    # Specialty → Doctors
    elif data.startswith("dept_"):
        dept = data.split("_")[1]
        edit_text(cid, mid, "👨‍⚕️ <b>እባክዎ ማማከር የሚፈልጉትን ስፔሻሊስት ይምረጡ፦</b>", markup=doctors_kb(dept))

    # Doctor selected
    elif data.startswith("select_doc_"):
        parts  = data.split("_")
        did    = int(parts[2])
        dname  = parts[3]
        edit_text(cid, mid, f"👨‍⚕️ <b>{dname}</b>\n\nእባክዎ የምክክር አይነት ይምረጡ፦", markup=call_type_kb(did, dname))

    # Call type → payment
    elif data.startswith("call_"):
        parts    = data.split("_")
        did      = int(parts[1])
        ctype    = parts[2]
        price    = float(parts[3])
        dname    = parts[4]
        s        = get_state(uid)
        role     = s["data"].get("user_role", "Patient")

        if role == "GP":
            set_state(uid, "waiting_for_gp_case", {"doctor_id": did, "doctor_name": dname, "price": price, "call_type": ctype})
            send(cid, f"👨‍⚕️ <b>ለ Dr. {dname} ማማከር የሚፈልጉትን የካርድ/የታካሚ ታሪክ (Case Details)</b> በአንድ መልእክት ጽፈው ይላኩ፦")
        else:
            set_state(uid, "waiting_for_receipt", {"doctor_id": did, "doctor_name": dname, "price": price, "call_type": ctype})
            send(cid,
                f"📋 <b>የምክክር ጥያቄ ለ Dr. {dname}</b>\n\n"
                f"📞 <b>ዓይነት:</b> {ctype.upper()} Consultation\n"
                f"💰 <b>ክፍያ:</b> {price} ETB\n\n"
                "እባክዎ ክፍያውን በሚከተለው ያስገቡ፦\n"
                "• <b>CBE:</b> <code>1000255631865</code> (Tazebachew Wudie)\n"
                "• <b>Telebirr:</b> <code>0908343267</code>\n\n"
                "<b>ክፍያውን ከፈጸሙ በኋላ የክፍያ ደረሰኙን (Screenshot) እዚህ ይላኩ፦</b>")

    # Doctor registration
    elif data == "start_doc_reg":
        set_state(uid, "doc_reg_name", {})
        send(cid, "📝 <b>የስፔሻሊስት/ዶክተር ምዝገባ</b>\n\nእባክዎ ሙሉ ስምዎን ያስገቡ (ምሳሌ: Dr. Abebe Kebede):")

    # Education store
    elif data.startswith("store_dept_"):
        dept = data.split("_")[2]
        edit_text(cid, mid, "📚 <b>እባክዎ ምርጫዎን ያድርጉ፦</b>", markup=digital_products_kb(dept))

    elif data.startswith("buy_prod_"):
        parts     = data.split("_")
        prod_name = parts[2]
        prod_price= float(parts[3])
        file_type = parts[4]
        author_id = int(parts[5]) if len(parts) > 5 else 0
        set_state(uid, "waiting_for_store_receipt", {"item_name": prod_name, "item_price": prod_price, "file_type": file_type, "author_id": author_id})
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
             "💎 <b>የፕሪሚየም ቻናል አባልነት (24 ETB/ወር)</b>\n\n"
             "ክፍያ ቦታ፦\n"
             "• <b>CBE:</b> <code>1000255631865</code>\n"
             "• <b>Telebirr:</b> <code>0908343267</code>\n\n"
             "<b>ደረሰኙን (Screenshot) ይላኩ፦</b>")

    # Info handlers
    elif data == "group_premium":
        send(cid, f"🔒 <b>ፕሪሚየም ቪዲዮ/ድምፅ ውይይት</b>\n\nወርሃዊ ክፍያ: 150 ETB\nአድሚን: {SUPPORT_USERNAME}")
    elif data == "homecare_info":
        send(cid, f"🏠 <b>የቤት ለቤት ህክምና</b>\n\n📞 <code>{SUPPORT_PHONE_1}</code> / <code>{SUPPORT_PHONE_2}</code>")
    elif data == "emergency_alert":
        send(cid, "🚨 <b>ድንገተኛ አደጋ</b>\n\nወደ አቅራቢያ ሆስፒታል ሄዱ!\n📞 <b>907</b> (ቀይ መስቀል)")

    # Admin: approve consultation payment
    elif data.startswith("approve_"):
        parts   = data.split("_")
        pat_id  = int(parts[1])
        doc_id  = int(parts[2])
        price   = float(parts[3]) if len(parts) > 3 else 300.0
        doc_name= parts[4] if len(parts) > 4 else get_doctor_name(doc_id)
        ctype   = "text" if price == 100 else ("voice" if price == 200 else "video")
        is_online = DOCTOR_STATUS.get(doc_id, False)

        # Record transaction in Supabase
        sb_post("bot_transactions", {
            "doctor_name": f"Dr. {doc_name}" if not doc_name.startswith("Dr.") else doc_name,
            "item_type": "Consultation",
            "item_title": f"1-on-1 {ctype.upper()}",
            "price": price,
            "user_id": pat_id,
        })

        if is_online:
            start_session(pat_id, doc_id, ctype)
            send(pat_id,
                 f"🟢 <b>ክፍያዎ ተቀባይነት አግኝቷል! ሀኪሙ online ናቸው!</b>\n\n"
                 f"ከ Dr. {doc_name} ጋር ምስጢራዊ ምክክር ተጀምሯል። አሁን መልእክት መላክ ይችላሉ።",
                 markup=end_consultation_kb(doc_id))
            send(doc_id,
                 f"👨‍⚕️ <b>አዲስ ታካሚ ተመድቦልዎታል!</b>\n\n"
                 f"👤 ታካሚ ID: <code>{pat_id}</code>\n💬 ዓይነት: {ctype.upper()}",
                 markup=end_consultation_kb(pat_id))
        else:
            send(pat_id, f"🔴 <b>Dr. {doc_name} አሁን online አይደሉም።</b>\n\nሀኪሙ ሲወሰኑ ሰዓቱ ይደርስዎታል!")
            send(doc_id,
                 f"🚨 <b>አዲስ ታካሚ ከፍሏል!</b>\n👤 ታካሚ ID: <code>{pat_id}</code>\n📞 {ctype.upper()}\n\nሰዓትዎን ይጠቁሙ:",
                 markup=ik([btn("🕒 ሰዓት ለመወሰን", cb=f"set_time_{pat_id}_{ctype}")]))

        edit_caption(cid, mid, f"{cb['message'].get('caption', '')}\n\n✅ <b>APPROVED</b>")

    elif data.startswith("approve_prem_"):
        pat_id = int(data.split("_")[2])
        tg("sendMessage", {"chat_id": pat_id,
            "text": f"🎉 <b>ክፍያዎ ተረጋግጧል!</b>\n\n🔗 {PREMIUM_CHANNEL}", "parse_mode": "HTML"})
        edit_caption(cid, mid, f"{cb['message'].get('caption', '')}\n\n✅ PREMIUM APPROVED")

    elif data.startswith("approve_doc_"):
        doc_id = int(data.split("_")[2])
        send(doc_id, "🎉 <b>የስፔሻሊስት ምዝገባዎ ጸድቋል!</b>\n\nአሁን ከሲስተሙ ጋር ተቀላቅለዋል።")
        edit_caption(cid, mid, f"{cb['message'].get('caption', '')}\n\n✅ DOCTOR APPROVED")

    elif data.startswith("reject_"):
        pat_id = int(data.split("_")[1])
        send(pat_id, "❌ <b>ደረሰኝዎ ውድቅ ተደርጓል!</b>\n\nትክክለኛ ደረሰኝ ይላኩ ወይም አድሚን ያናግሩ።")
        edit_caption(cid, mid, f"{cb['message'].get('caption', '')}\n\n❌ REJECTED")

    elif data.startswith("approve_store_"):
        parts     = data.split("_")
        pat_id    = int(parts[2])
        file_type = parts[3]
        author_id = int(parts[4])
        price     = float(parts[5])
        item_name = "_".join(parts[6:]) if len(parts) > 6 else "Digital Product"
        doc_name  = get_doctor_name(author_id)
        sb_post("bot_transactions", {"doctor_name": doc_name, "item_type": file_type.upper(), "item_title": item_name, "price": price, "user_id": pat_id})
        send(pat_id, f"🎉 <b>ክፍያዎ ተረጋግጧል!</b>\n\n{item_name} ({file_type.upper()}) ቶሎ ይደርስዎታል!")
        if author_id:
            send(author_id, f"🎉 የርስዎ {item_name} ተሸጧል!\n👤 ገዢ ID: <code>{pat_id}</code>")
        edit_caption(cid, mid, f"{cb['message'].get('caption', '')}\n\n✅ APPROVED")

    # Doctor sets schedule time
    elif data.startswith("set_time_"):
        parts    = data.split("_")
        pat_id   = int(parts[2])
        ctype    = parts[3]
        set_state(uid, "doc_scheduling", {"target_patient_id": pat_id, "scheduled_call_type": ctype})
        send(cid, "✍️ <b>እባክዎ ነፃ ሰዓቱን ይጻፉ (ምሳሌ: ነገ ከቀኑ 8:00):</b>")

    # End consultation
    elif data.startswith("confirm_end_"):
        other = int(data.split("_")[2])
        send(cid, "⚠️ <b>ምክክሩን ማጠናቀቅ ይፈልጋሉ?</b>",
             markup=ik([btn("✅ አዎ ጨርስ", cb=f"end_session_{other}"), btn("❌ አይ ቀጥል", cb=f"cancel_end_{other}")]))

    elif data.startswith("cancel_end_"):
        tg("deleteMessage", {"chat_id": cid, "message_id": mid})

    elif data.startswith("end_session_"):
        other = int(data.split("_")[2])
        end_session_state(uid, other)
        edit_text(cid, mid, "🔴 <b>የህክምና ምክክሩ ተጠናቋል።</b> አመሰግናለን!")
        send(other, "🔴 <b>የህክምና ምክክሩ ተጠናቋል።</b> አመሰግናለን!")
        # Send rating to patient (non-doctor side)
        patient_id = uid if uid not in SPECIALISTS.values() else other
        doc_id2    = other if uid not in SPECIALISTS.values() else uid
        send(patient_id, "⭐ <b>ሀኪምዎን አገልግሎት ይመዝኑ፦</b>", markup=rating_kb(doc_id2))
        set_state(patient_id, "waiting_for_rating", {"rating_doctor_id": doc_id2})

    # Rating
    elif data.startswith("rate_"):
        parts    = data.split("_")
        score    = parts[1]
        doc_id2  = parts[2]
        update_state_data(uid, {"rating_score": score, "rating_doctor_id": doc_id2})
        set_state(uid, "waiting_for_feedback_comment", get_state(uid)["data"])
        edit_text(cid, mid, f"⭐ ደረጃ ስለሰጡ አመሰግናለን ({score}/5)!\n\nተጨማሪ አስተያየት ካለ ጻፉ (ካለለዎት 'የለኝም' ይጻፉ):")


# ── Message dispatcher ─────────────────────────────────────────────

def handle_message(msg: dict):
    cid    = msg["chat"]["id"]
    user   = msg.get("from", {})
    uid    = user.get("id", 0)
    text   = msg.get("text", "")
    photo  = msg.get("photo")
    doc    = msg.get("document")

    # /start command
    if text.startswith("/start"):
        parts   = text.split(" ", 1)
        payload = parts[1].strip() if len(parts) > 1 else ""
        handle_start(cid, user, payload)
        return

    # /help
    if text.startswith("/help"):
        send(cid, f"📞 ስልክ: <code>{SUPPORT_PHONE_1}</code> / {SUPPORT_USERNAME}")
        return

    # Main menu text buttons
    for key, fn in MENU_HANDLERS.items():
        if text == key:
            fn(cid, user)
            return

    # Get current FSM state
    fsm = get_state(uid)
    state = fsm["state"]
    data  = fsm["data"]

    # ── Payment receipt ──────────────────────────────────────────────
    if state == "waiting_for_receipt" and (photo or doc):
        doc_name = data.get("doctor_name", "Specialist")
        doc_id   = data.get("doctor_id", 0)
        price    = data.get("price", 0)
        caption  = (
            f"🧾 <b>አዲስ የክፍያ ደረሰኝ!</b>\n\n"
            f"👤 <b>ታካሚ:</b> {user.get('full_name', user.get('first_name', ''))}\n"
            f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
            f"👨‍⚕️ <b>ሀኪም:</b> Dr. {doc_name} (ID: <code>{doc_id}</code>)\n"
            f"💳 <b>ክፍያ:</b> {price} ETB"
        )
        akb = admin_approve_kb(f"approve_{uid}_{doc_id}_{price}_{doc_name}", uid)
        for admin in ADMIN_IDS:
            fid = photo[-1]["file_id"] if photo else doc["file_id"]
            (fwd_photo if photo else fwd_doc)(admin, fid, caption, markup=akb)
        clear_state(uid)
        send(cid, "✅ ደረሰኝዎ ለአድሚን ተልኳል። ክፍያው ሲረጋገጥ ከሀኪሙ ጋር ይገናኛሉ።")
        return

    # ── GP Case details ──────────────────────────────────────────────
    if state == "waiting_for_gp_case" and text:
        data["case_details"] = text
        set_state(uid, "waiting_for_gp_receipt", data)
        send(cid,
             f"✅ <b>የታካሚ ታሪክ ተመዝግቧል!</b>\n\n"
             f"💳 ክፍያ: {data.get('price', 0)} ETB\n\n"
             "ክፍያ ቦታ፦\n"
             "• <b>CBE:</b> <code>1000255631865</code>\n"
             "• <b>Telebirr:</b> <code>0908343267</code>\n\n"
             "<b>ደረሰኙን ይላኩ፦</b>")
        return

    if state == "waiting_for_gp_receipt" and (photo or doc):
        doc_name    = data.get("doctor_name", "Specialist")
        doc_id      = data.get("doctor_id", 0)
        price       = data.get("price", 0)
        case_details= data.get("case_details", "")
        caption     = (
            f"🧾 <b>GP ማማከር ደረሰኝ!</b>\n\n"
            f"👤 GP: {user.get('first_name', '')} (<code>{uid}</code>)\n"
            f"👨‍⚕️ ስፔሻሊስት: Dr. {doc_name} (<code>{doc_id}</code>)\n"
            f"💳 {price} ETB\n\n"
            f"📝 Case Details:\n{case_details}"
        )
        akb = admin_approve_kb(f"approve_{uid}_{doc_id}_{price}_{doc_name}", uid)
        for admin in ADMIN_IDS:
            fid = photo[-1]["file_id"] if photo else doc["file_id"]
            (fwd_photo if photo else fwd_doc)(admin, fid, caption, markup=akb)
        clear_state(uid)
        send(cid, "✅ ደረሰኝዎ ለአድሚን ተልኳል። ከስፔሻሊስቱ ጋር ይገናኛሉ።")
        return

    # ── Store receipt ────────────────────────────────────────────────
    if state == "waiting_for_store_receipt" and (photo or doc):
        item_name  = data.get("item_name", "Product")
        item_price = data.get("item_price", 0)
        file_type  = data.get("file_type", "pdf")
        author_id  = data.get("author_id", 0)
        doc_name   = get_doctor_name(author_id)
        caption    = (
            f"🛒 <b>Digital Product ክፍያ!</b>\n\n"
            f"👤 ገዢ: {user.get('first_name', '')} (<code>{uid}</code>)\n"
            f"📦 ምርት: {item_name} ({file_type.upper()})\n"
            f"💳 {item_price} ETB\n"
            f"👨‍⚕️ ባለቤት: {doc_name}"
        )
        akb = admin_approve_kb(f"approve_store_{uid}_{file_type}_{author_id}_{item_price}_{item_name}", uid)
        for admin in ADMIN_IDS:
            fid = photo[-1]["file_id"] if photo else doc["file_id"]
            (fwd_photo if photo else fwd_doc)(admin, fid, caption, markup=akb)
        clear_state(uid)
        send(cid, "✅ ደረሰኝዎ ለአድሚን ተልኳል። ፋይሉ ቶሎ ይደርስዎታል!")
        return

    # ── Premium receipt ──────────────────────────────────────────────
    if state == "waiting_for_premium_receipt" and (photo or doc):
        caption = (
            f"💎 <b>Premium Channel ክፍያ!</b>\n\n"
            f"👤 {user.get('first_name', '')} (<code>{uid}</code>)\n"
            f"💳 24 ETB/ወር"
        )
        akb = admin_approve_kb(f"approve_prem_{uid}", uid)
        for admin in ADMIN_IDS:
            fid = photo[-1]["file_id"] if photo else doc["file_id"]
            (fwd_photo if photo else fwd_doc)(admin, fid, caption, markup=akb)
        clear_state(uid)
        send(cid, "✅ ደረሰኝዎ ለአድሚን ተልኳል! ቻናሉ ሊንክ ይደርስዎታል።")
        return

    # ── Doctor sets their own consultation fee ───────────────────────
    if state and state.startswith("setting_fee_") and text:
        fee_type = state.split("_")[2]  # text / voice / video
        try:
            new_fee = float(text.replace(" ETB", "").replace(",", "").strip())
            if new_fee <= 0:
                raise ValueError
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
             f"💬 Text Chat: <b>{fees['text']} ETB</b>\n"
             f"🎙️ Voice Call: <b>{fees['voice']} ETB</b>\n"
             f"📹 Video Call: <b>{fees['video']} ETB</b>",
             markup=MAIN_MENU)
        return

    # ── Doctor registration multi-step ───────────────────────────────
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
        send(cid, "📄 የህክምና ፈቃድዎን (Professional License) ፎቶ ወይም Document አድርጎ ይላኩ፦")
        return
    if state == "doc_reg_license" and (photo or doc):
        caption = (
            f"📝 <b>አዲስ ዶክተር ምዝገባ ጥያቄ!</b>\n\n"
            f"👤 ስም: {data.get('reg_name')}\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"🩺 ስፔሻሊቲ: {data.get('reg_specialty')}\n"
            f"🏥 ተቋም: {data.get('reg_institution')}\n"
            f"💳 ክፍያ: {data.get('reg_fee')} ETB"
        )
        akb = admin_approve_kb(f"approve_doc_{uid}", uid)
        for admin in ADMIN_IDS:
            fid = photo[-1]["file_id"] if photo else doc["file_id"]
            (fwd_photo if photo else fwd_doc)(admin, fid, caption, markup=akb)
        clear_state(uid)
        send(cid, "✅ ምዝገባ ጥያቄዎ ለአድሚን ተልኳል! ምዝገባው ሲጸድቅ ማሳወቂያ ይደርስዎታል!")
        return

    # ── Doctor scheduling ────────────────────────────────────────────
    if state == "doc_scheduling" and text:
        pat_id = data.get("target_patient_id")
        ctype  = data.get("scheduled_call_type", "")
        if pat_id:
            send(int(pat_id),
                 f"🗓️ <b>ቀጠሮ ሰዓት ተቆርጧል!</b>\n\n"
                 f"👨‍⚕️ ሀኪም: {user.get('first_name', '')}\n"
                 f"🕒 ሰዓት: {text}\n"
                 f"📞 ዓይነት: {ctype.upper()}")
            send(cid, "✅ ሰዓቱ ለታካሚው ተልኳል!")
        clear_state(uid)
        return

    # ── Feedback comment ─────────────────────────────────────────────
    if state == "waiting_for_feedback_comment" and text:
        doc_id2 = data.get("rating_doctor_id")
        score   = data.get("rating_score", "?")
        if doc_id2:
            send(int(doc_id2),
                 f"🌟 <b>አዲስ Feedback!</b>\n\n⭐ ደረጃ: {score}/5\n💬 አስተያየት: {text}")
        clear_state(uid)
        send(cid, "🙏 ለሰጡን አስተያየት እናመሰግናለን! ጤና ይስጥልን።", markup=MAIN_MENU)
        return

    # ── Active session relay ─────────────────────────────────────────
    if state == "in_session":
        partner = data.get("partner_id")
        if partner:
            copy_msg(int(partner), cid, msg["message_id"])
        return

    # ── Default ──────────────────────────────────────────────────────
    send(cid, "የተላከውን ማስተናገድ አልተቻለም። እባክዎ ከሜኑ ይምረጡ፦", markup=MAIN_MENU)


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
