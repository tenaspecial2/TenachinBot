from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config import settings

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        await message.answer("❌ እባክዎ ለዚህ ትዕዛዝ ፈቃድ የለዎትም።")
        return

    await message.answer(
        "⚙️ **የአድሚን መቆጣጠሪያ ፓነል (Admin Panel)**\n\n"
        "• የተጠቃሚዎችን ቁጥር ይመልከቱ\n"
        "• ክፍያዎችን ያረጋግጡ\n"
        "• መልእክቶችን ስርጭት ያድርጉ"
    )