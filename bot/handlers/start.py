from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from bot.keyboards import main_menu
from db.queries import get_or_create_client

router = Router()

START_TEXT = """
👋 Салам! Добро пожаловать в *Кабарман* 📣

Справочник услуг и бизнеса *Иссык-Кульской области*.

🔍 *Найти* — кафе, мастера, специалиста рядом с вами
📋 *Зарегистрировать* свой бизнес или услугу

Всё бесплатно. Выберите что вам нужно 👇
"""

@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await get_or_create_client(
        msg.from_user.id,
        msg.from_user.username,
        msg.from_user.full_name
    )
    await msg.answer(START_TEXT, parse_mode="Markdown", reply_markup=main_menu())

@router.message(F.text == "ℹ️ О Кабарман")
async def about(msg: Message):
    await msg.answer(
        "📣 *Кабарман* — Вестник Иссык-Куля\n\n"
        "Бесплатный справочник услуг и бизнеса:\n"
        "📍 Каракол · Ак-Суу · Тюп\n"
        "📍 Жети-Огуз · Тон · Чолпон-Ата\n\n"
        "🔍 Найди нужный сервис по району и категории\n"
        "📋 Зарегистрируй свой бизнес — бесплатно\n"
        "💬 Связывайся напрямую через WhatsApp\n\n"
        "По вопросам: @kabarman_admin",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer(START_TEXT, parse_mode="Markdown", reply_markup=main_menu())
    await cb.answer()

@router.callback_query(F.data == "new_search")
async def cb_new_search(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    from db.queries import get_districts
    from bot.keyboards import districts_keyboard
    districts = await get_districts()
    await cb.message.answer(
        "📍 *Выберите район:*",
        parse_mode="Markdown",
        reply_markup=districts_keyboard(districts, action="sd")
    )
    from bot.states import SearchStates
    await state.set_state(SearchStates.choosing_district)
    await cb.answer()
