from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from bot.keyboards import main_menu
from db.queries import get_or_create_client
import os

router = Router()

WELCOME_TEXT = """
👋 *Салам! Добро пожаловать в KABARMAN* 📣

Справочник услуг и бизнеса
*Иссык-Кульской области*

🔍 *Найти* — кафе, мастера, специалиста
📋 *Зарегистрировать* свой бизнес бесплатно

Выберите что вам нужно 👇
"""

async def send_welcome(message: Message):
    """Отправляет приветствие с логотипом"""
    logo_file_id = os.getenv("WELCOME_FILE_ID")

    if logo_file_id:
        # Используем сохранённый file_id (быстро)
        await message.answer_photo(
            photo=logo_file_id,
            caption=WELCOME_TEXT,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    elif os.path.exists("welcome.jpg"):
        # Отправляем файл и сохраняем file_id
        photo = FSInputFile("welcome.jpg")
        sent = await message.answer_photo(
            photo=photo,
            caption=WELCOME_TEXT,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
        # Выводим file_id в лог — скопируй и добавь в Railway Variables
        fid = sent.photo[-1].file_id
        print(f"📸 WELCOME_FILE_ID={fid}")
        print(f"Добавь в Railway Variables: WELCOME_FILE_ID={fid}")
    else:
        # Без картинки
        await message.answer(
            WELCOME_TEXT,
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await get_or_create_client(
        msg.from_user.id,
        msg.from_user.username,
        msg.from_user.full_name
    )
    await send_welcome(msg)

@router.message(F.text == "ℹ️ О Кабарман")
async def about(msg: Message):
    await msg.answer(
        "📣 *KABARMAN — Вестник Иссык-Куля*\n\n"
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
    await send_welcome(cb.message)
    await cb.answer()

@router.callback_query(F.data == "new_search")
async def cb_new_search(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    from db.queries import get_districts
    from bot.keyboards import districts_keyboard
    from bot.states import SearchStates
    districts = await get_districts()
    await cb.message.answer(
        "📍 *Выберите район:*",
        parse_mode="Markdown",
        reply_markup=districts_keyboard(districts, action="sd")
    )
    await state.set_state(SearchStates.choosing_district)
    await cb.answer()
