# bot/keyboards.py
"""
Модуль для хранения всех inline-клавиатур бота.
Централизация упрощает поддержку: если нужно изменить текст кнопки — правим в одном месте.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для приветственного сообщения /start."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать", callback_data="start_onboarding")]
    ])
    return keyboard


def get_period_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода для статистики."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Неделя", callback_data="period:week"),
            InlineKeyboardButton(text="📆 Месяц", callback_data="period:month")
        ],
        [
            InlineKeyboardButton(text="🗓 Квартал", callback_data="period:quarter"),
            InlineKeyboardButton(text="📊 Год", callback_data="period:year")
        ],
        [
            InlineKeyboardButton(text="🎯 Свой период", callback_data="period:custom")
        ]
    ])
    return keyboard


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены (используется в FSM-диалогах)."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    return keyboard