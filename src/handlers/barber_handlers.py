from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, date, time, timedelta
import pytz
from src.services import (
    ScheduleService,
    AppointmentService,
    UserService,
    NotificationService,
)
from src.config import settings
from src.utils import (
    logger,
    require_role,
    get_today,
    get_timezone,
    validate_name,
    validate_phone,
    safe_edit_text,
)
from src.enums import UserRole, NotificationType
from src.repositories import ScheduleRepository, TimeSlotRepository, UserRepository

router = Router()
schedule_service = ScheduleService()
appointment_service = AppointmentService()
user_service = UserService()


class ScheduleStates(StatesGroup):
    choosing_date = State()
    choosing_start_time = State()
    choosing_end_time = State()
    choosing_haircut_duration = State()
    choosing_haircut_and_beard_duration = State()


class BarberProfileEditStates(StatesGroup):
    editing_name = State()
    editing_phone = State()


class BarberServiceStates(StatesGroup):
    choosing_price = State()


class BarberBookingStates(StatesGroup):
    choosing_service = State()


@router.callback_query(F.data == "barber_create_schedule")
@require_role(UserRole.BARBER)
async def create_schedule_handler(callback: CallbackQuery, state: FSMContext):
    """Start schedule creation - show calendar"""
    # Clear any previous state data
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


def create_calendar_keyboard() -> InlineKeyboardMarkup:
    """Create calendar keyboard for date selection"""
    today = get_today()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    # Show 30 days from today
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


@router.callback_query(F.data.startswith("schedule_date_"))
@require_role(UserRole.BARBER)
async def process_date_callback(callback: CallbackQuery, state: FSMContext):
    """Process date selection"""
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


def create_price_keyboard(
    current_price: float = 0, service_type: str = "haircut"
) -> InlineKeyboardMarkup:
    """Create price selection keyboard with increment/decrement buttons"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➖ -5", callback_data=f"price_change_{service_type}_-5"
                ),
                InlineKeyboardButton(
                    text="➖ -1", callback_data=f"price_change_{service_type}_-1"
                ),
                InlineKeyboardButton(
                    text="➕ +1", callback_data=f"price_change_{service_type}_+1"
                ),
                InlineKeyboardButton(
                    text="➕ +5", callback_data=f"price_change_{service_type}_+5"
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"💰 {current_price} BYN", callback_data="noop"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Сохранить", callback_data=f"save_price_{service_type}"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data="barber_manage_services"
                ),
            ],
        ]
    )
    return keyboard


def create_time_keyboard(start=0, end=24) -> InlineKeyboardMarkup:
    """Create time selection keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for hour in range(start, end):
        time_str = f"{hour:02d}:00"

        if (hour - start) % 3 == 0:
            keyboard.inline_keyboard.append([])

        keyboard.inline_keyboard[-1].append(
            InlineKeyboardButton(text=time_str, callback_data=f"schedule_time_{hour}")
        )

    return keyboard


@router.callback_query(F.data.startswith("schedule_time_"))
@require_role(UserRole.BARBER)
async def process_start_time_callback(callback: CallbackQuery, state: FSMContext):
    """Process start time selection"""
    hour = int(callback.data.split("_")[-1])
    start_time = time(hour=hour, minute=0)

    data = await state.get_data()

    # Check if date exists in state
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

    # Show end times (only after start time)
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
    """Process end time selection"""
    hour = int(callback.data.split("_")[-1])
    end_time = time(hour=hour, minute=0)

    data = await state.get_data()

    # Check if we have the required data
    if "date" not in data or "start_time" not in data:
        await callback.message.edit_text(
            "❌ Ошибка: данные не найдены. Начни с начала.\n\n" "Нажми кнопку ниже:"
        )
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

    # Show duration selection for haircut
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    durations = [30, 45, 60, 75, 90, 120]

    for duration in durations:
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"⏱️ {duration} мин",
                    callback_data=f"schedule_haircut_duration_{duration}",
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
    """Process haircut duration selection"""
    duration = int(callback.data.split("_")[-1])
    data = await state.get_data()

    await state.update_data(haircut_duration_minutes=duration)

    # Show duration selection for haircut+beard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    durations = [30, 45, 60, 75, 90, 120]

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

    await safe_edit_text(
        callback.message,
        f"📅 Дата: <b>{data['date'].strftime('%d.%m.%Y')}</b>\n"
        f"🕐 Время: <b>{data['start_time'].strftime('%H:%M')} - {data['end_time'].strftime('%H:%M')}</b>\n"
        f"✂️ Стрижка: <b>{duration} мин</b>\n\n"
        "✂️💈 <b>Выбери длительность стрижки + борода</b>",
        reply_markup=keyboard,
    )
    await state.set_state(ScheduleStates.choosing_haircut_and_beard_duration)


@router.callback_query(F.data.startswith("schedule_haircut_beard_duration_"))
@require_role(UserRole.BARBER)
async def process_haircut_and_beard_duration_callback(
    callback: CallbackQuery, state: FSMContext
):
    """Process haircut+beard duration selection and create schedule"""
    duration = int(callback.data.split("_")[-1])
    data = await state.get_data()

    haircut_duration = data.get("haircut_duration_minutes", 60)

    # Create schedule with both durations
    user = await user_service.get_user(callback.from_user.id)
    schedule = await schedule_service.create_schedule(
        barber_id=str(user["_id"]),
        date_obj=data["date"],
        start_time=data["start_time"],
        end_time=data["end_time"],
        haircut_duration_minutes=haircut_duration,
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
        f"✂️💈 Стрижка + Борода: <b>{duration} мин</b>\n\n"
        "Опубликуй расписание, чтобы клиенты могли записаться.",
        reply_markup=keyboard,
    )

    await state.clear()


@router.callback_query(F.data.startswith("publish_schedule_"))
@require_role(UserRole.BARBER)
async def publish_schedule_handler(callback: CallbackQuery):
    """Publish schedule"""
    schedule_id = callback.data.split("_")[-1]

    result = await schedule_service.publish_schedule(schedule_id)
    if result:
        # Get schedule details
        from src.repositories import ScheduleRepository

        repo = ScheduleRepository()
        schedule = await repo.find_by_id(schedule_id)

        slots = await schedule_service.get_available_slots_for_barber(
            str(schedule["barber_id"]), schedule["date"]
        )

        # Get barber name
        user = await user_service.get_user(callback.from_user.id)

        # Notify all subscribers
        # Handle both datetime and string formats for start_time/end_time
        if hasattr(schedule["start_time"], "strftime"):
            start_time_str = schedule["start_time"].strftime("%H:%M")
        else:
            # For string times like "10:00:00", truncate to "10:00"
            start_time_str = (
                schedule["start_time"][:5]
                if len(schedule["start_time"]) > 5
                else schedule["start_time"]
            )

        if hasattr(schedule["end_time"], "strftime"):
            end_time_str = schedule["end_time"].strftime("%H:%M")
        else:
            # For string times like "21:00:00", truncate to "21:00"
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

        # Add booking button
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
            exclude_user_id=str(user["_id"]),  # Exclude barber from notifications
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


@router.callback_query(F.data == "barber_view_appointments")
@require_role(UserRole.BARBER)
async def view_barber_appointments(callback: CallbackQuery):
    """Show barber's appointments"""
    user = await user_service.get_user(callback.from_user.id)
    appointments = await appointment_service.get_barber_appointments(str(user["_id"]))

    # Filter only active appointments
    from src.enums import AppointmentStatus

    active = [
        a for a in appointments if a.get("status") == AppointmentStatus.BOOKED.value
    ]

    if not active:
        await safe_edit_text(
            callback.message, "📅 <b>Мои записи</b>\n\n" "У тебя нет активных записей"
        )
        return

    # Group by date
    from collections import defaultdict

    by_date = defaultdict(list)
    for appt in active:
        by_date[appt["appointment_date"]].append(appt)

    text = "📅 <b>Мои записи</b>\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for date_obj in sorted(by_date.keys()):
        text += f"<b>{date_obj.strftime('%d.%m.%Y')}</b>\n"
        for appt in by_date[date_obj]:
            time_str = appt["appointment_time"]  # appointment_time is already a string
            text += f"  🕐 {time_str} - {appt['client_name']}\n"
            # Add complete and cancel buttons for each appointment
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"✅ Завершить {time_str}",
                        callback_data=f"barber_complete_appt_{appt['_id']}",
                    ),
                    InlineKeyboardButton(
                        text=f"❌ Отменить",
                        callback_data=f"barber_cancel_appt_{appt['_id']}",
                    ),
                ]
            )
        text += "\n"

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="➕ Записать клиента", callback_data="barber_add_appointment"
            ),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    )

    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data == "barber_add_appointment")
@require_role(UserRole.BARBER)
async def barber_add_appointment_handler(callback: CallbackQuery):
    """Show list of clients to book appointment"""
    # Get all subscribed clients
    all_clients = await user_service.get_all_subscribed_clients()

    # Filter to only clients (not barbers)
    clients = [c for c in all_clients if not c.get("is_blocked", False)]

    if not clients:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")]
            ]
        )
        await safe_edit_text(
            callback.message,
            "👥 <b>Мои клиенты</b>\n\n" "Нет доступных клиентов для записи",
            reply_markup=keyboard,
        )
        return

    # Sort clients by name
    clients.sort(key=lambda c: c.get("full_name", ""))

    # Create keyboard with clients (max 10 per page for readability)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for client in clients[:10]:
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"👤 {client['full_name']}",
                    callback_data=f"barber_select_client_{client['_id']}",
                )
            ]
        )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data="barber_view_appointments"
            ),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    )

    text = f"👥 <b>Выбери клиента для записи</b>\n\n"
    text += f"Всего клиентов: <b>{len(clients)}</b>\n\n"
    text += "Нажми на клиента для записи:"

    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("barber_select_client_"))
@require_role(UserRole.BARBER)
async def barber_select_client_handler(callback: CallbackQuery, state: FSMContext):
    """Select client and show available dates"""
    client_id = callback.data.split("_")[-1]

    # Get client info
    repo = UserRepository()
    client = await repo.find_by_id(client_id)

    if not client:
        await callback.answer("❌ Клиент не найден", show_alert=True)
        return

    # Save client_id to state
    await state.update_data(
        selected_client_id=client_id, selected_client_name=client.get("full_name")
    )

    # Get available schedules (dates with slots)
    schedules = await ScheduleRepository().find_many({"is_published": True})

    if not schedules:
        await safe_edit_text(
            callback.message,
            "📅 <b>Нет доступных расписаний</b>\n\n"
            "Сначала создай расписание для записи клиента",
        )
        return

    # Show available dates
    text = f"📅 <b>Выбери дату для {client['full_name']}</b>\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    dates = set()
    for schedule in schedules:
        schedule_date = (
            schedule["date"].date()
            if hasattr(schedule["date"], "date")
            else schedule["date"]
        )
        if schedule_date >= get_today():
            dates.add(schedule_date)

    for date_obj in sorted(dates)[:10]:  # Show max 10 dates
        date_str = date_obj.strftime("%d.%m.%Y")
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=date_str,
                    callback_data=f"barber_select_date_{date_obj.isoformat()}",
                )
            ]
        )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data="barber_add_appointment"
            ),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    )

    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("barber_select_date_"))
@require_role(UserRole.BARBER)
async def barber_select_date_handler(callback: CallbackQuery, state: FSMContext):
    """Select date and show available time slots"""
    date_str = callback.data.split("_")[-1]
    date_obj = datetime.fromisoformat(date_str).date()

    data = await state.get_data()
    client_id = data.get("selected_client_id")
    client_name = data.get("selected_client_name")

    if not client_id:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад", callback_data="barber_add_appointment"
                    )
                ],
                [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
            ]
        )
        await callback.message.edit_text(
            "❌ Ошибка: клиент не выбран. Начни с начала.", reply_markup=keyboard
        )
        return

    # Get available slots for the date
    time_slot_repo = TimeSlotRepository()
    date_start = datetime.combine(date_obj, datetime.min.time())
    date_end = datetime.combine(date_obj, datetime.max.time())

    slots = await time_slot_repo.find_many(
        {"status": "available", "start_time": {"$gte": date_start, "$lte": date_end}}
    )

    if not slots:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад", callback_data="barber_add_appointment"
                    )
                ],
                [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
            ]
        )
        await callback.message.edit_text(
            f"📅 <b>Дата: {date_obj.strftime('%d.%m.%Y')}</b>\n\n"
            "На эту дату нет свободных мест"
        )
        return

    # Show available slots
    text = (
        f"📅 <b>Дата: {date_obj.strftime('%d.%m.%Y')}</b>\n"
        f"👤 <b>Клиент: {client_name}</b>\n\n"
        f"🕐 <b>Выбери время</b>\n\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    tz = get_timezone()
    added_times = set()
    slot_mapping = {}  # Map button index to slot_id

    button_idx = 0
    for slot in sorted(slots, key=lambda s: s["start_time"])[:20]:  # Max 20 slots
        start_time_utc = slot["start_time"]
        if start_time_utc.tzinfo is None:
            start_time_utc = pytz.utc.localize(start_time_utc)
        start_time_local = start_time_utc.astimezone(tz)
        time_str = start_time_local.strftime("%H:%M")

        if time_str in added_times:
            continue

        added_times.add(time_str)
        slot_mapping[button_idx] = str(slot["_id"])
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=time_str, callback_data=f"barber_book_slot_{button_idx}"
                )
            ]
        )
        button_idx += 1

    # Save slot mapping and selected date to state
    logger.info(f"Saving slot_mapping: {slot_mapping}, date: {date_obj}")
    await state.update_data(slot_mapping=slot_mapping, selected_date=date_obj)

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data="barber_add_appointment"
            ),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("barber_book_slot_"))
@require_role(UserRole.BARBER)
async def barber_book_slot_handler(callback: CallbackQuery, state: FSMContext):
    """Show service selection before booking"""
    # Get slot index from callback_data
    slot_idx = int(callback.data.split("_")[-1])

    # Get data from state
    data = await state.get_data()
    slot_mapping = data.get("slot_mapping", {})
    client_id = data.get("selected_client_id")

    logger.info(
        f"Booking slot: idx={slot_idx}, slot_mapping keys={list(slot_mapping.keys())}, client_id={client_id}"
    )

    if slot_idx not in slot_mapping:
        logger.error(
            f"Slot index {slot_idx} not in mapping. Available: {list(slot_mapping.keys())}"
        )
        await callback.answer("❌ Слот не найден", show_alert=True)
        return

    slot_id = slot_mapping[slot_idx]

    # Get client info
    repo = UserRepository()
    client = await repo.find_by_id(client_id)

    if not client:
        await callback.answer("❌ Клиент не найден", show_alert=True)
        return

    # Save slot_id to state for later use
    await state.update_data(selected_slot_id=slot_id)

    # Show service selection
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✂️ Стрижка",
                    callback_data="barber_book_service_haircut",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✂️💈 Стрижка + Борода",
                    callback_data="barber_book_service_haircut_and_beard",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="barber_add_appointment"
                ),
                InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
            ],
        ]
    )

    await safe_edit_text(
        callback.message,
        f"👤 <b>Клиент: {client['full_name']}</b>\n\n" "🪒 <b>Выбери услугу</b>",
        reply_markup=keyboard,
    )
    await state.set_state(BarberBookingStates.choosing_service)


@router.callback_query(F.data.startswith("barber_book_service_"))
@require_role(UserRole.BARBER)
async def barber_book_service_handler(callback: CallbackQuery, state: FSMContext):
    """Book appointment with selected service"""
    service_type = callback.data.replace("barber_book_service_", "")

    # Get data from state
    data = await state.get_data()
    slot_id = data.get("selected_slot_id")
    client_id = data.get("selected_client_id")
    client_name = data.get("selected_client_name")

    if not slot_id or not client_id:
        await callback.answer("❌ Ошибка: данные не найдены", show_alert=True)
        return

    # Get client info
    repo = UserRepository()
    client = await repo.find_by_id(client_id)

    if not client:
        await callback.answer("❌ Клиент не найден", show_alert=True)
        return

    # Book appointment with service type
    appointment = await appointment_service.book_appointment(
        slot_id, client_id, service_type=service_type
    )

    if not appointment:
        await callback.message.edit_text(
            "❌ Ошибка при бронировании. Место может быть уже занято. "
            "Попробуй другое время."
        )
        return

    # Format time and date
    time_str = appointment["appointment_time"]
    date_str = (
        appointment["appointment_date"].strftime("%d.%m.%Y")
        if hasattr(appointment["appointment_date"], "strftime")
        else str(appointment["appointment_date"])
    )
    service_name = "Стрижка" if service_type == "haircut" else "Стрижка + Борода"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Записи", callback_data="barber_view_appointments"
                )
            ],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
        ]
    )

    await callback.message.edit_text(
        f"✅ <b>Запись создана</b>\n\n"
        f"✂️ Услуга: {service_name}\n"
        f"👤 Клиент: {client['full_name']}\n"
        f"📅 Дата: {date_str}\n"
        f"🕐 Время: {time_str}",
        reply_markup=keyboard,
    )

    # Send notification to client
    from src.services import NotificationService

    barber = await user_service.get_user(callback.from_user.id)
    user_repo = UserRepository()
    client = await user_repo.find_by_id(client_id)
    notification_service = NotificationService(callback.bot)

    reminder_time = client.get("reminder_time", "09:00") if client else "09:00"

    message = (
        f"<b>✂️ Вас записали!</b>\n\n"
        f"✂️ Услуга: {service_name}\n"
        f"✂️ Барбер: {barber['full_name']}\n"
        f"📅 Дата: {date_str}\n"
        f"🕐 Время: {time_str}\n\n"
        f"⏰ В день приема получишь напоминание в {reminder_time}"
    )

    await notification_service.notify_user(
        user_id=client_id,
        notification_type=NotificationType.APPOINTMENT_BOOKED,
        title="✂️ Запись подтверждена",
        message=message,
    )

    await state.clear()


@router.callback_query(F.data.startswith("barber_complete_appt_"))
@require_role(UserRole.BARBER)
async def barber_complete_appointment_handler(callback: CallbackQuery):
    """Complete appointment (barber)"""
    appointment_id = callback.data.split("_")[-1]

    # Get appointment details
    appointment = await appointment_service.appointment_repo.find_by_id(appointment_id)

    if not appointment:
        await callback.message.edit_text("❌ Запись не найдена")
        return

    # Complete the appointment and award referral bonus if applicable
    result = await appointment_service.complete_appointment(appointment_id)

    if result:
        time_str = appointment["appointment_time"]
        date_str = (
            appointment["appointment_date"].strftime("%d.%m.%Y")
            if hasattr(appointment["appointment_date"], "strftime")
            else str(appointment["appointment_date"])
        )
        client_name = appointment["client_name"]

        # Check if referral bonus was awarded
        from src.services import UserService

        user_service_instance = UserService()
        client = await user_service_instance.user_repo.find_by_id(
            str(appointment["client_id"])
        )

        bonus_message = ""
        if client and client.get("referred_by"):
            bonus_message = f"\n\n💰 Бонус начислен рефереру!"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Вернуться к записям",
                        callback_data="barber_view_appointments",
                    )
                ],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")],
            ]
        )

        await callback.message.edit_text(
            f"✅ <b>Запись завершена</b>\n\n"
            f"👤 Клиент: {client_name}\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}{bonus_message}",
            reply_markup=keyboard,
        )
    else:
        await callback.message.edit_text("❌ Ошибка при завершении записи")


@router.callback_query(F.data.startswith("barber_cancel_appt_"))
@require_role(UserRole.BARBER)
async def barber_cancel_appointment_handler(callback: CallbackQuery):
    """Cancel appointment (barber)"""
    appointment_id = callback.data.split("_")[-1]

    # Get appointment details before canceling
    appointment = await appointment_service.appointment_repo.find_by_id(appointment_id)

    if not appointment:
        await callback.message.edit_text("❌ Запись не найдена")
        return

    result = await appointment_service.cancel_appointment(
        appointment_id=appointment_id,
        cancelled_by="BARBER",
        reason="Барбер отменил запись",
    )

    if result:
        time_str = appointment["appointment_time"]
        date_str = (
            appointment["appointment_date"].strftime("%d.%m.%Y")
            if hasattr(appointment["appointment_date"], "strftime")
            else str(appointment["appointment_date"])
        )
        client_name = appointment["client_name"]

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 Вернуться к записям",
                        callback_data="barber_view_appointments",
                    )
                ],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")],
            ]
        )

        await callback.message.edit_text(
            f"✅ <b>Запись отменена</b>\n\n"
            f"👤 Клиент: {client_name}\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}\n\n"
            "Клиент получил уведомление об отмене",
            reply_markup=keyboard,
        )

        # Notify client
        barber = await user_service.get_user(callback.from_user.id)
        notification_service = NotificationService(callback.bot)

        message = (
            f"<b>❌ Ваша запись была отменена</b>\n\n"
            f"✂️ Барбер: {barber['full_name']}\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}\n\n"
            f"💬 Вы можете записаться на другое время"
        )

        await notification_service.notify_user(
            user_id=str(appointment["client_id"]),
            notification_type=NotificationType.APPOINTMENT_CANCELLED,
            title="❌ Запись отменена",
            message=message,
        )
    else:
        await callback.message.edit_text("❌ Ошибка при отмене записи")


@router.callback_query(F.data.startswith("view_client_"))
@require_role(UserRole.BARBER)
async def view_client_details(callback: CallbackQuery):
    """Show client details (active client)"""
    client_id = callback.data.split("_")[-1]

    # Get client details
    from src.repositories import UserRepository

    repo = UserRepository()
    client = await repo.find_by_id(client_id)

    if not client:
        await callback.message.edit_text("❌ Клиент не найден")
        return

    # Get client appointments count
    client_appointments = await appointment_service.get_client_appointments(client_id)
    total_appointments = len(client_appointments)

    from src.enums import AppointmentStatus

    completed = len(
        [
            a
            for a in client_appointments
            if a.get("status") == AppointmentStatus.COMPLETED.value
        ]
    )
    active = len(
        [
            a
            for a in client_appointments
            if a.get("status") == AppointmentStatus.BOOKED.value
        ]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚫 Черный список", callback_data=f"block_client_{client_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="barber_view_clients"
                ),
                InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
            ],
        ]
    )

    text = (
        f"👤 <b>Информация о клиенте</b>\n\n"
        f"<b>Имя:</b> {client['full_name']}\n"
        f"<b>Телефон:</b> {client.get('phone', 'Не указано')}\n"
        f"<b>Username:</b> @{client.get('username', 'не установлено')}\n\n"
        f"<b>Статистика:</b>\n"
        f"  • Всего записей: {total_appointments}\n"
        f"  • Активных: {active}\n"
        f"  • Завершено: {completed}\n"
        f"  • Визитов: {client.get('visit_count', 0)}\n\n"
        f"<b>Статус:</b> {'✅ Активен' if client.get('is_active') else '❌ Неактивен'}\n"
        f"<b>Уведомления:</b> {'✅ Включены' if client.get('is_subscribed') else '❌ Отключены'}"
    )

    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("view_blacklist_client_"))
@require_role(UserRole.BARBER)
async def view_blacklist_client_details(callback: CallbackQuery):
    """Show blacklisted client details"""
    client_id = callback.data.split("_")[-1]

    # Get client details
    from src.repositories import UserRepository

    repo = UserRepository()
    client = await repo.find_by_id(client_id)

    if not client:
        await callback.message.edit_text("❌ Клиент не найден")
        return

    # Get client appointments count
    client_appointments = await appointment_service.get_client_appointments(client_id)
    total_appointments = len(client_appointments)

    from src.enums import AppointmentStatus

    completed = len(
        [
            a
            for a in client_appointments
            if a.get("status") == AppointmentStatus.COMPLETED.value
        ]
    )
    active = len(
        [
            a
            for a in client_appointments
            if a.get("status") == AppointmentStatus.BOOKED.value
        ]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Разблокировать",
                    callback_data=f"unblock_client_{client_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к чёрному списку",
                    callback_data="barber_view_blacklist",
                )
            ],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")],
        ]
    )

    text = (
        f"🚫 <b>Заблокированный клиент</b>\n\n"
        f"<b>Имя:</b> {client['full_name']}\n"
        f"<b>Телефон:</b> {client.get('phone', 'Не указано')}\n"
        f"<b>Username:</b> @{client.get('username', 'не установлено')}\n\n"
        f"<b>Статистика:</b>\n"
        f"  • Всего записей: {total_appointments}\n"
        f"  • Активных: {active}\n"
        f"  • Завершено: {completed}\n"
        f"  • Визитов: {client.get('visit_count', 0)}\n\n"
        f"<b>Статус:</b> {'✅ Активен' if client.get('is_active') else '❌ Неактивен'}\n"
        f"<b>Уведомления:</b> {'✅ Включены' if client.get('is_subscribed') else '❌ Отключены'}\n"
        f"<b>Статус:</b> 🚫 <b>В чёрном списке</b>"
    )

    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("block_client_"))
@require_role(UserRole.BARBER)
async def block_client_handler(callback: CallbackQuery):
    """Block client from receiving notifications"""
    client_id = callback.data.split("_")[-1]

    # Block the client
    success = await user_service.block_user(client_id)

    if success:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад к списку", callback_data="barber_view_clients"
                    )
                ],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")],
            ]
        )

        await callback.message.edit_text(
            "✅ <b>Клиент добавлен в чёрный список</b>\n\n"
            "Клиент больше не будет получать уведомления о новых расписаниях и других событиях.",
            reply_markup=keyboard,
        )

        logger.info(f"Barber {callback.from_user.id} blocked client {client_id}")
    else:
        await callback.message.edit_text("❌ Ошибка при добавлении в чёрный список")


@router.callback_query(F.data.startswith("unblock_client_"))
@require_role(UserRole.BARBER)
async def unblock_client_handler(callback: CallbackQuery):
    """Unblock client to receive notifications"""
    client_id = callback.data.split("_")[-1]

    # Unblock the client
    success = await user_service.unblock_user(client_id)

    if success:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад к чёрному списку",
                        callback_data="barber_view_blacklist",
                    )
                ],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")],
            ]
        )

        await callback.message.edit_text(
            "✅ <b>Клиент разблокирован</b>\n\n"
            "Клиент будет получать уведомления о новых расписаниях и других событиях.",
            reply_markup=keyboard,
        )

        logger.info(f"Barber {callback.from_user.id} unblocked client {client_id}")
    else:
        await callback.message.edit_text("❌ Ошибка при разблокировке клиента")


@router.callback_query(F.data == "barber_profile")
@require_role(UserRole.BARBER)
async def barber_profile_handler(callback: CallbackQuery):
    """Show barber profile"""
    user = await user_service.get_user(callback.from_user.id)
    appointments = await appointment_service.get_barber_appointments(str(user["_id"]))

    from src.enums import AppointmentStatus

    completed = len(
        [
            a
            for a in appointments
            if a.get("status") == AppointmentStatus.COMPLETED.value
        ]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Имя", callback_data="barber_edit_name"),
                InlineKeyboardButton(
                    text="✏️ Телефон", callback_data="barber_edit_phone"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💰 Услуги", callback_data="barber_manage_services"
                ),
                InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
            ],
        ]
    )

    await safe_edit_text(
        callback.message,
        f"👤 <b>Мой профиль</b>\n\n"
        f"Имя: {user['full_name']}\n"
        f"Телефон: {user.get('phone', 'Не указано')}\n"
        f"Завершено услуг: {completed}",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "barber_edit_name")
@require_role(UserRole.BARBER)
async def barber_edit_name_start(callback: CallbackQuery, state: FSMContext):
    """Start editing barber name"""
    user = await user_service.get_user(callback.from_user.id)

    await callback.message.edit_text(
        f"👤 Текущее имя: <b>{user['full_name']}</b>\n\n" "Введи новое имя:"
    )
    await state.set_state(BarberProfileEditStates.editing_name)


@router.message(BarberProfileEditStates.editing_name, F.text)
@require_role(UserRole.BARBER)
async def barber_edit_name_process(message: Message, state: FSMContext):
    """Process new barber name"""
    if not validate_name(message.text):
        await message.answer("❌ Имя должно быть минимум 2 символа. Попробуй ещё раз:")
        return

    success = await user_service.update_user_profile(
        telegram_id=message.from_user.id, full_name=message.text
    )

    if success:
        await message.answer(
            f"✅ <b>Имя обновлено!</b>\n\n" f"Твое новое имя: <b>{message.text}</b>"
        )

        user = await user_service.get_user(message.from_user.id)
        appointments = await appointment_service.get_barber_appointments(
            str(user["_id"])
        )

        from src.enums import AppointmentStatus

        completed = len(
            [
                a
                for a in appointments
                if a.get("status") == AppointmentStatus.COMPLETED.value
            ]
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ Изменить имя", callback_data="barber_edit_name"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✏️ Изменить телефон", callback_data="barber_edit_phone"
                    )
                ],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")],
            ]
        )

        await message.answer(
            f"👤 <b>Мой профиль</b>\n\n"
            f"Имя: {user['full_name']}\n"
            f"Телефон: {user.get('phone', 'Не указано')}\n"
            f"Завершено услуг: {completed}",
            reply_markup=keyboard,
        )
    else:
        await message.answer("❌ Ошибка при обновлении имени. Попробуй ещё раз.")

    await state.clear()


@router.callback_query(F.data == "barber_edit_phone")
@require_role(UserRole.BARBER)
async def barber_edit_phone_start(callback: CallbackQuery, state: FSMContext):
    """Start editing barber phone"""
    user = await user_service.get_user(callback.from_user.id)

    await callback.message.edit_text(
        f"📞 Текущий номер: <b>{user.get('phone', 'Не указано')}</b>\n\n"
        "Введи новый номер телефона:\n\n"
        "Подходящие форматы:\n"
        "• +375XXXXXXXXX (с плюсом)\n"
        "• 375XXXXXXXXX (без плюса - добавится автоматически)\n"
        "• 0XXXXXXXXX (локальный формат)"
    )
    await state.set_state(BarberProfileEditStates.editing_phone)


@router.message(BarberProfileEditStates.editing_phone, F.text)
@require_role(UserRole.BARBER)
async def barber_edit_phone_process(message: Message, state: FSMContext):
    """Process new barber phone"""
    if not validate_phone(message.text):
        await message.answer(
            "❌ Неверный формат телефона. Попробуй ещё раз:\n\n"
            "Подходящие форматы:\n"
            "• +375XXXXXXXXX (с плюсом)\n"
            "• 375XXXXXXXXX (без плюса)\n"
            "• 0XXXXXXXXX (локальный формат)"
        )
        return

    success = await user_service.update_user_profile(
        telegram_id=message.from_user.id, phone=message.text
    )

    if success:
        await message.answer(
            f"✅ <b>Номер телефона обновлен!</b>\n\n"
            f"Новый номер: <b>{message.text}</b>"
        )

        user = await user_service.get_user(message.from_user.id)
        appointments = await appointment_service.get_barber_appointments(
            str(user["_id"])
        )

        from src.enums import AppointmentStatus

        completed = len(
            [
                a
                for a in appointments
                if a.get("status") == AppointmentStatus.COMPLETED.value
            ]
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ Изменить имя", callback_data="barber_edit_name"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✏️ Изменить телефон", callback_data="barber_edit_phone"
                    )
                ],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")],
            ]
        )

        await message.answer(
            f"👤 <b>Мой профиль</b>\n\n"
            f"Имя: {user['full_name']}\n"
            f"Телефон: {user.get('phone', 'Не указано')}\n"
            f"Завершено услуг: {completed}",
            reply_markup=keyboard,
        )
    else:
        await message.answer(
            "❌ Ошибка при обновлении номера телефона. Попробуй ещё раз."
        )

    await state.clear()


@router.callback_query(F.data == "barber_view_clients")
@require_role(UserRole.BARBER)
async def barber_view_clients(callback: CallbackQuery):
    """Show all active clients to barber (excluding blocked)"""
    # Get all subscribed clients
    all_clients = await user_service.get_all_subscribed_clients()

    # Filter out blocked clients
    clients = [c for c in all_clients if not c.get("is_blocked", False)]

    if not clients:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")]
            ]
        )
        await callback.message.edit_text(
            "👥 <b>Мои клиенты</b>\n\n" "Нет активных клиентов", reply_markup=keyboard
        )
        return

    # Sort clients by name
    clients.sort(key=lambda c: c.get("full_name", ""))

    # Create keyboard with clients (max 10 per page for readability)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for client in clients[:10]:
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"👤 {client['full_name']}",
                    callback_data=f"view_client_{client['_id']}",
                )
            ]
        )

    # Get count of blocked clients
    all_clients = await user_service.get_all_subscribed_clients()
    blocked_clients = [c for c in all_clients if c.get("is_blocked", False)]

    # Only show blacklist button if there are blocked clients
    if blocked_clients:
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🚫 Чёрный список ({len(blocked_clients)})",
                    callback_data="barber_view_blacklist",
                )
            ]
        )

    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")]
    )

    text = f"👥 <b>Мои клиенты</b>\n\n"
    text += f"Активных клиентов: <b>{len(clients)}</b>\n\n"
    text += "Выбери клиента для просмотра информации:"

    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "barber_view_blacklist")
@require_role(UserRole.BARBER)
async def barber_view_blacklist(callback: CallbackQuery):
    """Show blacklisted clients to barber"""
    # Get all subscribed clients
    all_clients = await user_service.get_all_subscribed_clients()

    # Filter only blocked clients
    blocked_clients = [c for c in all_clients if c.get("is_blocked", False)]

    if not blocked_clients:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")]
            ]
        )
        await callback.message.edit_text(
            "🚫 <b>Чёрный список</b>\n\n" "Нет заблокированных клиентов",
            reply_markup=keyboard,
        )
        return

    # Sort clients by name
    blocked_clients.sort(key=lambda c: c.get("full_name", ""))

    # Create keyboard with blocked clients
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for client in blocked_clients[:10]:
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🚫 {client['full_name']}",
                    callback_data=f"view_blacklist_client_{client['_id']}",
                )
            ]
        )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к активным клиентам", callback_data="barber_view_clients"
            )
        ]
    )
    keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")]
    )

    text = f"🚫 <b>Чёрный список</b>\n\n"
    text += f"Заблокировано клиентов: <b>{len(blocked_clients)}</b>\n\n"
    text += "Выбери клиента для разблокировки:"

    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "barber_manage_services")
@require_role(UserRole.BARBER)
async def barber_manage_services(callback: CallbackQuery):
    """Show services management"""
    user = await user_service.get_user(callback.from_user.id)
    services = await user_service.get_barber_services(str(user["_id"]))

    # Format prices - always show all three services
    if not services:
        services = {}

    haircut = services.get("haircut")
    beard_trim = services.get("beard_trim")
    haircut_and_beard = services.get("haircut_and_beard")
    updated_at = services.get("updated_at")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✂️ Стрижка", callback_data="edit_service_haircut"
                ),
                InlineKeyboardButton(
                    text="💈 Борода", callback_data="edit_service_beard_trim"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✂️💈 Комбо", callback_data="edit_service_haircut_and_beard"
                ),
            ],
            [
                InlineKeyboardButton(text="⬅️ Профиль", callback_data="barber_profile"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
            ],
        ]
    )

    updated_text = ""
    if updated_at:
        if isinstance(updated_at, str):
            updated_text = f"\n⏰ <i>Последнее обновление: {updated_at}</i>"
        else:
            updated_text = f"\n⏰ <i>Последнее обновление: {updated_at.strftime('%d.%m.%Y %H:%M')}</i>"

    services_text = (
        f"💰 <b>Мои услуги (в BYN)</b>\n\n"
        f"✂️ <b>Стрижка:</b> {haircut if haircut is not None else 'не установлена'} BYN\n"
        f"💈 <b>Стрижка бороды:</b> {beard_trim if beard_trim is not None else 'не установлена'} BYN\n"
        f"✂️💈 <b>Стрижка + Борода:</b> {haircut_and_beard if haircut_and_beard is not None else 'не установлена'} BYN\n"
        f"{updated_text}\n\n"
        "Нажми на услугу для редактирования цены:"
    )

    await callback.message.edit_text(services_text, reply_markup=keyboard)


@router.callback_query(F.data == "edit_service_haircut")
@require_role(UserRole.BARBER)
async def edit_service_haircut(callback: CallbackQuery, state: FSMContext):
    """Start editing haircut price"""
    user = await user_service.get_user(callback.from_user.id)
    services = await user_service.get_barber_services(str(user["_id"]))

    if not services:
        services = {}

    current_haircut = services.get("haircut") or 0
    current_beard_trim = services.get("beard_trim")
    current_haircut_and_beard = services.get("haircut_and_beard")

    await state.update_data(service_type="haircut", temp_price=current_haircut)

    current_text = (
        f"✂️ <b>Стрижка</b>\n\n"
        f"<b>Текущие цены:</b>\n"
        f"✂️ Стрижка: {current_haircut if current_haircut else 'не установлена'} BYN\n"
        f"💈 Стрижка бороды: {current_beard_trim if current_beard_trim is not None else 'не установлена'} BYN\n"
        f"✂️💈 Стрижка + Борода: {current_haircut_and_beard if current_haircut_and_beard is not None else 'не установлена'} BYN\n\n"
        "<b>Выбери новую цену:</b>"
    )

    keyboard = create_price_keyboard(current_haircut, "haircut")
    await callback.message.edit_text(current_text, reply_markup=keyboard)
    await state.set_state(BarberServiceStates.choosing_price)


@router.callback_query(F.data == "edit_service_beard_trim")
@require_role(UserRole.BARBER)
async def edit_service_beard_trim(callback: CallbackQuery, state: FSMContext):
    """Start editing beard trim price"""
    user = await user_service.get_user(callback.from_user.id)
    services = await user_service.get_barber_services(str(user["_id"]))

    if not services:
        services = {}

    current_haircut = services.get("haircut")
    current_beard_trim = services.get("beard_trim") or 0
    current_haircut_and_beard = services.get("haircut_and_beard")

    await state.update_data(service_type="beard_trim", temp_price=current_beard_trim)

    current_text = (
        f"💈 <b>Стрижка бороды</b>\n\n"
        f"<b>Текущие цены:</b>\n"
        f"✂️ Стрижка: {current_haircut if current_haircut is not None else 'не установлена'} BYN\n"
        f"💈 Стрижка бороды: {current_beard_trim if current_beard_trim else 'не установлена'} BYN\n"
        f"✂️💈 Стрижка + Борода: {current_haircut_and_beard if current_haircut_and_beard is not None else 'не установлена'} BYN\n\n"
        "<b>Выбери новую цену:</b>"
    )

    keyboard = create_price_keyboard(current_beard_trim, "beard_trim")
    await callback.message.edit_text(current_text, reply_markup=keyboard)
    await state.set_state(BarberServiceStates.choosing_price)


@router.callback_query(F.data == "edit_service_haircut_and_beard")
@require_role(UserRole.BARBER)
async def edit_service_haircut_and_beard(callback: CallbackQuery, state: FSMContext):
    """Start editing haircut + beard price"""
    user = await user_service.get_user(callback.from_user.id)
    services = await user_service.get_barber_services(str(user["_id"]))

    if not services:
        services = {}

    current_haircut = services.get("haircut")
    current_beard_trim = services.get("beard_trim")
    current_haircut_and_beard = services.get("haircut_and_beard") or 0

    await state.update_data(
        service_type="haircut_and_beard", temp_price=current_haircut_and_beard
    )

    current_text = (
        f"✂️💈 <b>Стрижка + Борода</b>\n\n"
        f"<b>Текущие цены:</b>\n"
        f"✂️ Стрижка: {current_haircut if current_haircut is not None else 'не установлена'} BYN\n"
        f"💈 Стрижка бороды: {current_beard_trim if current_beard_trim is not None else 'не установлена'} BYN\n"
        f"✂️💈 Стрижка + Борода: {current_haircut_and_beard if current_haircut_and_beard else 'не установлена'} BYN\n\n"
        "<b>Выбери новую цену:</b>"
    )

    keyboard = create_price_keyboard(current_haircut_and_beard, "haircut_and_beard")
    await callback.message.edit_text(current_text, reply_markup=keyboard)
    await state.set_state(BarberServiceStates.choosing_price)


@router.callback_query(F.data.startswith("price_change_"))
@require_role(UserRole.BARBER)
async def price_change_handler(callback: CallbackQuery, state: FSMContext):
    """Handle price increment/decrement"""
    parts = callback.data.split("_")
    service_type = "_".join(parts[2:-1])
    change = int(parts[-1])

    data = await state.get_data()
    current_price = data.get("temp_price", 0)
    new_price = max(0, current_price + change)

    await state.update_data(temp_price=new_price)

    user = await user_service.get_user(callback.from_user.id)
    services = await user_service.get_barber_services(str(user["_id"]))

    if not services:
        services = {}

    current_haircut = services.get("haircut")
    current_beard_trim = services.get("beard_trim")
    current_haircut_and_beard = services.get("haircut_and_beard")

    service_names = {
        "haircut": "✂️ Стрижка",
        "beard_trim": "💈 Стрижка бороды",
        "haircut_and_beard": "✂️💈 Стрижка + Борода",
    }

    current_text = (
        f"{service_names.get(service_type, 'Услуга')}\n\n"
        f"<b>Текущие цены:</b>\n"
        f"✂️ Стрижка: {current_haircut if current_haircut is not None else 'не установлена'} BYN\n"
        f"💈 Стрижка бороды: {current_beard_trim if current_beard_trim is not None else 'не установлена'} BYN\n"
        f"✂️💈 Стрижка + Борода: {current_haircut_and_beard if current_haircut_and_beard is not None else 'не установлена'} BYN\n\n"
        "<b>Выбери новую цену:</b>"
    )

    keyboard = create_price_keyboard(new_price, service_type)
    await callback.message.edit_text(current_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("save_price_"))
@require_role(UserRole.BARBER)
async def save_price_handler(callback: CallbackQuery, state: FSMContext):
    """Save the selected price"""
    service_type = callback.data.replace("save_price_", "")
    data = await state.get_data()
    new_price = data.get("temp_price", 0)

    user = await user_service.get_user(callback.from_user.id)

    # Build kwargs with proper parameter names
    kwargs = {}
    if service_type == "haircut":
        kwargs["haircut"] = new_price
    elif service_type == "beard_trim":
        kwargs["beard_trim"] = new_price
    elif service_type == "haircut_and_beard":
        kwargs["haircut_and_beard"] = new_price

    success = await user_service.update_barber_services(str(user["_id"]), **kwargs)

    if success:
        service_names = {
            "haircut": "стрижку",
            "beard_trim": "стрижку бороды",
            "haircut_and_beard": "стрижку + бороду",
        }
        await callback.answer(
            f"✅ Цена на {service_names.get(service_type, 'услугу')} обновлена: {new_price} BYN",
            show_alert=True,
        )
    else:
        await callback.answer("❌ Ошибка при обновлении цены", show_alert=True)

    await state.clear()

    # Show services menu again
    services = await user_service.get_barber_services(str(user["_id"]))
    if not services:
        services = {}

    haircut = services.get("haircut")
    beard_trim = services.get("beard_trim")
    haircut_and_beard = services.get("haircut_and_beard")
    updated_at = services.get("updated_at")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✂️ Стрижка", callback_data="edit_service_haircut"
                ),
                InlineKeyboardButton(
                    text="💈 Борода", callback_data="edit_service_beard_trim"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✂️💈 Комбо", callback_data="edit_service_haircut_and_beard"
                ),
            ],
            [
                InlineKeyboardButton(text="⬅️ Профиль", callback_data="barber_profile"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
            ],
        ]
    )

    updated_text = ""
    if updated_at:
        if isinstance(updated_at, str):
            updated_text = f"\n⏰ <i>Последнее обновление: {updated_at}</i>"
        else:
            updated_text = f"\n⏰ <i>Последнее обновление: {updated_at.strftime('%d.%m.%Y %H:%M')}</i>"

    services_text = (
        f"💰 <b>Мои услуги (в BYN)</b>\n\n"
        f"✂️ <b>Стрижка:</b> {haircut if haircut is not None else 'не установлена'} BYN\n"
        f"💈 <b>Стрижка бороды:</b> {beard_trim if beard_trim is not None else 'не установлена'} BYN\n"
        f"✂️💈 <b>Стрижка + Борода:</b> {haircut_and_beard if haircut_and_beard is not None else 'не установлена'} BYN\n"
        f"{updated_text}\n\n"
        "Нажми на услугу для редактирования цены:"
    )

    await callback.message.edit_text(services_text, reply_markup=keyboard)
