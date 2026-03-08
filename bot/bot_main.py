import asyncio
import logging
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

# Настройка логирования, чтобы видеть статусы в консоли
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализируем роутер
router = Router()


# Обработчик команды /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        f"Привет, {message.from_user.first_name}! 👔👗\n\n"
        f"Я — <b>StyleMate</b>, твой умный виртуальный стилист.\n"
        f"Здесь ты можешь оцифровать свой гардероб, а я помогу тебе собрать идеальный лук для любого повода.\n\n"
        f"Нажми кнопку ниже, чтобы открыть приложение!"
    )

    # Заглушка для Web App (потом замените на ваш боевой домен)
    web_app_info = WebAppInfo(url="https://iadbc-5-228-131-139.a.free.pinggy.link")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ Открыть гардероб", web_app=web_app_info)]
        ]
    )

    # Отправляем сообщение
    await message.answer(
        text=welcome_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


# Основная функция запуска
async def main():
    # Загружаем токен из файла .env
    load_dotenv()
    bot_token = os.getenv('BOT_TOKEN')

    if not bot_token:
        logger.error("Токен не найден! Проверь файл .env")
        return

    # Инициализация бота и диспетчера
    bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Бот успешно запущен и ждет сообщений!")

    # Запуск опроса серверов Telegram
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот выключен пользователем.")