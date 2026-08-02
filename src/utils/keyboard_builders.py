"""Построители клавиатур и вспомогательные функции для UI."""

from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_date_selection_keyboard(
    dates: list[date],
    callback_prefix: str,
    max_dates: int = 10,
) -> InlineKeyboardMarkup:
    """
    Строит клавиатуру для выбора даты.

    Args:
        dates: Список дат для отображения
        callback_prefix: Префикс для callback_data (например, "select_date_")
        max_dates: Максимум дат для отображения

    Returns:
        InlineKeyboardMarkup с кнопками дат
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for date_obj in sorted(dates)[:max_dates]:
        date_str = date_obj.strftime("%d.%m.%Y")
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=date_str,
                    callback_data=f"{callback_prefix}{date_obj.isoformat()}",
                )
            ]
        )

    return keyboard


def build_service_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Строит клавиатуру для выбора услуги.

    Returns:
        InlineKeyboardMarkup с опциями услуг
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✂️ Стрижка",
                    callback_data="select_service_haircut",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💈 Стрижка бороды",
                    callback_data="select_service_beard_trim",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✂️💈 Стрижка + Борода",
                    callback_data="select_service_haircut_and_beard",
                )
            ],
        ]
    )


def build_time_keyboard(
    start: int = 9,
    end: int = 23,
) -> InlineKeyboardMarkup:
    """
    Строит клавиатуру для выбора времени.

    Args:
        start: Час начала
        end: Час конца

    Returns:
        InlineKeyboardMarkup с кнопками времени
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for hour in range(start, end):
        time_str = f"{hour:02d}:00"

        if (hour - start) % 3 == 0:
            keyboard.inline_keyboard.append([])

        keyboard.inline_keyboard[-1].append(
            InlineKeyboardButton(text=time_str, callback_data=f"schedule_time_{hour}")
        )

    return keyboard


def build_duration_keyboard(
    durations: list[int],
    callback_prefix: str,
) -> InlineKeyboardMarkup:
    """
    Строит клавиатуру для выбора длительности.

    Args:
        durations: Список длительностей в минутах
        callback_prefix: Префикс для callback_data

    Returns:
        InlineKeyboardMarkup с кнопками длительностей
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for duration in durations:
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"⏱️ {duration} мин",
                    callback_data=f"{callback_prefix}{duration}",
                )
            ]
        )

    return keyboard


def build_back_menu_buttons(
    back_callback: str = "menu",
    back_text: str = "⬅️ Назад",
) -> list[list[InlineKeyboardButton]]:
    """
    Строит кнопки для навигации назад и в меню.

    Args:
        back_callback: Callback для кнопки "назад"
        back_text: Текст для кнопки "назад"

    Returns:
        Список кнопок для добавления в клавиатуру
    """
    return [
        [
            InlineKeyboardButton(text=back_text, callback_data=back_callback),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    ]
