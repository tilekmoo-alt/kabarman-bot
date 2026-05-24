from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔍 Найти услугу")
    kb.button(text="📋 Зарегистрировать бизнес")
    kb.button(text="ℹ️ О Кабарман")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)

def districts_keyboard(districts, action="sd"):
    """action prefix: sd=search_district, rd=reg_district"""
    builder = InlineKeyboardBuilder()
    for d in districts:
        builder.button(text=f"📍 {d['name']}", callback_data=f"{action}:{d['id']}")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

def categories_keyboard(categories, action="sc"):
    """action prefix: sc=search_cat, rc=reg_cat"""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=f"{cat['emoji']} {cat['name']}", callback_data=f"{action}:{cat['id']}")
    builder.button(text="◀️ Назад", callback_data="back_districts_search")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

def reg_categories_keyboard(categories):
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=f"{cat['emoji']} {cat['name']}", callback_data=f"rc:{cat['id']}")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

def provider_result_keyboard(provider):
    builder = InlineKeyboardBuilder()
    wa_num = provider['phone'].replace('+', '').replace(' ', '').replace('-', '')
    builder.button(
        text="💬 WhatsApp",
        url=f"https://wa.me/{wa_num}?text=Здравствуйте%2C+нашёл+вас+через+Кабарман"
    )
    if provider.get('tg_username'):
        builder.button(text="✈️ Telegram", url=f"https://t.me/{provider['tg_username']}")
    builder.adjust(2)
    return builder.as_markup()

def back_to_results_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Новый поиск", callback_data="new_search")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

def confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Всё верно, отправить", callback_data="confirm_register")
    builder.button(text="✏️ Начать заново", callback_data="restart_register")
    builder.adjust(1)
    return builder.as_markup()

def admin_provider_keyboard(provider_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить", callback_data=f"approve:{provider_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject:{provider_id}")
    builder.adjust(2)
    return builder.as_markup()

def remove_keyboard():
    return ReplyKeyboardRemove()
