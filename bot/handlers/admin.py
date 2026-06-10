import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

from bot.keyboards import admin_provider_keyboard, main_menu
from db.queries import (
    get_all_providers_admin, approve_provider,
    reject_provider, admin_delete_provider, get_stats,
    deactivate_listing, get_full_stats
)

router = Router()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x]

def is_admin(uid): return uid in ADMIN_IDS
def esc(text): return html.escape(str(text)) if text else ''

def admin_active_keyboard(provider_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Удалить", callback_data=f"admin_del:{provider_id}")
    builder.adjust(1)
    return builder.as_markup()

def confirm_admin_delete_keyboard(provider_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"admin_del_confirm:{provider_id}")
    builder.button(text="❌ Отмена", callback_data="admin_cancel")
    builder.adjust(2)
    return builder.as_markup()

def admin_panel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика",      callback_data="admin_stats")
    builder.button(text="⏳ Заявки",           callback_data="admin_pending_btn")
    builder.button(text="📋 Каталог услуг",    callback_data="admin_active_btn")
    builder.adjust(1)
    return builder.as_markup()

@router.message(Command("admin"))
async def admin_panel(msg: Message):
    if not is_admin(msg.from_user.id): return
    await msg.answer(
        "🛠 <b>Панель управления — Кабарман</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard()
    )

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True); return
    await cb.answer("⏳ Загружаю...")
    s = await get_full_stats()

    total = s["total_listings"]
    photo_pct = round(s["with_photo"] / total * 100) if total else 0

    cat_lines = "\n".join(
        f"  {r['category']}: <b>{r['cnt']}</b>"
        for r in s["by_category"]
    )
    oblast_lines = "\n".join(
        f"  📍 {esc(r['name'])}: <b>{r['cnt']}</b>"
        for r in s["by_oblast"]
    )

    text = (
        "📊 <b>Статистика Кабарман</b>\n\n"
        f"📢 <b>Объявлений:</b> {total}\n"
        f"  🌐 Сайт: {s['web_listings']}  |  🤖 Бот: {s['bot_listings']}\n"
        f"  📸 С фото: {s['with_photo']} ({photo_pct}%)\n\n"
        f"<b>По категориям:</b>\n{cat_lines}\n\n"
        f"<b>По регионам:</b>\n{oblast_lines}\n\n"
        f"🏢 <b>Услуги:</b> {s['total_providers']} активных"
        + (f"  |  ⏳ {s['pending']} на проверке" if s['pending'] else "") + "\n"
        f"👥 <b>Пользователей бота:</b> {s['bot_users']}"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data="admin_stats")
    builder.button(text="◀️ Назад",    callback_data="admin_back")
    builder.adjust(2)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

@router.callback_query(F.data == "admin_back")
async def cb_admin_back(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    await cb.message.edit_text(
        "🛠 <b>Панель управления — Кабарман</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard()
    )
    await cb.answer()

@router.callback_query(F.data == "admin_pending_btn")
async def cb_admin_pending_btn(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    await cb.answer()
    providers = await get_all_providers_admin(approved=False)
    if not providers:
        await cb.message.answer("✅ Нет заявок на проверку"); return
    for p in providers:
        await cb.message.answer(
            f"⏳ <b>Заявка #{p['id']}</b>\n"
            f"📁 {esc(p['cat_name'])} · 📍 {esc(p['district_name'])}\n"
            f"🏷️ {esc(p['name'])}\n"
            f"📞 {esc(p['phone'])}\n"
            f"📝 {esc(p.get('description',''))}",
            parse_mode="HTML",
            reply_markup=admin_provider_keyboard(p['id'])
        )

@router.callback_query(F.data == "admin_active_btn")
async def cb_admin_active_btn(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): return
    await cb.answer()
    providers = await get_all_providers_admin(approved=True)
    if not providers:
        await cb.message.answer("Каталог пуст"); return
    for p in providers:
        await cb.message.answer(
            f"✅ <b>#{p['id']} {esc(p['name'])}</b>\n"
            f"📁 {esc(p['cat_name'])} · 📍 {esc(p['district_name'])}\n"
            f"📞 {esc(p['phone'])}",
            parse_mode="HTML",
            reply_markup=admin_active_keyboard(p['id'])
        )

@router.message(Command("pending"))
async def admin_pending(msg: Message):
    if not is_admin(msg.from_user.id): return
    providers = await get_all_providers_admin(approved=False)
    if not providers:
        await msg.answer("✅ Нет заявок на проверку"); return
    for p in providers:
        await msg.answer(
            f"⏳ <b>Заявка #{p['id']}</b>\n"
            f"📁 {esc(p['cat_name'])} · 📍 {esc(p['district_name'])}\n"
            f"🏷️ {esc(p['name'])}\n"
            f"📞 {esc(p['phone'])}\n"
            f"📝 {esc(p.get('description',''))}\n"
            f"🏠 {esc(p.get('address',''))}",
            parse_mode="HTML",
            reply_markup=admin_provider_keyboard(p['id'])
        )

@router.message(Command("active"))
async def admin_active(msg: Message):
    if not is_admin(msg.from_user.id): return
    providers = await get_all_providers_admin(approved=True)
    if not providers:
        await msg.answer("Каталог пуст"); return
    for p in providers:
        await msg.answer(
            f"✅ <b>#{p['id']} {esc(p['name'])}</b>\n"
            f"📁 {esc(p['cat_name'])} · 📍 {esc(p['district_name'])}\n"
            f"📞 {esc(p['phone'])}",
            parse_mode="HTML",
            reply_markup=admin_active_keyboard(p['id'])
        )

@router.callback_query(F.data.startswith("approve:"))
async def cb_approve(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True); return
    provider_id = int(cb.data.split(":")[1])
    await approve_provider(provider_id)
    await cb.message.edit_text(
        cb.message.text + "\n\n✅ ОДОБРЕНО"
    )
    from db.database import get_pool
    p = await (await get_pool()).fetchrow("SELECT * FROM providers WHERE id=$1", provider_id)
    if p and p['tg_id'] and p['tg_id'] != 0:
        try:
            await cb.bot.send_message(
                p['tg_id'],
                f"🎉 Ваш бизнес одобрен!\n\n"
                f"{esc(p['name'])} теперь виден всем в Кабарман 📣\n\n"
                f"Управление: /mybiz"
            )
        except Exception: pass
    await cb.answer("✅ Одобрено!")

@router.callback_query(F.data.startswith("reject:"))
async def cb_reject(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True); return
    provider_id = int(cb.data.split(":")[1])
    await reject_provider(provider_id)
    await cb.message.edit_text(cb.message.text + "\n\n❌ ОТКЛОНЕНО")
    from db.database import get_pool
    p = await (await get_pool()).fetchrow("SELECT * FROM providers WHERE id=$1", provider_id)
    if p and p['tg_id'] and p['tg_id'] != 0:
        try:
            await cb.bot.send_message(p['tg_id'],
                "❌ Ваша заявка отклонена.\nПо вопросам: @kabarman_admin")
        except Exception: pass
    await cb.answer("❌ Отклонено")

@router.callback_query(F.data.startswith("admin_del:"))
async def cb_admin_del(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True); return
    provider_id = int(cb.data.split(":")[1])
    await cb.message.answer(
        f"⚠️ Удалить бизнес #{provider_id}?",
        reply_markup=confirm_admin_delete_keyboard(provider_id)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("admin_del_confirm:"))
async def cb_admin_del_confirm(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True); return
    provider_id = int(cb.data.split(":")[1])
    await admin_delete_provider(provider_id)
    await cb.message.edit_text(f"🗑 Бизнес #{provider_id} удалён.")
    await cb.answer("Удалено")

@router.callback_query(F.data == "admin_cancel")
async def cb_admin_cancel(cb: CallbackQuery):
    await cb.message.delete()
    await cb.answer("Отменено")

# ── Удалить объявление (из уведомления или жалобы) ────────
@router.callback_query(F.data.startswith("del_listing:"))
async def cb_del_listing(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True); return
    listing_id = int(cb.data.split(":")[1])
    await deactivate_listing(listing_id, tg_id=None)
    await cb.message.edit_text(cb.message.text + "\n\n🗑 УДАЛЕНО")
    await cb.answer("Объявление удалено")

# ── Удалить бизнес (из уведомления или жалобы) ────────────
@router.callback_query(F.data.startswith("del_provider:"))
async def cb_del_provider(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True); return
    provider_id = int(cb.data.split(":")[1])
    await admin_delete_provider(provider_id)
    await cb.message.edit_text(cb.message.text + "\n\n🗑 УДАЛЕНО")
    await cb.answer("Бизнес удалён")
