from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "💬 አስተያየት ለመስጠት")
async def user_feedback(message: Message):
    await message.answer(
        "💬 **አስተያየት እና ጥቆማ:**\n\n"
        "የእርስዎን አስተያየት፣ ጥያቄ ወይም ቅሬታ እዚህ ይፃፉልን።"
    )