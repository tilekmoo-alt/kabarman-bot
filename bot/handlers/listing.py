import html
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import ListingStates
from bot.keyboards import (
    listing_menu, listing_categories_keyboard, listing_photo_keyboard,
    listing_price_keyboard, listing_confirm_keyboard,
    oblasts_keyboard, reg_districts_keyboard, main_menu
)
from db.queries import (
    get_oblasts, get_oblast, get_districts_by_oblast, get_district,
    create_listing, get_listings, get_listings_by_tg, deactivate_listing
)

router = Router()

def esc(text): return html.escape(str(text)) if text else ''

# ── Вход в раздел объявлений ──────────────────────────────
@router.message(F.text == "🛍 Объявления")
async def listings_menu(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "🛍 <b>Объявления Кабарман</b>\n\n"
        "Купля-продажа, аренда, скот, транспорт и многое другое",
        parse_mode="HTML",
        reply_markup=listing_menu()
    )

# ── Подать объявление прямо из главного меню ──────────────
@router.message(F.text == "📢 Подать объявление")
async def listing_new_from_menu(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "➕ <b>Новое объявление</b>\n\n"
        "Шаг 1 из 7 — Выберите категорию:",
        parse_mode="HTML",
        reply_markup=listing_categories_keyboard()
    )
    await state.set_state(ListingStates.choosing_category)

# ── Смотреть объявления ───────────────────────────────────
@router.callback_query(F.data == "listings_browse")
async def browse_listings(cb: CallbackQuery, state: FSMContext):
    listings = await get_listings(limit=10)
    if not listings:
        await cb.message.edit_text(
            "😔 Объявлений пока нет.\n\nБудьте первым!",
            reply_markup=listing_menu()
        )
        await cb.answer()
        return

    await cb.message.edit_text(
        f"📋 <b>Последние объявления ({len(listings)})</b>",
        parse_mode="HTML"
    )
    for l in listings:
        price_str = (
            f"{l['price']:,} сом".replace(',', ' ') if l['price'] and not l['is_negotiable']
            else ("Бесплатно" if l['price'] == 0 else "Договорная")
        )
        photos_str = f"📸 {len(l['photos'])} фото\n" if l['photos'] else ""
        location = f"📍 {esc(l['district_name'] or l['oblast_name'] or '')}\n" if (l.get('district_name') or l.get('oblast_name')) else ""
        text = (
            f"<b>{esc(l['title'])}</b>\n"
            f"🏷 {esc(l['category'])} · 💰 {price_str}\n"
            f"{location}"
            f"{photos_str}"
            f"📞 {esc(l['contact_phone'])}"
        )
        await cb.message.answer(text, parse_mode="HTML")

    await cb.answer()

# ── Мои объявления ────────────────────────────────────────
@router.callback_query(F.data == "listings_mine")
async def my_listings(cb: CallbackQuery):
    listings = await get_listings_by_tg(cb.from_user.id)
    if not listings:
        await cb.message.edit_text(
            "У вас нет активных объявлений.",
            reply_markup=listing_menu()
        )
        await cb.answer()
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for l in listings:
        builder.button(
            text=f"{'✅' if l['is_active'] else '❌'} {l['title'][:30]}",
            callback_data=f"lmine:{l['id']}"
        )
    builder.button(text="◀️ Назад", callback_data="listings_menu_back")
    builder.adjust(1)

    await cb.message.edit_text(
        f"📁 <b>Мои объявления ({len(listings)})</b>",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data.startswith("lmine:"))
async def view_my_listing(cb: CallbackQuery):
    listing_id = int(cb.data.split(":")[1])
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Удалить объявление", callback_data=f"ldel:{listing_id}")
    builder.button(text="◀️ Назад",             callback_data="listings_mine")
    builder.adjust(1)
    await cb.message.edit_text(
        f"Объявление #{listing_id}\n\nВыберите действие:",
        reply_markup=builder.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data.startswith("ldel:"))
async def delete_my_listing(cb: CallbackQuery):
    listing_id = int(cb.data.split(":")[1])
    await deactivate_listing(listing_id, cb.from_user.id)
    await cb.message.edit_text("✅ Объявление удалено.", reply_markup=listing_menu())
    await cb.answer()

@router.callback_query(F.data == "listings_menu_back")
async def back_to_listing_menu(cb: CallbackQuery):
    await cb.message.edit_text(
        "📢 <b>Объявления Кабарман</b>",
        parse_mode="HTML",
        reply_markup=listing_menu()
    )
    await cb.answer()

# ── Подать объявление — шаги ──────────────────────────────
@router.callback_query(F.data == "listings_new")
@router.callback_query(F.data == "listing_restart")
async def new_listing_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        "➕ <b>Новое объявление</b>\n\n"
        "Шаг 1 из 7 — Выберите категорию:",
        parse_mode="HTML",
        reply_markup=listing_categories_keyboard()
    )
    await state.set_state(ListingStates.choosing_category)
    await cb.answer()

@router.callback_query(F.data.startswith("lcat:"))
async def listing_category(cb: CallbackQuery, state: FSMContext):
    category = cb.data.split(":", 1)[1]
    await state.update_data(category=category)
    oblasts = await get_oblasts()
    await cb.message.edit_text(
        f"Категория: <b>{esc(category)}</b> ✅\n\n"
        "Шаг 2 из 7 — Выберите область:",
        parse_mode="HTML",
        reply_markup=oblasts_keyboard(oblasts, action="lo")
    )
    await state.set_state(ListingStates.choosing_oblast)
    await cb.answer()

@router.callback_query(F.data.startswith("lo:"))
async def listing_oblast(cb: CallbackQuery, state: FSMContext):
    oblast_id = int(cb.data.split(":")[1])
    oblast = await get_oblast(oblast_id)
    await state.update_data(oblast_id=oblast_id, oblast_name=oblast['name'])
    districts = await get_districts_by_oblast(oblast_id)
    data = await state.get_data()
    await cb.message.edit_text(
        f"Категория: <b>{esc(data['category'])}</b> ✅\n"
        f"Область: <b>{esc(oblast['name'])}</b> ✅\n\n"
        "Шаг 3 из 7 — Выберите район:",
        parse_mode="HTML",
        reply_markup=reg_districts_keyboard(districts)
    )
    await state.set_state(ListingStates.choosing_district)
    await cb.answer()

@router.callback_query(F.data.startswith("rd:"), ListingStates.choosing_district)
async def listing_district(cb: CallbackQuery, state: FSMContext):
    dist_id = int(cb.data.split(":")[1])
    dist = await get_district(dist_id)
    await state.update_data(district_id=dist_id, district_name=dist['name'])
    await cb.message.edit_text(
        "Шаг 4 из 7 — Введите заголовок объявления:\n\n"
        "Например: <i>Продам Toyota Camry 2018</i>",
        parse_mode="HTML"
    )
    await state.set_state(ListingStates.entering_title)
    await cb.answer()

@router.message(ListingStates.entering_title)
async def listing_title(msg: Message, state: FSMContext):
    if len(msg.text.strip()) < 3:
        await msg.answer("Заголовок слишком короткий. Попробуйте ещё раз:")
        return
    await state.update_data(title=msg.text.strip())
    await msg.answer(
        "Шаг 5 из 7 — Опишите товар или услугу подробнее:\n\n"
        "Укажите состояние, характеристики, причину продажи..."
    )
    await state.set_state(ListingStates.entering_desc)

@router.message(ListingStates.entering_desc)
async def listing_desc(msg: Message, state: FSMContext):
    await state.update_data(description=msg.text.strip())
    await msg.answer(
        "Шаг 6 из 7 — Укажите цену (в сомах):\n\n"
        "Или нажмите кнопку ниже:",
        reply_markup=listing_price_keyboard()
    )
    await state.set_state(ListingStates.entering_price)

@router.message(ListingStates.entering_price)
async def listing_price_text(msg: Message, state: FSMContext):
    text = msg.text.strip().replace(' ', '').replace(',', '')
    if not text.isdigit():
        await msg.answer("Введите число (цену в сомах) или нажмите кнопку:",
                         reply_markup=listing_price_keyboard())
        return
    await state.update_data(price=int(text), is_negotiable=False)
    await _ask_photos(msg, state)

@router.callback_query(F.data == "lprice_negotiable")
async def listing_price_negotiable(cb: CallbackQuery, state: FSMContext):
    await state.update_data(price=None, is_negotiable=True)
    await cb.message.edit_text("Цена: Договорная ✅")
    await _ask_photos(cb.message, state)
    await cb.answer()

@router.callback_query(F.data == "lprice_free")
async def listing_price_free(cb: CallbackQuery, state: FSMContext):
    await state.update_data(price=0, is_negotiable=False)
    await cb.message.edit_text("Цена: Бесплатно ✅")
    await _ask_photos(cb.message, state)
    await cb.answer()

async def _ask_photos(message: Message, state: FSMContext):
    await message.answer(
        "Шаг 7 из 7 — Отправьте фото (до 5 штук)\n\n"
        "Отправляйте по одному. Когда закончите — нажмите <b>Готово</b>.",
        parse_mode="HTML",
        reply_markup=listing_photo_keyboard(0)
    )
    await state.update_data(photos=[])
    await state.set_state(ListingStates.uploading_photos)

@router.message(ListingStates.uploading_photos, F.photo)
async def listing_photo(msg: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])
    if len(photos) >= 5:
        await msg.answer("Максимум 5 фото. Нажмите Готово.",
                         reply_markup=listing_photo_keyboard(len(photos)))
        return

    bot: Bot = msg.bot
    file = await bot.get_file(msg.photo[-1].file_id)
    bio = await bot.download_file(file.file_path)

    try:
        from bot.utils.r2 import upload_photo
        url = await upload_photo(bio.read())
        photos.append(url)
        await state.update_data(photos=photos)
        await msg.answer(
            f"📸 Фото {len(photos)} загружено ✅",
            reply_markup=listing_photo_keyboard(len(photos))
        )
    except Exception as e:
        await msg.answer(
            "⚠️ Не удалось загрузить фото. Попробуйте ещё раз или пропустите.",
            reply_markup=listing_photo_keyboard(len(photos))
        )

@router.callback_query(F.data.in_({"lphoto_done", "lphoto_skip"}))
async def listing_photos_done(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "Введите ваш контактный телефон:\n\n"
        "Например: +996 700 123 456"
    )
    await state.set_state(ListingStates.entering_contact)
    await cb.answer()

@router.message(ListingStates.entering_contact)
async def listing_contact(msg: Message, state: FSMContext):
    phone = msg.text.strip()
    if len(phone) < 9:
        await msg.answer("Введите корректный номер телефона:")
        return
    await state.update_data(
        contact_phone=phone,
        contact_name=msg.from_user.full_name,
        tg_username=msg.from_user.username
    )
    await _show_listing_confirm(msg, state)

async def _show_listing_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    price_str = (
        f"{data['price']:,} сом".replace(',', ' ') if data.get('price') and not data.get('is_negotiable')
        else ("Бесплатно" if data.get('price') == 0 else "Договорная")
    )
    photos_count = len(data.get('photos', []))
    text = (
        "Проверьте объявление:\n\n"
        f"📌 {data['title']}\n"
        f"🏷 {data['category']}\n"
        f"📍 {data.get('oblast_name','')} · {data.get('district_name','')}\n"
        f"💰 {price_str}\n"
        f"📸 Фото: {photos_count}\n"
        f"📝 {data.get('description','')[:100]}...\n"
        f"📞 {data['contact_phone']}\n\n"
        "Всё верно?"
    )
    await message.answer(text, reply_markup=listing_confirm_keyboard())
    await state.set_state(ListingStates.confirming)

@router.callback_query(F.data == "listing_confirm")
async def listing_publish(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await create_listing(
        title=data['title'],
        description=data.get('description'),
        price=data.get('price'),
        is_negotiable=data.get('is_negotiable', False),
        photos=data.get('photos', []),
        category=data['category'],
        oblast_id=data.get('oblast_id'),
        district_id=data.get('district_id'),
        contact_name=data.get('contact_name'),
        contact_phone=data['contact_phone'],
        tg_username=data.get('tg_username'),
        tg_id=cb.from_user.id,
        source='bot'
    )
    await state.clear()
    await cb.message.edit_text(
        "✅ Объявление опубликовано!\n\n"
        "Оно будет активно 30 дней.\n"
        "Управление: /mylistings"
    )
    await cb.message.answer("Главное меню:", reply_markup=main_menu())
    await cb.answer()
