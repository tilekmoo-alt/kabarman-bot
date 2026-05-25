from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import SearchStates
from bot.keyboards import (
    districts_keyboard, categories_keyboard,
    provider_result_keyboard, back_to_results_keyboard
)
from db.queries import (
    get_districts, get_categories, get_district, get_category,
    search_providers, search_providers_by_text,
    get_or_create_client, log_search
)

router = Router()

# ── Поиск по категориям ───────────────────────────────────
@router.message(F.text == "🔍 Найти услугу")
async def search_start(msg: Message, state: FSMContext):
    await state.clear()
    districts = await get_districts()
    await msg.answer(
        "📍 *Шаг 1 из 2 — Выберите район:*",
        parse_mode="Markdown",
        reply_markup=districts_keyboard(districts, action="sd")
    )
    await state.set_state(SearchStates.choosing_district)

@router.callback_query(F.data.startswith("sd:"))
async def search_district_chosen(cb: CallbackQuery, state: FSMContext):
    district_id = int(cb.data.split(":")[1])
    district = await get_district(district_id)
    await state.update_data(district_id=district_id, district_name=district['name'])
    cats = await get_categories()
    await cb.message.edit_text(
        f"📍 Район: *{district['name']}*\n\n"
        f"📂 *Шаг 2 из 2 — Выберите категорию:*",
        parse_mode="Markdown",
        reply_markup=categories_keyboard(cats, action="sc")
    )
    await state.set_state(SearchStates.choosing_category)
    await cb.answer()

@router.callback_query(F.data == "back_districts_search")
async def back_districts(cb: CallbackQuery, state: FSMContext):
    districts = await get_districts()
    await cb.message.edit_text(
        "📍 *Шаг 1 из 2 — Выберите район:*",
        parse_mode="Markdown",
        reply_markup=districts_keyboard(districts, action="sd")
    )
    await state.set_state(SearchStates.choosing_district)
    await cb.answer()

@router.callback_query(F.data.startswith("sc:"))
async def search_results(cb: CallbackQuery, state: FSMContext):
    cat_id = int(cb.data.split(":")[1])
    data = await state.get_data()
    district_id   = data.get("district_id")
    district_name = data.get("district_name", "")

    cat = await get_category(cat_id)

    # Редирект на бота по недвижимости
    if cat.get('redirect_bot_url'):
        await cb.message.edit_text(
            f"🏠 *Недвижимость*\n\n"
            f"По вопросам купли-продажи и аренды недвижимости в Иссык-Кульской области "
            f"обращайтесь к нашему специализированному боту 👇",
            parse_mode="Markdown",
            reply_markup=__import__('aiogram.utils.keyboard', fromlist=['InlineKeyboardBuilder']).InlineKeyboardBuilder().button(
                text="🏠 Перейти в бот Недвижимости",
                url=cat['redirect_bot_url']
            ).as_markup()
        )
        await cb.answer()
        return

    results = await search_providers(cat_id, district_id)

    client = await get_or_create_client(
        cb.from_user.id, cb.from_user.username, cb.from_user.full_name
    )
    await log_search(client['id'], cat_id, district_id, len(results))

    if not results:
        await cb.message.edit_text(
            f"{cat['emoji']} *{cat['name']}* · 📍 {district_name}\n\n"
            "😔 В этом районе пока никто не зарегистрирован в данной категории.\n\n"
            "💡 Зарегистрируй свой бизнес — это *бесплатно!*",
            parse_mode="Markdown",
            reply_markup=back_to_results_keyboard()
        )
        await cb.answer()
        return

    await cb.message.edit_text(
        f"{cat['emoji']} *{cat['name']}* · 📍 {district_name}\n"
        f"✅ Найдено: *{len(results)}*",
        parse_mode="Markdown"
    )

    for p in results:
        await cb.message.answer(
            _format_card(p),
            parse_mode="Markdown",
            reply_markup=provider_result_keyboard(p)
        )

    await cb.message.answer(
        "👆 Нажмите *WhatsApp* чтобы написать напрямую",
        parse_mode="Markdown",
        reply_markup=back_to_results_keyboard()
    )
    await state.clear()
    await cb.answer()

# ── Поиск по тексту ───────────────────────────────────────
@router.message(F.text == "🔎 Поиск по слову")
async def text_search_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "🔎 *Поиск по слову*\n\n"
        "Напишите что ищете — название, категорию или район:\n\n"
        "_Например: сантехник, кафе, Чолпон-Ата, ремонт..._",
        parse_mode="Markdown"
    )
    await state.set_state(SearchStates.typing_query)

@router.message(SearchStates.typing_query)
async def text_search_results(msg: Message, state: FSMContext):
    query = msg.text.strip()
    if len(query) < 2:
        await msg.answer("⚠️ Введите минимум 2 символа")
        return

    results = await search_providers_by_text(query)

    client = await get_or_create_client(
        msg.from_user.id, msg.from_user.username, msg.from_user.full_name
    )
    await log_search(client['id'], None, None, len(results), query)

    if not results:
        await msg.answer(
            f"😔 По запросу *«{query}»* ничего не найдено.\n\n"
            "Попробуйте другое слово или выберите категорию через 🔍 *Найти услугу*",
            parse_mode="Markdown",
            reply_markup=back_to_results_keyboard()
        )
        await state.clear()
        return

    await msg.answer(
        f"🔎 По запросу *«{query}»* найдено: *{len(results)}*",
        parse_mode="Markdown"
    )

    for p in results:
        await msg.answer(
            _format_card(p),
            parse_mode="Markdown",
            reply_markup=provider_result_keyboard(p)
        )

    await msg.answer(
        "👆 Нажмите *WhatsApp* чтобы написать напрямую",
        parse_mode="Markdown",
        reply_markup=back_to_results_keyboard()
    )
    await state.clear()

@router.callback_query(F.data == "new_search")
async def back_to_cats(cb: CallbackQuery, state: FSMContext):
    districts = await get_districts()
    await cb.message.answer(
        "📍 *Шаг 1 из 2 — Выберите район:*",
        parse_mode="Markdown",
        reply_markup=districts_keyboard(districts, action="sd")
    )
    await state.set_state(SearchStates.choosing_district)
    await cb.answer()

# ── Форматирование карточки ───────────────────────────────
def _format_card(p) -> str:
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"{p['cat_emoji']} {p['name']}",
        f"📁 {p['cat_name']} · 📍 {p['district_name']}",
    ]
    if p.get('description'):
        lines.append(f"📝 {p['description']}")
    if p.get('address'):
        lines.append(f"🏠 {p['address']}")
    lines.append(f"📞 {p['phone']}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)
