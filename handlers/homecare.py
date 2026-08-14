from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "🏠 የቤት ውስጥ ህክምና")
async def homecare_service(message: Message):
    await message.answer(
        "🏠 **የቤት ውስጥ የህክምና አገልግሎት:**\n\n"
        "በቤትዎ ሆነው የነርሲንግ እና የህክምና ክትትል ለማግኘት ያነጋግሩን።"
    )