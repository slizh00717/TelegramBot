"""Обработчики для создания и управления расписанием барбера."""

from datetime import datetime, time, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from src.enums import NotificationType, UserRole
from src.services import NotificationService, ScheduleService, UserService
from src.utils import (
    get_today,
    require_role,
    safe_edit_text,
)

router = Router()
schedule_service = ScheduleService()
user_service = UserService()


class ScheduleStates(StatesGroup):
    """Состояния для создания расписания."""

    choosing_date = State()
    choosing_start_time = State()
    choosing_end_time = State()
    choosing_haircut_duration = State()
    choosing_beard_trim_duration = State()
    choosing_haircut_and_beard_duration = State()


def create_calendar_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора даты (календарь на 30 дней)."""
    today = get_today()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for i in range(30):
        current_date = today + timedelta(days=i)
        date_str = current_date.strftime("%d.%m")
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][current_date.weekday()]

        if i % 3 == 0:
            keyboard.inline_keyboard.append([])

        keyboard.inline_keyboard[-1].append(
            InlineKeyboardButton(
                text=f"{date_str} {day_name}",
                callback_data=f"schedule_date_{current_date.isoformat()}",
            )
        )

    return keyboard


def create_time_keyboard(start=0, end=24) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру выбора времени."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for hour in range(start, end):
        time_str = f"{hour:02d}:00"

        if (hour - start) % 3 == 0:
            keyboard.inline_keyboard.append([])

        keyboard.inline_keyboard[-1].append(
            InlineKeyboardButton(text=time_str, callback_data=f"schedule_time_{hour}")
        )

    return keyboard


@router.callback_query(F.data == "barber_create_schedule")
@require_role(UserRole.BARBER)
async def create_schedule_handler(callback: CallbackQuery, state: FSMContext):
    """Начало создания расписания - показать календарь."""
    await state.clear()

    keyboard = create_calendar_keyboard()
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")]
    )

    await callback.message.edit_text(
        "📅 <b>Выбери дату</b>\n\n" "Доступны даты на 30 дней вперед",
        reply_markup=keyboard,
    )
    await state.set_state(ScheduleStates.choosing_date)


@router.callback_query(F.data.startswith("schedule_date_"))
@require_role(UserRole.BARBER)
async def process_date_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты."""
    try:
        date_str = callback.data.split("_")[-1]
        date_obj = datetime.fromisoformat(date_str).date()
    except (ValueError, IndexError):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📅 Создать расписание",
                        callback_data="barber_create_schedule",
                    )
                ],
                [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
            ]
        )
        await callback.message.edit_text(
            "❌ Ошибка при обработке даты. Попробуй снова.", reply_markup=keyboard
        )
        await state.clear()
        return

    await state.update_data(date=date_obj)

    keyboard = create_time_keyboard(start=9, end=23)
    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data="barber_create_schedule"
            ),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    )

    await safe_edit_text(
        callback.message,
        f"📅 Дата: <b>{date_obj.strftime('%d.%m.%Y')}</b>\n\n"
        "🕐 <b>Выбери время начала</b>",
        reply_markup=keyboard,
    )
    await state.set_state(ScheduleStates.choosing_start_time)


@router.callback_query(F.data.startswith("schedule_time_"))
@require_role(UserRole.BARBER)
async def process_start_time_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени начала."""
    hour = int(callback.data.split("_")[-1])
    start_time = time(hour=hour, minute=0)

    data = await state.get_data()

    if "date" not in data:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📅 Создать расписание",
                        callback_data="barber_create_schedule",
                    )
                ],
                [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
            ]
        )
        await callback.message.edit_text(
            "❌ Ошибка: дата не найдена. Начни с начала.", reply_markup=keyboard
        )
        await state.clear()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for end_hour in range(hour + 1, 24):
        time_str = f"{end_hour:02d}:00"

        if (end_hour - hour - 1) % 3 == 0:
            keyboard.inline_keyboard.append([])

        keyboard.inline_keyboard[-1].append(
            InlineKeyboardButton(
                text=time_str, callback_data=f"schedule_end_time_{end_hour}"
            )
        )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data="barber_create_schedule"
            ),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    )

    await state.update_data(start_time=start_time)

    await safe_edit_text(
        callback.message,
        f"📅 Дата: <b>{data['date'].strftime('%d.%m.%Y')}</b>\n"
        f"🕐 Начало: <b>{start_time.strftime('%H:%M')}</b>\n\n"
        "🕐 <b>Выбери время окончания</b>",
        reply_markup=keyboard,
    )
    await state.set_state(ScheduleStates.choosing_end_time)


@router.callback_query(F.data.startswith("schedule_end_time_"))
@require_role(UserRole.BARBER)
async def process_end_time_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени окончания."""
    hour = int(callback.data.split("_")[-1])
    end_time = time(hour=hour, minute=0)

    data = await state.get_data()

    if "date" not in data or "start_time" not in data:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📅 Создать расписание",
                        callback_data="barber_create_schedule",
                    )
                ],
                [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
            ]
        )
        await callback.message.edit_text(
            "❌ Ошибка: данные не найдены. Начни с начала.", reply_markup=keyboard
        )
        await state.clear()
        return

    await state.update_data(end_time=end_time)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    durations = [15, 20, 25, 30, 45, 60]

    for dur in durations:
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"⏱️ {dur} мин",
                    callback_data=f"schedule_haircut_duration_{dur}",
                )
            ]
        )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data="barber_create_schedule"
            ),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    )

    await safe_edit_text(
        callback.message,
        f"📅 Дата: <b>{data['date'].strftime('%d.%m.%Y')}</b>\n"
        f"🕐 Время: <b>{data['start_time'].strftime('%H:%M')} - {end_time.strftime('%H:%M')}</b>\n\n"
        "✂️ <b>Выбери длительность стрижки</b>",
        reply_markup=keyboard,
    )
    await state.set_state(ScheduleStates.choosing_haircut_duration)


@router.callback_query(F.data.startswith("schedule_haircut_duration_"))
@require_role(UserRole.BARBER)
async def process_haircut_duration_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора длительности стрижки."""
    duration = int(callback.data.split("_")[-1])
    data = await state.get_data()

    await state.update_data(haircut_duration_minutes=duration)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    durations = [15, 20, 25, 30, 45, 60]

    for dur in durations:
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"⏱️ {dur} мин",
                    callback_data=f"schedule_beard_trim_duration_{dur}",
                )
            ]
        )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data="barber_create_schedule"
            ),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    )

    await safe_edit_text(
        callback.message,
        f"📅 Дата: <b>{data['date'].strftime('%d.%m.%Y')}</b>\n"
        f"🕐 Время: <b>{data['start_time'].strftime('%H:%M')} - {data['end_time'].strftime('%H:%M')}</b>\n"
        f"✂️ Стрижка: <b>{duration} мин</b>\n\n"
        "💈 <b>Выбери длительность стрижки бороды</b>",
        reply_markup=keyboard,
    )
    await state.set_state(ScheduleStates.choosing_beard_trim_duration)


@router.callback_query(F.data.startswith("schedule_beard_trim_duration_"))
@require_role(UserRole.BARBER)
async def process_beard_trim_duration_callback(
    callback: CallbackQuery, state: FSMContext
):
    """Обработка выбора длительности стрижки бороды."""
    duration = int(callback.data.split("_")[-1])
    data = await state.get_data()

    await state.update_data(beard_trim_duration_minutes=duration)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    durations = [45, 60, 75, 90, 105, 120]

    for dur in durations:
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"⏱️ {dur} мин",
                    callback_data=f"schedule_haircut_beard_duration_{dur}",
                )
            ]
        )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data="barber_create_schedule"
            ),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    )

    haircut_duration = data.get("haircut_duration_minutes", 60)

    await safe_edit_text(
        callback.message,
        f"📅 Дата: <b>{data['date'].strftime('%d.%m.%Y')}</b>\n"
        f"🕐 Время: <b>{data['start_time'].strftime('%H:%M')} - {data['end_time'].strftime('%H:%M')}</b>\n"
        f"✂️ Стрижка: <b>{haircut_duration} мин</b>\n"
        f"💈 Стрижка бороды: <b>{duration} мин</b>\n\n"
        "✂️💈 <b>Выбери длительность стрижки + борода</b>",
        reply_markup=keyboard,
    )
    await state.set_state(ScheduleStates.choosing_haircut_and_beard_duration)


@router.callback_query(F.data.startswith("schedule_haircut_beard_duration_"))
@require_role(UserRole.BARBER)
async def process_haircut_and_beard_duration_callback(
    callback: CallbackQuery, state: FSMContext
):
    """Обработка выбора длительности стрижки + бороды и создание расписания."""
    duration = int(callback.data.split("_")[-1])
    data = await state.get_data()

    haircut_duration = data.get("haircut_duration_minutes", 60)
    beard_trim_duration = data.get("beard_trim_duration_minutes", 30)

    user = await user_service.get_user(callback.from_user.id)
    schedule = await schedule_service.create_schedule(
        barber_id=str(user["_id"]),
        date_obj=data["date"],
        start_time=data["start_time"],
        end_time=data["end_time"],
        haircut_duration_minutes=haircut_duration,
        beard_trim_duration_minutes=beard_trim_duration,
        haircut_and_beard_duration_minutes=duration,
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Опубликовать",
                    callback_data=f"publish_schedule_{schedule['_id']}",
                )
            ],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")],
        ]
    )

    await callback.message.edit_text(
        f"✅ <b>Расписание создано</b>\n\n"
        f"📅 Дата: <b>{data['date'].strftime('%d.%m.%Y')}</b>\n"
        f"🕐 Время: <b>{data['start_time'].strftime('%H:%M')} - {data['end_time'].strftime('%H:%M')}</b>\n"
        f"✂️ Стрижка: <b>{haircut_duration} мин</b>\n"
        f"💈 Стрижка бороды: <b>{beard_trim_duration} мин</b>\n"
        f"✂️💈 Стрижка + Борода: <b>{duration} мин</b>\n\n"
        "Опубликуй расписание, чтобы клиенты могли записаться.",
        reply_markup=keyboard,
    )

    await state.clear()


@router.callback_query(F.data.startswith("publish_schedule_"))
@require_role(UserRole.BARBER)
async def publish_schedule_handler(callback: CallbackQuery):
    """Публикация расписания и уведомление подписчиков."""
    schedule_id = callback.data.split("_")[-1]

    result = await schedule_service.publish_schedule(schedule_id)
    if result:
        from src.repositories import ScheduleRepository

        repo = ScheduleRepository()
        schedule = await repo.find_by_id(schedule_id)

        slots = await schedule_service.get_available_slots_for_barber(
            str(schedule["barber_id"]), schedule["date"]
        )

        user = await user_service.get_user(callback.from_user.id)

        if hasattr(schedule["start_time"], "strftime"):
            start_time_str = schedule["start_time"].strftime("%H:%M")
        else:
            start_time_str = (
                schedule["start_time"][:5]
                if len(schedule["start_time"]) > 5
                else schedule["start_time"]
            )

        if hasattr(schedule["end_time"], "strftime"):
            end_time_str = schedule["end_time"].strftime("%H:%M")
        else:
            end_time_str = (
                schedule["end_time"][:5]
                if len(schedule["end_time"]) > 5
                else schedule["end_time"]
            )

        date_str = (
            schedule["date"].strftime("%d.%m.%Y")
            if hasattr(schedule["date"], "strftime")
            else str(schedule["date"])
        )

        message = (
            f"<b>✂️ Новое расписание от {user['full_name']}</b>\n\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время работы: {start_time_str} - {end_time_str}\n"
            f"✨ Доступно мест: {len(slots)}\n\n"
            f"Запишись прямо сейчас!"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📝 Записаться", callback_data="client_book_appointment"
                    )
                ],
            ]
        )

        notification_service = NotificationService(callback.bot)
        sent_count = await notification_service.notify_subscribers(
            notification_type=NotificationType.SCHEDULE_PUBLISHED,
            title="Новое расписание",
            message=message,
            reply_markup=keyboard,
            exclude_user_id=str(user["_id"]),
        )

        await callback.message.edit_text(
            f"✅ <b>Расписание опубликовано!</b>\n\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {start_time_str} - {end_time_str}\n"
            f"✨ Свободных мест: {len(slots)}\n\n"
            f"Уведомления отправлены {sent_count} подписчикам"
        )
    else:
        await callback.message.edit_text("❌ Ошибка при публикации расписания")
