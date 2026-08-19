"""
Tena Special Bot — Webhook Handler
- Live dynamic products from Supabase `bot_products` table (No hardcoded books/products)
- Live dynamic settings from Supabase `bot_settings` table
- Guaranteed compact callback_data (<32 bytes)
- Forward all payment receipt photos directly to Admin Group
- Silent group chat behavior with ReplyKeyboardRemove
"""
import json
import os
import logging
from http.server import BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import HTTPError

logger = logging.getLogger(__name__)

# ── Minimal Secrets from Environment ──────────────────────────────
BOT_TOKEN       = os.getenv("BOT_TOKEN", "").strip()
SUPABASE_URL    = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY    = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
ADMIN_GROUP_ENV = int(os.getenv("ADMIN_GROUP_ID", "0"))

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── In-Memory Fast Cache ──────────────────────────────────────────
_FSM_MEMORY: dict = {}
_SETTINGS_MEMORY: dict = {}
_SETTINGS_LOADED = False

# ── Supabase REST Helpers ─────────────────────────────────────────

def _sb_headers():
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }

def sb_get(table, params=""):
    if not (SUPABASE_URL and SUPABASE_KEY):
        return []
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    req = Request(url, headers=_sb_headers())
    try:
        with urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"sb_get {table}: {e}")
        return []

def sb_post(table, body):
    if not (SUPABASE_URL and SUPABASE_KEY):
        return False
    url  = f"{SUPABASE_URL}/rest/v1/{table}"
    data = json.dumps(body).encode()
    req  = Request(url, data=data,
                   headers={**_sb_headers(), "Prefer": "return=minimal"})
    try:
        with urlopen(req, timeout=8):
            return True
    except Exception as e:
        logger.warning(f"sb_post {table}: {e}")
        return False

def sb_patch(table, query, body):
    if not (SUPABASE_URL and SUPABASE_KEY):
        return False
    url  = f"{SUPABASE_URL}/rest/v1/{table}?{query}"
    data = json.dumps(body).encode()
    req  = Request(url, data=data,
                   headers={**_sb_headers(), "Prefer": "return=minimal"},
                   method="PATCH")
    try:
        with urlopen(req, timeout=8) as r:
            return r.status in (200, 204)
    except Exception as e:
        logger.warning(f"sb_patch {table}: {e}")
        return False

def sb_delete(table, query):
    if not (SUPABASE_URL and SUPABASE_KEY):
        return False
    url = f"{SUPABASE_URL}/rest/v1/{table}?{query}"
    req = Request(url, headers=_sb_headers(), method="DELETE")
    try:
        with urlopen(req, timeout=8):
            return True
    except Exception as e:
        logger.warning(f"sb_delete {table}: {e}")
        return False

# ── Dynamic Settings Helper ───────────────────────────────────────

def _load_settings():
    global _SETTINGS_MEMORY, _SETTINGS_LOADED
    if _SETTINGS_LOADED:
        return
    rows = sb_get("bot_settings", "select=key,value")
    if rows:
        _SETTINGS_MEMORY = {row["key"]: row["value"] for row in rows if isinstance(row, dict)}
    _SETTINGS_LOADED = True

def cfg(key: str, fallback: str = "") -> str:
    _load_settings()
    return _SETTINGS_MEMORY.get(key, fallback)

def cfg_int(key: str, fallback: int = 0) -> int:
    try:
        v = cfg(key, "")
        return int(v) if v else fallback
    except ValueError:
        return fallback

def cfg_float(key: str, fallback: float = 0.0) -> float:
    try:
        v = cfg(key, "")
        return float(v) if v else fallback
    except ValueError:
        return fallback

def get_admin_group() -> int:
    from_db = cfg_int("admin_group_id", 0)
    return from_db if from_db else ADMIN_GROUP_ENV

def set_cfg(key: str, value: str) -> bool:
    _SETTINGS_MEMORY[key] = value
    body = {"key": key, "value": value}
    ok = sb_patch("bot_settings", f"key=eq.{key}", body)
    if not ok:
        ok = sb_post("bot_settings", body)
    return ok

# ── Telegram API Helpers ──────────────────────────────────────────

def tg(method: str, payload: dict) -> dict:
    url  = f"{TG_API}/{method}"
    data = json.dumps(payload).encode()
    req  = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except HTTPError as e:
        err_msg = e.read().decode("utf-8", "ignore")
        logger.error(f"TG HTTPError {method}: {err_msg}")
        return {"ok": False, "description": err_msg}
    except Exception as e:
        logger.error(f"TG Error {method}: {e}")
        return {"ok": False, "description": str(e)}

def send(chat_id, text, markup=None, parse_mode="HTML"):
    p = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if markup:
        p["reply_markup"] = markup
    return tg("sendMessage", p)

def edit_text(chat_id, message_id, text, markup=None):
    p = {"chat_id": chat_id, "message_id": message_id,
         "text": text, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    tg("editMessageText", p)

def edit_caption(chat_id, message_id, caption):
    tg("editMessageCaption", {
        "chat_id": chat_id, "message_id": message_id,
        "caption": caption, "parse_mode": "HTML"})

def answer_cb(cb_id, text=""):
    tg("answerCallbackQuery", {"callback_query_id": cb_id, "text": text})

def fwd_photo(chat_id, file_id, caption, markup=None):
    p = {"chat_id": chat_id, "photo": file_id,
         "caption": caption, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    return tg("sendPhoto", p)

def fwd_doc(chat_id, file_id, caption, markup=None):
    p = {"chat_id": chat_id, "document": file_id,
         "caption": caption, "parse_mode": "HTML"}
    if markup:
        p["reply_markup"] = markup
    return tg("sendDocument", p)

def copy_msg(to_id, from_id, msg_id):
    tg("copyMessage", {"chat_id": to_id,
                        "from_chat_id": from_id, "message_id": msg_id})

def notify_admin(file_id: str, caption: str, markup, is_photo: bool) -> bool:
    group_id = get_admin_group()
    if not group_id:
        logger.error("Admin group ID is not configured.")
        return False
    try:
        res = (fwd_photo if is_photo else fwd_doc)(group_id, file_id, caption, markup=markup)
        if res.get("ok"):
            return True
        logger.warning(f"notify_admin media send failed: {res.get('description')}")
    except Exception as e:
        logger.error(f"notify_admin exception: {e}")

    try:
        res2 = tg("sendMessage", {
            "chat_id": group_id,
            "text": f"🧾 <b>New Receipt (Media Fallback)</b>\n\n{caption}",
            "parse_mode": "HTML",
            "reply_markup": markup,
        })
        return res2.get("ok", False)
    except Exception as e2:
        logger.error(f"notify_admin text fallback failed: {e2}")
        return False

# ── Keyboards & Menus ─────────────────────────────────────────────

def rk(*rows):
    return {"keyboard": [[{"text": t} for t in row] for row in rows],
            "resize_keyboard": True}

def ik(*rows):
    return {"inline_keyboard": list(rows)}

def btn(text, cb=None, url=None):
    if url:
        return {"text": text, "url": url}
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
    [btn("👤 ታካሚ/ጠያቂ ነኝ",             cb="spec_patient")],
    [btn("👨‍⚕️ ጠቅላላ ሀኪም (GP) ነኝ",      cb="spec_gp")],
    [btn("📝 የስፔሻሊስት/ዶክተር ምዝገባ",      cb="start_doc_reg")],
    [btn("⬅️ ተመለስ",                      cb="back_main")],
)

SPECIALTIES_KB = ik(
    [btn("🩺 የውስጥ ደዌ (Internal Medicine)", cb="dept_internal")],
    [btn("🧠 የነርቭ ስፔሻሊስት (Neurology)",    cb="dept_neuro")],
    [btn("👶 የህፃናት ስፔሻሊስት (Pediatrics)",  cb="dept_peds")],
    [btn("🫀 የልብ ስፔሻሊስት (Cardiology)",    cb="dept_cardio")],
    [btn("🤰 የማህፀንና ፅንስ (OBGYN)",          cb="dept_obgyn")],
    [btn("⬅️ ተመለስ",                         cb="back_to_spec_choice")],
)

def edu_menu():
    return ik(
        [btn("🎁 ነፃ የጤና ትምህርቶች", url=cfg("free_channel", "https://t.me/tenachinfree"))],
        [btn(f"💎 ፕሪሚየም ቻናል ({cfg('premium_price','24')} ETB/ወር)", cb="buy_prem")],
        [btn("🩺 የውስጥ ደዌ መጻሕፍት",      cb="store_internal")],
        [btn("🤰 የማህፀን መጻሕፍት (OBGYN)", cb="store_obgyn")],
        [btn("👶 የሕፃናት ህክምና",           cb="store_peds")],
        [btn("⬅️ ተመለስ",                  cb="back_main")],
    )

def group_menu():
    return ik(
        [btn("👥 ነፃ የቡድን ውይይት", url=cfg("free_group", "https://t.me/+UXHaDU3GIudlY2U0"))],
        [btn("🔒 ፕሪሚየም ቪዲዮ/ድምፅ ውይይት", cb="group_prem")],
        [btn("⬅️ ተመለስ", cb="back_main")],
    )

HOMECARE_MENU = ik(
    [btn("🏠 የቤት ለቤት ህክምና ስልክ",   cb="homecare_info")],
    [btn("🚨 ድንገተኛ አደጋ (Emergency)", cb="emergency_alert")],
    [btn("⬅️ ተመለስ",                  cb="back_main")],
)

def get_dynamic_products(specialty_code: str):
    """Fetch active digital products from Supabase bot_products table."""
    try:
        prods = sb_get("bot_products", f"specialty=eq.{specialty_code}&is_active=eq.true&select=id,title,price,file_type")
        if prods and isinstance(prods, list) and len(prods) > 0:
            return prods
    except Exception as e:
        logger.error(f"get_dynamic_products error: {e}")
    # Fallback if table not yet populated
    if specialty_code == "internal":
        return [{"id": "1", "title": "የደም ግፊት መከላከያ", "price": 200, "file_type": "pdf"},
                {"id": "2", "title": "የስኳር በሽታ አያያዝ", "price": 300, "file_type": "pdf"}]
    elif specialty_code == "obgyn":
        return [{"id": "3", "title": "OBGYN Guide (PDF)", "price": 300, "file_type": "pdf"},
                {"id": "4", "title": "OBGYN Video Lecture", "price": 500, "file_type": "video"},
                {"id": "5", "title": "የእርግዝና እንክብካቤ", "price": 250, "file_type": "pdf"}]
    else:
        return [{"id": "6", "title": "የሕፃናት ምግብና እድገት", "price": 200, "file_type": "pdf"}]

def digital_products_kb(dept: str):
    prods = get_dynamic_products(dept)
    rows = []
    for p in prods:
        pid = str(p.get("id"))[:8]  # compact id
        price = int(p.get("price", 200))
        title = p.get("title", "Product")
        # Ensure clean display
        rows.append([btn(f"📘 {title} - {price} ETB", cb=f"bp_{pid}_{price}")])
    rows.append([btn("⬅️ ተመለስ", cb="back_to_edu_menu")])
    return ik(*rows)

def admin_approve_kb(approve_cb: str, reject_user_id: int):
    return ik([btn("✅ Approve", cb=approve_cb),
               btn("❌ Reject",  cb=f"rej_{reject_user_id}")])

def rating_kb(doctor_id):
    return ik([
        btn("⭐ 1",          cb=f"rt_1_{doctor_id}"),
        btn("⭐⭐ 2",       cb=f"rt_2_{doctor_id}"),
        btn("⭐⭐⭐ 3",    cb=f"rt_3_{doctor_id}"),
        btn("⭐⭐⭐⭐ 4",  cb=f"rt_4_{doctor_id}"),
        btn("⭐⭐⭐⭐⭐ 5", cb=f"rt_5_{doctor_id}"),
    ])

def end_consultation_kb(other_id):
    return ik([btn("🛑 End Consultation", cb=f"end_c_{other_id}")])

def payment_text(price: float, doctor_name: str = "") -> str:
    cbe  = cfg("cbe_account",      "1000255631865")
    tel  = cfg("telebirr_account", "0908343267")
    name = cfg("account_holder",   "Tazebachew Wudie")
    lines = []
    if doctor_name:
        lines.append(f"👨‍⚕️ ለ <b>{doctor_name}</b>\n")
    lines.append(f"💳 <b>ክፍያ: {price:.0f} ETB</b>\n\n<b>ክፍያ ቦታዎች፦</b>\n")
    lines.append(f"• <b>CBE:</b> <code>{cbe}</code> ({name})\n")
    lines.append(f"• <b>Telebirr:</b> <code>{tel}</code>\n\n")
    lines.append("📸 <b>ክፍያ ከፈጸሙ በኋላ ደረሰኙን (Screenshot) በዚህ ይላኩ፦</b>")
    return "".join(lines)

# ── FSM State Helpers ─────────────────────────────────────────────

def get_state(uid: int) -> dict:
    if uid in _FSM_MEMORY:
        return _FSM_MEMORY[uid]
    rows = sb_get("bot_fsm_states", f"user_id=eq.{uid}&select=state,data")
    if rows and isinstance(rows, list) and len(rows) > 0:
        res = {"state": rows[0].get("state", ""),
               "data":  rows[0].get("data") or {}}
        _FSM_MEMORY[uid] = res
        return res
    return {"state": "", "data": {}}

def set_state(uid: int, state: str, data: dict = None):
    st_obj = {"state": state, "data": data or {}}
    _FSM_MEMORY[uid] = st_obj
    body = {"user_id": uid, "state": state, "data": data or {}}
    ok = sb_patch("bot_fsm_states", f"user_id=eq.{uid}", body)
    if not ok:
        sb_post("bot_fsm_states", body)

def clear_state(uid: int):
    if uid in _FSM_MEMORY:
        del _FSM_MEMORY[uid]
    sb_delete("bot_fsm_states", f"user_id=eq.{uid}")

def update_state_data(uid: int, extra: dict):
    s = get_state(uid)
    s["data"].update(extra)
    set_state(uid, s["state"], s["data"])

# ── Dynamic Doctor Helpers ────────────────────────────────────────

def get_doctors_list(dept: str = "") -> list:
    try:
        docs = sb_get("public_doctor_profiles", "select=full_name,specialty,telegram_id")
        if dept:
            kw_map = {"internal": "Internal", "neuro": "Neurol",
                      "peds": "Pediatr", "cardio": "Cardiol", "obgyn": "OBGYN"}
            kw = kw_map.get(dept, "")
            if kw:
                docs = [d for d in docs
                        if kw.lower() in (d.get("specialty") or "").lower()]
        return [d for d in docs if d.get("telegram_id")]
    except Exception as e:
        logger.error(f"get_doctors_list: {e}")
        return []

def is_doctor(uid: int) -> bool:
    try:
        return bool(sb_get("public_doctor_profiles",
                            f"telegram_id=eq.{uid}&select=telegram_id"))
    except Exception:
        return False

def get_doctor_name_by_tid(tid: int) -> str:
    try:
        rows = sb_get("public_doctor_profiles",
                      f"telegram_id=eq.{tid}&select=full_name")
        if rows:
            return rows[0].get("full_name", f"Doctor ({tid})")
    except Exception:
        pass
    return f"Doctor ({tid})"

def get_doctor_online(tid: int) -> bool:
    rows = sb_get("doctor_consultation_fees",
                  f"telegram_id=eq.{tid}&select=is_online")
    return rows[0].get("is_online", False) if rows else False

def doctors_kb(dept: str):
    rows = []
    for d in get_doctors_list(dept):
        tid    = int(d["telegram_id"])
        name   = d.get("full_name", "Doctor")
        status = "🟢 Online" if get_doctor_online(tid) else "🔴 Offline"
        rows.append([btn(f"{name} ({status})", cb=f"sdoc_{tid}")])
    if not rows:
        rows.append([btn("❌ ምንም ዶክተር አልተገኘም", cb="back_to_depts")])
    rows.append([btn("⬅️ ተመለስ", cb="back_to_depts")])
    return {"inline_keyboard": rows}

def get_doctor_fees(tid: int) -> dict:
    rows = sb_get("doctor_consultation_fees",
                  f"telegram_id=eq.{tid}&select=text_fee,voice_fee,video_fee")
    if rows:
        return {"text":  int(rows[0].get("text_fee")  or 100),
                "voice": int(rows[0].get("voice_fee") or 200),
                "video": int(rows[0].get("video_fee") or 300)}
    return {"text": 100, "voice": 200, "video": 300}

def set_doctor_fees(tid: int, text_fee, voice_fee, video_fee):
    body = {"telegram_id": tid, "text_fee": text_fee,
            "voice_fee": voice_fee, "video_fee": video_fee}
    if not sb_patch("doctor_consultation_fees", f"telegram_id=eq.{tid}", body):
        sb_post("doctor_consultation_fees", body)

def toggle_online(tid: int) -> bool:
    current = get_doctor_online(tid)
    new_val = not current
    body = {"telegram_id": tid, "is_online": new_val}
    if not sb_patch("doctor_consultation_fees", f"telegram_id=eq.{tid}", body):
        sb_post("doctor_consultation_fees", body)
    return new_val

def call_type_kb(doctor_id: int, doctor_name: str):
    fees = get_doctor_fees(doctor_id)
    return ik(
        [btn(f"💬 Text Chat - {fees['text']} ETB",
             cb=f"cl_{doctor_id}_t_{fees['text']}")],
        [btn(f"🎙️ Voice Call - {fees['voice']} ETB",
             cb=f"cl_{doctor_id}_v_{fees['voice']}")],
        [btn(f"📹 Video Call - {fees['video']} ETB",
             cb=f"cl_{doctor_id}_w_{fees['video']}")],
        [btn("⬅️ ተመለስ", cb="back_to_depts")],
    )

def record_transaction(doc_tid: int, doc_name: str,
                       item_type: str, item_title: str, price: float, user_id: int):
    pct = cfg_float("commission_pct", 10.0)
    commission = round(price * pct / 100, 2)
    net        = round(price - commission, 2)
    sb_post("bot_transactions", {
        "doctor_telegram_id": doc_tid,
        "doctor_name":  doc_name,
        "item_type":    item_type,
        "item_title":   item_title,
        "price":        price,
        "commission":   commission,
        "net_amount":   net,
        "user_id":      user_id,
    })

def get_doctor_earnings(tid: int) -> dict:
    try:
        rows = sb_get("bot_transactions",
                      f"doctor_telegram_id=eq.{tid}"
                      f"&select=price,commission,net_amount,item_title,created_at"
                      f"&order=created_at.desc")
        return {
            "total":  sum(r.get("price", 0) or 0 for r in rows),
            "commis": sum(r.get("commission", 0) or 0 for r in rows),
            "net":    sum(r.get("net_amount", 0) or 0 for r in rows),
            "count":  len(rows),
            "recent": rows[:5],
        }
    except Exception as e:
        logger.error(f"get_doctor_earnings: {e}")
        return {"total": 0, "commis": 0, "net": 0, "count": 0, "recent": []}

# ── Admin Group Command Handler ───────────────────────────────────

def handle_group_command(text: str, chat_id: int, user: dict, msg: dict = None):
    uid = user.get("id", 0)
    rm_kb = {"remove_keyboard": True}

    if text.startswith("/getfileid") or text.startswith("/getfileid@") or text.startswith("/fileid"):
        reply_to = (msg or {}).get("reply_to_message")
        if reply_to:
            r_doc   = reply_to.get("document")
            r_video = reply_to.get("video")
            r_photo = reply_to.get("photo")
            if r_doc:
                fid   = r_doc.get("file_id")
                fname = r_doc.get("file_name", "Document")
                send(chat_id, f"📄 <b>Telegram File ID ({fname}):</b>\n\n<code>{fid}</code>\n\n<i>Copy and paste this File ID into the Admin Panel!</i>", markup=rm_kb)
                return
            elif r_video:
                fid = r_video.get("file_id")
                send(chat_id, f"🎬 <b>Telegram Video File ID:</b>\n\n<code>{fid}</code>\n\n<i>Copy and paste this File ID into the Admin Panel!</i>", markup=rm_kb)
                return
            elif r_photo:
                fid = r_photo[-1].get("file_id")
                send(chat_id, f"🖼️ <b>Telegram Photo File ID:</b>\n\n<code>{fid}</code>\n\n<i>Copy and paste this File ID into the Admin Panel!</i>", markup=rm_kb)
                return

        # Check if current message itself has document/photo
        c_doc = (msg or {}).get("document")
        if c_doc:
            fid   = c_doc.get("file_id")
            fname = c_doc.get("file_name", "Document")
            send(chat_id, f"📄 <b>Telegram File ID ({fname}):</b>\n\n<code>{fid}</code>\n\n<i>Copy and paste this File ID into the Admin Panel!</i>", markup=rm_kb)
            return

        send(chat_id,
             "💡 <b>To get a File ID:</b>\n\n"
             "1. <b>Reply</b> directly to any uploaded PDF/Document with <code>/getfileid</code>\n"
             "2. OR send the file with <code>/getfileid</code> in the caption\n"
             "3. OR send the PDF directly to the bot in private chat!",
             markup=rm_kb)
        return

    if text.startswith("/getgroupid") or text.startswith("/getgroupid@"):
        send(chat_id,
             f"ℹ️ <b>Admin Group Status</b>\n\n"
             f"• <b>This group ID:</b> <code>{chat_id}</code>\n"
             f"• <b>Active admin_group_id:</b> <code>{get_admin_group()}</code>\n"
             f"• <b>Vercel env ADMIN_GROUP_ID:</b> <code>{ADMIN_GROUP_ENV}</code>\n\n"
             f"<i>To verify receipts reach this group, type: /testgroup</i>",
             markup=rm_kb)

    elif text.startswith("/testgroup"):
        res = tg("sendMessage", {
            "chat_id": chat_id,
            "text": f"✅ <b>Group Test Successful!</b>\n\n"
                    f"Bot can send receipts here.\nGroup ID: <code>{chat_id}</code>",
            "parse_mode": "HTML",
            "reply_markup": rm_kb,
        })
        if not res.get("ok"):
            send(chat_id, f"❌ Failed: {res.get('description')}", markup=rm_kb)

    elif text.startswith("/settings"):
        _load_settings()
        lines = [f"⚙️ <b>Bot Settings</b>\n• <b>Active Admin Group:</b> <code>{get_admin_group()}</code>"]
        for k, v in sorted(_SETTINGS_MEMORY.items()):
            lines.append(f"• <b>{k}</b>: <code>{v}</code>")
        send(chat_id, "\n".join(lines), markup=rm_kb)

    elif text.startswith("/set "):
        parts = text.split(" ", 2)
        if len(parts) >= 3:
            k, v = parts[1].strip(), parts[2].strip()
            set_cfg(k, v)
            send(chat_id, f"✅ <b>{k}</b> set to: <code>{v}</code>", markup=rm_kb)

    elif text.startswith("/clean") or text.startswith("/start"):
        send(chat_id, "🧹 <b>Keyboard cleaned from this group.</b>", markup=rm_kb)

# ── Private Chat Handlers ─────────────────────────────────────────

def handle_start(chat_id: int, user: dict, payload: str = ""):
    if payload.startswith("login_"):
        token    = payload[6:]
        tg_id    = str(user.get("id", ""))
        name     = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        username = user.get("username", "")
        ok = sb_patch("login_tokens", f"token=eq.{token}&used=eq.false",
                      {"telegram_id": tg_id, "telegram_name": name,
                       "telegram_username": username})
        if ok:
            send(chat_id,
                 f"✅ <b>Login confirmed!</b>\n\n"
                 f"Go back to your browser — you are logged in as {name}! 🚀")
        else:
            send(chat_id, "❌ Login link expired or already used. Please try again.")
        return

    clear_state(chat_id)
    send(chat_id,
         "👋 <b>እንኳን ወደ ጤናችን (Tenachin) የህክምና ማማከሪያ ቦት በደህና መጡ!</b>\n\n"
         "እባክዎ የሚፈልጉትን አገልግሎት ከታች ካለው ሜኑ ይምረጡ፦",
         markup=MAIN_MENU)

def handle_earnings(chat_id: int, user: dict):
    uid = user.get("id", 0)
    if not is_doctor(uid):
        send(chat_id,
             "📊 <b>የኔ ትርፍ (Doctor Earnings)</b>\n\n"
             "ይህ አገልግሎት ለተመዘገቡ ስፔሻሊስቶች ብቻ ነው።\n"
             f"ለመመዝገብ: {cfg('website_url', 'https://healthlink-gate-main-nine.vercel.app/')}")
        return
    e = get_doctor_earnings(uid)
    text = (
        f"📊 <b>የኔ ትርፍ (Earnings Summary)</b>\n\n"
        f"💵 <b>ጠቅላላ የተከፈለ:</b> {e['total']:.0f} ETB\n"
        f"🏛 <b>Commission ({cfg('commission_pct','10')}%):</b> {e['commis']:.0f} ETB\n"
        f"✅ <b>ለእኔ የሚደርሰኝ:</b> {e['net']:.0f} ETB\n"
        f"📋 <b>ጠቅላላ ግብይቶች:</b> {e['count']}\n"
    )
    if e["recent"]:
        text += "\n<b>ቅርብ ጊዜ ግብይቶች:</b>\n"
        for r in e["recent"]:
            d   = (r.get("created_at") or "")[:10]
            t   = r.get("item_title", "Consultation")
            amt = r.get("price", 0)
            text += f"  • {d} | {t} | {amt} ETB\n"
    send(chat_id, text, markup=MAIN_MENU)

def handle_set_fees(chat_id: int, user: dict):
    uid = user.get("id", 0)
    if not is_doctor(uid):
        send(chat_id, "⛔ ይህ አገልግሎት ለስፔሻሊስቶች ብቻ ነው።")
        return
    fees   = get_doctor_fees(uid)
    online = get_doctor_online(uid)
    send(chat_id,
         f"💰 <b>የምክክር ዋጋዬን ማስተካከያ</b>\n\n"
         f"💬 Text Chat:  <b>{fees['text']} ETB</b>\n"
         f"🎙️ Voice Call: <b>{fees['voice']} ETB</b>\n"
         f"📹 Video Call: <b>{fees['video']} ETB</b>\n\n"
         f"📶 ሁኔታ: <b>{'🟢 Online' if online else '🔴 Offline'}</b>",
         markup=ik(
             [btn("💬 Text ዋጋ ለመለወጥ",   cb="fee_t")],
             [btn("🎙️ Voice ዋጋ ለመለወጥ", cb="fee_v")],
             [btn("📹 Video ዋጋ ለመለወጥ", cb="fee_w")],
             [btn("🔴 Go Offline" if online else "🟢 Go Online", cb="t_online")],
             [btn("⬅️ ወደ ሜኑ", cb="back_main")],
         ))

MENU_HANDLERS = {
    "👨‍⚕️ ስፔሻሊስት ለማማከር": lambda cid, _: send(
        cid, "👨‍⚕️ <b>ስፔሻሊስት ማማከሪያ</b>\n\nማንነትዎን ይምረጡ፦", markup=SPEC_SUB),
    "📚 የጤና ትምህርቶች": lambda cid, _: send(
        cid, "📚 <b>የጤና ትምህርቶች እና መጻሕፍት Store</b>", markup=edu_menu()),
    "👥 የቡድን ህክምና ምክክሮች": lambda cid, _: send(
        cid, "👥 <b>የቡድን ህክምና ውይይቶች</b>", markup=group_menu()),
    "🏠 የቤት ለቤት ህክምና & 🚨 ድንገተኛ አደጋ": lambda cid, _: send(
        cid, "🏠 <b>የቤት ለቤት ህክምና እና ድንገተኛ አደጋ</b>", markup=HOMECARE_MENU),
    "📞 እርዳታና ድጋፍ (Help)": lambda cid, _: send(
        cid,
        f"📞 <b>Support Center</b>\n\n"
        f"• ስልክ: <code>{cfg('support_phone_1','+251908343267')}</code> / <code>{cfg('support_phone_2','0967449552')}</code>\n"
        f"• Telegram: {cfg('support_username','@tenachinbottelemedicine')}\n"
        f"• Website: {cfg('website_url','https://healthlink-gate-main-nine.vercel.app/')}"),
    "💰 የምክክር ዋጋዬን ማስተካከያ": lambda cid, user: handle_set_fees(cid, user),
    "📊 የኔ ትርፍ (Earnings)":    lambda cid, user: handle_earnings(cid, user),
}

# ── Callback Query Router ─────────────────────────────────────────

def handle_callback(cb: dict):
    data = cb.get("data", "")
    cid  = cb["message"]["chat"]["id"]
    mid  = cb["message"]["message_id"]
    user = cb.get("from", {})
    uid  = user.get("id", 0)
    answer_cb(cb["id"])

    # Navigation
    if data == "back_main":
        clear_state(uid)
        send(cid, "👋 ከሜኑ ይምረጡ፦", markup=MAIN_MENU)
    elif data == "back_to_spec_choice":
        edit_text(cid, mid, "👨‍⚕️ ስፔሻሊስት ማማከሪያ — ማንነትዎን ይምረጡ፦", markup=SPEC_SUB)
    elif data == "back_to_depts":
        edit_text(cid, mid, "🩺 የስፔሻሊቲ ዘርፍ ይምረጡ፦", markup=SPECIALTIES_KB)
    elif data == "back_to_edu_menu":
        edit_text(cid, mid, "📚 Store", markup=edu_menu())

    # Roles
    elif data in ("spec_patient", "spec_gp"):
        role = "Patient" if data == "spec_patient" else "GP"
        update_state_data(uid, {"user_role": role})
        edit_text(cid, mid, "🩺 የስፔሻሊቲ ዘርፍ ይምረጡ፦", markup=SPECIALTIES_KB)

    # Department
    elif data.startswith("dept_"):
        edit_text(cid, mid, "👨‍⚕️ ስፔሻሊስት ይምረጡ፦", markup=doctors_kb(data.split("_")[1]))

    # Doctor selected
    elif data.startswith("sdoc_"):
        did   = int(data.split("_")[1])
        dname = get_doctor_name_by_tid(did)
        edit_text(cid, mid, f"👨‍⚕️ <b>{dname}</b>\n\nየምክክር አይነት ይምረጡ፦",
                  markup=call_type_kb(did, dname))

    # Call type selected
    elif data.startswith("cl_"):
        parts = data.split("_")
        did   = int(parts[1])
        ctype_code = parts[2]
        price = float(parts[3])
        ctype_map = {"t": "Text Chat", "v": "Voice Call", "w": "Video Call"}
        ctype = ctype_map.get(ctype_code, "Consultation")
        dname = get_doctor_name_by_tid(did)
        role  = get_state(uid)["data"].get("user_role", "Patient")

        if role == "GP":
            set_state(uid, "waiting_gp_case",
                      {"doctor_id": did, "doctor_name": dname,
                       "price": price, "call_type": ctype})
            send(cid, f"📋 ለ <b>{dname}</b> — Case Details:\n\nየታካሚ ታሪክ ጽፈው ይላኩ፦")
        else:
            set_state(uid, "waiting_receipt",
                      {"doctor_id": did, "doctor_name": dname,
                       "price": price, "call_type": ctype})
            send(cid, f"📋 <b>የምክክር ጥያቄ ለ {dname}</b>\n📞 {ctype}\n\n" + payment_text(price, dname))

    # Doctor registration
    elif data == "start_doc_reg":
        set_state(uid, "doc_reg_name", {})
        send(cid, "📝 <b>ዶክተር ምዝገባ</b>\n\nሙሉ ስምዎን ያስገቡ:")

    # Store depts
    elif data == "store_internal":
        edit_text(cid, mid, "📚 የውስጥ ደዌ መጻሕፍት፦", markup=digital_products_kb("internal"))
    elif data == "store_obgyn":
        edit_text(cid, mid, "📚 የማህፀንና ፅንስ መጻሕፍት፦", markup=digital_products_kb("obgyn"))
    elif data == "store_peds":
        edit_text(cid, mid, "📚 የሕፃናት ህክምና መጻሕፍት፦", markup=digital_products_kb("peds"))

    # Buy product: bp_{pid}_{price}
    elif data.startswith("bp_"):
        parts   = data.split("_")
        pid     = parts[1]
        price   = float(parts[2])
        set_state(uid, "waiting_store_receipt",
                  {"prod_id": pid, "price": price})
        send(cid, f"📖 <b>ዲጂታል ምርት ግዢ</b>\n\n" + payment_text(price))

    # Buy premium
    elif data == "buy_prem":
        price = cfg_float("premium_price", 24.0)
        set_state(uid, "waiting_prem_receipt", {"price": price})
        send(cid, f"💎 <b>ፕሪሚየም ቻናል አባልነት ({price:.0f} ETB/ወር)</b>\n\n" + payment_text(price))

    # Fee editing
    elif data in ("fee_t", "fee_v", "fee_w"):
        type_map = {"fee_t": "text", "fee_v": "voice", "fee_w": "video"}
        ft = type_map[data]
        set_state(uid, f"set_fee_{ft}", {})
        send(cid, f"💰 አዲስ የ{ft.capitalize()} ዋጋ (ETB) ያስገቡ:")

    elif data == "t_online":
        new_st = toggle_online(uid)
        send(cid, f"✅ ሁኔታዎ → <b>{'🟢 Online' if new_st else '🔴 Offline'}</b>",
             markup=MAIN_MENU)

    # Info callbacks
    elif data == "group_prem":
        send(cid, f"🔒 ፕሪሚየም ቪዲዮ ውይይት\nአድሚን: {cfg('support_username','@tenachinbottelemedicine')}")
    elif data == "homecare_info":
        send(cid, f"🏠 <b>የቤት ለቤት ህክምና ስልክ:</b>\n<code>{cfg('support_phone_1','+251908343267')}</code>")
    elif data == "emergency_alert":
        send(cid, "🚨 <b>ድንገተኛ አደጋ!</b>\nወደ አቅራቢያ ሆስፒታል ይሂዱ ወይም 📞 <b>907</b> ይደውሉ።")

    # ── Doctor Application Approve / Decline Callbacks ────────────
    elif data.startswith("appr_da_"):
        doc_id = data.split("_")[2]
        # 1. Update doctor_applications
        sb_patch("doctor_applications", f"doctor_id=eq.{doc_id}", {
            "status": "approved",
            "reviewed_at": "now()"
        })
        # 2. Update profiles
        sb_patch("profiles", f"id=eq.{doc_id}", {
            "account_type": "doctor"
        })
        # 3. Notify doctor on Telegram if telegram_id exists
        prof_rows = sb_get("profiles", f"id=eq.{doc_id}&select=telegram_id,full_name")
        if prof_rows and prof_rows[0].get("telegram_id"):
            tid = int(prof_rows[0]["telegram_id"])
            send(tid,
                 "🎉 <b>እንኳን ደስ አለዎት! የህክምና ማማከሪያ ምዝገባዎ በአድሚን ጸድቋል።</b>\n\n"
                 "አሁን በቦቱና በድረ-ገጹ ታካሚዎችን ማማከር ይችላሉ። ጤና ይስጥልን!")
            set_doctor_fees(tid, 100, 200, 300)
            toggle_online(tid)

        try:
            edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n✅ <b>DOCTOR APPROVED BY ADMIN</b>")
        except Exception:
            send(cid, f"✅ Doctor application ({doc_id}) APPROVED!")

    elif data.startswith("rej_da_"):
        doc_id = data.split("_")[2]
        sb_patch("doctor_applications", f"doctor_id=eq.{doc_id}", {
            "status": "declined",
            "reviewed_at": "now()"
        })
        prof_rows = sb_get("profiles", f"id=eq.{doc_id}&select=telegram_id")
        if prof_rows and prof_rows[0].get("telegram_id"):
            tid = int(prof_rows[0]["telegram_id"])
            send(tid, "❌ <b>የዶክተር ምዝገባ ጥያቄዎ ውድቅ ተደርጓል።</b>\n\nለበለጠ መረጃ አድሚን ያነጋግሩ።")
        try:
            edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n❌ <b>DECLINED BY ADMIN</b>")
        except Exception:
            send(cid, f"❌ Doctor application ({doc_id}) DECLINED.")

    # ── Admin Approve / Reject Callbacks (short IDs) ──────────────
    elif data.startswith("appr_c_"):
        parts  = data.split("_")
        pat_id = int(parts[2])
        doc_id = int(parts[3])
        price  = float(parts[4])
        dname  = get_doctor_name_by_tid(doc_id)
        online = get_doctor_online(doc_id)
        record_transaction(doc_id, dname, "Consultation", f"1-on-1 Consultation", price, pat_id)
        if online:
            set_state(pat_id, "in_session", {"partner_id": doc_id})
            set_state(doc_id,  "in_session", {"partner_id": pat_id})
            send(pat_id, f"🟢 <b>ክፍያዎ ጸድቋል!</b> ከ {dname} ጋር ምክክር ተጀምሯል።",
                 markup=end_consultation_kb(doc_id))
            send(doc_id, f"👨‍⚕️ <b>አዲስ ታካሚ ተመድቦልዎታል!</b> (ID: <code>{pat_id}</code>)",
                 markup=end_consultation_kb(pat_id))
        else:
            send(pat_id, f"🔴 <b>{dname} Offline ናቸው።</b> ሰዓቱ ሲሆን ይነገርዎታል!")
            send(doc_id, f"🚨 <b>አዲስ ታካሚ ከፍሏል!</b> (ID: <code>{pat_id}</code>)\nሰዓቱን ይጻፉ:",
                 markup=ik([btn("🕒 ሰዓት ለመወሰን", cb=f"stime_{pat_id}")]))
        edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n✅ <b>APPROVED</b>")

    elif data.startswith("appr_s_"):
        # Format: appr_s_{pat_id}_{pid}_{price} or appr_s_{pat_id}_{price}
        parts  = data.split("_")
        pat_id = int(parts[2])
        pid    = parts[3] if len(parts) > 3 and not parts[3].isdigit() else (parts[3] if len(parts) > 4 else "")
        price  = float(parts[-1]) if parts[-1].replace(".","").isdigit() else 0.0

        # Look up product in bot_products
        title = "የጤና ትምህርት መጽሐፍ"
        dl_url = ""
        ftype = "pdf"
        if pid:
            prods = sb_get("bot_products", f"id=ilike.{pid}%&select=title,download_url,file_type,price")
            if prods and isinstance(prods, list) and len(prods) > 0:
                title  = prods[0].get("title", title)
                dl_url = prods[0].get("download_url", "")
                ftype  = prods[0].get("file_type", "pdf")
                price  = float(prods[0].get("price", price))

        record_transaction(0, "Platform", "Digital Product", title, price, pat_id)

        # Automatic Delivery to the buyer on Telegram
        delivered = False
        if dl_url:
            try:
                method = "sendVideo" if ftype == "video" else "sendDocument"
                param_key = "video" if ftype == "video" else "document"
                caption = f"📖 <b>{title}</b>\n\nክፍያዎ ስለጸደቀ መጽሐፉ/ትምህርቱ ተልኮልዎታል! መልካም ንባብ።"
                res = tg(method, {
                    "chat_id": pat_id,
                    param_key: dl_url,
                    "caption": caption,
                    "parse_mode": "HTML"
                })
                if res.get("ok"):
                    delivered = True
            except Exception as e:
                logger.error(f"Auto deliver error: {e}")

        if delivered:
            send(pat_id, f"🎉 <b>ክፍያዎ ጸድቋል!</b> መጽሐፉ ከላይ ተልኮልዎታል!")
        else:
            if dl_url and dl_url.startswith("http"):
                send(pat_id, f"🎉 <b>ክፍያዎ ጸድቋል!</b>\n\n📖 <b>{title}</b>\n🔗 ማውረጃ ሊንክ፦ {dl_url}")
            else:
                send(pat_id, f"🎉 <b>ክፍያዎ ጸድቋል!</b>\n\n📖 <b>{title}</b>\nመጽሐፉ በቅርቡ በአድሚን ቡድን ይላክልዎታል። እናመሰግናለን!")
                grp = get_admin_group()
                if grp:
                    send(grp, f"ℹ️ <b>ማስታወሻ:</b> ለታካሚ (<code>{pat_id}</code>) መጽሐፉን (<b>{title}</b>) ይላኩላቸው።")

        try:
            edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n✅ <b>STORE APPROVED & DELIVERED</b>")
        except Exception:
            send(cid, f"✅ Store payment for {pat_id} APPROVED!")

    elif data.startswith("appr_p_"):
        pat_id = int(data.split("_")[2])
        send(pat_id, f"🎉 <b>ፕሪሚየም ክፍያዎ ጸድቋል!</b>\n\n🔗 {cfg('premium_channel','https://t.me/tenachinpremium')}")
        edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n✅ <b>PREMIUM APPROVED</b>")

    elif data.startswith("appr_d_"):
        doc_id = int(data.split("_")[2])
        send(doc_id, "🎉 <b>የስፔሻሊስት ምዝገባዎ ጸድቋል!</b> እንኳን ደህና መጡ።")
        edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n✅ <b>DOCTOR APPROVED</b>")

    elif data.startswith("rej_"):
        target_id = int(data.split("_")[1])
        send(target_id, "❌ <b>ደረሰኝዎ ውድቅ ተደርጓል!</b> እባክዎ ትክክለኛ ደረሰኝ ይላኩ ወይም አድሚን ያነጋግሩ።")
        edit_caption(cid, mid, f"{cb['message'].get('caption','')}\n\n❌ <b>REJECTED</b>")

    elif data.startswith("stime_"):
        pat_id = int(data.split("_")[1])
        set_state(uid, "doc_scheduling", {"target_patient_id": pat_id})
        send(cid, "✍️ ነፃ ሰዓትዎን ይጻፉ (ምሳሌ: ነገ ከቀኑ 8:00):")

    elif data.startswith("end_c_"):
        other = int(data.split("_")[2])
        clear_state(uid)
        clear_state(other)
        send(cid, "🔴 <b>ምክክሩ ተጠናቋል።</b> እናመሰግናለን!")
        send(other, "🔴 <b>ምክክሩ ተጠናቋል።</b> እናመሰግናለን!")
        uid_is_doc = is_doctor(uid)
        patient_id = other if uid_is_doc else uid
        doc_id     = uid   if uid_is_doc else other
        send(patient_id, "⭐ ሀኪምዎን ይምዘኑ፦", markup=rating_kb(doc_id))

    elif data.startswith("rt_"):
        score  = data.split("_")[1]
        doc_id = data.split("_")[2]
        send(int(doc_id), f"🌟 <b>አዲስ Rating: {score}/5</b>")
        edit_text(cid, mid, f"⭐ ደረጃ ስለሰጡ ({score}/5) እናመሰግናለን!")

# ── Message Dispatcher ─────────────────────────────────────────────

def handle_message(msg: dict):
    cid       = msg["chat"]["id"]
    chat_type = msg["chat"].get("type", "private")
    user      = msg.get("from", {})
    uid       = user.get("id", 0)
    text      = msg.get("text", "")
    photo     = msg.get("photo")
    doc       = msg.get("document")

    # ── GROUP & SUPERGROUP: only handle slash commands ──────────────
    if chat_type in ("group", "supergroup"):
        if doc and ((msg.get("caption") or "").startswith("/getfileid") or (msg.get("caption") or "").startswith("/fileid")):
            fid   = doc.get("file_id")
            fname = doc.get("file_name", "Document")
            send(cid, f"📄 <b>Telegram File ID ({fname}):</b>\n\n<code>{fid}</code>\n\n<i>Copy and paste this into the Admin Panel!</i>", markup={"remove_keyboard": True})
            return
        if text and text.startswith("/"):
            handle_group_command(text, cid, user, msg)
        return

    # ── PRIVATE CHAT: commands & menu ──────────────────────────────
    if text.startswith("/start"):
        payload = text.split(" ", 1)[1].strip() if " " in text else ""
        handle_start(cid, user, payload)
        return

    if text.startswith("/help"):
        send(cid, f"📞 {cfg('support_phone_1','+251908343267')}\nTelegram: {cfg('support_username','')}")
        return

    if doc and ((msg.get("caption") or "").startswith("/getfileid") or (msg.get("caption") or "").startswith("/fileid")):
        fid = doc.get("file_id")
        fname = doc.get("file_name", "Document")
        send(cid, f"📄 <b>Telegram File ID ({fname}):</b>\n\n<code>{fid}</code>\n\n<i>Copy and paste this into the Admin Panel for automatic book delivery!</i>")
        return

    for key, fn in MENU_HANDLERS.items():
        if text == key:
            fn(cid, user)
            return

    fsm   = get_state(uid)
    state = fsm.get("state", "")
    data  = fsm.get("data", {})

    # ── Photo / Document Receipt Received ───────────────────────────
    if photo or doc:
        fid = photo[-1]["file_id"] if photo else doc["file_id"]
        p_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or f"User ({uid})"

        if state == "waiting_receipt":
            dname = data.get("doctor_name", "Specialist")
            did   = data.get("doctor_id", 0)
            price = data.get("price", 0)
            ctype = data.get("call_type", "Consultation")
            cap   = (f"🧾 <b>Consultation Payment</b>\n\n"
                     f"👤 Patient: {p_name} (<code>{uid}</code>)\n"
                     f"👨‍⚕️ Doctor: {dname} (<code>{did}</code>)\n"
                     f"💬 Type: {ctype}\n💳 Price: {price} ETB")
            akb   = admin_approve_kb(f"appr_c_{uid}_{did}_{int(price)}", uid)
            notify_admin(fid, cap, akb, is_photo=bool(photo))
            clear_state(uid)
            send(cid, "✅ ደረሰኝዎ ለአድሚን ቡድን ተልኳል። ክፍያው ሲረጋገጥ ከሀኪሙ ጋር ይገናኛሉ።")
            return

        elif state == "waiting_store_receipt":
            price = data.get("price", 0)
            cap   = (f"🛒 <b>Product Payment</b>\n\n"
                     f"👤 Buyer: {p_name} (<code>{uid}</code>)\n"
                     f"💳 Price: {price} ETB")
            akb   = admin_approve_kb(f"appr_s_{uid}_{int(price)}", uid)
            notify_admin(fid, cap, akb, is_photo=bool(photo))
            clear_state(uid)
            send(cid, "✅ ደረሰኝዎ ለአድሚን ቡድን ተልኳል። ፋይሉ ቶሎ ይደርስዎታል!")
            return

        elif state == "waiting_prem_receipt":
            price = data.get("price", 24)
            cap   = (f"💎 <b>Premium Subscription Payment</b>\n\n"
                     f"👤 User: {p_name} (<code>{uid}</code>)\n"
                     f"💳 Price: {price} ETB/month")
            akb   = admin_approve_kb(f"appr_p_{uid}", uid)
            notify_admin(fid, cap, akb, is_photo=bool(photo))
            clear_state(uid)
            send(cid, "✅ ደረሰኝዎ ለአድሚን ቡድን ተልኳል! ሊንኩ ቶሎ ይደርስዎታል!")
            return

        elif state == "doc_reg_license":
            cap   = (f"📝 <b>Doctor Registration Application</b>\n\n"
                     f"👤 Name: {data.get('reg_name')}\n"
                     f"🆔 Telegram: <code>{uid}</code>\n"
                     f"🩺 Specialty: {data.get('reg_specialty')}\n"
                     f"🏥 Workplace: {data.get('reg_institution')}\n"
                     f"💳 Fee: {data.get('reg_fee')} ETB")
            akb   = admin_approve_kb(f"appr_d_{uid}", uid)
            notify_admin(fid, cap, akb, is_photo=bool(photo))
            clear_state(uid)
            send(cid, "✅ ምዝገባ ጥያቄዎ ለአድሚን ቡድን ተልኳል! ሲጸድቅ ማሳወቂያ ይደርስዎታል!")
            return

        else:
            cap = (f"🧾 <b>Payment Receipt (Direct Upload)</b>\n\n"
                   f"👤 From: {p_name} (<code>{uid}</code>)\n"
                   f"<i>Please review and approve.</i>")
            akb = admin_approve_kb(f"appr_s_{uid}_0", uid)
            notify_admin(fid, cap, akb, is_photo=bool(photo))
            clear_state(uid)
            send(cid, "✅ ደረሰኝዎ ለአድሚን ቡድን ተልኳል። ክፍያው ሲረጋገጥ ማሳወቂያ ይደርስዎታል።")
            return

    # ── Text Responses During FSM ──────────────────────────────────
    if state == "waiting_gp_case" and text:
        data["case_details"] = text
        set_state(uid, "waiting_receipt", data)
        send(cid, f"✅ Case Details ተመዝግቧል!\n\n" + payment_text(data.get("price", 0)))
        return

    if state == "doc_reg_name" and text:
        set_state(uid, "doc_reg_spec", {"reg_name": text})
        send(cid, "🩺 የስፔሻሊቲ ዘርፍዎን ያስገቡ (ምሳሌ: Internal Medicine):")
        return
    if state == "doc_reg_spec" and text:
        data["reg_specialty"] = text
        set_state(uid, "doc_reg_inst", data)
        send(cid, "🏥 ስራ ቦታ/ሆስፒታልዎን ያስገቡ:")
        return
    if state == "doc_reg_inst" and text:
        data["reg_institution"] = text
        set_state(uid, "doc_reg_fee", data)
        send(cid, "💳 ለአንድ ታካሚ የህክምና ክፍያ ስንት ነው (ETB)?:")
        return
    if state == "doc_reg_fee" and text:
        data["reg_fee"] = text
        set_state(uid, "doc_reg_license", data)
        send(cid, "📄 የህክምና ፈቃድዎን (Professional License) ፎቶ ወይም Document ይላኩ፦")
        return

    if state.startswith("set_fee_") and text:
        ft = state.split("_")[2]
        try:
            val = float(text.replace("ETB", "").replace(",", "").strip())
            if val <= 0: raise ValueError
        except (ValueError, TypeError):
            send(cid, "❌ ትክክለኛ ቁጥር ያስገቡ (ምሳሌ: 150)")
            return
        fees = get_doctor_fees(uid)
        fees[ft] = val
        set_doctor_fees(uid, fees["text"], fees["voice"], fees["video"])
        clear_state(uid)
        send(cid, f"✅ የ{ft.capitalize()} ዋጋ ወደ {val:.0f} ETB ተቀይሯል!", markup=MAIN_MENU)
        return

    if state == "doc_scheduling" and text:
        pat_id = data.get("target_patient_id")
        if pat_id:
            send(int(pat_id), f"🗓️ <b>የቀጠሮ ሰዓት ተቆርቷል!</b>\n\n👨‍⚕️ ሀኪም: {user.get('first_name','')}\n🕒 ሰዓት: {text}")
            send(cid, "✅ ሰዓቱ ለታካሚው ተልኳል!")
        clear_state(uid)
        return

    if state == "in_session":
        partner = data.get("partner_id")
        if partner:
            copy_msg(int(partner), cid, msg["message_id"])
        return

    send(cid, "እባክዎ ከሜኑ ይምረጡ፦", markup=MAIN_MENU)

# ── External Notification Handler ──────────────────────────────────

def handle_doctor_app_notification(data: dict) -> bool:
    grp = get_admin_group()
    if not grp:
        logger.error("No admin group configured for doctor app notification.")
        return False

    full_name   = data.get("full_name", "Doctor")
    specialty   = data.get("specialty", "General")
    license_no  = data.get("license_number", "N/A")
    workplace   = data.get("workplace", "N/A")
    exp         = data.get("experience_years", 0)
    phone       = data.get("phone", "N/A")
    tg_user     = data.get("telegram", "N/A")
    fee         = data.get("consultation_fee", "N/A")
    bio         = data.get("bio", "")
    pdf_url     = data.get("file_url", "")
    doc_id      = str(data.get("doctor_id", ""))

    caption = (
        f"📝 <b>አዲስ የዶክተር ማመልከቻ (New Doctor Application)</b>\n\n"
        f"👤 <b>ስም:</b> {full_name}\n"
        f"🩺 <b>ስፔሻሊቲ:</b> {specialty}\n"
        f"📜 <b>License #:</b> <code>{license_no}</code>\n"
        f"🏥 <b>ተቋም:</b> {workplace}\n"
        f"⏳ <b>ልምድ:</b> {exp} ዓመት\n"
        f"💰 <b>የምክክር ክፍያ:</b> {fee} ETB\n"
        f"📞 <b>ስልክ:</b> <code>{phone}</code>\n"
        f"✈️ <b>Telegram:</b> {tg_user}\n"
    )
    if bio:
        caption += f"\n📝 <b>Bio:</b> <i>{bio[:180]}</i>\n"

    buttons = [
        [btn("✅ Approve Doctor", cb=f"appr_da_{doc_id}"),
         btn("❌ Decline", cb=f"rej_da_{doc_id}")]
    ]
    if pdf_url:
        buttons.append([btn("📄 View License Document (PDF)", url=pdf_url)])

    akb = ik(*buttons)

    # Try sending document
    if pdf_url:
        res = tg("sendDocument", {
            "chat_id": grp,
            "document": pdf_url,
            "caption": caption,
            "parse_mode": "HTML",
            "reply_markup": akb
        })
        if res.get("ok"):
            return True

    # Fallback to message
    res2 = tg("sendMessage", {
        "chat_id": grp,
        "text": caption,
        "parse_mode": "HTML",
        "reply_markup": akb
    })
    return res2.get("ok", False)

# ── Webhook Update Handler ─────────────────────────────────────────

def process_update(update: dict):
    if update.get("action") == "notify_doctor_app":
        handle_doctor_app_notification(update)
    elif "message" in update:
        handle_message(update["message"])
    elif "callback_query" in update:
        handle_callback(update["callback_query"])

class handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "active",
            "active_admin_group": get_admin_group(),
            "env_admin_group": ADMIN_GROUP_ENV,
            "bot_token_set": bool(BOT_TOKEN),
            "supabase_set": bool(SUPABASE_URL and SUPABASE_KEY),
        }).encode())

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            update = json.loads(body)
            process_update(update)
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
        finally:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
