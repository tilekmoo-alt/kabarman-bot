from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import SearchStates
from bot.keyboards import (
    districts_keyboard, categories_keyboard,
    provider_result_keyboard, back_to_results_keyboard, main_menu
)
from db.queries import (
    get_districts, get_categories, get_district, get_category,
    search_providers, get_or_create_client, log_search
)

router = Router()

# ── Шаг 1: выбор района ───────────────────────────────────
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

# ── Шаг 2: выбор категории ────────────────────────────────
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

# ── Назад к районам ───────────────────────────────────────
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

# ── Результаты поиска ─────────────────────────────────────
@router.callback_query(F.data.startswith("sc:"))
async def search_results(cb: CallbackQuery, state: FSMContext):
    cat_id = int(cb.data.split(":")[1])
    data = await state.get_data()
    district_id   = data.get("district_id")
    district_name = data.get("district_name", "")

    cat      = await get_category(cat_id)
    results  = await search_providers(cat_id, district_id)

    client = await get_or_create_client(
        cb.from_user.id,
        cb.from_user.username,
        cb.from_user.full_name
    )
    await log_search(client['id'], cat_id, district_id, len(results))

    header = f"{cat['emoji']} *{cat['name']}* · 📍 {district_name}"

    if not results:
        await cb.message.edit_text(
            f"{header}\n\n"
            "😔 В этом районе по данной категории пока никто не зарегистрирован.\n\n"
            "💡 Вы можете сами зарегистрировать свой бизнес — это *бесплатно!*",
            parse_mode="Markdown",
            reply_markup=back_to_results_keyboard()
        )
        await cb.answer()
        return

    # Заголовок
    await cb.message.edit_text(
        f"{header}\n\n"
        f"✅ Найдено: *{len(results)}*",
        parse_mode="Markdown"
    )

    # Карточки
    for p in results:
        lines = [f"*{p['name']}*"]
        lines.append(f"📁 {p['cat_emoji']} {p['cat_name']} · 📍 {p['district_name']}")
        if p['description']:
            lines.append(f"📝 {p['description']}")
        if p['address']:
            lines.append(f"🏠 {p['address']}")
        lines.append(f"📞 {p['phone']}")

        await cb.message.answer(
            "\n".join(lines),
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
