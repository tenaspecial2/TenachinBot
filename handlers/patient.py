from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import settings
from keyboards.menus import (
    get_specialties_keyboard,
    get_doctors_keyboard,
    get_specialist_sub_menu,
    get_digital_products_keyboard,
    get_end_consultation_keyboard
)

router = Router()

# In-memory storage for active consultation sessions: {user_id: partner_user_id}
active_sessions: dict[int, int] = {}


# --- FSM States ---

class PaymentState(StatesGroup):
    waiting_for_receipt = State()


class GPConsultState(StatesGroup):
    waiting_for_case_details = State()


class DoctorRegisterState(StatesGroup):
    waiting_for_name = State()
    waiting_for_specialty = State()
    waiting_for_institution = State()
    waiting_for_fee = State()
    waiting_for_license_photo = State()


# ==========================================
# 🔄 CLEAN BACK HANDLERS
# ==========================================

@router.callback_query(F.data == "back_delete")
async def back_delete_handler(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "back_to_spec_choice")
async def back_to_spec_choice_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "👨‍⚕️ **የስፔሻሊስት ማማከሪያ ክፍል**\n\nእባክዎ ማንነትዎን ይምረጡ፦",
        reply_markup=get_specialist_sub_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_depts")
async def back_to_depts_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "🩺 **እባክዎ የሚፈልጉትን የስፔሻሊቲ ዘርፍ ይምረጡ፦**",
        reply_markup=get_specialties_keyboard()
    )
    await callback.answer()


# ==========================================
# 🩺 SPECIALIST REGISTRATION FLOW
# ==========================================

@router.message(Command("register_doctor"))
@router.callback_query(F.data == "start_doc_reg")
async def start_doctor_registration(event, state: FSMContext):
    await state.set_state(DoctorRegisterState.waiting_for_name)
    text = (
        "👨‍⚕️ **የስፔሻሊስት/ዶክተር ምዝገባ ፎርም**\n\n"
        "እንኳን ወደ ጤናችን ቦት በደህና መጡ! በፕላትፎርማችን ላይ ለመመዝገብ እባክዎን **ሙሉ ስምዎን ከማዕረግዎ ጋር** ያስገቡ (ምሳሌ፦ Dr. Abebe Bekele)፦"
    )
    if isinstance(event, CallbackQuery):
        await event.message.answer(text)
        await event.answer()
    else:
        await event.answer(text)


@router.message(DoctorRegisterState.waiting_for_name)
async def process_doctor_name(message: Message, state: FSMContext):
    await state.update_data(doc_name=message.text)
    await state.set_state(DoctorRegisterState.waiting_for_specialty)
    await message.answer("🩺 **የስፔሻሊቲ ዘርፍዎን ያስገቡ** (ምሳሌ፦ Internal Medicine, Pediatrics, OBGYN, Neurology)፦")


@router.message(DoctorRegisterState.waiting_for_specialty)
async def process_doctor_specialty(message: Message, state: FSMContext):
    await state.update_data(doc_specialty=message.text)
    await state.set_state(DoctorRegisterState.waiting_for_institution)
    await message.answer("🏥 **የሚሰሩበትን ተቋም/ሆስፒታል/ክሊኒክ ስም ያስገቡ**፦")


@router.message(DoctorRegisterState.waiting_for_institution)
async def process_doctor_institution(message: Message, state: FSMContext):
    await state.update_data(doc_institution=message.text)
    await state.set_state(DoctorRegisterState.waiting_for_fee)
    await message.answer("💳 **ለአንድ ታካሚ የማማከሪያ ክፍያዎ በብር (ETB) ስንት ነው?** (ምሳሌ፦ 300)፦")


@router.message(DoctorRegisterState.waiting_for_fee)
async def process_doctor_fee(message: Message, state: FSMContext):
    await state.update_data(doc_fee=message.text)
    await state.set_state(DoctorRegisterState.waiting_for_license_photo)
    await message.answer("📄 **እባክዎን የሙያ ፈቃድዎን (Medical License) ፎቶ እዚህ ይላኩ**፦")


@router.message(DoctorRegisterState.waiting_for_license_photo, F.photo)
async def process_doctor_license(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    user_data = await state.get_data()
    doc_id = message.from_user.id

    admin_approval_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve Doctor", callback_data=f"approve_doc_{doc_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_doc_{doc_id}")
        ]
    ])

    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=photo_id,
                caption=f"🩺 **አዲስ የስፔሻሊስት ምዝገባ ጥያቄ!**\n\n"
                        f"👤 **ስም:** {user_data.get('doc_name')}\n"
                        f"🩺 **ስፔሻሊቲ:** {user_data.get('doc_specialty')}\n"
                        f"🏥 **ተቋም:** {user_data.get('doc_institution')}\n"
                        f"💳 **ክፍያ:** {user_data.get('doc_fee')} ETB\n"
                        f"🆔 **Telegram ID:** `{doc_id}`",
                reply_markup=admin_approval_kb
            )
        except Exception as e:
            print(f"Could not notify admin {admin_id}: {e}")

    await state.clear()
    await message.answer("✅ የምዝገባ መረጃዎ እና የሙያ ፈቃድዎ ለአድሚን ተልኳል። ከተረጋገጠ በኋላ ቦቱ ላይ የሚታወቁ ይሆናል። አመሰግናለሁ!")


@router.callback_query(F.data.startswith("approve_doc_"))
async def approve_doctor_callback(callback: CallbackQuery, bot: Bot):
    doc_id = callback.data.split("_")[2]

    await bot.send_message(
        chat_id=int(doc_id),
        text="🎉 **እንኳን ደስ አለዎት!**\n\nየስፔሻሊስት ምዝገባዎ በአድሚን ተረጋግጦ ፀድቋል። አሁን በጤናችን ቦት ላይ አገልግሎት መስጠት ይችላሉ።"
    )
    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\n✅ **APPROVED DOCTOR**"
    )
    await callback.answer("Doctor Approved!")


@router.callback_query(F.data.startswith("reject_doc_"))
async def reject_doctor_callback(callback: CallbackQuery, bot: Bot):
    doc_id = callback.data.split("_")[2]

    await bot.send_message(
        chat_id=int(doc_id),
        text="❌ **የምዝገባ ጥያቄዎ አልተቀበለም።**\n\nእባክዎ ትክክለኛ የሙያ ፈቃድ መላክዎን ያረጋገጡ ወይም ለአድሚን ይደውሉ (0908343267)።"
    )
    await callback.message.edit_caption(
        caption=f"{callback.message.caption}\n\n❌ **REJECTED DOCTOR**"
    )
    await callback.answer("Doctor Rejected!")


# ==========================================
# 👤 PATIENT & GP CONSULTATION FLOWS
# ==========================================

@router.callback_query(F.data.in_(["spec_patient", "spec_gp"]))
async def start_consultation_flow(callback: CallbackQuery, state: FSMContext):
    user_type = "GP" if callback.data == "spec_gp" else "Patient"
    await state.update_data(user_type=user_type)

    title = "👨‍⚕️ **የጠቅላላ ሀኪሞች (GP) ማማከሪያ**" if user_type == "GP" else "👤 **የታካሚዎች ማማከሪያ**"

    await callback.message.edit_text(
        f"{title}\n\n🩺 እባክዎ ማማከር የሚፈልጉትን የስፔሻሊቲ ዘርፍ ይምረጡ፦",
        reply_markup=get_specialties_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dept_"))
async def select_doctor_step(callback: CallbackQuery):
    dept_code = callback.data.split("_")[1]
    await callback.message.edit_text(
        "👨‍⚕️ **በዚህ ዘርፍ የተመዘገቡ ባለሙያዎች፦**\n\nእባክዎ ማማከር የሚፈልጉትን ዶክተር ይምረጡ፦",
        reply_markup=get_doctors_keyboard(dept_code)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("doc_"))
async def doctor_payment_step(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_type = data.get("user_type", "Patient")

    if user_type == "GP":
        await state.set_state(GPConsultState.waiting_for_case_details)
        await callback.message.answer(
            "📝 **የታካሚ መረጃ እና የክፍያ ማረጋገጫ**\n\n"
            "እባክዎን የሚከተሉትን መረጃዎች በአንድ መልእክት (ከታካሚው የክፍያ Screenshot ጋር) ይላኩ፦\n\n"
            "1. የስምዎ እና የሚሰሩበት ተቋም/ክሊኒክ ስም\n"
            "2. የታካሚው ዋና ዋና ምልክቶች (History & Case Summary)\n"
            "3. የታካሚው የክፍያ ደረሰኝ (Screenshot)\n\n"
            "*(መረጃውን እንደ ጽሁፍ፣ ድምፅ ወይም ፎቶ አያይዘው መላክ ይችላሉ)*"
        )
    else:
        await state.set_state(PaymentState.waiting_for_receipt)
        await callback.message.answer(
            "💳 **የክፍያ መመሪያ (Payment Instructions)**\n\n"
            "እባክዎ ለአገልግሎቱ ክፍያውን በሚከተለው የባንክ ሂሳብ ያስገቡ:\n"
            "• **CBE:** `1000255631865` (Tazebachew Wudie)\n"
            "• **Telebirr:** `0908343267`\n\n"
            "ክፍያውን ከፈጸሙ በኋላ **የክፍያ ደረሰኙን (Screenshot)** እዚህ ይላኩ።",
            parse_mode="Markdown"
        )
    await callback.answer()


# --- GP Case Forwarding ---

@router.message(GPConsultState.waiting_for_case_details)
async def process_gp_case(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve & Start In-Bot Session", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}")
        ]
    ])

    for admin_id in settings.ADMIN_IDS:
        try:
            if message.photo:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=message.photo[-1].file_id,
                    caption=f"🩺 **አዲስ የGP ማማከሪያ ጥያቄ!**\n\n"
                            f"👤 **GP Name:** {user_name}\n"
                            f"🆔 **User ID:** `{user_id}`\n\n"
                            f"📄 **Case Details:**\n{message.caption or 'የታካሚ ደረሰኝ/መረጃ ተያይዟል'}",
                    reply_markup=admin_kb
                )
            else:
                await bot.send_message(
                    chat_id=admin_id,
                    text=f"🩺 **አዲስ የGP ማማከሪያ ጥያቄ!**\n\n"
                         f"👤 **GP Name:** {user_name}\n"
                         f"🆔 **User ID:** `{user_id}`\n\n"
                         f"📄 **Case Details:**\n{message.text}",
                    reply_markup=admin_kb
                )
        except Exception as e:
            print(f"Could not notify admin {admin_id}: {e}")

    await state.clear()
    await message.answer("✅ የታካሚዎ መረጃ እና ክፍያ ለአድሚን ተልኳል። ከተረጋገጠ በኋላ ከስፔሻሊስቱ ጋር እዚሁ ቦቱ ላይ ይገናኛሉ! አመሰግናለሁ።")


# ==========================================
# 📚 DIGITAL STORE & PREMIUM CHANNELS
# ==========================================

@router.callback_query(F.data == "edu_premium")
@router.callback_query(F.data == "group_premium")
async def premium_payment_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PaymentState.waiting_for_receipt)
    await callback.message.answer(
        "💳 **የፕሪሚየም አባልነት ክፍያ መመሪያ**\n\n"
        "እባክዎ ክፍያውን በሚከተለው የባንክ ሂሳብ ያስገቡ:\n"
        "• **CBE:** `1000255631865` (Tazebachew Wudie)\n"
        "• **Telebirr:** `0908343267`\n\n"
        "ክፍያውን ከፈጸሙ በኋላ **የክፍያ ደረሰኙን (Screenshot)** እዚህ ይላኩ።",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("store_dept_"))
async def show_department_products(callback: CallbackQuery):
    dept_code = callback.data.split("_")[2]
    await callback.message.edit_text(
        "📚 **በዚህ ዘርፍ የተዘጋጁ ዲጂታል መጻሕፍትና የተቀረፁ ቪዲዮዎች፦**\n\nእባክዎ መግዛት የሚፈልጉትን ይምረጡ፦",
        reply_markup=get_digital_products_keyboard(dept_code)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_prod_"))
async def buy_single_product(callback: CallbackQuery, state: FSMContext):
    prod_info = callback.data.split("_")
    price = prod_info[-1]

    await state.set_state(PaymentState.waiting_for_receipt)
    await state.update_data(selected_product=callback.data)

    await callback.message.answer(
        f"💳 **የክፍያ መመሪያ (Payment Instructions)**\n\n"
        f"ለመረጡት መጽሐፍ/ቪዲዮ ክፍያ መጠን፦ **{price} ETB**\n\n"
        "እባክዎ ክፍያውን በሚከተለው የባንክ ሂሳብ ያስገቡ:\n"
        "• **CBE:** `1000255631865` (Tazebachew Wudie)\n"
        "• **Telebirr:** `0908343267`\n\n"
        "ክፍያውን ከፈጸሙ በኋላ **የክፍያ ደረሰኙን (Screenshot)** እዚህ ይላኩ።",
        parse_mode="Markdown"
    )
    await callback.answer()


# ==========================================
# 🏠 HOMECARE & EMERGENCY ALERTS
# ==========================================

@router.callback_query(F.data == "homecare_info")
async def homecare_info_handler(callback: CallbackQuery):
    await callback.message.answer(
        "🏠 **የቤት ለቤት ህክምና ማስተባበሪያ**\n\n"
        "በከተማዎ ያሉ ባለሙያዎችን ለማግኘት እና ለማገናኘት እባክዎን በቀጥታ ለአስተባባሪው ይደውሉ፦\n\n"
        "📞 **የአስተባባሪ ስልክ ቁጥር፦** `0967449552`\n\n"
        "አስተባባሪው ባለሙያዎችን ከአካባቢዎ ያገናኝዎታል።",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "emergency_alert")
async def emergency_alert_flow(callback: CallbackQuery):
    await callback.message.answer(
        "🚨🚨 **አስቸኳይ ማስጠንቀቂያ (EMERGENCY)!!** 🚨🚨\n\n"
        "❌ እባክዎን በቦቱ መልእክት መመለስን አይጠብቁ!\n"
        "🏥 **በአቅራቢያዎ ወደሚገኝ የሆስፒታል ወይም የጤና ጣቢያ ድንገተኛ ክፍል (Emergency Room) በአካል በአስቸኳይ ይሂዱ!**",
        parse_mode="Markdown"
    )
    await callback.answer()


# ==========================================
# 📩 RECEIPT PROCESSING & IN-BOT CONSULTATION APPROVALS
# ==========================================

@router.message(PaymentState.waiting_for_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve & Connect In-Bot", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Reject (ሰርዝ)", callback_data=f"reject_{user_id}")
        ]
    ])

    for admin_id in settings.ADMIN_IDS:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=photo_id,
                caption=f"📥 **አዲስ የታካሚ/የምርት ክፍያ ማረጋገጫ!**\n\n"
                        f"👤 **ተጠቃሚ:** {user_name}\n"
                        f"🆔 **User ID:** `{user_id}`",
                reply_markup=admin_kb
            )
        except Exception as e:
            print(f"Could not send receipt to admin {admin_id}: {e}")

    await state.clear()
    await message.answer("✅ የክፍያ ደረሰኝዎ ለአድሚን ተልኳል። ከተረጋገጠ በኋላ ከስፔሻሊስቱ ጋር እዚሁ ቦቱ ላይ ይገናኛሉ! አመሰግናለሁ።")


@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    patient_id = int(callback.data.split("_")[1])

    # Assign Doctor (Using first admin ID as assigned specialist for live session)
    assigned_doctor_id = settings.ADMIN_IDS[0]

    # Establish bi-directional active live relay session
    active_sessions[patient_id] = assigned_doctor_id
    active_sessions[assigned_doctor_id] = patient_id

    # Notify Patient
    await bot.send_message(
        chat_id=patient_id,
        text="🎉 **ማማከሪያዎ ተፈቅዷል!**\n\n"
             "🟢 **ከስፔሻሊስቱ ጋር ያለዎት የቀጥታ ውይይት ተጀምሯል!**\n"
             "ማንኛውንም ጥያቄ፣ ጽሁፍ፣ ድምፅ ወይም ፎቶ እዚሁ ቦት ላይ መላክ ይችላሉ። ስፔሻሊስቱ ቀጥታ ይመልስልዎታል!\n\n"
             "ምክክሩን ሲጨርሱ ከታች ያለውን **🔴 End Consultation** የሚለውን ይጫኑ።",
        reply_markup=get_end_consultation_keyboard(assigned_doctor_id)
    )

    # Notify Doctor
    await bot.send_message(
        chat_id=assigned_doctor_id,
        text=f"🩺 **አዲስ የህክምና ማማከሪያ ክፍለ-ጊዜ ተጀምሯል!**\n\n"
             f"👤 **Patient User ID:** `{patient_id}`\n\n"
             f"እዚሁ ቦት ላይ የሚጽፉት መልእክት ቀጥታ ወደ ታካሚው ይደርሳል። ውይይቱን ሲጨርሱ ከታች ያለውን **🔴 End Consultation** ይጫኑ።",
        reply_markup=get_end_consultation_keyboard(patient_id)
    )

    await callback.message.edit_caption(
        caption=f"{callback.message.caption or callback.message.text}\n\n✅ **APPROVED & CONNECTED IN-BOT SESSION**"
    )
    await callback.answer("Session Created Successfully!")


@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    user_id = callback.data.split("_")[1]

    await bot.send_message(
        chat_id=int(user_id),
        text="❌ **ጥያቄዎ አልተቀበለም።**\n\nእባክዎ ትክክለኛ መረጃ/የክፍያ ደረሰኝ መላክዎን ያረጋግጡ ወይም ለአድሚን ይደውሉ (0908343267)።"
    )
    await callback.message.edit_caption(
        caption=f"{callback.message.caption or callback.message.text}\n\n❌ **ተሰርዟል (REJECTED)**"
    )
    await callback.answer("Rejected!")


# ==========================================
# 🔴 END CONSULTATION SESSION HANDLER
# ==========================================

@router.callback_query(F.data.startswith("end_session_"))
async def end_session_handler(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    partner_id = int(callback.data.split("_")[2])

    # Remove active session entries
    active_sessions.pop(user_id, None)
    active_sessions.pop(partner_id, None)

    # Notify clicking user
    await callback.message.answer("🛑 **የህክምና ምክክሩ በስኬት ተጠናቋል።**\n\nአገልግሎታችንን ስለተጠቀሙ እናመሰግናለን!")

    # Notify session partner
    try:
        await bot.send_message(
            chat_id=partner_id,
            text="🛑 **የህክምና ምክክሩ ተጠናቋል።**\n\nአገልግሎታችንን ስለተጠቀሙ እናመሰግናለን!"
        )
    except Exception as e:
        print(f"Could not notify partner {partner_id}: {e}")

    await callback.answer("Consultation Ended!")


# ==========================================
# 💬 IN-BOT LIVE RELAY CHAT ROUTER
# ==========================================

@router.message(F.text | F.photo | F.voice | F.audio | F.document)
async def relay_live_chat_message(message: Message, bot: Bot):
    sender_id = message.from_user.id

    # Check if sender is currently in an active live session
    if sender_id in active_sessions:
        partner_id = active_sessions[sender_id]
        try:
            # Forward copy of message directly to partner
            await bot.copy_message(
                chat_id=partner_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=get_end_consultation_keyboard(sender_id)
            )
        except Exception as e:
            await message.answer("❌ መልእክቱን ማስተላለፍ አልተቻለም። ውይይቱ ተዘግቶ ሊሆን ይችላል።")
            print(f"Relay error from {sender_id} to {partner_id}: {e}")