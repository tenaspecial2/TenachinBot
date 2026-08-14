import asyncio
import logging
import os
import sqlite3
import uuid
from dotenv import load_dotenv

load_dotenv()
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, 
    CallbackQuery, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    FSInputFile,
    WebAppInfo
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

# Configuration Parameters
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "501384766,5872954068").split(",")]
DEFAULT_SPECIALIST_ID = 5872954068
COMMISSION_PERCENTAGE = 10.0

# 🔴 CONTACT INFO & LINKS
SUPPORT_PHONE_1 = "+251 90 834 3267"
SUPPORT_PHONE_2 = "0967449552"
SUPPORT_USERNAME = "@tenachinbottelemedicine"  
WEBSITE_URL = "https://healthlink-gate-main.vercel.app/"

# 🔗 CHANNELS & GROUPS LINKS
FREE_CHANNEL_LINK = "https://t.me/tenachinfree"
PREMIUM_CHANNEL_LINK = "https://t.me/tenachinpremium"
FREE_GROUP_LINK = "https://t.me/+UXHaDU3GIudlY2U0"

# Specialists Registry
SPECIALISTS = {
    "Abebe": 5872954068,
    "Kebede": 8571717581,
    "Tazebachew": 501384766
}

# 🟢 Doctor Status Tracking (Online/Offline)
doctor_online_status = {
    5872954068: True,   # Dr. Abebe
    8571717581: False,  # Dr. Kebede
    501384766: True     # Dr. Tazebachew
}

active_sessions: dict[int, int] = {}

# ==================== DATABASE SETUP ====================
DB_NAME = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_name TEXT,
            item_type TEXT,      
            item_title TEXT,     
            price REAL,          
            user_id INTEGER,     
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def record_transaction(doctor_name: str, item_type: str, item_title: str, price: float, user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (doctor_name, item_type, item_title, price, user_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (doctor_name, item_type, item_title, price, user_id))
    conn.commit()
    conn.close()

def get_doctor_name_by_id(doctor_id: int) -> str:
    for name, d_id in SPECIALISTS.items():
        if d_id == doctor_id:
            return f"Dr. {name}"
    return f"Dr. Unknown ({doctor_id})"

# --- FSM States ---
class PaymentState(StatesGroup):
    waiting_for_receipt = State()

class DoctorScheduleState(StatesGroup):
    waiting_for_free_time = State()

class GPConsultState(StatesGroup):
    waiting_for_case_details = State()
    waiting_for_gp_receipt = State()

class PremiumChannelState(StatesGroup):
    waiting_for_receipt = State()

class DoctorRegisterState(StatesGroup):
    waiting_for_name = State()
    waiting_for_specialty = State()
    waiting_for_institution = State()
    waiting_for_fee = State()
    waiting_for_license_doc = State()

class FeedbackState(StatesGroup):
    waiting_for_rating = State()
    waiting_for_comment = State()

class StorePaymentState(StatesGroup):
    waiting_for_store_receipt = State()


# --- KEYBOARDS ---
def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨‍⚕️ ስፔሻሊስት ለማማከር")],
            [KeyboardButton(text="📚 የጤና ትምህርቶች")],
            [KeyboardButton(text="👥 የቡድን ህክምና ምክክሮች")],
            [KeyboardButton(text="🏠 የቤት ለቤት ህክምና & 🚨 ድንገተኛ አደጋ")],
            [KeyboardButton(text="📞 እርዳታና ድጋፍ (Help)")]
        ],
        resize_keyboard=True
    )

def get_specialist_sub_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 ታካሚ/ጠያቂ ነኝ", callback_data="spec_patient")],
            [InlineKeyboardButton(text="👨‍⚕️ ጠቅላላ ሀኪም (GP) ነኝ (ስፔሻሊስት ለማማከር)", callback_data="spec_gp")],
            [InlineKeyboardButton(text="📝 የስፔሻሊስት/ዶክተር ምዝገባ (For Specialists)", callback_data="start_doc_reg")],
            [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_delete")]
        ]
    )

def get_specialties_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🩺 የውስጥ ደዌ (Internal Medicine)", callback_data="dept_internal")],
            [InlineKeyboardButton(text="🧠 የነርቭ ስፔሻሊስት (Neurology)", callback_data="dept_neuro")],
            [InlineKeyboardButton(text="👶 የህፃናት ስፔሻሊስት (Pediatrics)", callback_data="dept_peds")],
            [InlineKeyboardButton(text="🫀 የልብ ሰብ-ስፔሻሊስት (Cardiology)", callback_data="dept_cardio")],
            [InlineKeyboardButton(text="🤰 የማህፀንና ፅንስ (OBGYN)", callback_data="dept_obgyn")],
            [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_to_spec_choice")]
        ]
    )

def get_doctors_keyboard(dept: str) -> InlineKeyboardMarkup:
    buttons = []
    docs = [
        {"name": "Dr. Abebe", "id": SPECIALISTS["Abebe"]},
        {"name": "Dr. Kebede", "id": SPECIALISTS["Kebede"]}
    ]
    if dept == "obgyn":
        docs = [{"name": "Dr. Tazebachew", "id": SPECIALISTS["Tazebachew"]}]

    for d in docs:
        is_online = doctor_online_status.get(d["id"], False)
        status_icon = "🟢 Online" if is_online else "🔴 Offline"
        btn_text = f"{d['name']} ({status_icon})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"select_doc_{d['id']}_{d['name']}")])

    buttons.append([InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_to_depts")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_call_type_keyboard(doctor_id: int, doctor_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Text Chat - 100 ETB", callback_data=f"call_{doctor_id}_text_100_{doctor_name}")],
            [InlineKeyboardButton(text="🎙️ Voice Call - 200 ETB", callback_data=f"call_{doctor_id}_voice_200_{doctor_name}")],
            [InlineKeyboardButton(text="📹 Video Call - 300 ETB", callback_data=f"call_{doctor_id}_video_300_{doctor_name}")],
            [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_to_depts")]
        ]
    )

def get_education_sub_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 ነፃ የጤና ትምህርቶች (Free Channel)", url=FREE_CHANNEL_LINK)],
            [InlineKeyboardButton(text="💎 ፕሪሚየም ቻናል (24 ETB/ወር)", callback_data="buy_premium_channel")],
            [InlineKeyboardButton(text="🩺 የውስጥ ደዌ መጻሕፍት/ቪዲዮዎች (Internal Med)", callback_data="store_dept_internal")],
            [InlineKeyboardButton(text="🤰 የማህፀንና ፅንስ መጻሕፍት/ቪዲዮዎች (OBGYN)", callback_data="store_dept_obgyn")],
            [InlineKeyboardButton(text="👶 የሕፃናት ህክምና መጻሕፍት/ቪዲዮዎች (Pediatrics)", callback_data="store_dept_peds")],
            [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_delete")]
        ]
    )

def get_digital_products_keyboard(dept: str) -> InlineKeyboardMarkup:
    tazebachew_id = SPECIALISTS["Tazebachew"]
    abebe_id = SPECIALISTS["Abebe"]
    
    if dept == "internal":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📘 የደም ግፊት መከላከያ መጽሐፍ - 200 ETB", callback_data=f"buy_prod_HTN Book_200_pdf_{abebe_id}")],
                [InlineKeyboardButton(text="📙 የስኳር በሽታ አያያዝ መጽሐፍ - 300 ETB", callback_data=f"buy_prod_DM Book_300_pdf_{abebe_id}")],
                [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_to_edu_menu")]
            ]
        )
    elif dept == "obgyn":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📗 OBGYN Guide (PDF Book) - 300 ETB", callback_data=f"buy_prod_OBGYN Guide Book_300_pdf_{tazebachew_id}")],
                [InlineKeyboardButton(text="🎬 OBGYN Video Lecture - 500 ETB", callback_data=f"buy_prod_OBGYN Video Lecture_500_video_{tazebachew_id}")],
                [InlineKeyboardButton(text="📘 የእርግዝናና የእናትነት እንክብካቤ - 250 ETB", callback_data=f"buy_prod_Pregnancy Care_250_pdf_{tazebachew_id}")],
                [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_to_edu_menu")]
            ]
        )
    else:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📘 የሕፃናት ምግብና እድገት መጽሐፍ - 200 ETB", callback_data=f"buy_prod_Child Health_200_pdf_{abebe_id}")],
                [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_to_edu_menu")]
            ]
        )

def get_group_consultation_sub_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 ነፃ የቡድን ውይይት (Free Group)", url=FREE_GROUP_LINK)],
            [InlineKeyboardButton(text="🔒 ፕሪሚየም የቪዲዮ/ድምፅ ውይይት", callback_data="group_premium")],
            [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_delete")]
        ]
    )

def get_homecare_emergency_sub_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 የቤት ለቤት ህክምና ማስተባበሪያ ስልክ", callback_data="homecare_info")],
            [InlineKeyboardButton(text="🚨 ድንገተኛ አደጋ (Emergency)", callback_data="emergency_alert")],
            [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_delete")]
        ]
    )

# 🌐 DIRECT JITSI EMBED (FOR VOICE / VIDEO)
def get_end_consultation_keyboard(other_user_id: int, room_id: str = None, call_type: str = "video") -> InlineKeyboardMarkup:
    inline_keyboard = []

    if call_type in ["voice", "video"]:
        if not room_id:
            room_id = str(uuid.uuid4())[:8]
            
        call_url = f"https://meet.jit.si/TenachinConsultation_{room_id}#config.prejoinPageEnabled=false&config.deeplinking.disabled=true"
        
        if call_type == "voice":
            call_url += "&config.startWithVideoMuted=true"
            label = "🎙️ Voice Call inside Bot (Web App)"
        else:
            label = "📹 Video Call inside Bot (Web App)"

        inline_keyboard.append([InlineKeyboardButton(text=label, web_app=WebAppInfo(url=call_url))])

    inline_keyboard.append([InlineKeyboardButton(text="🛑 End Consultation", callback_data=f"confirm_end_{other_user_id}")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_confirm_end_keyboard(other_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ አዎ ጨርስ (Yes)", callback_data=f"end_session_{other_user_id}"),
                InlineKeyboardButton(text="❌ አይ ቀጥል (Cancel)", callback_data=f"cancel_end_{other_user_id}")
            ]
        ]
    )

def get_rating_keyboard(doctor_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ 1", callback_data=f"rate_1_{doctor_id}"),
                InlineKeyboardButton(text="⭐ 2", callback_data=f"rate_2_{doctor_id}"),
                InlineKeyboardButton(text="⭐ 3", callback_data=f"rate_3_{doctor_id}"),
                InlineKeyboardButton(text="⭐ 4", callback_data=f"rate_4_{doctor_id}"),
                InlineKeyboardButton(text="⭐ 5", callback_data=f"rate_5_{doctor_id}")
            ]
        ]
    )


# --- ROUTER SETUP ---
router = Router()

# 1. START & MAIN MENU BUTTONS
@router.message(CommandStart())
async def command_start_handler(message: Message):
    welcome_text = (
        "👋 **እንኳን ወደ ጤናችን (Tenachin) የህክምና ማማከሪያ ቦት በደህና መጡ!**\n\n"
        "እባክዎ የሚፈልጉትን አገልግሎት ከታች ካለው ሜኑ ይምረጡ፦"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

# ADMIN REPORT COMMAND
@router.message(Command("report"))
async def generate_report(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ ይህንን ማዘዣ የመጠቀም መብት የለዎትም።")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT doctor_name FROM transactions")
    doctors = cursor.fetchall()

    if not doctors:
        await message.answer("📊 እስካሁን ምንም የተመዘገበ የሽያጭ/የክፍያ መረጃ የለም።")
        conn.close()
        return

    report_text = "📊 **የዶክተሮች አጠቃላይ የሽያጭ እና ክፍያ ሪፖርት**\n"
    report_text += "═══════════════════════════\n\n"

    total_platform_revenue = 0
    total_platform_commission = 0

    for doc in doctors:
        doc_name = doc[0]
        report_text += f"👨‍⚕️ **{doc_name}**\n"
        
        cursor.execute(
            "SELECT item_type, item_title, price, COUNT(*) FROM transactions WHERE doctor_name = ? GROUP BY item_title",
            (doc_name,)
        )
        items = cursor.fetchall()

        doc_total = 0.0
        for item_type, item_title, price, count in items:
            subtotal = price * count
            doc_total += subtotal
            report_text += f"  • [{item_type}] {item_title} (x{count}) - {subtotal:.2f} ETB (ዋጋ: {price:.2f} ETB)\n"

        commission = (doc_total * COMMISSION_PERCENTAGE) / 100.0
        net_payable = doc_total - commission

        total_platform_revenue += doc_total
        total_platform_commission += commission

        report_text += f"  -----------------------------------\n"
        report_text += f"  💵 **ጠቅላላ ገቢ (Total):** {doc_total:.2f} ETB\n"
        report_text += f"  📉 **የአድሚን ኮሚሽን ({COMMISSION_PERCENTAGE}%):** -{commission:.2f} ETB\n"
        report_text += f"  💰 **ለዶክተሩ የሚከፈል (Net Payable):** {net_payable:.2f} ETB\n\n"

    report_text += "═══════════════════════════\n"
    report_text += f"📈 **የፕላትፎርሙ አጠቃላይ ገቢ:** {total_platform_revenue:.2f} ETB\n"
    report_text += f"🏛️ **የአድሚን አጠቃላይ ኮሚሽን (ትርፍ):** {total_platform_commission:.2f} ETB\n"

    conn.close()
    await message.answer(report_text, parse_mode="Markdown")

@router.message(F.text == "👨‍⚕️ ስፔሻሊስት ለማማከር")
async def specialist_menu_trigger(message: Message):
    await message.answer("👨‍⚕️ **የስፔሻሊስት ማማከሪያ ክፍል**\n\nእባክዎ ማንነትዎን ይምረጡ፦", reply_markup=get_specialist_sub_menu())

@router.message(F.text == "📚 የጤና ትምህርቶች")
async def education_menu_trigger(message: Message):
    await message.answer("📚 **የጤና ትምህርቶች እና ዲጂታል መጻሕፍት Store**\n\nእባክዎ የሚፈልጉትን ይምረጡ፦", reply_markup=get_education_sub_menu())

@router.message(F.text == "👥 የቡድን ህክምና ምክክሮች")
async def group_menu_trigger(message: Message):
    await message.answer("👥 **የቡድን ህክምና ውይይቶች**\n\nእባክዎ የሚፈልጉትን ማህበረሰብ ይምረጡ፦", reply_markup=get_group_consultation_sub_menu())

@router.message(F.text == "🏠 የቤት ለቤት ህክምና & 🚨 ድንገተኛ አደጋ")
async def homecare_menu_trigger(message: Message):
    await message.answer("🏠 **የቤት ለቤት ህክምና እና ድንገተኛ አደጋ አገልግሎት**\n\nእባክዎ የሚፈልጉትን ይምረጡ፦", reply_markup=get_homecare_emergency_sub_menu())

@router.message(F.text == "📞 እርዳታና ድጋፍ (Help)")
async def help_trigger(message: Message):
    await message.answer(
        "📞 **እርዳታና ድጋፍ (Support Center)**\n\n"
        "ማንኛውም ጥያቄ፣ የክፍያ ችግር ወይም ድጋፍ ካለዎት በደስታ እንረዳዎታለን፦\n\n"
        f"• **ስልክ ቁጥር:** `{SUPPORT_PHONE_1}` / `{SUPPORT_PHONE_2}`\n"
        f"• **Telegram Admin:** {SUPPORT_USERNAME}\n"
        f"• **ድህረ ገፅ (Website):** {WEBSITE_URL}\n\n"
        "አገልግሎታችንን ስለተጠቀሙ እናመሰግናለን!",
        parse_mode="Markdown"
    )

# Navigation Handlers
@router.callback_query(F.data == "back_delete")
async def back_delete_handler(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "back_to_edu_menu")
async def back_to_edu_menu_handler(callback: CallbackQuery):
    await callback.message.edit_text("📚 **የጤና ትምህርቶች እና ዲጂታል መጻሕፍት Store**\n\nእባክዎ የሚፈልጉትን ይምረጡ፦", reply_markup=get_education_sub_menu())
    await callback.answer()

@router.callback_query(F.data == "back_to_spec_choice")
async def back_to_spec_choice_handler(callback: CallbackQuery):
    await callback.message.edit_text("👨‍⚕️ **የስፔሻሊስት ማማከሪያ ክፍል**\n\nእባክዎ ማንነትዎን ይምረጡ፦", reply_markup=get_specialist_sub_menu())
    await callback.answer()

@router.callback_query(F.data == "back_to_depts")
async def back_to_depts_handler(callback: CallbackQuery):
    await callback.message.edit_text("🩺 **እባክዎ የሚፈልጉትን የስፔሻሊቲ ዘርፍ ይምረጡ፦**", reply_markup=get_specialties_keyboard())
    await callback.answer()

# Premium Channel Flow
@router.callback_query(F.data == "buy_premium_channel")
async def buy_premium_channel_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PremiumChannelState.waiting_for_receipt)
    msg = (
        "💎 **የፕሪሚየም ቻናል አባልነት (80 ሳንቲም በቀን / 24 ETB በወር)**\n\n"
        "በቻናሉ ውስጥ የየዕለቱ የጤና ምክሮች እና የስፔሻሊስቶች ጥያቄና መልስ ያገኛሉ።\n\n"
        "እባክዎ የ 24 ETB ክፍያውን በሚከተለው ያስገቡ፦\n"
        "• **CBE:** `1000255631865` (Tazebachew Wudie)\n"
        "• **Telebirr:** `0908343267`\n\n"
        "ክፍያውን ከፈጸሙ በኋላ **የክፍያ ደረሰኙን (Screenshot)** እዚህ ይላኩ፦"
    )
    await callback.message.answer(msg, parse_mode="Markdown")
    await callback.answer()

@router.message(PremiumChannelState.waiting_for_receipt, F.photo | F.document)
async def process_premium_receipt(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    caption = (
        f"💎 **አዲስ የፕሪሚየም ቻናል ክፍያ!**\n\n"
        f"👤 **ተጠቃሚ:** {message.from_user.full_name}\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"💳 **ክፍያ:** 24 ETB (ወርሃዊ)"
    )

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve & Send Link", callback_data=f"approve_prem_{user_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}")
        ]
    ])

    for admin_id in ADMIN_IDS:
        try:
            if message.photo:
                await bot.send_photo(chat_id=admin_id, photo=message.photo[-1].file_id, caption=caption, reply_markup=admin_kb)
            elif message.document:
                await bot.send_document(chat_id=admin_id, document=message.document.file_id, caption=caption, reply_markup=admin_kb)
        except Exception as e:
            logging.error(f"Error sending premium receipt to admin {admin_id}: {e}")

    await state.clear()
    await message.answer("✅ የክፍያ ደረሰኝዎ ለአድሚን ተልኳል። ክፍያው ሲረጋገጥ የፕሪሚየም ቻናሉ መግቢያ ሊንክ ይላክልዎታል።")

@router.callback_query(F.data.startswith("approve_prem_"))
async def approve_premium_callback(callback: CallbackQuery, bot: Bot):
    user_id = int(callback.data.split("_")[2])
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🎉 **ክፍያዎ ተረጋግጧል!**\n\nወደ ፕሪሚየም ቻናል ለመቀላቀል የሚከተለውን ሊንክ ይጫኑ፦\n🔗 {PREMIUM_CHANNEL_LINK}"
        )
        await callback.message.edit_caption(caption=f"{callback.message.caption or ''}\n\n✅ **PREMIUM APPROVED & LINK SENT**")
    except Exception as e:
        logging.error(f"Error approving premium user {user_id}: {e}")
    await callback.answer()

# Education Store Handlers
@router.callback_query(F.data.startswith("store_dept_"))
async def store_dept_handler(callback: CallbackQuery):
    dept = callback.data.split("_")[2]
    await callback.message.edit_text("📚 **እባክዎ የሚፈልጉትን መጽሐፍ/ቪዲዮ ይምረጡ፦**", reply_markup=get_digital_products_keyboard(dept))
    await callback.answer()

@router.callback_query(F.data.startswith("buy_prod_"))
async def buy_product_handler(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    prod_name = parts[2]
    prod_price = float(parts[3])
    file_type = parts[4]  
    author_id = int(parts[5]) if len(parts) > 5 else 0

    await state.update_data(item_name=prod_name, item_price=prod_price, file_type=file_type, author_id=author_id)
    await state.set_state(StorePaymentState.waiting_for_store_receipt)

    msg = (
        f"📖 **{prod_name} ለመግዛት**\n\n"
        f"💳 **ዋጋ:** {prod_price} ETB\n\n"
        "እባክዎ ክፍያውን በሚከተለው ያስገቡ፦\n"
        "• **CBE:** `1000255631865` (Tazebachew Wudie)\n"
        "• **Telebirr:** `0908343267`\n\n"
        "ክፍያውን ከፈጸሙ በኋላ **የክፍያ ደረሰኙን (Screenshot)** እዚህ ይላኩ፦"
    )
    await callback.message.answer(msg, parse_mode="Markdown")
    await callback.answer()

@router.message(StorePaymentState.waiting_for_store_receipt, F.photo | F.document)
async def process_store_receipt(message: Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    item_name = user_data.get("item_name", "Digital Product")
    item_price = user_data.get("item_price", 0.0)
    file_type = user_data.get("file_type", "pdf")
    author_id = user_data.get("author_id", 0)
    user_id = message.from_user.id

    doc_name = get_doctor_name_by_id(author_id)

    caption = (
        f"🛒 **አዲስ የዲጂታል ምርት ክፍያ!**\n\n"
        f"👤 **ገዢ:** {message.from_user.full_name}\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"👨‍⚕️ **ባለቤት:** {doc_name}\n"
        f"📦 **ዕቃ/አገልግሎት:** {item_name}\n"
        f"📂 **ዓይነት:** {file_type.upper()}\n"
        f"💳 **ዋጋ:** {item_price} ETB"
    )

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve & Send", callback_data=f"approve_store_{user_id}_{file_type}_{author_id}_{item_price}_{item_name}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}")
        ]
    ])

    for admin_id in ADMIN_IDS:
        try:
            if message.photo:
                await bot.send_photo(chat_id=admin_id, photo=message.photo[-1].file_id, caption=caption, reply_markup=admin_kb)
            elif message.document:
                await bot.send_document(chat_id=admin_id, document=message.document.file_id, caption=caption, reply_markup=admin_kb)
        except Exception as e:
            logging.error(f"Error sending to admin {admin_id}: {e}")

    await state.clear()
    await message.answer("✅ የክፍያ ደረሰኝዎ ለአድሚን ተልኳል። ክፍያው እንደተረጋገጠ የተመረጠው ፋይል ይላክልዎታል። አመሰግናለን!")

@router.callback_query(F.data.startswith("approve_store_"))
async def approve_store_callback(callback: CallbackQuery, bot: Bot):
    await callback.answer("⏳ Processing payment and sending file...")

    parts = callback.data.split("_")
    user_id = int(parts[2])
    file_type = parts[3]  
    author_id = int(parts[4])
    price = float(parts[5])
    item_name = parts[6] if len(parts) > 6 else "Digital Product"

    doctor_name = get_doctor_name_by_id(author_id)

    record_transaction(
        doctor_name=doctor_name,
        item_type=file_type.upper(),
        item_title=item_name,
        price=price,
        user_id=user_id
    )

    base_dir = os.path.dirname(os.path.abspath(__file__))

    await callback.message.edit_caption(
        caption=f"{callback.message.caption or ''}\n\n⏳ **SENDING {file_type.upper()} TO USER...**"
    )

    try:
        await bot.send_message(
            chat_id=user_id,
            text="🎉 **ክፍያዎ ተረጋግጧል!**\n\nየገዙት ፋይል ከታች ተያይዞ ተልኮልዎታል። መልካም ጊዜ!"
        )
        
        if file_type.lower() == "pdf":
            pdf_path = os.path.join(base_dir, "books", "obgyn_guide.pdf")
            if os.path.exists(pdf_path):
                pdf_file = FSInputFile(pdf_path)
                await bot.send_document(
                    chat_id=user_id, 
                    document=pdf_file,
                    caption=f"📗 **{item_name}**"
                )
            else:
                await callback.message.reply(f"❌ **ስህተት፦** PDF ፋይሉ በ `{pdf_path}` አልተገኘም!")

        elif file_type.lower() == "video":
            video_path = os.path.join(base_dir, "books", "obgyn_lecture.mp4")
            if os.path.exists(video_path):
                video_file = FSInputFile(video_path)
                await bot.send_video(
                    chat_id=user_id,
                    video=video_file,
                    caption=f"🎬 **{item_name}**"
                )
            else:
                await callback.message.reply(f"❌ **ስህተት፦** ቪዲዮ ፋይሉ በ `{video_path}` አልተገኘም!")
        
        await callback.message.edit_caption(
            caption=f"{callback.message.caption or ''}\n\n✅ **APPROVED & RECORDED IN DATABASE!**"
        )
        
    except Exception as e:
        error_details = f"❌ **ፋይሉን ሲልክ Error አጋጥሟል፦**\n`{e}`"
        logging.error(f"Error sending file to buyer {user_id}: {e}")
        await callback.message.reply(error_details, parse_mode="Markdown")

    if author_id != 0:
        try:
            await bot.send_message(
                chat_id=author_id,
                text=f"🎉 **እንኳን ደስ አለዎት {doctor_name}!**\n\nየእርስዎ {item_name} ({file_type.upper()}) በቦቱ በኩል ተሸጧል!\n👤 **ገዢ ID:** `{user_id}`"
            )
        except Exception as e:
            logging.error(f"Error notifying author {author_id}: {e}")

# Other Menu Handlers
@router.callback_query(F.data == "group_premium")
async def group_premium_handler(callback: CallbackQuery):
    await callback.message.answer(
        "🔒 **ፕሪሚየም የቪዲዮ/ድምፅ ውይይት**\n\n"
        "ከስፔሻሊስቶች ጋር በሳምንት 2 ቀን በቀጥታ የቪዲዮ/ድምፅ ውይይት ለማድረግ፦\n"
        "• **ወርሃዊ ክፍያ:** 150 ETB\n"
        f"ለበለጠ መረጃ አድሚን ያናግሩ፦ {SUPPORT_USERNAME}"
    )
    await callback.answer()

@router.callback_query(F.data == "homecare_info")
async def homecare_info_handler(callback: CallbackQuery):
    await callback.message.answer(
        "🏠 **የቤት ለቤት ህክምና አገልግሎት**\n\n"
        "በቤትዎ ሆነው የነርሲንግ፣ የሀኪም እና የላቦራቶሪ አገልግሎት ለማግኘት በስልክ ቁጥሮቻችን ይደውሉ፦\n"
        f"📞 `{SUPPORT_PHONE_1}` / `{SUPPORT_PHONE_2}`"
    )
    await callback.answer()

@router.callback_query(F.data == "emergency_alert")
async def emergency_alert_handler(callback: CallbackQuery):
    await callback.message.answer(
        "🚨 **ድንገተኛ አደጋ (Emergency)**\n\n"
        "ለድንገተኛ (Emergency) ህክምና ከሆነ እባክዎ አቅራቢያዎ ወደሚገኝ ህክምና ተቋም አሁኑኑ ይሂዱ።\n\n"
        "ለአምቡላንስ ወይም ለአስቸኳይ ጥሪ፦\n"
        "📞 **907** (ቀይ መስቀል)\n"
        f"📞 `{SUPPORT_PHONE_1}` (የጤናችን ድገፋ)"
    )
    await callback.answer()

# 3. SPECIALIST CONSULTATION & DOCTOR REGISTRATION FLOWS
@router.callback_query(F.data.in_({"spec_patient", "spec_gp"}))
async def spec_choice_handler(callback: CallbackQuery, state: FSMContext):
    user_role = "Patient" if callback.data == "spec_patient" else "GP"
    await state.update_data(user_role=user_role)
    await callback.message.edit_text("🩺 **እባክዎ የሚፈልጉትን የስፔሻሊቲ ዘርፍ ይምረጡ፦**", reply_markup=get_specialties_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("dept_"))
async def dept_choice_handler(callback: CallbackQuery):
    dept = callback.data.split("_")[1]
    await callback.message.edit_text("👨‍⚕️ **እባክዎ ማማከር የሚፈልጉትን ስፔሻሊስት ይምረጡ፦**", reply_markup=get_doctors_keyboard(dept))
    await callback.answer()

# Doctor selected -> Select Text, Voice or Video Call
@router.callback_query(F.data.startswith("select_doc_"))
async def doctor_selected(callback: CallbackQuery):
    parts = callback.data.split("_")
    doctor_id = int(parts[2])
    doctor_name = parts[3]
    
    await callback.message.edit_text(
        f"👨‍⚕️ **{doctor_name}**\n\nእባክዎ የምክክር አይነት ይምረጡ፦",
        reply_markup=get_call_type_keyboard(doctor_id, doctor_name)
    )
    await callback.answer()

# Call type selected -> Proceed to Payment
@router.callback_query(F.data.startswith("call_"))
async def call_type_selected(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    doctor_id = int(parts[1])
    call_type = parts[2]
    price = float(parts[3])
    doctor_name = parts[4]

    await state.update_data(
        doctor_id=doctor_id, 
        doctor_name=doctor_name, 
        price=price, 
        call_type=call_type
    )
    
    user_data = await state.get_data()
    role = user_data.get("user_role", "Patient")

    if role == "GP":
        await state.set_state(GPConsultState.waiting_for_case_details)
        await callback.message.answer(
            f"👨‍⚕️ **ለ Dr. {doctor_name} ማማከር የሚፈልጉትን የካርድ/የታካሚ ታሪክ (Case Details)** በአንድ መልእክት ጽፈው ይላኩ፦"
        )
    else:
        await state.set_state(PaymentState.waiting_for_receipt)
        msg = (
            f"📋 **የምክክር ጥያቄ ለ Dr. {doctor_name}**\n\n"
            f"📞 **ዓይነት:** {call_type.upper()} Consultation\n"
            f"💰 **የምክክር ክፍያ:** {price} ETB\n\n"
            "እባክዎ የምክክር ክፍያውን በሚከተለው የባንክ ሂሳብ ያስገቡ፦\n"
            "• **CBE:** `1000255631865` (Tazebachew Wudie)\n"
            "• **Telebirr:** `0908343267`\n\n"
            "ክፍያውን ከፈጸሙ በኋላ **የክፍያ ደረሰኙን (Screenshot)** እዚህ ይላኩ፦"
        )
        await callback.message.answer(msg, parse_mode="Markdown")

    await callback.answer()

# GP Case Details Flow
@router.message(GPConsultState.waiting_for_case_details)
async def process_gp_case_details(message: Message, state: FSMContext):
    await state.update_data(case_details=message.text)
    await state.set_state(GPConsultState.waiting_for_gp_receipt)
    
    user_data = await state.get_data()
    price = user_data.get("price", 300.0)
    doctor_name = user_data.get("doctor_name", "Specialist")

    msg = (
        f"✅ **የታካሚ ታሪክ መረጃ ተመዝግቧል!**\n\n"
        f"👨‍⚕️ **የተመረጠው ስፔሻሊስት:** Dr. {doctor_name}\n"
        f"💳 **የስፔሻሊስት ማማከሪያ ክፍያ:** {price} ETB\n\n"
        "እባክዎ ክፍያውን በሚከተለው ያስገቡ፦\n"
        "• **CBE:** `1000255631865` (Tazebachew Wudie)\n"
        "• **Telebirr:** `0908343267`\n\n"
        "ክፍያውን ከፈጸሙ በኋላ **የክፍያ ደረሰኙን (Screenshot)** እዚህ ይላኩ፦"
    )
    await message.answer(msg, parse_mode="Markdown")

@router.message(GPConsultState.waiting_for_gp_receipt, F.photo | F.document)
async def process_gp_receipt(message: Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    doctor_id = user_data.get("doctor_id", DEFAULT_SPECIALIST_ID)
    doctor_name = user_data.get("doctor_name", "Specialist")
    case_details = user_data.get("case_details", "No details provided")
    price = user_data.get("price", 300.0)
    user_id = message.from_user.id

    caption = (
        f"🧾 **አዲስ የስፔሻሊስት ማማከር (ከ GP) የክፍያ ደረሰኝ!**\n\n"
        f"👤 **GP Name:** {message.from_user.full_name}\n"
        f"🆔 **GP User ID:** `{user_id}`\n"
        f"👨‍⚕️ **የተመረጠው ስፔሻሊስት:** Dr. {doctor_name} (ID: `{doctor_id}`)\n"
        f"💳 **ክፍያ:** {price} ETB\n\n"
        f"📝 **የካርድ/የታካሚ ታሪክ (Case Details):**\n{case_details}"
    )

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve GP Case", callback_data=f"approve_{user_id}_{doctor_id}_{price}_{doctor_name}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}")
        ]
    ])

    for admin_id in ADMIN_IDS:
        try:
            if message.photo:
                await bot.send_photo(chat_id=admin_id, photo=message.photo[-1].file_id, caption=caption, reply_markup=admin_kb)
            elif message.document:
                await bot.send_document(chat_id=admin_id, document=message.document.file_id, caption=caption, reply_markup=admin_kb)
        except Exception as e:
            logging.error(f"Error sending GP receipt to admin {admin_id}: {e}")

    await state.clear()
    await message.answer("✅ የክፍያ ደረሰኝዎ እና የካርድ መረጃው ለአድሚን ተልኳል። ክፍያው ሲረጋገጥ ከስፔሻሊስት ሀኪሙ ጋር ይገናኛሉ።")

# Doctor Registration Flow
@router.callback_query(F.data == "start_doc_reg")
async def start_doc_reg_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DoctorRegisterState.waiting_for_name)
    await callback.message.answer("📝 **የስፔሻሊስት/ዶክተር ምዝገባ**\n\nእባክዎ ሙሉ ስምዎን ከነማዕረግዎ ያስገቡ (ምሳሌ: Dr. Abebe Kebede):")
    await callback.answer()

@router.message(DoctorRegisterState.waiting_for_name)
async def process_doc_name(message: Message, state: FSMContext):
    await state.update_data(reg_name=message.text)
    await state.set_state(DoctorRegisterState.waiting_for_specialty)
    await message.answer("🩺 የስፔሻሊቲ ዘርፍዎን ያስገቡ (ምሳሌ: Internal Medicine, Cardiology):")

@router.message(DoctorRegisterState.waiting_for_specialty)
async def process_doc_specialty(message: Message, state: FSMContext):
    await state.update_data(reg_specialty=message.text)
    await state.set_state(DoctorRegisterState.waiting_for_institution)
    await message.answer("ስራ ቦታ/የሚሰሩበትን ሆስፒታል ወይም ክሊኒክ ያስገቡ:")

@router.message(DoctorRegisterState.waiting_for_institution)
async def process_doc_institution(message: Message, state: FSMContext):
    await state.update_data(reg_institution=message.text)
    await state.set_state(DoctorRegisterState.waiting_for_fee)
    await message.answer("💳 ለአንድ ታካሚ የህክምና ማማከር ክፍያዎ ስንት ነው (በ ETB)?:")

@router.message(DoctorRegisterState.waiting_for_fee)
async def process_doc_fee(message: Message, state: FSMContext):
    await state.update_data(reg_fee=message.text)
    await state.set_state(DoctorRegisterState.waiting_for_license_doc)
    await message.answer("📄 እባክዎ የህክምና ፈቃድዎን (Professional License/ID) በፎቶ ወይም በ Document ይላኩ፦")

@router.message(DoctorRegisterState.waiting_for_license_doc, F.photo | F.document)
async def process_doc_license(message: Message, state: FSMContext, bot: Bot):
    reg_data = await state.get_data()
    doc_id = message.from_user.id

    caption = (
        f"📝 **አዲስ የዶክተር/ስፔሻሊስት ምዝገባ ጥያቄ!**\n\n"
        f"👤 **ስም:** {reg_data.get('reg_name')}\n"
        f"🆔 **Telegram ID:** `{doc_id}`\n"
        f"🩺 **ስፔሻሊቲ:** {reg_data.get('reg_specialty')}\n"
        f"🏥 **ተቋም:** {reg_data.get('reg_institution')}\n"
        f"💳 **ክፍያ:** {reg_data.get('reg_fee')} ETB"
    )

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve Doctor", callback_data=f"approve_doc_{doc_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{doc_id}")
        ]
    ])

    for admin_id in ADMIN_IDS:
        try:
            if message.photo:
                await bot.send_photo(chat_id=admin_id, photo=message.photo[-1].file_id, caption=caption, reply_markup=admin_kb)
            elif message.document:
                await bot.send_document(chat_id=admin_id, document=message.document.file_id, caption=caption, reply_markup=admin_kb)
        except Exception as e:
            logging.error(f"Error sending doc registration to admin {admin_id}: {e}")

    await state.clear()
    await message.answer("✅ የምዝገባ ጥያቄዎ እና ማስረጃዎ ለአድሚን ተልኳል። መረጃዎ ተመርምሮ ምዝገባው እንደጸደቀ ማሳወቂያ ይደርስዎታል!")

@router.callback_query(F.data.startswith("approve_doc_"))
async def approve_doc_callback(callback: CallbackQuery, bot: Bot):
    doc_id = int(callback.data.split("_")[2])
    try:
        await bot.send_message(
            chat_id=doc_id,
            text="🎉 **እንኳን ደስ አለዎት! የስፔሻሊስት ምዝገባዎ በሲስተሙ ጸድቋል።**\n\nአሁን በቦቱ በኩል የታካሚዎችና የሀኪሞች የማማከር ጥያቄዎችን ማስተናገድ ይችላሉ።"
        )
    except Exception as e:
        logging.error(f"Error notifying doctor {doc_id}: {e}")

    await callback.message.edit_caption(caption=f"{callback.message.caption or ''}\n\n✅ **DOCTOR APPROVED**")
    await callback.answer("Doctor Approved!")


# 4. PAYMENT & ADMIN APPROVAL (WITH ONLINE/OFFLINE LOGIC)
@router.message(PaymentState.waiting_for_receipt, F.photo | F.document)
async def process_payment_receipt(message: Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    doctor_id = user_data.get("doctor_id", DEFAULT_SPECIALIST_ID)
    doctor_name = user_data.get("doctor_name", "Specialist")
    price = user_data.get("price", 300.0)
    user_id = message.from_user.id

    caption = (
        f"🧾 **አዲስ የክፍያ ደረሰኝ!**\n\n"
        f"👤 **ታካሚ:** {message.from_user.full_name}\n"
        f"🆔 **User ID:** `{user_id}`\n"
        f"👨‍⚕️ **የተመረጠው ሀኪም:** Dr. {doctor_name} (ID: `{doctor_id}`)\n"
        f"💳 **የክፍያ መጠን:** {price} ETB"
    )

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user_id}_{doctor_id}_{price}_{doctor_name}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}")
        ]
    ])

    for admin_id in ADMIN_IDS:
        try:
            if message.photo:
                await bot.send_photo(chat_id=admin_id, photo=message.photo[-1].file_id, caption=caption, reply_markup=admin_kb)
            elif message.document:
                await bot.send_document(chat_id=admin_id, document=message.document.file_id, caption=caption, reply_markup=admin_kb)
        except Exception as e:
            logging.error(f"Error sending to admin {admin_id}: {e}")

    await state.clear()
    await message.answer("✅ የክፍያ ደረሰኝዎ ለአድሚን ተልኳል። ክፍያው ተረጋግጦ አድሚን ሲያጸድቀው ከሀኪሙ ጋር ይገናኛሉ።")

@router.callback_query(F.data.startswith("approve_"))
async def approve_payment_callback(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    user_id = int(parts[1])
    doctor_id = int(parts[2])
    price = float(parts[3]) if len(parts) > 3 else 300.0
    doc_name = parts[4] if len(parts) > 4 else get_doctor_name_by_id(doctor_id)

    call_type = "text" if price == 100.0 else ("voice" if price == 200.0 else "video")

    record_transaction(
        doctor_name=f"Dr. {doc_name}" if not doc_name.startswith("Dr.") else doc_name,
        item_type="Consultation",
        item_title=f"1-on-1 {call_type.upper()} Consultation",
        price=price,
        user_id=user_id
    )

    is_online = doctor_online_status.get(doctor_id, False)

    if is_online:
        # 🟢 ONLINE DOCTOR: START IMMEDIATELY
        consult_room_id = f"room_{user_id}_{doctor_id}"
        active_sessions[user_id] = doctor_id
        active_sessions[doctor_id] = user_id

        patient_kb = get_end_consultation_keyboard(doctor_id, room_id=consult_room_id, call_type=call_type)
        doctor_kb = get_end_consultation_keyboard(user_id, room_id=consult_room_id, call_type=call_type)

        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"🟢 **ክፍያዎ ተቀባይነት አግኝቷል! ሀኪሙ መስመር ላይ ይገኛሉ!**\n\n"
                    f"ከ Dr. {doc_name} ጋር ምስጢራዊ ምክክር ተጀምሯል። "
                    f"አሁን መልእክት፣ ፎቶ ወይም የካርድ መረጃ መላክ ይችላሉ።"
                ),
                reply_markup=patient_kb
            )
        except Exception as e:
            logging.error(f"Error sending approval to user {user_id}: {e}")

        try:
            await bot.send_message(
                chat_id=doctor_id,
                text=(
                    f"👨‍⚕️ **አዲስ ታካሚ ተመድቦሎታል!**\n\n"
                    f"👤 **ታካሚ ID:** `{user_id}`\n"
                    f"💬 **ዓይነት:** {call_type.upper()} Consultation"
                ),
                reply_markup=doctor_kb
            )
        except Exception as e:
            logging.error(f"Error notifying doctor {doctor_id}: {e}")

    else:
        # 🔴 OFFLINE DOCTOR: PROMPT DOCTOR FOR TIME
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🔴 **Dr. {doc_name} በአሁኑ ሰዓት መስመር ላይ የሉም።**\n\nለሀኪሙ ማሳወቂያ ተልኳል። ሀኪሙ የሚመቸውን ሰዓት ሲገልጽ መልእክት ይደርስዎታል!"
            )
        except Exception as e:
            logging.error(f"Error sending offline update to user {user_id}: {e}")

        doc_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🕒 ሰዓት ለመወሰን የመልሱ", callback_data=f"set_time_{user_id}_{call_type}")]
        ])
        
        try:
            await bot.send_message(
                chat_id=doctor_id,
                text=(
                    f"🚨 **አዲስ የተከፈለ ክፍያ አለ!**\n\n"
                    f"👤 **ታካሚ ID:** `{user_id}`\n"
                    f"📞 **የጥሪ ዓይነት:** {call_type.upper()}\n\n"
                    f"⚠️ **በአሁኑ ሰዓት Offline ስለሆኑ እባክዎ መቼ ይመችዎታል?**"
                ),
                reply_markup=doc_kb
            )
        except Exception as e:
            logging.error(f"Error asking doctor for availability: {e}")

    await callback.message.edit_caption(caption=f"{callback.message.caption or ''}\n\n✅ **APPROVED**")
    await callback.answer("Approved!")

@router.callback_query(F.data.startswith("set_time_"))
async def doctor_set_time_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    patient_id = int(parts[2])
    call_type = parts[3]

    await state.update_data(target_patient_id=patient_id, scheduled_call_type=call_type)
    await state.set_state(DoctorScheduleState.waiting_for_free_time)

    await callback.message.answer("✍️ **እባክዎ ነፃ የሚሆኑበትን ቀን እና ሰዓት ይጻፉ (ምሳሌ፦ ዛሬ ማታ 2:00 ሰዓት ወይም ነገ ከቀኑ 8:00 ሰዓት):**")
    await callback.answer()

@router.message(DoctorScheduleState.waiting_for_free_time)
async def doctor_saved_time(message: Message, state: FSMContext, bot: Bot):
    free_time = message.text
    data = await state.get_data()
    patient_id = data.get("target_patient_id")
    call_type = data.get("scheduled_call_type")

    try:
        await bot.send_message(
            chat_id=patient_id,
            text=(
                f"🗓️ **የቀጠሮ ሰዓት ተቆርጧል!**\n\n"
                f"👨‍⚕️ **ሀኪም:** {message.from_user.full_name}\n"
                f"🕒 **የተመደበው ሰዓት:** {free_time}\n"
                f"📞 **ዓይነት:** {call_type.upper()}\n\n"
                "በተጠቀሰው ሰዓት ቦቱ ላይ በመገኘት ጥሪ ወይም የፅሁፍ ውይይት ማድረግ ይችላሉ!"
            )
        )
        await message.answer("✅ የቀጠሮው ሰዓት ለታካሚው በስኬት ተልኳል!")
    except Exception as e:
        await message.answer(f"❌ ለታካሚው መልክት መላክ አልተቻለም: {e}")

    await state.clear()

@router.callback_query(F.data.startswith("reject_"))
async def reject_payment_callback(callback: CallbackQuery, bot: Bot):
    user_id = int(callback.data.split("_")[1])
    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ **የላኩት ደረሰኝ ውድቅ ተደርጓል!**\n\nእባክዎ ትክክለኛ የክፍያ ማረጋገጫ ደረሰኝ እንደገና ይላኩ ወይም በአድራሻችን አድሚንን ያናግሩ።"
        )
    except Exception as e:
        logging.error(f"Error sending rejection to user {user_id}: {e}")

    await callback.message.edit_caption(caption=f"{callback.message.caption or ''}\n\n❌ **REJECTED**")
    await callback.answer("Rejected!")


# 5. CONSULTATION SESSION & CHAT RELAY
@router.callback_query(F.data.startswith("confirm_end_"))
async def confirm_end_session(callback: CallbackQuery):
    other_user_id = int(callback.data.split("_")[2])
    await callback.message.reply(
        "⚠️ **እርግጠኛ ነዎት የህክምና ምክክሩን ማጠናቀቅ ይፈልጋሉ?**",
        reply_markup=get_confirm_end_keyboard(other_user_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cancel_end_"))
async def cancel_end_session(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("ምክክሩ ቀጥሏል።")

@router.callback_query(F.data.startswith("end_session_"))
async def process_end_session(callback: CallbackQuery, state: FSMContext, bot: Bot):
    other_user_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    if user_id in active_sessions:
        del active_sessions[user_id]
    if other_user_id in active_sessions:
        del active_sessions[other_user_id]

    await callback.message.edit_text("🔴 **የህክምና ምክክሩ በስኬት ተጠናቋል።** አመሰግናለን!")

    try:
        await bot.send_message(
            chat_id=other_user_id,
            text="🔴 **የህክምና ምክክሩ በሌላኛው ወገን ተጠናቋል።** አመሰግናለን!"
        )
    except Exception as e:
        logging.error(f"Error sending session end to {other_user_id}: {e}")

    doctor_id = other_user_id if user_id not in SPECIALISTS.values() else user_id
    patient_id = user_id if user_id not in SPECIALISTS.values() else other_user_id

    await state.update_data(rating_doctor_id=doctor_id)
    await state.set_state(FeedbackState.waiting_for_rating)

    try:
        await bot.send_message(
            chat_id=patient_id,
            text="⭐ **የስፔሻሊስት ሀኪምዎን አገልግሎት እንዴት ይመዝኑታል?**\n\nእባክዎ ከ1 እስከ 5 ኮከብ ይምረጡ፦",
            reply_markup=get_rating_keyboard(doctor_id)
        )
    except Exception as e:
        logging.error(f"Error sending rating to patient {patient_id}: {e}")

    await callback.answer()

# Feedback Process
@router.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    rating_val = parts[1]
    doctor_id = parts[2]

    await state.update_data(rating_score=rating_val, rating_doctor_id=doctor_id)
    await state.set_state(FeedbackState.waiting_for_comment)

    await callback.message.edit_text(
        f"⭐ ደረጃ ስለሰጡ አመሰግናለን ({rating_val}/5)!\n\n"
        "ለሀኪሙ የሚያስተላልፉት ተጨማሪ አስተያየት ካለ እባክዎ በፅሁፍ ይላኩ (ካለለዎት 'የለኝም' ብለው ይጻፉ)፦"
    )
    await callback.answer()

@router.message(FeedbackState.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext, bot: Bot):
    feedback_data = await state.get_data()
    doctor_id = feedback_data.get("rating_doctor_id")
    score = feedback_data.get("rating_score")
    comment_text = message.text

    feedback_msg = (
        f"🌟 **አዲስ የታካሚ አስተያየት (Feedback)**\n\n"
        f"⭐ **ደረጃ:** {score}/5\n"
        f"💬 **አስተያየት:** {comment_text}"
    )

    if doctor_id:
        try:
            await bot.send_message(chat_id=int(doctor_id), text=feedback_msg)
        except Exception as e:
            logging.error(f"Error sending feedback to doc {doctor_id}: {e}")

    await state.clear()
    await message.answer("🙏 ለሰጡን አስተያየት እናመሰግናለን! ጤና ይስጥልን።", reply_markup=get_main_menu_keyboard())

# Relaying Messages/Files between Active Users (Patient <-> Specialist/GP)
@router.message()
async def relay_messages(message: Message, bot: Bot):
    if message.web_app_data:
        return

    user_id = message.from_user.id

    if user_id in active_sessions:
        partner_id = active_sessions[user_id]
        try:
            await bot.copy_message(
                chat_id=partner_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
        except Exception as e:
            logging.error(f"Error relaying message from {user_id} to {partner_id}: {e}")
            await message.answer("❌ መልእክቱን ማስተላለፍ አልተቻለም። ውይይቱ ተቋርጦ ሊሆን ይችላል።")
    else:
        await message.answer(
            "የተላከውን መልእክት ማስተናገድ አልተቻለም። እባክዎ ከታች ካለው ሜኑ የሚፈልጉትን አገልግሎት ይምረጡ፦",
            reply_markup=get_main_menu_keyboard()
        )


# 6. MAIN APPLICATION ENTRY
async def main():
    init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logging.info("Tenachin Healthcare Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")