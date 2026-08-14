from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main reply keyboard menu."""
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
    """Sub-menu for Patients, GPs, and Specialist Registration."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 ታካሚ/ጠያቂ ነኝ", callback_data="spec_patient")],
            [InlineKeyboardButton(text="👨‍⚕️ ጠቅላላ ሀኪም (GP) ነኝ (ስፔሻሊስት ለማማከር)", callback_data="spec_gp")],
            [InlineKeyboardButton(text="📝 የስፔሻሊስት/ዶክተር ምዝገባ (For Specialists)", callback_data="start_doc_reg")],
            [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_delete")]
        ]
    )


def get_specialties_keyboard() -> InlineKeyboardMarkup:
    """Specialty departments menu for patient/GP consultations."""
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
    """Doctors list under a selected department."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👨‍⚕️ Dr. Abebe (Senior) - 300 ETB", callback_data=f"doc_1_{dept}")],
            [InlineKeyboardButton(text="👩‍⚕️ Dr. Kebede (Sub-specialist) - 400 ETB", callback_data=f"doc_2_{dept}")],
            [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_to_depts")]
        ]
    )


def get_education_sub_menu() -> InlineKeyboardMarkup:
    """Education channels & specialty-based digital products store."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 ነፃ የጤና ትምህርቶች (Free Channel)", url="https://t.me/tenachinfree")],
            [InlineKeyboardButton(text="💎 ፕሪሚየም ቻናል (0.80 ሳንቲም/ቀን)", callback_data="edu_premium")],
            [InlineKeyboardButton(text="🩺 የውስጥ ደዌ መጻሕፍት/ቪዲዮዎች (Internal Med)", callback_data="store_dept_internal")],
            [InlineKeyboardButton(text="🤰 የማህፀንና ፅንስ መጻሕፍት/ቪዲዮዎች (OBGYN)", callback_data="store_dept_obgyn")],
            [InlineKeyboardButton(text="👶 የህፃናት ህክምና መጻሕፍት/ቪዲዮዎች (Pediatrics)", callback_data="store_dept_peds")],
            [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_delete")]
        ]
    )


def get_digital_products_keyboard(dept: str) -> InlineKeyboardMarkup:
    """Specific digital books & videos under selected specialty."""
    if dept == "internal":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📘 የደም ግፊት መከላከያ መጽሐፍ - 200 ETB", callback_data="buy_prod_htn_200")],
                [InlineKeyboardButton(text="📙 የስኳር በሽታ አያያዝ መጽሐፍ - 300 ETB", callback_data="buy_prod_dm_300")],
                [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_delete")]
            ]
        )
    elif dept == "obgyn":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📗 የእርግዝናና የእናትነት እንክብካቤ - 250 ETB", callback_data="buy_prod_ob_250")],
                [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_delete")]
            ]
        )
    else:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📘 የሕፃናት ምግብና እድገት መጽሐፍ - 200 ETB", callback_data="buy_prod_peds_200")],
                [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_delete")]
            ]
        )


def get_group_consultation_sub_menu() -> InlineKeyboardMarkup:
    """Group consultation links and premium subscription."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 ነፃ የቡድን ውይይት (Free Group)", url="https://t.me/+UXHaDU3GIudlY2U0")],
            [InlineKeyboardButton(text="🔒 ፕሪሚየም የቪዲዮ/ድምፅ ውይይት", callback_data="group_premium")],
            [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_delete")]
        ]
    )


def get_homecare_emergency_sub_menu() -> InlineKeyboardMarkup:
    """Homecare & Emergency support options."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 የቤት ለቤት ህክምና ማስተባበሪያ ስልክ", callback_data="homecare_info")],
            [InlineKeyboardButton(text="🚨 ድንገተኛ አደጋ (Emergency)", callback_data="emergency_alert")],
            [InlineKeyboardButton(text="⬅️ ተመለስ", callback_data="back_delete")]
        ]
    )


def get_end_consultation_keyboard(other_user_id: int) -> InlineKeyboardMarkup:
    """End consultation button attached to live sessions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔴 End Consultation (ምክክሩን ጨርስ)", callback_data=f"end_session_{other_user_id}")]
        ]
    )