from aiogram.types import ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

LISTING_CATS = [
    ('🚗', 'Транспорт'),
    ('🐄', 'Скот и животные'),
    ('🏠', 'Недвижимость'),
    ('📱', 'Электроника'),
    ('👗', 'Одежда и обувь'),
    ('🛋', 'Мебель и дом'),
    ('🌾', 'С/х и техника'),
    ('💼', 'Работа'),
    ('📦', 'Другое'),
]

# ── Главное меню ──────────────────────────────────────────
def main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📢 Подать объявление")
    kb.button(text="🔍 Поиск")
    kb.button(text="🛍 Объявления")
    kb.button(text="ℹ️ О Кабарман")
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)

# ── Выбор типа объявления ─────────────────────────────────
def post_choice_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 Продаю товар",       callback_data="post_listing")
    builder.button(text="🔧 Предлагаю услугу",    callback_data="post_service")
    builder.adjust(1)
    return builder.as_markup()

# ── Меню услуг ────────────────────────────────────────────
def services_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Найти по категории", callback_data="services_catalog")
    builder.button(text="🔎 Найти по слову",     callback_data="services_text")
    builder.adjust(1)
    return builder.as_markup()

# ── Просмотр объявлений: фильтры ──────────────────────────
def browse_categories_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Все категории", callback_data="bccat:all")
    for emoji, name in LISTING_CATS:
        builder.button(text=f"{emoji} {name}", callback_data=f"bccat:{name}")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

def browse_oblasts_keyboard(oblasts):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇰🇬 Вся страна", callback_data="bcob:all")
    for o in oblasts:
        builder.button(text=f"🗺 {o['name']}", callback_data=f"bcob:{o['id']}")
    builder.button(text="◀️ Назад", callback_data="bcob_back")
    builder.adjust(2)
    return builder.as_markup()

def browse_nav_keyboard(page: int, has_prev: bool, has_next: bool):
    builder = InlineKeyboardBuilder()
    row = []
    if has_prev:
        builder.button(text="◀️ Назад", callback_data=f"lb_nav:{page - 1}")
    builder.button(text=f"стр. {page}", callback_data="lb_noop")
    if has_next:
        builder.button(text="Далее ▶️", callback_data=f"lb_nav:{page + 1}")
    builder.button(text="🔄 Фильтр",      callback_data="listings_browse")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    cols = sum([has_prev, True, has_next])
    builder.adjust(cols, 2)
    return builder.as_markup()

# ── Объявления ────────────────────────────────────────────
def listing_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Смотреть объявления", callback_data="listings_browse")
    builder.button(text="📁 Мои объявления",       callback_data="listings_mine")
    builder.adjust(1)
    return builder.as_markup()

def listing_categories_keyboard():
    builder = InlineKeyboardBuilder()
    for emoji, name in LISTING_CATS:
        builder.button(text=f"{emoji} {name}", callback_data=f"lcat:{name}")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

def listing_photo_keyboard(count: int):
    builder = InlineKeyboardBuilder()
    if count > 0:
        builder.button(text=f"✅ Готово ({count} фото)", callback_data="lphoto_done")
    builder.button(text="⏭ Пропустить фото", callback_data="lphoto_skip")
    builder.adjust(1)
    return builder.as_markup()

def listing_price_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🤝 Договорная", callback_data="lprice_negotiable")
    builder.button(text="🆓 Бесплатно",  callback_data="lprice_free")
    builder.adjust(2)
    return builder.as_markup()

def listing_confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Опубликовать", callback_data="listing_confirm")
    builder.button(text="✏️ Начать заново", callback_data="listing_restart")
    builder.adjust(1)
    return builder.as_markup()

# ── Области ───────────────────────────────────────────────
def oblasts_keyboard(oblasts, action="so"):
    builder = InlineKeyboardBuilder()
    for o in oblasts:
        builder.button(text=f"🗺 {o['name']}", callback_data=f"{action}:{o['id']}")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

def reg_oblasts_keyboard(oblasts):
    return oblasts_keyboard(oblasts, action="ro")

# ── Районы ────────────────────────────────────────────────
def districts_keyboard(districts, action="sd"):
    builder = InlineKeyboardBuilder()
    for d in districts:
        builder.button(text=f"📍 {d['name']}", callback_data=f"{action}:{d['id']}")
    builder.button(text="◀️ Назад к областям", callback_data="back_oblasts_search")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(2)
    return builder.as_markup()

def reg_districts_keyboard(districts):
    builder = InlineKeyboardBuilder()
    for d in districts:
        builder.button(text=f"📍 {d['name']}", callback_data=f"rd:{d['id']}")
    builder.button(text="◀️ Назад к областям", callback_data="back_oblasts_reg")
    builder.adjust(2)
    return builder.as_markup()

# ── Категории ─────────────────────────────────────────────
def categories_keyboard(categories, action="sc"):
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=f"{cat['emoji']} {cat['name']}", callback_data=f"{action}:{cat['id']}")
    builder.button(text="◀️ Назад к районам", callback_data="back_districts_search")
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

# ── Карточка провайдера ───────────────────────────────────
def provider_result_keyboard(provider):
    builder = InlineKeyboardBuilder()

    wa_num = provider['phone'].replace('+', '').replace(' ', '').replace('-', '')
    builder.button(
        text="💬 WhatsApp",
        url=f"https://wa.me/{wa_num}?text=Здравствуйте%2C+нашёл+вас+через+Кабарман"
    )

    if provider.get('tg_username'):
        builder.button(text="✈️ Telegram", url=f"https://t.me/{provider['tg_username']}")

    if provider.get('social_link'):
        social = provider['social_link']
        if social.startswith('@'):
            url = f"https://instagram.com/{social[1:]}"
        elif social.startswith('http'):
            url = social
        else:
            url = f"https://instagram.com/{social}"
        builder.button(text="📸 Instagram", url=url)

    if provider.get('address'):
        addr_encoded = provider['address'].replace(' ', '+')
        builder.button(text="🗺 2GIS", url=f"https://2gis.kg/search/{addr_encoded}")
        builder.button(text="📍 Google Maps", url=f"https://www.google.com/maps/search/{addr_encoded}")

    builder.adjust(2)
    return builder.as_markup()

# ── Результаты поиска ─────────────────────────────────────
def back_to_results_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Новый поиск", callback_data="new_search")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()

# ── Подтверждение регистрации ─────────────────────────────
def confirm_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Всё верно, отправить", callback_data="confirm_register")
    builder.button(text="✏️ Начать заново", callback_data="restart_register")
    builder.adjust(1)
    return builder.as_markup()

# ── Пропустить шаг ────────────────────────────────────────
def skip_keyboard(skip_data="skip"):
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data=skip_data)
    builder.adjust(1)
    return builder.as_markup()

# ── Админ ─────────────────────────────────────────────────
def admin_provider_keyboard(provider_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить", callback_data=f"approve:{provider_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject:{provider_id}")
    builder.adjust(2)
    return builder.as_markup()

def remove_keyboard():
    return ReplyKeyboardRemove()
