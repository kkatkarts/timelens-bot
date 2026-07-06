# bot/handlers/start.py
"""
Обработчик команды /start и кнопки "Начать".
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.keyboards import get_start_keyboard, get_period_keyboard

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    welcome_text = (
        "👋 *Привет! Я TimeLens — твой личный аналитик времени.*\n\n"
        "Я помогу понять, на что уходят твои часы, анализируя календарь iCloud.\n\n"
        "🔐 *Как это работает:*\n"
        "• Подключаюсь к твоему iCloud Calendar\n"
        "• Группирую события по категориям (работа, спорт, учёба и т.д.)\n"
        "• Показываю красивую статистику\n\n"
        "⚙️ *Для начала нужно настроить доступ к календарю.*\n"
        "Это займёт 2 минуты."
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_start_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "start_onboarding")
async def process_start_button(callback: CallbackQuery):
    """Обработчик нажатия кнопки 'Начать'."""
    onboarding_text = (
        "🔑 *Настройка доступа к iCloud Calendar*\n\n"
        "Чтобы я мог анализировать твой календарь, нужны:\n"
        "1️⃣ Твой Apple ID (email)\n"
        "2️⃣ App-Specific Password (специальный пароль для бота)\n\n"
        "📝 *Как получить App-Specific Password:*\n"
        "1. Зайди на [appleid.apple.com](https://appleid.apple.com)\n"
        "2. Войди в аккаунт → «Безопасность»\n"
        "3. «App-Specific Passwords» → «Сгенерировать»\n"
        "4. Назови его «TimeLens» и скопируй пароль\n\n"
        "⚠️ *Этот пароль даёт доступ только к календарю, не ко всему аккаунту.*\n\n"
        "👇 *Введи свой Apple ID (email):*"
    )
    
    await callback.message.edit_text(
        onboarding_text,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    
    # TODO: Здесь будет переход в FSM-состояние ожидания email
    # Пока просто отвечаем, что приняли
    await callback.answer()