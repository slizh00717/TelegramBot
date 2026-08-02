"""Утилиты для работы с букингом и записями клиентов."""

from datetime import date, datetime
from typing import Any

from src.enums import AppointmentStatus


def format_appointment_info(appointment: dict[str, Any]) -> tuple[str, str]:
    """
    Форматирует информацию о записи для показа пользователю.

    Args:
        appointment: Объект записи

    Returns:
        Кортеж (время, дата) в строковом формате
    """
    time_str = appointment["appointment_time"]
    appointment_date = appointment["appointment_date"]

    # Handle datetime, date, and string types
    if isinstance(appointment_date, datetime) or isinstance(appointment_date, date):
        date_str = appointment_date.strftime("%d.%m.%Y")
    elif isinstance(appointment_date, str):
        date_str = appointment_date
    else:
        raise ValueError(
            f"Invalid date type: {type(appointment_date)}. Expected date, datetime, or str."
        )

    return time_str, date_str


def get_service_emoji(service_type: str) -> str:
    """Получает эмодзи для типа услуги."""
    emojis = {
        "haircut": "✂️",
        "beard_trim": "💈",
        "haircut_and_beard": "✂️💈",
    }
    return emojis.get(service_type, "✂️")


def is_appointment_active(appointment: dict[str, Any]) -> bool:
    """Проверяет, активна ли запись."""
    return appointment.get("status") == AppointmentStatus.BOOKED.value


def is_appointment_completed(appointment: dict[str, Any]) -> bool:
    """Проверяет, завершена ли запись."""
    return appointment.get("status") == AppointmentStatus.COMPLETED.value


def is_appointment_cancelled(appointment: dict[str, Any]) -> bool:
    """Проверяет, отменена ли запись."""
    return appointment.get("status") == AppointmentStatus.CANCELLED.value


def group_appointments_by_date(appointments: list) -> dict[Any, list]:
    """
    Группирует записи по датам.

    Args:
        appointments: Список записей

    Returns:
        Словарь вида {дата: [записи]}
    """
    from collections import defaultdict

    by_date = defaultdict(list)
    for appt in appointments:
        by_date[appt["appointment_date"]].append(appt)
    return by_date


def build_appointment_message(
    appointment: dict[str, Any],
    client_name: str,
    service_name: str,
    barber_name: str | None = None,
) -> str:
    """
    Строит сообщение о записи для отправки пользователю.

    Args:
        appointment: Объект записи
        client_name: Имя клиента
        service_name: Название услуги
        barber_name: Имя барбера (опционально)

    Returns:
        Отформатированное сообщение
    """
    time_str, date_str = format_appointment_info(appointment)

    if barber_name:
        return (
            f"<b>✂️ Вас записали!</b>\n\n"
            f"{get_service_emoji(appointment.get('service_type', 'haircut'))} "
            f"Услуга: {service_name}\n"
            f"👤 Барбер: {barber_name}\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}"
        )
    else:
        return (
            f"<b>✂️ Запись подтверждена</b>\n\n"
            f"👤 Клиент: {client_name}\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}"
        )
