"""
FSM-состояния для диалогов бота.
Каждое состояние = шаг в диалоге с пользователем.
"""
from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """Состояния для онбординга (настройка ключей iCloud)."""
    waiting_for_email = State()      # Ждём ввод Apple ID
    waiting_for_password = State()   # Ждём ввод App-Specific Password
    waiting_for_confirmation = State()  # Ждём подтверждение перезаписи (если пользователь уже есть)


class SettingsStates(StatesGroup):
    """Состояния для меню настроек."""
    waiting_for_email = State()
    waiting_for_password = State()