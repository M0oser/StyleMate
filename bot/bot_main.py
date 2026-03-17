import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://rrsdx-5-228-131-139.a.free.pinggy.link")

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть StyleMate",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ]
        ]
    )

    try:
        await message.answer(
            "StyleMate запущен. Нажми кнопку ниже, чтобы открыть приложение.",
            reply_markup=keyboard
        )
    except TelegramNetworkError as e:
        logger.error(f"Сетевая ошибка при answer(): {e}")
    except Exception as e:
        logger.exception(f"Ошибка в /start: {e}")


async def main():
    if not BOT_TOKEN:
        logger.error(f"Токен не найден. Проверь {ENV_PATH}")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    dp.include_router(router)

    try:
        logger.info("Проверяю соединение с Telegram...")
        me = await bot.get_me()
        logger.info(f"Успешное подключение к Telegram API. Бот: @{me.username}")

        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception as e:
            logger.warning(f"delete_webhook пропущен: {e}")

        logger.info("Бот запущен и ждет сообщений.")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")