from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "👨‍⚕️ የሐኪም ማማከር")
async def doctor_consultation(message: Message):
    await message.answer(
        "👨‍⚕️ **ከሐኪም ጋር ለመማከር:**\n\n"
        "እባክዎ የህመምዎን ምልክቶች ባጭሩ ይፃፉልን።"
    )