# bot/main.py
"""
Точка входа Telegram-бота TimeLens.
Запускает polling (бот опрашивает Telegram о новых сообщениях).
"""
import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Загружаем .env
load_dotenv()

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота."""
    # Получаем токен из .env
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("❌ BOT_TOKEN не найден в .env")
        return
    
    # Инициализируем бота и диспетчер
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()
    
    # Импортируем и регистрируем роутеры (обработчики команд)
    from bot.handlers import start
    dp.include_router(start.router)
    
    logger.info("🚀 Бот запущен. Ожидаю сообщения...")
    
    # Запускаем polling (бесконечный цикл опроса Telegram)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Бот остановлен пользователем")