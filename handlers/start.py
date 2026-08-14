from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from keyboards.menus import get_main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def command_start_handler(message: Message):
    welcome_text = (
        f"👋 **እንኳን ወደ ጤናችን ቦት ደህና መጡ!**\n\n"
        f"ይህ የስፔሻሊስት እና ሰብስፔሻሊስቶችን የጤና ምክሮች፣ የቡድን ውይይቶችን "
        f"እና የህክምና ትምህርቶችን የሚያገኙበት ፕላትፎርም ነው።\n\n"
        f"⚠️ **Disclaimer (የህግ ተጠያቂነት ማስታወቂያ):**\n"
        f"በዚህ ቦት የሚሰጡ መረጃዎችና የኦንላይን ምክክሮች የአካል ህክምና ምርመራን ሙሉ በሙሉ አይተኩም። "
        f"ለበለጠ እና ለተሟላ ህክምና በአካል ወደ ህክምና ተቋም በመሄድ መታየት የተሻለ መሆኑን እንገልጻለን።\n\n"
        f"እባክዎ ከታች ካሉት አማራጮች አንዱን ይምረጡ👇"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")