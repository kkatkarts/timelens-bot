# core/sync.py
import os
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Optional
import caldav
import pandas as pd
from icalendar import Calendar as ICalCalendar
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Загружаем .env (если есть)
load_dotenv()
logger = logging.getLogger(__name__)

ICLOUD_CALDAV_URL = "https://caldav.icloud.com/"


def _normalize_dt(dt_obj):
    """Приводит date/datetime к UTC. Возвращает (datetime_utc, is_allday)"""
    if isinstance(dt_obj, date) and not isinstance(dt_obj, datetime):
        # Целодневное событие
        return datetime(dt_obj.year, dt_obj.month, dt_obj.day, tzinfo=ZoneInfo("UTC")), True
    
    if dt_obj.tzinfo is None:
        return dt_obj.replace(tzinfo=ZoneInfo("UTC")), False
    return dt_obj.astimezone(ZoneInfo("UTC")), False


def get_period_dates(period: str = "week") -> tuple[datetime, datetime]:
    """
    Возвращает (start, end) в UTC для чистых календарных периодов.
    Исключает сегодня, берёт полные дни.
    """
    today_utc = datetime.now(timezone.utc).date()
    
    if period == "day":
        start_date = today_utc - timedelta(days=1)
    elif period == "week":
        start_date = today_utc - timedelta(days=7)
    elif period == "month":
        start_date = today_utc.replace(day=1)
    elif period == "quarter":
        quarter_month = ((today_utc.month - 1) // 3) * 3 + 1
        start_date = today_utc.replace(month=quarter_month, day=1)
    elif period == "year":
        start_date = today_utc.replace(month=1, day=1)
    else:
        start_date = today_utc - timedelta(days=7)
        
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(today_utc, datetime.min.time(), tzinfo=timezone.utc)
    
    return start_dt, end_dt


def fetch_events_to_df(
    start_date: datetime,
    end_date: datetime,
    excluded_calendars: Optional[list[str]] = None
) -> pd.DataFrame:
    """
    Загружает события из iCloud за период, фильтрует, парсит и возвращает чистый DataFrame.
    """
    username = os.getenv("ICLOUD_USERNAME")
    password = os.getenv("ICLOUD_APP_SPECIFIC_PASSWORD")
    
    if not (username and password):
        raise ValueError("Missing ICLOUD_USERNAME or ICLOUD_APP_SPECIFIC_PASSWORD in .env")

    client = caldav.DAVClient(ICLOUD_CALDAV_URL, username=username, password=password)
    principal = client.principal()
    calendars = principal.calendars()

    excluded = [c.lower() for c in (excluded_calendars or [])]
    rows = []
    now_utc = datetime.now(timezone.utc)

    for cal in calendars:
        # 🔧 Исправление #1: используем get_display_name() вместо устаревшего .name
        cal_name = cal.get_display_name() or cal.id or "Unknown"
        
        # 1. Исключаем календари по подстроке
        if any(exc in cal_name.lower() for exc in excluded):
            logger.info(f"⏭️ Пропускаем календарь: {cal_name}")
            continue

        # 2. Запрашиваем события
        # 🔧 Исправление #2: используем search() вместо устаревшего date_search()
        try:
            events = cal.search(
                start=start_date,
                end=end_date,
                expand=True,
                comp_class=caldav.Event
            )
        except Exception as e:
            logger.warning(f"❌ Ошибка при запросе к {cal_name}: {e}")
            continue

        for event in events:
            try:
                ical_comp = ICalCalendar.from_ical(event.data).walk("VEVENT")
                if not ical_comp:
                    continue
                    
                ev = ical_comp[0]
                summary = str(ev.get("SUMMARY", "Без названия"))
                status = str(ev.get("STATUS", "CONFIRMED")).upper()
                
                # Пропускаем отменённые
                if status == "CANCELLED":
                    continue

                # Даты
                dtstart_raw = ev.get("DTSTART")
                dtend_raw = ev.get("DTEND")
                
                if not dtstart_raw:
                    continue
                    
                dtstart_utc, is_allday = _normalize_dt(dtstart_raw.dt)
                dtend_utc = None
                duration_h = 0.0

                if dtend_raw:
                    dtend_utc, _ = _normalize_dt(dtend_raw.dt)
                    duration_h = round((dtend_utc - dtstart_utc).total_seconds() / 3600, 2)
                else:
                    dtend_utc = dtstart_utc  # Фоллбек, если конец не указан

                # Для MVP исключаем будущие события
                if dtend_utc > now_utc:
                    continue

                # Целодневные события не считаем в часах
                if is_allday:
                    duration_h = 0.0

                location = str(ev.get("LOCATION", "") or "")
                description = str(ev.get("DESCRIPTION", "") or "")
                categories = str(ev.get("CATEGORIES", "") or "")

                # 🔍 Детекция встроенного времени на дорогу (macOS/iOS)
                has_travel_tag = bool(
                    ev.get("X-APPLE-TRAVEL-TO-DTSTART") or 
                    ev.get("X-APPLE-TRAVEL-TO-DTEND") or 
                    ev.get("RELATED-TO")
                )

                rows.append({
                    "uid": str(ev.get("UID", "")),
                    "summary": summary,
                    "dtstart_utc": dtstart_utc,
                    "dtend_utc": dtend_utc,
                    "duration_hours": duration_h,
                    "is_allday": is_allday,
                    "is_travel_block": has_travel_tag,
                    "calendar_name": cal_name,
                    "calendar_url": str(cal.url),
                    # 🔧 Исправление #3: убираем get_etag() — его больше нет в API
                    "event_etag": "",  # Для v2: получить через event.props
                    "event_url": str(event.url),
                    "location": location,
                    "description": description,
                    "categories": categories,
                    "status": status
                })
            except Exception as e:
                logger.warning(f"⚠️ Ошибка парсинга события: {e}")
                continue

    df = pd.DataFrame(rows)
    if df.empty:
        logger.info("📭 Событий за период не найдено")
        return pd.DataFrame()

    # Базовая очистка типов
    df["dtstart_utc"] = pd.to_datetime(df["dtstart_utc"], utc=True)
    df["dtend_utc"] = pd.to_datetime(df["dtend_utc"], utc=True)
    
    logger.info(f"✅ Загружено {len(df)} событий за период {start_date.date()} - {end_date.date()}")
    return df


# === Улучшенный тест в консоли ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    start, end = get_period_dates("week")
    print(f"🗓 Запрос периода: {start.date()} 00:00 → {end.date()} 00:00 (UTC)")
    
    EXCLUDED = ["Birthdays", "Holidays", "Reminders", "Дни рождения", "Напоминания"]
    df = fetch_events_to_df(start, end, excluded_calendars=EXCLUDED)
    
    if not df.empty:
        df_timed = df[df["is_allday"] == False].copy()
        df_allday = df[df["is_allday"] == True].copy()
        
        print(f"\n📊 Сводка за период:")
        print(f"⏱️ Всего часов (временные события): {df_timed['duration_hours'].sum():.2f}")
        print(f"⏳ Временных событий: {len(df_timed)}")
        print(f"📅 Целодневных событий: {len(df_allday)}")
        
        if not df_timed.empty:
            print("\n📁 Разбивка по календарям:")
            print(df_timed["calendar_name"].value_counts().to_string())
            
            print("\n🕒 Топ-5 событий (по длительности):")
            top = df_timed.sort_values("duration_hours", ascending=False).head(5)
            cols = ["summary", "calendar_name", "duration_hours", "dtstart_utc", "location", "is_travel_block"]
            print(top[cols].to_string(index=False))
            
        if not df_allday.empty:
            print("\n📅 Целодневные события (по календарям):")
            print(df_allday["calendar_name"].value_counts().to_string())
            print(f"💡 Примеры: {df_allday['summary'].head(3).tolist()}")
    else:
        print("\n📭 Пусто за выбранный период.")