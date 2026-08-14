from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "👥 የቴሌግራም ግሩፕ")
async def group_links(message: Message):
    await message.answer(
        "👥 **የጤናችን ማህበረሰብ:**\n\n"
        "ወደ ውይይት ግሩፓችን ለመቀላቀል ሊንኩን ይጫኑ!"
    )