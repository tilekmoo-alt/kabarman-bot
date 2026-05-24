from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import os

from bot.keyboards import admin_provider_keyboard, main_menu
from db.queries import get_all_providers_admin, approve_provider, reject_provider, get_stats

router = Router()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x]

def is_admin(uid): return uid in ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(msg: Message):
    if not is_admin(msg.from_user.id): return
    providers, pending, clients, searches, by_district = await get_stats()

    district_lines = "\n".join(
        f"  📍 {r['name']}: *{r['cnt']}*" for r in by_district
    )
    await msg.answer(
        "🛠 *Панель — Кабарман*\n\n"
        f"✅ Активных в каталоге: *{providers}*\n"
        f"⏳ Ожидают проверки: *{pending}*\n"
        f"👥 Клиентов в боте: *{clients}*\n"
        f"🔍 Всего поисков: *{searches}*\n\n"
        f"По районам:\n{district_lines}\n\n"
        "Команды:\n"
        "/pending — заявки на проверку\n"
        "/active — активный каталог",
        parse_mode="Markdown"
    )

@router.message(Command("pending"))
async def admin_pending(msg: Message):
    if not is_admin(msg.from_user.id): return
    providers = await get_all_providers_admin(approved=False)
    if not providers:
        await msg.answer("✅ Нет заявок на проверку"); return
    for p in providers:
        await msg.answer(
            f"⏳ *Заявка #{p['id']}*\n"
            f"📁 {p['cat_name']} · 📍 {p['district_name']}\n"
            f"🏷️ {p['name']}\n"
            f"📞 {p['phone']}\n"
            f"📝 {p['description']}\n"
            f"🏠 {p['address']}",
            parse_mode="Markdown",
            reply_markup=admin_provider_keyboard(p['id'])
        )

@router.message(Command("active"))
async def admin_active(msg: Message):
    if not is_admin(msg.from_user.id): return
    providers = await get_all_providers_admin(approved=True)
    if not providers:
        await msg.answer("Каталог пуст"); return
    text = f"✅ *Активных: {len(providers)}*\n\n"
    for p in providers:
        text += f"• {p['name']} | {p['cat_name']} | 📍{p['district_name']} | {p['phone']}\n"
    await msg.answer(text, parse_mode="Markdown")

@router.callback_query(F.data.startswith("approve:"))
async def cb_approve(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True); return
    provider_id = int(cb.data.split(":")[1])
    await approve_provider(provider_id)
    await cb.message.edit_text(cb.message.text + "\n\n✅ *ОДОБРЕНО*", parse_mode="Markdown")

    from db.database import get_pool
    pool = await get_pool()
    p = await pool.fetchrow("SELECT * FROM providers WHERE id=$1", provider_id)
    if p:
        try:
            await cb.bot.send_message(
                p['tg_id'],
                "🎉 *Ваша заявка одобрена!*\n\n"
                f"*{p['name']}* теперь виден всем пользователям Кабарман.\n"
                "Клиенты смогут найти вас через поиск по вашему району 📍",
                parse_mode="Markdown"
            )
        except Exception: pass
    await cb.answer("✅ Одобрено!")

@router.callback_query(F.data.startswith("reject:"))
async def cb_reject(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("⛔ Нет доступа", show_alert=True); return
    provider_id = int(cb.data.split(":")[1])
    await reject_provider(provider_id)
    await cb.message.edit_text(cb.message.text + "\n\n❌ *ОТКЛОНЕНО*", parse_mode="Markdown")

    from db.database import get_pool
    pool = await get_pool()
    p = await pool.fetchrow("SELECT * FROM providers WHERE id=$1", provider_id)
    if p:
        try:
            await cb.bot.send_message(
                p['tg_id'],
                "❌ К сожалению, ваша заявка была отклонена.\n"
                "По вопросам: @kabarman_admin"
            )
        except Exception: pass
    await cb.answer("❌ Отклонено")
