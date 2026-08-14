from aiogram import Router, F
from aiogram.types import Message
from keyboards.menus import (
    get_specialist_sub_menu,
    get_education_sub_menu,
    get_group_consultation_sub_menu,
    get_homecare_emergency_sub_menu,
)

router = Router()


@router.message(F.text == "👨‍⚕️ ስፔሻሊስት ለማማከር")
async def specialist_menu_handler(message: Message):
    await message.answer(
        "👨‍⚕️ **የስፔሻሊስት ማማከሪያ ክፍል**\n\nእባክዎ ማንነትዎን ይምረጡ፦",
        reply_markup=get_specialist_sub_menu()
    )


@router.message(F.text == "📚 የጤና ትምህርቶች")
async def education_menu_handler(message: Message):
    await message.answer(
        "📚 **የጤና ትምህርቶች እና መረጃዎች**\n\nየሚፈልጉትን የትምህርት አይነት ይምረጡ፦",
        reply_markup=get_education_sub_menu()
    )


@router.message(F.text == "👥 የቡድን ህክምና ምክክሮች")
async def group_menu_handler(message: Message):
    await message.answer(
        "👥 **የቡድን ህክምና ምክክር እና የላይቭ ውይይት**\n\nየሚፈልጉትን ይምረጡ፦",
        reply_markup=get_group_consultation_sub_menu()
    )


@router.message(F.text == "🏠 የቤት ለቤት ህክምና & 🚨 ድንገተኛ አደጋ")
async def homecare_emergency_handler(message: Message):
    await message.answer(
        "🏠 **የቤት ለቤት ህክምና እና ድንገተኛ አደጋ**\n\nአገልግሎት ይምረጡ፦",
        reply_markup=get_homecare_emergency_sub_menu()
    )


@router.message(F.text == "📞 እርዳታና ድጋፍ (Help)")
async def help_menu_handler(message: Message):
    await message.answer(
        "📞 **የደንበኞች አገልግሎት እና እርዳታ**\n\n"
        "የቦቱ አጠቃቀም ካስቸገረዎት ወይም ተጨማሪ ጥያቄ ካለዎት በደስታ እንረዳዎታለን፦\n\n"
        "📱 **የአድሚን ስልክ ቁጥር፦** `0908343267`\n"
        "🏠 **የቤት ለቤት ህክምና ማስተባበሪያ፦** `0967449552`\n\n"
        "እባክዎን በስራ ሰዓት ይደውሉልን!",
        parse_mode="Markdown"
    )