import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from db.database import setup_db
from bot.handlers import start, search, register, admin, mybiz, listing

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BOT_TOKEN    = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL", "").rstrip("/")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
PORT         = int(os.getenv("PORT", 8080))


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(search.router)
    dp.include_router(register.router)
    dp.include_router(listing.router)
    dp.include_router(mybiz.router)
    dp.include_router(admin.router)
    return dp


# ── Webhook режим (Railway / production) ──────────────────
def run_webhook(bot: Bot, dp: Dispatcher):
    webhook_url = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

    async def on_startup(_):
        await setup_db()
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        logging.info(f"✅ Webhook: {webhook_url}")

    async def on_shutdown(_):
        await bot.delete_webhook()

    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    logging.info(f"🚀 Кабарман бот (webhook) на порту {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)


# ── Polling режим (локальная разработка) ──────────────────
async def run_polling(bot: Bot, dp: Dispatcher):
    await setup_db()
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("🚀 Кабарман бот (polling)")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp  = build_dispatcher()

    if WEBHOOK_HOST:
        run_webhook(bot, dp)
    else:
        asyncio.run(run_polling(bot, dp))
