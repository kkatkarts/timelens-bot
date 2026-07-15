# bot/handlers/settings.py
"""
Обработчики FSM-диалогов для настройки ключей iCloud.
"""
import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.states import OnboardingStates, SettingsStates
from bot.keyboards import get_cancel_keyboard
from core.database import save_user, get_user, user_exists
from core.crypto import encrypt_secret

logger = logging.getLogger(__name__)

router = Router()


# === ОНБОРДИНГ (первичная настройка) ===

@router.callback_query(F.data == "start_onboarding")
async def process_onboarding_start(callback: CallbackQuery, state: FSMContext):
    logger.info(f"🔘 [КНОПКА] Нажата кнопка 'Начать' от {callback.from_user.id}")
    
    await state.set_state(OnboardingStates.waiting_for_email)
    
    # Отправляем НОВОЕ сообщение (не редактируем приветствие)
    bot_message = await callback.message.answer(
        "📧 *Шаг 1/2: Введи свой Apple ID (email)*\n\n"
        "Это email, который ты используешь для входа в iCloud.\n\n"
        "💡 Пример: `ivanov@apple.com`",
        parse_mode="Markdown"
    )
    
    # Сохраняем ID сообщения бота, чтобы потом удалить его
    await state.update_data(bot_email_request_id=bot_message.message_id)
    
    await callback.answer()
    logger.info("✅ [КНОПКА] Отправлен запрос email")


@router.message(OnboardingStates.waiting_for_email)
async def process_email_input(message: Message, state: FSMContext):
    logger.info(f"📩 [ШАГ 1] Получен email от {message.from_user.id}")
    
    email = message.text.strip()
    
    # Защита от команд (если пользователь отправил /start, /help и т.д.)
    if email.startswith("/"):
        logger.info(f"⚠️ Получена команда '{email}' во время FSM — игнорируем")
        return  # Не обрабатываем как email

    # Валидация
    if "@" not in email or "." not in email:
        await message.answer(
            "❌ Неверный формат email. Попробуй ещё раз.\n\n"
            "💡 Пример: `ivanov@apple.com`",
            parse_mode="Markdown"
        )
        return
    
    # Сохраняем email
    await state.update_data(icloud_username=email)
    
    # Удаляем сообщение пользователя с email
    try:
        await message.delete()
        logger.info("🗑 Сообщение пользователя с email удалено")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить сообщение пользователя: {e}")
    
    # Удаляем сообщение бота с запросом email
    data = await state.get_data()
    bot_email_request_id = data.get("bot_email_request_id")
    if bot_email_request_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=bot_email_request_id
            )
            logger.info("🗑 Сообщение бота с запросом email удалено")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить сообщение бота: {e}")
    
    # Переключаем состояние
    await state.set_state(OnboardingStates.waiting_for_password)
    
    # Отправляем запрос пароля
    bot_password_request = await message.answer(
        "✅ Apple ID принят.\n\n"
        "🔑 *Шаг 2/2: Введи App-Specific Password*\n\n"
        "Это специальный пароль для бота (не основной пароль от Apple ID).\n\n"
        "📝 *Как получить:*\n"
        "1. Зайди на [appleid.apple.com](https://appleid.apple.com)\n"
        "2. «Безопасность» → «App-Specific Passwords»\n"
        "3. «Сгенерировать» → назови «TimeLens» → скопируй\n\n"
        "⚠️ Пароль выглядит как: `xxxx-xxxx-xxxx-xxxx`",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    
    # Сохраняем ID сообщения с запросом пароля
    await state.update_data(bot_password_request_id=bot_password_request.message_id)
    
    logger.info("✅ Отправлен запрос пароля")


@router.message(OnboardingStates.waiting_for_password)
async def process_password_input(message: Message, state: FSMContext):
    logger.info(f"📩 [ШАГ 2] Получен пароль от {message.from_user.id}")
    
    password = message.text.strip()
    
    # Защита от команд (если пользователь отправил /start, /help и т.д.)
    if email.startswith("/"):
        logger.info(f"⚠️ Получена команда '{email}' во время FSM — игнорируем")
        return  # Не обрабатываем как email

    # Валидация
    if len(password) < 10 or "-" not in password:
        await message.answer(
            "❌ Неверный формат пароля. App-Specific Password выглядит как `xxxx-xxxx-xxxx-xxxx`.\n\n"
            "Попробуй ещё раз.",
        )
        return
    
    # Получаем email из состояния
    data = await state.get_data()
    email = data.get("icloud_username")
    
    if not email:
        await message.answer("❌ Ошибка: Apple ID не найден. Начни заново с /start")
        await state.clear()
        return
    
    telegram_id = message.from_user.id
    
    # Удаляем сообщение пользователя с паролем
    try:
        await message.delete()
        logger.info("🗑 Сообщение пользователя с паролем удалено")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить сообщение пользователя: {e}")
    
    # Удаляем сообщение бота с запросом пароля
    bot_password_request_id = data.get("bot_password_request_id")
    if bot_password_request_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=bot_password_request_id
            )
            logger.info("🗑 Сообщение бота с запросом пароля удалено")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось удалить сообщение бота: {e}")
    
    # Проверяем, существует ли пользователь
    existing_user = await get_user(telegram_id)
    
    if existing_user:
        # Пользователь уже есть — спрашиваем подтверждение
        await state.update_data(icloud_app_password=password)
        await state.set_state(OnboardingStates.waiting_for_confirmation)
        
        await message.answer(
            "⚠️ *У тебя уже настроены ключи.*\n\n"
            "Ты уверен(а), что хочешь их заменить?\n\n"
            "👇 Выбери действие:",
            parse_mode="Markdown",
            reply_markup=_get_confirmation_keyboard()
        )
    else:
        # Новый пользователь — сохраняем сразу
        await _save_credentials(message, state, email, password, telegram_id)


@router.callback_query(OnboardingStates.waiting_for_confirmation, F.data.in_(["confirm_overwrite", "cancel_overwrite"]))
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения перезаписи ключей."""
    if callback.data == "cancel_overwrite":
        await callback.message.edit_text("✅ Отменено. Ключи не изменены.")
        await state.clear()
        await callback.answer()
        return
    
    # Подтверждено — сохраняем
    data = await state.get_data()
    email = data.get("icloud_username")
    password = data.get("icloud_app_password")
    telegram_id = callback.from_user.id
    
    await _save_credentials(callback.message, state, email, password, telegram_id, is_edit=True)
    await callback.answer()


async def _save_credentials(message: Message, state: FSMContext, email: str, password: str, telegram_id: int, is_edit: bool = False):
    """Сохраняет зашифрованные ключи в БД."""
    try:
        is_new = await save_user(telegram_id, email, password)
        
        # Удаляем сообщение с паролем (безопасность)
        try:
            await message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение с паролем: {e}")
        
        # Очищаем состояние
        await state.clear()
        
        # Отправляем подтверждение
        action = "настроены" if is_new else "обновлены"
        await message.answer(
            f"✅ *Ключи {action}!*\n\n"
            "🔐 Твои данные зашифрованы и сохранены.\n\n"
            "👇 Теперь выбери период для анализа:",
            parse_mode="Markdown",
            reply_markup=_get_period_keyboard()
        )
        
        logger.info(f"✅ Пользователь {telegram_id} {'создан' if is_new else 'обновлён'}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения ключей: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении. Попробуй ещё раз с /start"
        )
        await state.clear()


# === НАСТРОЙКИ (редактирование ключей) ===

@router.callback_query(F.data == "settings_edit_keys")
async def process_settings_edit_keys(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования ключей из меню /settings."""
    await state.set_state(SettingsStates.waiting_for_email)
    
    await callback.message.edit_text(
        "📧 *Введи новый Apple ID (email)*\n\n"
        "💡 Пример: `ivanov@apple.com`",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(SettingsStates.waiting_for_email)
async def process_settings_email(message: Message, state: FSMContext):
    """Обработка ввода email в настройках."""
    email = message.text.strip()
    
    if "@" not in email or "." not in email:
        await message.answer("❌ Неверный формат email. Попробуй ещё раз.")
        return
    
    await state.update_data(icloud_username=email)
    
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение с email: {e}")
    
    await state.set_state(SettingsStates.waiting_for_password)
    
    await message.answer(
        "✅ Apple ID принят.\n\n"
        "🔑 *Введи новый App-Specific Password*",
        parse_mode="Markdown"
    )


@router.message(SettingsStates.waiting_for_password)
async def process_settings_password(message: Message, state: FSMContext):
    """Обработка ввода пароля в настройках."""
    password = message.text.strip()
    
    if len(password) < 10 or "-" not in password:
        await message.answer("❌ Неверный формат пароля. Попробуй ещё раз.")
        return
    
    data = await state.get_data()
    email = data.get("icloud_username")
    telegram_id = message.from_user.id
    
    try:
        await save_user(telegram_id, email, password)
        
        try:
            await message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение с паролем: {e}")
        
        await state.clear()
        
        await message.answer(
            "✅ *Ключи обновлены!*\n\n"
            "🔐 Твои данные зашифрованы и сохранены.",
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Пользователь {telegram_id} обновил ключи через /settings")
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения ключей: {e}")
        await message.answer("❌ Произошла ошибка. Попробуй ещё раз.")
        await state.clear()


# === ОТМЕНА ===

@router.callback_query(F.data == "cancel", StateFilter("*"))
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена любого FSM-диалога — возврат в главное меню (редактирование сообщения)."""
    logger.info(f"❌ Отмена FSM-диалога от {callback.from_user.id}")
    
    # Очищаем состояние
    await state.clear()
    
    # Проверяем, есть ли пользователь в БД
    telegram_id = callback.from_user.id
    exists = await user_exists(telegram_id)
    
    # Импортируем функции для редактирования сообщений
    from bot.handlers.start import edit_existing_user_menu, edit_new_user_welcome
    
    try:
        if exists:
            # Существующий пользователь — редактируем сообщение с меню
            await edit_existing_user_menu(callback.message)
        else:
            # Новый пользователь — редактируем приветствие
            await edit_new_user_welcome(callback.message)
    except Exception as e:
        # Если редактирование не удалось (например, сообщение слишком старое), отправляем новое
        logger.warning(f"⚠️ Не удалось отредактировать сообщение: {e}. Отправляем новое.")
        from bot.handlers.start import show_existing_user_menu, show_new_user_welcome
        
        if exists:
            await show_existing_user_menu(callback.message)
        else:
            await show_new_user_welcome(callback.message)
    
    await callback.answer()


# === ВСПОМОГАТЕЛЬНЫЕ КЛАВИАТУРЫ ===

def _get_confirmation_keyboard():
    """Клавиатура подтверждения перезаписи ключей."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, заменить", callback_data="confirm_overwrite"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_overwrite")
        ]
    ])


def _get_period_keyboard():
    """Клавиатура выбора периода (временная заглушка, потом перенесём в keyboards.py)."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Неделя", callback_data="period:week"),
            InlineKeyboardButton(text="📆 Месяц", callback_data="period:month")
        ],
        [
            InlineKeyboardButton(text="🗓 Квартал", callback_data="period:quarter"),
            InlineKeyboardButton(text="📊 Год", callback_data="period:year")
        ]
    ])