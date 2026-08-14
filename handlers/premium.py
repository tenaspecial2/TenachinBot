from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import settings

router = Router()


class PaymentState(StatesGroup):
    waiting_for_receipt = State()


# 1. Show Payment Info
@router.callback_query(F.data == "pay_manual")
async def start_manual_payment(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PaymentState.waiting_for_receipt)
    await callback.message.answer(
        "💳 **የክፍያ መመሪያ (Payment Instructions)**\n\n"
        "እባክዎ ክፍያውን በሚከተለው የባንክ ሂሳብ ያስገቡ:\n"
        "• **CBE:** 1000123456789\n"
        "• **Telebirr:** 0912345678\n\n"
        "ክፍያውን ከፈጸሙ በኋላ **ደረሰኙን (Screenshot)** እዚህ ይላኩ።"
    )
    await callback.answer()


# 2. Receive Receipt Photo & Forward to Admin
@router.message(PaymentState.waiting_for_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext, bot: Bot):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}")
        ]
    ])

    # Send receipt to the first Admin ID configured
    admin_id = settings.ADMIN_IDS[0] if settings.ADMIN_IDS else user_id
    await bot.send_photo(
        chat_id=admin_id,
        photo=photo_id,
        caption=f"📥 **አዲስ የክፍያ ማረጋገጫ!**\n\n"
                f"👤 **ተጠቃሚ:** {user_name}\n"
                f"🆔 **User ID:** `{user_id}`",
        reply_markup=admin_kb
    )

    await state.clear()
    await message.answer("የክፍያ ደረሰኝዎ ተልኳል። ከተረጋገጠ በኋላ መልእክት ይደርስዎታል! አመሰግናለሁ።")


# 3. Admin Approves
@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    user_id = callback.data.split("_")[1]

    # Send success message to the user
    await bot.send_message(
        chat_id=int(user_id),
        text="🎉 **ክፍያዎ ተረጋግጧል!**\n\nአሁን የሜምበርሺፕ አገልግሎቶችን ማግኘት ይችላሉ።"
    )
    
    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ **ተቀብለዋል (APPROVED)**")
    await callback.answer("Approved!")


# 4. Admin Rejects
@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    user_id = callback.data.split("_")[1]

    # Send failure message to the user
    await bot.send_message(
        chat_id=int(user_id),
        text="❌ **ክፍያዎ አልተረጋገጠም።**\n\nእባክዎ ትክክለኛ የክፍያ ደረሰኝ መላክዎን ያረጋግጡ ወይም ለአድሚን ያውሩ።"
    )

    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ **ተሰርዟል (REJECTED)**")
    await callback.answer("Rejected!")