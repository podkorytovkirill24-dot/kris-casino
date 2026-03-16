import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from app.config import load_config
from app.db import Database
from app.routers import common, games, payments, admin, withdrawals


async def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    config = load_config()
    db = Database(config.db_path)
    await db.init()

    bot = Bot(token=config.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(common.router)
    dp.include_router(games.router)
    dp.include_router(payments.router)
    dp.include_router(admin.router)
    dp.include_router(withdrawals.router)

    await dp.start_polling(bot, db=db, config=config)


if __name__ == "__main__":
    asyncio.run(main())
