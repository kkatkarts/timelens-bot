# core/crypto.py
"""
Модуль шифрования секретов (Apple ID, App-Specific Password) с помощью Fernet.

Fernet обеспечивает:
- Симметричное шифрование AES-128-CBC
- Проверку целостности через HMAC-SHA256
- Удобное хранение в виде base64-строк

Использование:
    encrypted = encrypt_secret("my_password")  # → "gAAAAAB..."
    decrypted = decrypt_secret(encrypted)      # → "my_password"
"""
import os
import logging
from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """
    Инициализирует Fernet с ключом из .env.
    Вызывается при каждом шифровании/дешифровании (лёгкая операция).
    """
    key = os.getenv("FERNET_KEY")
    if not key:
        raise ValueError("❌ FERNET_KEY не найден в .env. Сгенерируй ключ: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
    
    try:
        return Fernet(key.encode())
    except Exception as e:
        raise ValueError(f"❌ Неверный формат FERNET_KEY: {e}")


def encrypt_secret(plaintext: str) -> str:
    """
    Шифрует строку и возвращает base64-строку.
    
    Args:
        plaintext: Открытый текст (например, Apple ID или пароль)
    
    Returns:
        Зашифрованная строка в формате base64
    
    Raises:
        ValueError: Если FERNET_KEY не настроен или невалиден
    """
    if not plaintext:
        return ""
    
    fernet = _get_fernet()
    encrypted_bytes = fernet.encrypt(plaintext.encode())
    return encrypted_bytes.decode()


def decrypt_secret(encrypted_text: str) -> str:
    """
    Дешифрует base64-строку обратно в открытый текст.
    
    Args:
        encrypted_text: Зашифрованная строка (из БД)
    
    Returns:
        Расшифрованный текст
    
    Raises:
        ValueError: Если данные повреждены или ключ неверный
    """
    if not encrypted_text:
        return ""
    
    fernet = _get_fernet()
    
    try:
        decrypted_bytes = fernet.decrypt(encrypted_text.encode())
        return decrypted_bytes.decode()
    except InvalidToken:
        logger.error("❌ Не удалось дешифровать: неверный ключ или повреждённые данные")
        raise ValueError("Не удалось дешифровать данные. Возможно, FERNET_KEY изменился или данные повреждены.")
    except Exception as e:
        logger.error(f"❌ Ошибка дешифрования: {e}")
        raise ValueError(f"Ошибка дешифрования: {e}")


# === Тестовый запуск в консоли ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🔐 Тест модуля шифрования Fernet\n")
    
    # Тест 1: Шифрование и дешифрование
    test_password = "my_secret_password_123"
    print(f"📝 Исходный текст: {test_password}")
    
    encrypted = encrypt_secret(test_password)
    print(f"🔒 Зашифровано: {encrypted[:50]}...")  # Показываем первые 50 символов
    
    decrypted = decrypt_secret(encrypted)
    print(f"🔓 Дешифровано: {decrypted}")
    
    # Проверка
    if decrypted == test_password:
        print("\n✅ Шифрование работает корректно!")
    else:
        print("\n❌ Ошибка: дешифрованный текст не совпадает с исходным")
    
    # Тест 2: Пустая строка
    empty_encrypted = encrypt_secret("")
    empty_decrypted = decrypt_secret(empty_encrypted)
    print(f"\n📝 Пустая строка: '{empty_decrypted}' (должна быть пустой)")
    
    # Тест 3: Неверные данные
    print("\n⚠️ Тест с неверными данными:")
    try:
        decrypt_secret("invalid_encrypted_data")
    except ValueError as e:
        print(f"✅ Ожидаемая ошибка: {e}")
    
    print("\n" + "="*50)
    print("💡 Модуль готов к использованию в database.py")