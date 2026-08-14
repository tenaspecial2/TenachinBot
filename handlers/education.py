from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "📚 የጤና ትምህርት")
async def health_education(message: Message):
    await message.answer(
        "📚 **የጤና ትምህርትና ምክሮች**\n\n"
        "1. በየቀኑ በቂ ውኃ ይጠጡ።\n"
        "2. የተመጣጠነ ምግብ ይመገቡ።\n"
        "3. በቀን ቢያንስ ለ30 ደቂቃ አካላዊ እንቅስቃሴ ያድርጉ።"
    )