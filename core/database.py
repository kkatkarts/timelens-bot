# core/database.py
"""
Модуль работы с базой данных пользователей (SQLite + aiosqlite).

Хранит зашифрованные учётные данные iCloud для каждого пользователя Telegram.
Все операции асинхронные (совместимо с aiogram).

Использование:
    await init_db()  # Создать таблицу при первом запуске
    await save_user(123456, "user@apple.com", "xxxx-xxxx", "Europe/Moscow")
    user = await get_user(123456)  # → {"telegram_id": 123456, "icloud_username": "user@apple.com", ...}
    await delete_user(123456)
"""
import os
import logging
import aiosqlite
from typing import Optional
from datetime import datetime

from .crypto import encrypt_secret, decrypt_secret

logger = logging.getLogger(__name__)

# Путь к базе данных (создаётся в корне проекта)
DB_PATH = os.getenv("DATABASE_PATH", "data/users.db")


async def init_db():
    """
    Инициализирует базу данных: создаёт таблицу users, если её нет.
    Вызывается при запуске бота.
    """
    # Создаём папку data/, если её нет
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                icloud_username TEXT,
                icloud_app_password TEXT,
                timezone TEXT DEFAULT 'UTC',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        logger.info(f"✅ База данных инициализирована: {DB_PATH}")


async def save_user(
    telegram_id: int,
    icloud_username: str,
    icloud_app_password: str,
    timezone: str = "UTC"
) -> bool:
    """
    Сохраняет или обновляет учётные данные пользователя.
    Шифрует username и password перед сохранением.
    
    Returns:
        True если пользователь создан, False если обновлён
    """
    # Шифруем секреты
    encrypted_username = encrypt_secret(icloud_username)
    encrypted_password = encrypt_secret(icloud_app_password)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, существует ли пользователь
        cursor = await db.execute(
            "SELECT telegram_id FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        exists = await cursor.fetchone()
        
        if exists:
            # Обновляем существующего
            await db.execute("""
                UPDATE users 
                SET icloud_username = ?, icloud_app_password = ?, timezone = ?
                WHERE telegram_id = ?
            """, (encrypted_username, encrypted_password, timezone, telegram_id))
            logger.info(f"🔄 Пользователь {telegram_id} обновлён")
            is_new = False
        else:
            # Создаём нового
            await db.execute("""
                INSERT INTO users (telegram_id, icloud_username, icloud_app_password, timezone)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, encrypted_username, encrypted_password, timezone))
            logger.info(f"✅ Пользователь {telegram_id} создан")
            is_new = True
        
        await db.commit()
        return is_new


async def get_user(telegram_id: int) -> Optional[dict]:
    """
    Получает учётные данные пользователя и дешифрует их.
    
    Returns:
        dict с ключами: telegram_id, icloud_username, icloud_app_password, timezone, created_at
        None если пользователь не найден
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT telegram_id, icloud_username, icloud_app_password, timezone, created_at FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
        
        # Дешифруем секреты
        try:
            username = decrypt_secret(row[1])
            password = decrypt_secret(row[2])
        except ValueError as e:
            logger.error(f"❌ Не удалось дешифровать данные пользователя {telegram_id}: {e}")
            return None
        
        return {
            "telegram_id": row[0],
            "icloud_username": username,
            "icloud_app_password": password,
            "timezone": row[3],
            "created_at": row[4]
        }


async def delete_user(telegram_id: int) -> bool:
    """
    Удаляет пользователя из базы данных.
    
    Returns:
        True если пользователь удалён, False если не найден
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        await db.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"🗑 Пользователь {telegram_id} удалён")
            return True
        else:
            logger.warning(f"⚠️ Пользователь {telegram_id} не найден для удаления")
            return False


async def user_exists(telegram_id: int) -> bool:
    """
    Проверяет, существует ли пользователь в базе.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return row is not None


# === Тестовый запуск в консоли ===
async def _test():
    """Тестовая функция для проверки работы БД."""
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    print("🗄 Тест базы данных пользователей\n")
    
    # 1. Инициализация
    await init_db()
    
    # 2. Создание пользователя
    test_id = 999999999
    test_username = "test@apple.com"
    test_password = "test-password-1234"
    
    print(f"\n📝 Создаём тестового пользователя {test_id}...")
    is_new = await save_user(test_id, test_username, test_password, "Europe/Moscow")
    print(f"✅ Пользователь {'создан' if is_new else 'обновлён'}")
    
    # 3. Чтение пользователя
    print(f"\n🔍 Читаем пользователя {test_id}...")
    user = await get_user(test_id)
    if user:
        print(f"✅ Найден:")
        print(f"   • telegram_id: {user['telegram_id']}")
        print(f"   • icloud_username: {user['icloud_username']}")
        print(f"   • icloud_app_password: {user['icloud_app_password']}")
        print(f"   • timezone: {user['timezone']}")
        print(f"   • created_at: {user['created_at']}")
        
        # Проверка дешифрования
        if user['icloud_username'] == test_username and user['icloud_app_password'] == test_password:
            print("\n✅ Шифрование/дешифрование работает корректно!")
        else:
            print("\n❌ Ошибка: дешифрованные данные не совпадают")
    else:
        print("❌ Пользователь не найден")
    
    # 4. Проверка существования
    print(f"\n🔎 Проверяем существование...")
    exists = await user_exists(test_id)
    print(f"✅ Пользователь {'существует' if exists else 'не существует'}")
    
    # 5. Удаление
    print(f"\n🗑 Удаляем пользователя {test_id}...")
    deleted = await delete_user(test_id)
    print(f"✅ Пользователь {'удалён' if deleted else 'не найден'}")
    
    # 6. Проверка после удаления
    exists_after = await user_exists(test_id)
    print(f"{'✅' if not exists_after else '❌'} После удаления: {'не существует' if not exists_after else 'существует (ошибка!)'}")
    
    print("\n" + "="*50)
    print("💡 База данных готова к использованию в bot/handlers/")


if __name__ == "__main__":
    import asyncio
    asyncio.run(_test())