# core/categories.py
"""
Библиотека категорий и правил для агрегации времени.
Легко расширяется: в v2 можно заменить на чтение из SQLite.
"""

# Полный список категорий (9 + other)
CATEGORIES = [
    "work", "sport", "study", "health_beauty", 
    "chores", "hobbies", "social", "transit", "other"
]

# Маппинг имен календарей -> категории (Приоритет 3)
# Ключи в нижнем регистре для нечеткого поиска
CALENDAR_MAPPING = {
    "работа": "work", "work": "work", "business": "work", "офис": "work",
    "учеба": "study", "study": "study", "курсы": "study", "универ": "study",
    "семья": "social", "family": "social", "друзья": "social",
    "дом": "chores", "быт": "chores", "house": "chores", "домашние дела": "chores",
}

# Дефолтные триггеры для поиска в тексте (Приоритет 2)
# pattern: regex, category: целевая категория, scope: где искать, priority: вес
DEFAULT_TRIGGERS = [
    {"pattern": r"встреча|колл|дедлайн|отчёт|планерка|офис|zoom|meet|call|работа", "category": "work", "scope": "summary", "priority": 2},
    {"pattern": r"тренировка|йога|бег|зал|плавание|пилатес|спорт|gym|walk|фитнес", "category": "sport", "scope": "summary", "priority": 2},
    {"pattern": r"курс|лекция|урок|чтение|учеба|изучение|язык|study|практика", "category": "study", "scope": "summary", "priority": 2},
    {"pattern": r"врач|стоматолог|анализы|здоровье|массаж|сон|beauty|косметолог", "category": "health_beauty", "scope": "summary", "priority": 2},
    {"pattern": r"уборка|счета|почта|магазин|доставка|ремонт|продукты|chores", "category": "chores", "scope": "summary", "priority": 2},
    {"pattern": r"рисование|гитара|вязание|настолки|хобби|творчество|craft", "category": "hobbies", "scope": "summary", "priority": 2},
    {"pattern": r"друзья|семья|вечеринка|праздник|свидание|кафе|ресторан|social", "category": "social", "scope": "summary", "priority": 2},
    {"pattern": r"дорога|в пути|еду|поездка|транзит|commute|drive|transit|путь|маршрут", "category": "transit", "scope": "summary", "priority": 2},
]