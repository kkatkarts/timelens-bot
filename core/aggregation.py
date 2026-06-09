# core/aggregation.py
import logging
import re
from datetime import datetime, timezone
import pandas as pd
from typing import Optional

from .categories import CATEGORIES, CALENDAR_MAPPING, DEFAULT_TRIGGERS

logger = logging.getLogger(__name__)

def _categorize_event(row: pd.Series, user_rules: list[dict]) -> str:
    """
    Каскадная категоризация события.
    Приоритет: travel_block(0) -> user_rules(1) -> default_triggers(2) -> calendar_map(3) -> other(99)
    """
    text_summary = str(row.get("summary", "")).lower().strip()
    text_location = str(row.get("location", "")).lower().strip()
    cal_name = str(row.get("calendar_name", "")).lower().strip()
    
    # 0. Системный флаг перемещения (Apple Travel Time)
    if row.get("is_travel_block"):
        return "transit"

    # Собираем все правила и сортируем по приоритету (меньше = выше)
    all_rules = (user_rules or []) + DEFAULT_TRIGGERS
    all_rules = sorted(all_rules, key=lambda x: x.get("priority", 99))

    # 1 & 2. Проверка пользовательских и дефолтных правил
    for rule in all_rules:
        scope = rule.get("scope", "summary")
        if scope == "summary":
            text_to_check = text_summary
        elif scope == "location":
            text_to_check = text_location
        else:
            text_to_check = f"{text_summary} {text_location}"
            
        if re.search(rule["pattern"], text_to_check, re.IGNORECASE):
            return rule["category"]

    # 3. Маппинг по имени календаря
    for cal_key, category in CALENDAR_MAPPING.items():
        if cal_key in cal_name:
            return category

    # 99. Fallback
    return "other"


def _calculate_overlaps(df_timed: pd.DataFrame) -> dict:
    """
    Базовый расчёт пересечений для MVP (O(N log N) после сортировки).
    Считает общее время наложений и возвращает выборку.
    """
    if df_timed.empty:
        return {"total_pairs": 0, "total_minutes": 0, "sample": []}

    # Сортируем по времени начала
    df_sorted = df_timed.sort_values("dtstart_utc").reset_index(drop=True)
    total_overlap_minutes = 0
    sample_overlaps = []

    for i in range(len(df_sorted) - 1):
        current_end = df_sorted.loc[i, "dtend_utc"]
        next_start = df_sorted.loc[i + 1, "dtstart_utc"]
        
        if current_end > next_start:
            overlap_seconds = (current_end - next_start).total_seconds()
            total_overlap_minutes += int(overlap_seconds / 60)
            
            if len(sample_overlaps) < 5:  # Берём максимум 5 примеров
                sample_overlaps.append({
                    "uid_a": str(df_sorted.loc[i, "uid"]),
                    "uid_b": str(df_sorted.loc[i + 1, "uid"]),
                    "minutes": int(overlap_seconds / 60)
                })

    return {
        "total_pairs": len(sample_overlaps), # Упрощённо для MVP
        "total_minutes": total_overlap_minutes,
        "sample": sample_overlaps
    }


def _analyze_allday(df_allday: pd.DataFrame) -> dict:
    """Аналитика целодневных событий: группировка по названию и расчёт паттернов."""
    if df_allday.empty:
        return {"total_count": 0, "groups": []}

    groups = []
    # Группируем по названию и календарю
    grouped = df_allday.groupby(["summary", "calendar_name"])
    
    for (summary, cal_name), group in grouped:
        if not summary or summary == "nan":
            summary = "Без названия"
            
        dates = sorted(group["dtstart_utc"].dt.date.tolist())
        count = len(dates)
        
        # Расчёт среднего интервала (в днях)
        avg_gap = 0.0
        if count >= 2:
            gaps = [(dates[i] - dates[i-1]).days for i in range(1, count)]
            avg_gap = round(sum(gaps) / len(gaps), 1)
            
        groups.append({
            "name": str(summary)[:50], # Обрезаем длинные названия
            "calendar": str(cal_name),
            "count": count,
            "dates": [d.isoformat() for d in dates[:5]], # Храним только первые 5 дат для экономии
            "avg_gap_days": avg_gap,
            "is_cyclic": avg_gap > 0 and avg_gap < 15 # Эвристика для v2
        })

    # Сортируем по частоте (count desc) и берём топ-20
    groups = sorted(groups, key=lambda x: x["count"], reverse=True)[:20]

    return {
        "total_count": len(df_allday),
        "groups": groups
    }


def calculate_time_stats(
    df: pd.DataFrame, 
    user_rules: Optional[list[dict]] = None, 
    period_label: str = "week"
) -> dict:
    """
    Главная функция агрегации. Превращает сырой DataFrame в готовый к сериализации отчёт.
    """
    if df is None or df.empty:
        return {
            "meta": {"period": {"label": period_label}, "total_events": 0},
            "metrics": {"total_hours": 0.0, "by_category": {}, "by_calendar": {}},
            "allday_analytics": {"total_count": 0, "groups": []},
            "overlaps": {"total_pairs": 0, "total_minutes": 0, "sample": []},
            "hints": ["Нет событий за выбранный период."]
        }

    # 1. Разделение на временные и целодневные
    df_timed = df[df["is_allday"] == False].copy()
    df_allday = df[df["is_allday"] == True].copy()
    
    missing_end_count = 0

    # 2. Категоризация временных событий
    if not df_timed.empty:
        # Проверка на отсутствие dtend
        missing_end_count = df_timed["dtend_utc"].isna().sum()
        if missing_end_count > 0:
            logger.warning(f"Найдено {missing_end_count} событий без dtend. Длительность = 0.")
            df_timed["duration_hours"] = df_timed["duration_hours"].fillna(0.0)
            
        df_timed["category"] = df_timed.apply(lambda row: _categorize_event(row, user_rules or []), axis=1)

    # 3. Расчёт основных метрик
    total_hours = round(df_timed["duration_hours"].sum(), 2) if not df_timed.empty else 0.0
    
    by_category = df_timed.groupby("category")["duration_hours"].sum().round(2).to_dict() if not df_timed.empty else {}
    by_calendar = df_timed.groupby("calendar_name")["duration_hours"].sum().round(2).to_dict() if not df_timed.empty else {}

    # 4. Аналитика целодневных и пересечений
    allday_analytics = _analyze_allday(df_allday)
    overlaps = _calculate_overlaps(df_timed)

    # 5. Формирование подсказок (hints)
    hints = []
    if missing_end_count > 0:
        hints.append(f"⚠️ {missing_end_count} событий без времени окончания учтены как 0 часов.")
    if by_category.get("other", 0) > (total_hours * 0.3) and total_hours > 0:
        hints.append("💡 Много времени в категории 'other'. Попробуй добавить свои правила через /set_rule (v2).")

    # 6. Сборка финального контракта
    start_date = df["dtstart_utc"].min().date().isoformat() if not df.empty else ""
    end_date = df["dtend_utc"].max().date().isoformat() if not df.empty else ""

    return {
        "meta": {
            "period": {"start": start_date, "end": end_date, "label": period_label},
            "total_events": len(df),
            "timed_count": len(df_timed),
            "allday_count": len(df_allday),
            "events_missing_end": int(missing_end_count),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0"
        },
        "metrics": {
            "total_hours": total_hours,
            "by_category": by_category,
            "by_calendar": by_calendar
        },
        "allday_analytics": allday_analytics,
        "overlaps": overlaps,
        "hints": hints
    }


# === Тестовый запуск в консоли ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Импортируем sync для получения реальных данных
    from .sync import fetch_events_to_df, get_period_dates
    
    print("🔄 Загружаем данные из iCloud...")
    start, end = get_period_dates("week")
    
    # Исключаем мусорные календари для чистоты теста
    EXCLUDED = ["Birthdays", "Holidays", "Reminders", "Дни рождения", "Напоминания"]
    df = fetch_events_to_df(start, end, excluded_calendars=EXCLUDED)
    
    print("📊 Агрегируем данные...")
    report = calculate_time_stats(df, period_label="week")
    
    # Красивый вывод отчёта
    print("\n" + "="*50)
    print(f"📅 ПЕРИОД: {report['meta']['period']['start']} — {report['meta']['period']['end']} ({report['meta']['period']['label']})")
    print(f"⏱️ ВСЕГО ЧАСОВ: {report['metrics']['total_hours']} ч.")
    print(f"📊 СОБЫТИЙ: {report['meta']['timed_count']} временных, {report['meta']['allday_count']} целодневных")
    print("-" * 50)
    
    print("🗂 ПО КАТЕГОРИЯМ:")
    for cat, hours in sorted(report['metrics']['by_category'].items(), key=lambda x: x[1], reverse=True):
        print(f"  • {cat:<15}: {hours:>5.2f} ч.")
        
    print("\n📅 ЦЕЛОДНЕВНЫЕ (Топ паттернов):")
    for group in report['allday_analytics']['groups'][:5]:
        print(f"  • '{group['name']}' ({group['calendar']}): {group['count']} раз, ср. интервал {group['avg_gap_days']} дн.")
        
    if report['overlaps']['total_minutes'] > 0:
        print(f"\n⚠️ ПЕРЕСЕЧЕНИЯ: {report['overlaps']['total_minutes']} минут наложений.")
        
    if report['hints']:
        print("\n💡 ПОДСКАЗКИ:")
        for hint in report['hints']:
            print(f"  {hint}")
    print("="*50 + "\n")