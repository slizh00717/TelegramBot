"""Утилиты для работы со слотами и доступностью расписания."""

from datetime import datetime, timedelta
from typing import Any

from src.utils import get_timezone, logger


def generate_time_slots(
    schedule: dict[str, Any],
    duration_minutes: int,
    service_type: str,
) -> list[dict[str, Any]]:
    """
    Генерирует доступные слоты на основе расписания и длительности услуги.

    Args:
        schedule: Объект расписания из БД
        duration_minutes: Длительность услуги в минутах
        service_type: Тип услуги (haircut, beard_trim, haircut_and_beard)

    Returns:
        Список доступных слотов
    """
    tz = get_timezone()

    # Парсим дату и время из расписания
    date_obj = schedule["date"].date() if hasattr(schedule["date"], "date") else schedule["date"]
    start_time = schedule["start_time"]
    end_time = schedule["end_time"]

    # Конвертируем строковое время в объекты time если нужно
    if isinstance(start_time, str):
        start_hour, start_min = map(int, start_time.split(":"))
        from datetime import time as time_obj

        start_time = time_obj(hour=start_hour, minute=start_min)
    if isinstance(end_time, str):
        end_hour, end_min = map(int, end_time.split(":"))
        from datetime import time as time_obj

        end_time = time_obj(hour=end_hour, minute=end_min)

    # Создаем datetime объекты с учетом временной зоны
    current_time = datetime.combine(date_obj, start_time)
    current_time = tz.localize(current_time)
    end_datetime = datetime.combine(date_obj, end_time)
    end_datetime = tz.localize(end_datetime)

    # Генерируем слоты
    slots = []
    while current_time < end_datetime:
        slot_end = current_time + timedelta(minutes=duration_minutes)

        if slot_end > end_datetime:
            break

        slot = {
            "_id": str(schedule["_id"]),
            "start_time": current_time,
            "end_time": slot_end,
            "barber_id": schedule["barber_id"],
            "service_type": service_type,
            "status": "available",
        }
        slots.append(slot)
        current_time = slot_end

    logger.info(f"Generated {len(slots)} slots for service {service_type} with duration {duration_minutes}min")
    return slots


def filter_available_slots(
    slots: list[dict[str, Any]],
    booked_appointments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Фильтрует слоты, исключая уже забронированные времена.

    Args:
        slots: Список сгенерированных слотов
        booked_appointments: Список забронированных записей

    Returns:
        Отфильтрованный список доступных слотов
    """
    # Создаем набор забронированных времен
    booked_times = set()
    for appt in booked_appointments:
        appt_time = appt["appointment_time"]
        booked_times.add(appt_time)

    # Фильтруем слоты
    available_slots = []
    for slot in slots:
        slot_time = slot["start_time"].strftime("%H:%M")
        if slot_time not in booked_times:
            available_slots.append(slot)

    return available_slots


def get_service_duration(schedule: dict[str, Any], service_type: str) -> int:
    """
    Получает длительность услуги из расписания.

    Args:
        schedule: Объект расписания
        service_type: Тип услуги

    Returns:
        Длительность в минутах
    """
    if service_type == "haircut_and_beard":
        duration_key = "haircut_and_beard_duration_minutes"
        default_duration = 90
    elif service_type == "beard_trim":
        duration_key = "beard_trim_duration_minutes"
        default_duration = 30
    else:  # haircut
        duration_key = "haircut_duration_minutes"
        default_duration = 60

    return schedule.get(duration_key, default_duration)


def get_service_name(service_type: str) -> str:
    """Получает человеческое имя для типа услуги."""
    service_names = {
        "haircut": "Стрижка",
        "beard_trim": "Стрижка бороды",
        "haircut_and_beard": "Стрижка + Борода",
    }
    return service_names.get(service_type, "Услуга")
