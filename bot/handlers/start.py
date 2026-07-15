# bot/handlers/start.py
"""
Обработчик команды /start.
Проверяет наличие пользователя в БД и показывает соответствующее меню.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards import get_start_keyboard
from core.database import user_exists

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))  # Убрали StateFilter(None) — работает в ЛЮБОМ состоянии
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    telegram_id = message.from_user.id
    logger.info(f"📩 Получен /start от пользователя {telegram_id}")
    
    # Очищаем состояние (на случай, если было что-то незавершённое)
    await state.clear()
    
    # Проверяем, есть ли пользователь в БД
    exists = await user_exists(telegram_id)
    
    if exists:
        # Существующий пользователь
        logger.info(f"✅ Пользователь {telegram_id} найден в БД")
        await show_existing_user_menu(message)
    else:
        # Новый пользователь
        logger.info(f"🆕 Пользователь {telegram_id} не найден в БД — показываем онбординг")
        await show_new_user_welcome(message)


async def show_new_user_welcome(message: Message):
    """Показывает приветствие для нового пользователя."""
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


async def show_existing_user_menu(message: Message):
    """Показывает меню для существующего пользователя."""
    menu_text = (
        "✅ *Привет! Рад видеть тебя снова.*\n\n"
        "Твои ключи уже настроены и зашифрованы.\n\n"
        "👇 *Что хочешь сделать?*"
    )
    
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Получить статистику", callback_data="show_stats")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="show_settings")],
        [InlineKeyboardButton(text="🔑 Изменить ключи", callback_data="settings_edit_keys")]
    ])
    
    await message.answer(
        menu_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def edit_existing_user_menu(message: Message):
    """Редактирует сообщение с меню для существующего пользователя (для callback)."""
    menu_text = (
        "✅ *Привет! Рад видеть тебя снова.*\n\n"
        "Твои ключи уже настроены и зашифрованы.\n\n"
        "👇 *Что хочешь сделать?*"
    )
    
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Получить статистику", callback_data="show_stats")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="show_settings")],
        [InlineKeyboardButton(text="🔑 Изменить ключи", callback_data="settings_edit_keys")]
    ])
    
    await message.edit_text(
        menu_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def edit_new_user_welcome(message: Message):
    """Редактирует приветственное сообщение для нового пользователя (для callback)."""
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
    
    from bot.keyboards import get_start_keyboard
    await message.edit_text(
        welcome_text,
        reply_markup=get_start_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "show_stats", StateFilter(None))
async def process_show_stats(callback: CallbackQuery):
    """Обработчик кнопки 'Получить статистику'."""
    # TODO: Здесь будет вызов агрегации и формирование отчёта
    await callback.message.edit_text(
        "📊 *Статистика*\n\n"
        "Эта функция скоро будет доступна!\n\n"
        "Сейчас мы работаем над визуализацией данных.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "show_settings", StateFilter(None))
async def process_show_settings(callback: CallbackQuery):
    """Обработчик кнопки 'Настройки'."""
    settings_text = (
        "⚙️ *Настройки TimeLens*\n\n"
        "👇 *Что хочешь изменить?*"
    )
    
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Изменить ключи iCloud", callback_data="settings_edit_keys")],
        [InlineKeyboardButton(text="🗑 Удалить мои данные", callback_data="settings_delete_me")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()