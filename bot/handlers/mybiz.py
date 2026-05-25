"""
Личный кабинет мастера — /mybiz
Показывает все бизнесы, позволяет удалить
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.queries import get_providers_by_tg, delete_provider
from bot.keyboards import main_menu

router = Router()

def my_biz_keyboard(providers):
    builder = InlineKeyboardBuilder()
    for p in providers:
        status = "✅" if p['is_approved'] else "⏳"
        builder.button(
            text=f"{status} {p['name']} · {p['district_name']}",
            callback_data=f"mybiz_view:{p['id']}"
        )
    builder.adjust(1)
    return builder.as_markup()

def biz_actions_keyboard(provider_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Удалить этот бизнес", callback_data=f"mybiz_delete:{provider_id}")
    builder.button(text="◀️ Назад к списку", callback_data="mybiz_list")
    builder.adjust(1)
    return builder.as_markup()

def confirm_delete_keyboard(provider_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"mybiz_confirm_delete:{provider_id}")
    builder.button(text="❌ Нет, отмена", callback_data=f"mybiz_view:{provider_id}")
    builder.adjust(2)
    return builder.as_markup()

@router.message(Command("mybiz"))
async def cmd_mybiz(msg: Message):
    await show_mybiz(msg, msg.from_user.id)

async def show_mybiz(message, tg_id: int, edit=False):
    providers = await get_providers_by_tg(tg_id)
    if not providers:
        text = (
            "📋 У вас пока нет зарегистрированных бизнесов.\n\n"
            "Нажмите *📋 Зарегистрировать бизнес* чтобы добавить."
        )
        if edit:
            await message.edit_text(text, parse_mode="Markdown")
        else:
            await message.answer(text, parse_mode="Markdown", reply_markup=main_menu())
        return

    text = f"📋 *Ваши бизнесы ({len(providers)}):*\n\n"
    for p in providers:
        status = "✅ Активен" if p['is_approved'] else "⏳ На проверке"
        text += f"• *{p['name']}* — {p['district_name']} — {status}\n"
    text += "\nВыберите бизнес для управления:"

    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=my_biz_keyboard(providers))
    else:
        await message.answer(text, parse_mode="Markdown", reply_markup=my_biz_keyboard(providers))

@router.callback_query(F.data == "mybiz_list")
async def cb_mybiz_list(cb: CallbackQuery):
    await show_mybiz(cb.message, cb.from_user.id, edit=True)
    await cb.answer()

@router.callback_query(F.data.startswith("mybiz_view:"))
async def cb_mybiz_view(cb: CallbackQuery):
    from db.queries import get_provider_by_id
    provider_id = int(cb.data.split(":")[1])
    p = await get_provider_by_id(provider_id)

    if not p or p['tg_id'] != cb.from_user.id:
        await cb.answer("⛔ Нет доступа", show_alert=True)
        return

    status = "✅ Активен" if p['is_approved'] else "⏳ На проверке"
    text = (
        f"*{p['name']}*\n"
        f"Статус: {status}\n"
        f"📞 {p['phone']}\n"
        f"📝 {p['description'] or '—'}\n"
        f"🏠 {p['address'] or '—'}\n"
        f"🔗 {p['social_link'] or '—'}"
    )
    await cb.message.edit_text(text, parse_mode="Markdown",
                                reply_markup=biz_actions_keyboard(provider_id))
    await cb.answer()

@router.callback_query(F.data.startswith("mybiz_delete:"))
async def cb_mybiz_delete(cb: CallbackQuery):
    provider_id = int(cb.data.split(":")[1])
    await cb.message.edit_text(
        "⚠️ *Вы уверены что хотите удалить этот бизнес?*\n\n"
        "Это действие нельзя отменить.",
        parse_mode="Markdown",
        reply_markup=confirm_delete_keyboard(provider_id)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("mybiz_confirm_delete:"))
async def cb_mybiz_confirm_delete(cb: CallbackQuery):
    provider_id = int(cb.data.split(":")[1])
    await delete_provider(provider_id, cb.from_user.id)
    await cb.message.edit_text("✅ Бизнес удалён.")
    await cb.message.answer(
        "Вы можете зарегистрировать новый бизнес через главное меню.",
        reply_markup=main_menu()
    )
    await cb.answer()
