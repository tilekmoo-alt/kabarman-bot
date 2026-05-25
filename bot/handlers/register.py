from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import os

from bot.states import RegisterStates
from bot.keyboards import (
    reg_categories_keyboard, districts_keyboard,
    confirm_keyboard, skip_keyboard, main_menu
)
from db.queries import (
    get_categories, get_districts, get_category, get_district,
    create_provider
)

router = Router()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x]

@router.message(F.text == "📋 Зарегистрировать бизнес")
async def register_start(msg: Message, state: FSMContext):
    await state.clear()
    cats = await get_categories()
    await msg.answer(
        "📋 Регистрация в Кабарман\n\n"
        "Бесплатно. После проверки появитесь в каталоге.\n"
        "Для управления своими бизнесами: /mybiz\n\n"
        "1 из 7 — Выберите категорию:",
        reply_markup=reg_categories_keyboard(cats)
    )
    await state.set_state(RegisterStates.choosing_category)

@router.callback_query(F.data.startswith("rc:"))
async def reg_category(cb: CallbackQuery, state: FSMContext):
    cat_id = int(cb.data.split(":")[1])
    cat = await get_category(cat_id)
    await state.update_data(category_id=cat_id, cat_name=f"{cat['emoji']} {cat['name']}")
    districts = await get_districts()
    await cb.message.edit_text(
        f"Категория: {cat['emoji']} {cat['name']} ✅\n\n"
        "2 из 7 — Выберите ваш район:",
        reply_markup=districts_keyboard(districts, action="rd")
    )
    await state.set_state(RegisterStates.choosing_district)
    await cb.answer()

@router.callback_query(F.data.startswith("rd:"))
async def reg_district(cb: CallbackQuery, state: FSMContext):
    dist_id = int(cb.data.split(":")[1])
    dist = await get_district(dist_id)
    await state.update_data(district_id=dist_id, dist_name=dist['name'])
    await cb.message.edit_text(
        f"Район: {dist['name']} ✅\n\n"
        "3 из 7 — Введите название бизнеса или своё имя:\n\n"
        "Например: Кафе Жаннат, Мастер Бакыт"
    )
    await state.set_state(RegisterStates.entering_name)
    await cb.answer()

@router.message(RegisterStates.entering_name)
async def reg_name(msg: Message, state: FSMContext):
    if len(msg.text.strip()) < 2:
        await msg.answer("Название слишком короткое. Попробуйте ещё раз:")
        return
    await state.update_data(name=msg.text.strip())
    await msg.answer(
        "4 из 7 — Введите номер телефона:\n\n"
        "Например: +996 700 123 456"
    )
    await state.set_state(RegisterStates.entering_phone)

@router.message(RegisterStates.entering_phone)
async def reg_phone(msg: Message, state: FSMContext):
    if len(msg.text.strip()) < 9:
        await msg.answer("Введите корректный номер телефона:")
        return
    await state.update_data(phone=msg.text.strip())
    await msg.answer(
        "5 из 7 — Опишите ваш бизнес или услуги:\n\n"
        "Например: Уютное кафе, завтраки и обеды. Есть доставка."
    )
    await state.set_state(RegisterStates.entering_desc)

@router.message(RegisterStates.entering_desc)
async def reg_desc(msg: Message, state: FSMContext):
    if len(msg.text.strip()) < 10:
        await msg.answer("Описание слишком короткое. Расскажите подробнее:")
        return
    await state.update_data(description=msg.text.strip())
    await msg.answer(
        "6 из 7 — Введите адрес:\n\n"
        "Например: ул. Токтогула 12, центр Каракола\n"
        "Или: Работаю на выезд по всей области"
    )
    await state.set_state(RegisterStates.entering_address)

@router.message(RegisterStates.entering_address)
async def reg_address(msg: Message, state: FSMContext):
    await state.update_data(address=msg.text.strip())
    await msg.answer(
        "7 из 7 — Ваш Instagram или другая соцсеть:\n\n"
        "Напишите никнейм, например: @mykafe\n\n"
        "Или нажмите Пропустить если нет",
        reply_markup=skip_keyboard("skip_social")
    )
    await state.set_state(RegisterStates.entering_social)

@router.message(RegisterStates.entering_social)
async def reg_social(msg: Message, state: FSMContext):
    link = msg.text.strip()
    if not link.startswith("@") and not link.startswith("http"):
        link = "@" + link
    await state.update_data(social_link=link)
    await _show_confirm(msg, state)

@router.callback_query(F.data == "skip_social")
async def skip_social(cb: CallbackQuery, state: FSMContext):
    await state.update_data(social_link=None)
    await _show_confirm(cb.message, state)
    await cb.answer()

async def _show_confirm(message, state: FSMContext):
    data = await state.get_data()
    social = data.get('social_link') or 'не указано'
    summary = (
        "Проверьте данные:\n\n"
        f"Категория: {data['cat_name']}\n"
        f"Район: {data['dist_name']}\n"
        f"Название: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Описание: {data['description']}\n"
        f"Адрес: {data['address']}\n"
        f"Соцсеть: {social}\n\n"
        "Всё верно?"
    )
    await message.answer(summary, reply_markup=confirm_keyboard())
    await state.set_state(RegisterStates.confirming)

@router.callback_query(F.data == "confirm_register")
async def reg_confirm(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    provider = await create_provider(
        tg_id=cb.from_user.id,
        tg_username=cb.from_user.username,
        name=data['name'],
        phone=data['phone'],
        category_id=data['category_id'],
        district_id=data['district_id'],
        description=data['description'],
        address=data['address'],
        social_link=data.get('social_link')
    )
    await state.clear()
    await cb.message.edit_text(
        "✅ Заявка отправлена!\n\n"
        "Модератор проверит данные в течение 24 часов.\n\n"
        "Управление вашими бизнесами: /mybiz"
    )
    await cb.message.answer("Главное меню:", reply_markup=main_menu())

    from aiogram import Bot
    from bot.keyboards import admin_provider_keyboard
    bot: Bot = cb.bot
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"Новая заявка — Кабарман\n\n"
                f"{data['cat_name']} — {data['dist_name']}\n"
                f"Название: {data['name']}\n"
                f"Телефон: {data['phone']}\n"
                f"Описание: {data['description']}\n"
                f"Адрес: {data['address']}\n"
                f"Соцсеть: {data.get('social_link') or 'нет'}\n"
                f"ID: {provider['id']}",
                reply_markup=admin_provider_keyboard(provider['id'])
            )
        except Exception:
            pass
    await cb.answer()

@router.callback_query(F.data == "restart_register")
async def reg_restart(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    cats = await get_categories()
    await cb.message.edit_text(
        "Начнём заново\n\n1 из 7 — Выберите категорию:",
        reply_markup=reg_categories_keyboard(cats)
    )
    await state.set_state(RegisterStates.choosing_category)
    await cb.answer()
