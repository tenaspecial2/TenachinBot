from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "🚨 ድንገተኛ አደጋ")
async def emergency_info(message: Message):
    await message.answer(
        "🚨 **የድንገተኛ አደጋ ስልክ ቁጥሮች:**\n\n"
        "• **የአምቡላንስ ጥሪ:** 907\n"
        "• **ቀይ መስቀል:** 822\n"
        "• **የፖሊስ ጥሪ:** 991"
    )