import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import SearchStates
from bot.keyboards import (
    oblasts_keyboard, districts_keyboard, categories_keyboard,
    provider_result_keyboard, back_to_results_keyboard
)
from db.queries import (
    get_oblasts, get_oblast, get_districts_by_oblast, get_districts,
    get_categories, get_district, get_category,
    search_providers, search_providers_by_text,
    get_or_create_client, log_search
)

router = Router()

def esc(text): return html.escape(str(text)) if text else ''

# ── Поиск: шаг 1 — область ───────────────────────────────
@router.callback_query(F.data == "services_catalog")
async def search_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    oblasts = await get_oblasts()
    await cb.message.edit_text(
        "🗺 <b>Шаг 1 из 3 — Выберите область:</b>",
        parse_mode="HTML",
        reply_markup=oblasts_keyboard(oblasts, action="so")
    )
    await state.set_state(SearchStates.choosing_oblast)
    await cb.answer()

@router.callback_query(F.data.startswith("so:"))
async def search_oblast_chosen(cb: CallbackQuery, state: FSMContext):
    oblast_id = int(cb.data.split(":")[1])
    oblast = await get_oblast(oblast_id)
    await state.update_data(oblast_id=oblast_id, oblast_name=oblast['name'])
    districts = await get_districts_by_oblast(oblast_id)
    await cb.message.edit_text(
        f"🗺 Область: <b>{esc(oblast['name'])}</b>\n\n"
        f"📍 <b>Шаг 2 из 3 — Выберите район:</b>",
        parse_mode="HTML",
        reply_markup=districts_keyboard(districts, action="sd")
    )
    await state.set_state(SearchStates.choosing_district)
    await cb.answer()

@router.callback_query(F.data == "back_oblasts_search")
async def back_oblasts_search(cb: CallbackQuery, state: FSMContext):
    oblasts = await get_oblasts()
    await cb.message.edit_text(
        "🗺 <b>Шаг 1 из 3 — Выберите область:</b>",
        parse_mode="HTML",
        reply_markup=oblasts_keyboard(oblasts, action="so")
    )
    await state.set_state(SearchStates.choosing_oblast)
    await cb.answer()

@router.callback_query(F.data.startswith("sd:"))
async def search_district_chosen(cb: CallbackQuery, state: FSMContext):
    district_id = int(cb.data.split(":")[1])
    district = await get_district(district_id)
    await state.update_data(district_id=district_id, district_name=district['name'])
    cats = await get_categories()
    data = await state.get_data()
    await cb.message.edit_text(
        f"🗺 {esc(data.get('oblast_name',''))} · 📍 <b>{esc(district['name'])}</b>\n\n"
        f"📂 <b>Шаг 3 из 3 — Выберите категорию:</b>",
        parse_mode="HTML",
        reply_markup=categories_keyboard(cats, action="sc")
    )
    await state.set_state(SearchStates.choosing_category)
    await cb.answer()

@router.callback_query(F.data == "back_districts_search")
async def back_districts(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    oblast_id = data.get('oblast_id')
    oblast_name = data.get('oblast_name', '')
    if oblast_id:
        districts = await get_districts_by_oblast(oblast_id)
    else:
        districts = await get_districts()
    await cb.message.edit_text(
        f"🗺 <b>{esc(oblast_name)}</b>\n\n📍 <b>Выберите район:</b>" if oblast_name
        else "📍 <b>Выберите район:</b>",
        parse_mode="HTML",
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

    if cat.get('redirect_bot_url'):
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="🏠 Перейти в бот Недвижимости", url=cat['redirect_bot_url'])
        await cb.message.edit_text(
            "🏠 <b>Недвижимость</b>\n\n"
            "По вопросам недвижимости обращайтесь к нашему специализированному боту 👇",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
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
            f"{esc(cat['emoji'])} <b>{esc(cat['name'])}</b> · 📍 {esc(district_name)}\n\n"
            "😔 В этом районе пока никто не зарегистрирован.\n\n"
            "💡 Зарегистрируй свой бизнес — это <b>бесплатно!</b>",
            parse_mode="HTML",
            reply_markup=back_to_results_keyboard()
        )
        await cb.answer()
        return

    await cb.message.edit_text(
        f"{esc(cat['emoji'])} <b>{esc(cat['name'])}</b> · 📍 {esc(district_name)}\n"
        f"✅ Найдено: <b>{len(results)}</b>",
        parse_mode="HTML"
    )
    for p in results:
        await cb.message.answer(_format_card(p), parse_mode="HTML",
                                reply_markup=provider_result_keyboard(p))
    await cb.message.answer(
        "👆 Нажмите <b>WhatsApp</b> чтобы написать напрямую",
        parse_mode="HTML", reply_markup=back_to_results_keyboard()
    )
    await state.clear()
    await cb.answer()

# ── Поиск по тексту ───────────────────────────────────────
@router.callback_query(F.data == "services_text")
async def text_search_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        "🔎 <b>Поиск по слову</b>\n\n"
        "Напишите что ищете — название, категорию или город:\n\n"
        "<i>Например: сантехник, кафе, Бишкек, ремонт...</i>",
        parse_mode="HTML"
    )
    await state.set_state(SearchStates.typing_query)
    await cb.answer()

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
            f"😔 По запросу <b>«{esc(query)}»</b> ничего не найдено.\n\n"
            "Попробуйте другое слово или 🔍 <b>Найти услугу</b>",
            parse_mode="HTML", reply_markup=back_to_results_keyboard()
        )
        await state.clear()
        return

    await msg.answer(
        f"🔎 По запросу <b>«{esc(query)}»</b> найдено: <b>{len(results)}</b>",
        parse_mode="HTML"
    )
    for p in results:
        await msg.answer(_format_card(p), parse_mode="HTML",
                         reply_markup=provider_result_keyboard(p))
    await msg.answer(
        "👆 Нажмите <b>WhatsApp</b> чтобы написать напрямую",
        parse_mode="HTML", reply_markup=back_to_results_keyboard()
    )
    await state.clear()

@router.callback_query(F.data == "new_search")
async def new_search(cb: CallbackQuery, state: FSMContext):
    oblasts = await get_oblasts()
    await cb.message.answer(
        "🗺 <b>Шаг 1 из 3 — Выберите область:</b>",
        parse_mode="HTML",
        reply_markup=oblasts_keyboard(oblasts, action="so")
    )
    await state.set_state(SearchStates.choosing_oblast)
    await cb.answer()

# ── Карточка (HTML-safe) ──────────────────────────────────
def _format_card(p) -> str:
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"{esc(p['cat_emoji'])} <b>{esc(p['name'])}</b>",
        f"📁 {esc(p['cat_name'])} · 📍 {esc(p['district_name'])}",
    ]
    if p.get('description'):
        lines.append(f"📝 {esc(p['description'])}")
    if p.get('address'):
        lines.append(f"🏠 {esc(p['address'])}")
    lines.append(f"📞 {esc(p['phone'])}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)
