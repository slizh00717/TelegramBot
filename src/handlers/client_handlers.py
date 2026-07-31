from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
)
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import pytz
from src.services import (
    AppointmentService,
    ScheduleService,
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
from src.enums import UserRole, AppointmentStatus, NotificationType
from src.repositories import ScheduleRepository, TimeSlotRepository

router = Router()
appointment_service = AppointmentService()
schedule_service = ScheduleService()
user_service = UserService()


def get_client_profile_keyboard() -> InlineKeyboardMarkup:
    """Create client profile keyboard"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Имя", callback_data="client_edit_name"),
                InlineKeyboardButton(
                    text="✏️ Телефон", callback_data="client_edit_phone"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏰ Напоминание", callback_data="client_edit_reminder"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎁 Пригласить", callback_data="client_invite_friend"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить", callback_data="client_delete_account"
                ),
                InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
            ],
        ]
    )


class ProfileEditStates(StatesGroup):
    editing_name = State()
    editing_phone = State()
    confirming_deletion = State()
    editing_reminder = State()


class PriceViewStates(StatesGroup):
    viewing_price = State()


class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()


@router.callback_query(F.data == "client_book_appointment")
@require_role(UserRole.CLIENT)
async def book_appointment_handler(callback: CallbackQuery, state: FSMContext):
    """Start appointment booking - choose service"""
    await state.clear()

    keyboard = InlineKeyboardMarkup(
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
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")],
        ]
    )

    try:
        await callback.message.edit_text(
            "🪒 <b>Выбери услугу</b>\n\n"
            "✂️ <b>Стрижка</b> - классическая стрижка\n"
            "💈 <b>Стрижка бороды</b> - уход за бородой\n"
            "✂️💈 <b>Стрижка + Борода</b> - полный уход",
            reply_markup=keyboard,
        )
        await state.set_state(BookingStates.choosing_service)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.startswith("select_service_"))
@require_role(UserRole.CLIENT)
async def select_service_handler(callback: CallbackQuery, state: FSMContext):
    """Handle service selection"""
    service_type = callback.data.replace("select_service_", "")

    await state.update_data(selected_service=service_type)

    # Get available dates
    schedule_repo = ScheduleRepository()
    schedules = await schedule_repo.find_many({"is_published": True})

    if not schedules:
        await callback.message.edit_text(
            "📅 <b>Записаться</b>\n\n"
            "😔 К сожалению, нет доступных расписаний. "
            "Попробуй позже или свяжись с барбером"
        )
        await state.clear()
        return

    # Show available dates
    text = (
        "📅 <b>Выбери дату</b>\n\n"
        f"Услуга: <b>{'Стрижка' if service_type == 'haircut' else 'Стрижка + Борода'}</b>\n\n"
    )
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

    for date_obj in sorted(dates)[:10]:
        date_str = date_obj.strftime("%d.%m.%Y")
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=date_str, callback_data=f"select_date_{date_obj.isoformat()}"
                )
            ]
        )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data="client_book_appointment"
            ),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu"),
        ]
    )

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(BookingStates.choosing_date)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.startswith("select_date_"))
@require_role(UserRole.CLIENT)
async def select_date_handler(callback: CallbackQuery, state: FSMContext):
    """Show available slots for selected date and service"""
    date_str = callback.data.split("_")[-1]
    date_obj = datetime.fromisoformat(date_str).date()

    # Get selected service type
    data = await state.get_data()
    service_type = data.get("selected_service", "haircut")

    # Get schedule repo to find all barbers with schedules on this date
    schedule_repo = ScheduleRepository()
    schedule_service = ScheduleService()

    schedules = await schedule_repo.find_many({"is_published": True})

    # Collect all slots from all barbers for this date and service type
    all_slots = []
    barber_info = {}

    for schedule in schedules:
        schedule_date = (
            schedule["date"].date()
            if hasattr(schedule["date"], "date")
            else schedule["date"]
        )

        if schedule_date == date_obj:
            barber_id = str(schedule["barber_id"])
            slots = await schedule_service.get_available_slots_for_service(
                barber_id, date_obj, service_type
            )
            all_slots.extend(slots)
            barber_info[barber_id] = schedule

    if not all_slots:
        try:
            await callback.message.edit_text(
                f"📅 Выбранная дата: <b>{date_obj.strftime('%d.%m.%Y')}</b>\n\n"
                "😔 На эту дату нет свободных мест"
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        return

    # Show available slots
    service_name = "Стрижка" if service_type == "haircut" else "Стрижка + Борода"
    text = (
        f"📅 Выбранная дата: <b>{date_obj.strftime('%d.%m.%Y')}</b>\n"
        f"Услуга: <b>{service_name}</b>\n\n"
        f"🕐 <b>Выбери время</b>\n\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    tz = get_timezone()
    added_times = set()
    slot_mapping = {}
    button_idx = 0

    for slot in sorted(all_slots, key=lambda s: s["start_time"])[:20]:
        start_time_utc = slot["start_time"]
        if start_time_utc.tzinfo is None:
            start_time_utc = pytz.utc.localize(start_time_utc)
        start_time_local = start_time_utc.astimezone(tz)
        time_str = start_time_local.strftime("%H:%M")

        if time_str in added_times:
            continue

        added_times.add(time_str)
        slot_mapping[button_idx] = slot
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=time_str, callback_data=f"book_slot_{button_idx}"
                )
            ]
        )
        button_idx += 1

    # Save slot mapping and service type to state
    await state.update_data(
        slot_mapping=slot_mapping, booking_date=date_obj, booking_service=service_type
    )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data="client_book_appointment"
            ),
        ]
    )

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(BookingStates.choosing_time)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@router.callback_query(F.data.startswith("book_slot_"))
@require_role(UserRole.CLIENT)
async def confirm_booking_handler(callback: CallbackQuery, state: FSMContext):
    """Confirm appointment booking"""
    button_idx = int(callback.data.split("_")[-1])

    # Get data from state
    data = await state.get_data()
    slot_mapping = data.get("slot_mapping", {})
    service_type = data.get("booking_service", "haircut")

    if button_idx not in slot_mapping:
        await callback.message.edit_text("❌ Ошибка: слот не найден. Попробуй ещё раз.")
        return

    slot = slot_mapping[button_idx]

    # Get user
    user = await user_service.get_user(callback.from_user.id)

    # Get barber info from slot
    barber_id = str(slot["barber_id"])
    barber = await user_service.user_repo.find_by_id(barber_id)

    # Book appointment with service type
    appointment = await appointment_service.book_appointment(
        slot, str(user["_id"]), service_type=service_type
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

    reminder_time = user.get("reminder_time", "09:00")

    await callback.message.edit_text(
        f"✅ <b>Запись подтверждена</b>\n\n"
        f"✂️ Услуга: {service_name}\n"
        f"👤 Барбер: {barber.get('full_name', 'Барбер') if barber else 'Барбер'}\n"
        f"📅 Дата: {date_str}\n"
        f"🕐 Время: {time_str}\n\n"
        f"⏰ В день приема получишь напоминание в {reminder_time}"
    )

    # Notify barber via direct message
    try:
        await callback.bot.send_message(
            chat_id=settings.barber_chat_id,
            text=(
                f"📝 <b>Новая запись</b>\n\n"
                f"✂️ Услуга: {service_name}\n"
                f"👤 Клиент: {user['full_name']}\n"
                f"📱 Телефон: {user.get('phone', 'не указан')}\n"
                f"📅 Дата: {date_str}\n"
                f"🕐 Время: {time_str}"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Could not send booking notification to barber: {e}")

    logger.info(
        f"Client {callback.from_user.id} booked appointment {appointment['_id']} for service {service_type}"
    )

    await state.clear()


@router.callback_query(F.data == "client_view_appointments")
@require_role(UserRole.CLIENT)
async def view_client_appointments(callback: CallbackQuery):
    """Show client's appointments"""
    user = await user_service.get_user(callback.from_user.id)
    appointments = await appointment_service.get_client_appointments(str(user["_id"]))

    if not appointments:
        await callback.message.edit_text(
            "📅 <b>Мои записи</b>\n\n" "У тебя нет записей"
        )
        return

    # Group by status
    from collections import defaultdict

    by_status = defaultdict(list)
    for appt in appointments:
        by_status[appt["status"]].append(appt)

    text = "📅 <b>Мои записи</b>\n\n"
    keyboard_buttons = []

    # Show active appointments
    if by_status.get(AppointmentStatus.BOOKED.value):
        text += "<b>📌 Активные записи</b>\n"
        for appt in sorted(
            by_status[AppointmentStatus.BOOKED.value],
            key=lambda a: a["appointment_date"],
        ):
            date_str = (
                appt["appointment_date"].strftime("%d.%m.%Y")
                if hasattr(appt["appointment_date"], "strftime")
                else str(appt["appointment_date"])
            )
            time_str = appt["appointment_time"]  # appointment_time is already a string
            text += f"  {date_str} в {time_str}\n"

            # Add cancel button for each appointment
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"❌ Отменить {time_str}",
                        callback_data=f"cancel_appt_{appt['_id']}",
                    )
                ]
            )
        text += "\n"

    # Show completed appointments
    if by_status.get(AppointmentStatus.COMPLETED.value):
        text += "<b>✅ Завершённые</b>\n"
        for appt in by_status[AppointmentStatus.COMPLETED.value][-5:]:  # Last 5
            date_str = (
                appt["appointment_date"].strftime("%d.%m.%Y")
                if hasattr(appt["appointment_date"], "strftime")
                else str(appt["appointment_date"])
            )
            time_str = appt["appointment_time"]  # appointment_time is already a string
            text += f"  {date_str} в {time_str}\n"

    # Add menu button at the end
    keyboard_buttons.append(
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("cancel_appt_"))
@require_role(UserRole.CLIENT)
async def cancel_appointment_handler(callback: CallbackQuery):
    """Cancel appointment"""
    appointment_id = callback.data.split("_")[-1]

    result = await appointment_service.cancel_appointment(
        appointment_id=appointment_id,
        cancelled_by="CLIENT",
        reason="Клиент отменил запись",
    )

    if result:
        await callback.message.edit_text(
            "✅ <b>Запись отменена</b>\n\n" "Барбер получил уведомление об отмене"
        )

        # Notify barber
        appointment = await appointment_service.appointment_repo.find_by_id(
            appointment_id
        )
        if appointment:
            user = await user_service.get_user(callback.from_user.id)
            notification_service = NotificationService(callback.bot)

            date_str = (
                appointment["appointment_date"].strftime("%d.%m.%Y")
                if hasattr(appointment["appointment_date"], "strftime")
                else str(appointment["appointment_date"])
            )
            time_str = appointment["appointment_time"]

            message = (
                f"<b>❌ Запись была отменена</b>\n\n"
                f"👤 Клиент: {user['full_name']}\n"
                f"📞 Телефон: {user.get('phone', 'не указан')}\n"
                f"📅 Дата: {date_str}\n"
                f"🕐 Время: {time_str}\n\n"
                f"💬 Причина: Клиент отменил запись"
            )

            await notification_service.notify_user(
                user_id=str(appointment["barber_id"]),
                notification_type=NotificationType.APPOINTMENT_CANCELLED,
                title="❌ Запись отменена клиентом",
                message=message,
            )
    else:
        await callback.message.edit_text("❌ Ошибка при отмене записи")


@router.callback_query(F.data == "client_profile")
@require_role(UserRole.CLIENT)
async def client_profile_handler(callback: CallbackQuery):
    """Show client profile"""
    user = await user_service.get_user(callback.from_user.id)
    bonus_balance = user.get("bonus_balance", 0)
    reminder_time = user.get("reminder_time", "09:00")

    keyboard = get_client_profile_keyboard()

    await safe_edit_text(
        callback.message,
        f"👤 <b>Мой профиль</b>\n\n"
        f"Имя: {user['full_name']}\n"
        f"Телефон: {user.get('phone', 'Не указано')}\n"
        f"Записей: {user.get('visit_count', 0)}\n"
        f"💰 Бонусные баллы: <b>{bonus_balance}</b>\n"
        f"⏰ Напоминание: <b>{reminder_time}</b>\n\n"
        f"Уведомления: {'✅ Включены' if user.get('is_subscribed') else '❌ Отключены'}",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "client_view_price")
@require_role(UserRole.CLIENT)
async def client_view_price(callback: CallbackQuery):
    """Show barber price list"""
    # Get barber (assuming there's one main barber for now)
    barbers = await user_service.get_barbers()

    if not barbers:
        await callback.message.edit_text(
            "💰 <b>Прайс</b>\n\n" "К сожалению, цены пока не установлены."
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")]
        ]
    )

    # Build price list from all barbers
    price_text = "💰 <b>Прайс услуг (BYN)</b>\n\n"

    for barber in barbers:
        barber_name = barber.get("full_name", "Барбер")
        services = barber.get("services", {})

        if not services:
            services = {}

        haircut = services.get("haircut")
        beard_trim = services.get("beard_trim")
        haircut_and_beard = services.get("haircut_and_beard")

        # Check if at least one service is set
        has_prices = (
            haircut is not None
            or beard_trim is not None
            or haircut_and_beard is not None
        )

        if has_prices:
            price_text += f"<b>{barber_name}</b>\n"

            if haircut is not None:
                price_text += f"✂️ Стрижка: {haircut} BYN\n"
            else:
                price_text += f"✂️ Стрижка: не установлена\n"

            if beard_trim is not None:
                price_text += f"💈 Стрижка бороды: {beard_trim} BYN\n"
            else:
                price_text += f"💈 Стрижка бороды: не установлена\n"

            if haircut_and_beard is not None:
                price_text += f"✂️💈 Стрижка + Борода: {haircut_and_beard} BYN\n"
            else:
                price_text += f"✂️💈 Стрижка + Борода: не установлена\n"

            # Show updated_at if available (converted to local timezone)
            updated_at = services.get("updated_at")
            if updated_at:
                if isinstance(updated_at, str):
                    price_text += f"<i>Обновлено: {updated_at}</i>\n"
                else:
                    # Convert UTC to local timezone (Minsk)
                    tz = get_timezone()
                    if updated_at.tzinfo is None:
                        # If naive datetime, assume UTC
                        updated_at = pytz.UTC.localize(updated_at)
                    local_time = updated_at.astimezone(tz)
                    price_text += (
                        f"<i>Обновлено: {local_time.strftime('%d.%m.%Y %H:%M')}</i>\n"
                    )

            price_text += "\n"
        else:
            price_text += f"<b>{barber_name}</b> - цены не установлены\n\n"

    await callback.message.edit_text(price_text, reply_markup=keyboard)


@router.callback_query(F.data == "client_edit_name")
@require_role(UserRole.CLIENT)
async def client_edit_name_start(callback: CallbackQuery, state: FSMContext):
    """Start editing client name"""
    user = await user_service.get_user(callback.from_user.id)

    await callback.message.edit_text(
        f"👤 Текущее имя: <b>{user['full_name']}</b>\n\n" "Введи новое имя:"
    )
    await state.set_state(ProfileEditStates.editing_name)


@router.message(ProfileEditStates.editing_name, F.text)
@require_role(UserRole.CLIENT)
async def client_edit_name_process(message: Message, state: FSMContext):
    """Process new name"""
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
        bonus_balance = user.get("bonus_balance", 0)
        keyboard = get_client_profile_keyboard()

        await message.answer(
            f"👤 <b>Мой профиль</b>\n\n"
            f"Имя: {user['full_name']}\n"
            f"Телефон: {user.get('phone', 'Не указано')}\n"
            f"Записей: {user.get('visit_count', 0)}\n"
            f"💰 Бонусные баллы: <b>{bonus_balance}</b>\n\n"
            f"Уведомления: {'✅ Включены' if user.get('is_subscribed') else '❌ Отключены'}",
            reply_markup=keyboard,
        )
    else:
        await message.answer("❌ Ошибка при обновлении имени. Попробуй ещё раз.")

    await state.clear()


@router.callback_query(F.data == "client_edit_phone")
@require_role(UserRole.CLIENT)
async def client_edit_phone_start(callback: CallbackQuery, state: FSMContext):
    """Start editing client phone"""
    user = await user_service.get_user(callback.from_user.id)

    await callback.message.edit_text(
        f"📞 Текущий номер: <b>{user.get('phone', 'Не указано')}</b>\n\n"
        "Введи новый номер телефона:\n\n"
        "Подходящие форматы:\n"
        "• +375XXXXXXXXX (с плюсом)\n"
        "• 375XXXXXXXXX (без плюса - добавится автоматически)\n"
        "• 0XXXXXXXXX (локальный формат)"
    )
    await state.set_state(ProfileEditStates.editing_phone)


@router.message(ProfileEditStates.editing_phone, F.text)
@require_role(UserRole.CLIENT)
async def client_edit_phone_process(message: Message, state: FSMContext):
    """Process new phone"""
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
        bonus_balance = user.get("bonus_balance", 0)
        keyboard = get_client_profile_keyboard()

        await message.answer(
            f"👤 <b>Мой профиль</b>\n\n"
            f"Имя: {user['full_name']}\n"
            f"Телефон: {user.get('phone', 'Не указано')}\n"
            f"Записей: {user.get('visit_count', 0)}\n"
            f"💰 Бонусные баллы: <b>{bonus_balance}</b>\n\n"
            f"Уведомления: {'✅ Включены' if user.get('is_subscribed') else '❌ Отключены'}",
            reply_markup=keyboard,
        )
    else:
        await message.answer(
            "❌ Ошибка при обновлении номера телефона. Попробуй ещё раз."
        )

    await state.clear()


@router.callback_query(F.data == "client_delete_account")
@require_role(UserRole.CLIENT)
async def client_delete_account_start(callback: CallbackQuery, state: FSMContext):
    """Start account deletion process"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Удалить", callback_data="confirm_delete_account"
                ),
                InlineKeyboardButton(text="❌ Отмена", callback_data="client_profile"),
            ]
        ]
    )

    await callback.message.edit_text(
        "⚠️ <b>Удаление аккаунта</b>\n\n"
        "Ты уверен? Это действие нельзя отменить!\n\n"
        "При удалении:\n"
        "• Будут удалены все твои данные\n"
        "• Будут отменены все активные записи\n"
        "• Ты больше не сможешь использовать этот бот",
        reply_markup=keyboard,
    )
    await state.set_state(ProfileEditStates.confirming_deletion)


@router.callback_query(F.data == "confirm_delete_account")
@require_role(UserRole.CLIENT)
async def client_confirm_delete_account(callback: CallbackQuery, state: FSMContext):
    """Confirm account deletion"""
    # Delete the account
    success = await user_service.delete_user(callback.from_user.id)

    if success:
        await callback.message.edit_text(
            "✅ <b>Аккаунт удален</b>\n\n"
            "Твой аккаунт и все данные были удалены.\n"
            "Чтобы вернуться, используй /start"
        )
        logger.info(f"Client {callback.from_user.id} deleted their account")
    else:
        await callback.message.edit_text("❌ Ошибка при удалении аккаунта")

    await state.clear()


@router.callback_query(F.data == "client_invite_friend")
@require_role(UserRole.CLIENT)
async def client_invite_friend(callback: CallbackQuery):
    """Show invite link"""
    user = await user_service.get_user(callback.from_user.id)

    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    referral_code = user.get("referral_code")
    if not referral_code:
        await callback.answer("⚠️ Реферальный код не инициализирован", show_alert=True)
        return

    referral_count = user.get("referral_count", 0)
    bonus_balance = user.get("bonus_balance", 0)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Профиль", callback_data="client_profile"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
            ]
        ]
    )

    invite_link = f"https://t.me/{settings.telegram_bot_username}?start={referral_code}"

    text = (
        f"🎁 <b>Пригласить друга</b>\n\n"
        f"<b>Как это работает:</b>\n"
        f"1️⃣ Отправь эту ссылку другу\n"
        f"2️⃣ Пусть друг зарегистрируется и запишется на прием\n"
        f"3️⃣ После его первого приема ты получишь бонусные баллы!\n\n"
        f"<b>Твоя персональная ссылка:</b>\n"
        f"<code>{invite_link}</code>\n\n"
        f"👥 Уже пригласил: <b>{referral_count}</b> друзей\n"
        f"💰 Получено баллов: <b>{bonus_balance}</b>"
    )

    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data == "client_edit_reminder")
@require_role(UserRole.CLIENT)
async def client_edit_reminder_handler(callback: CallbackQuery):
    """Show reminder time selection"""
    user = await user_service.get_user(callback.from_user.id)
    current_time = user.get("reminder_time", "09:00")

    # Create keyboard with time options
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    hours = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]

    for i, hour in enumerate(hours):
        if (i % 3) == 0:
            keyboard.inline_keyboard.append([])

        time_str = f"{hour:02d}:00"
        is_selected = time_str == current_time
        prefix = "✅ " if is_selected else ""

        keyboard.inline_keyboard[-1].append(
            InlineKeyboardButton(
                text=f"{prefix}{time_str}", callback_data=f"set_reminder_{hour:02d}"
            )
        )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="client_profile"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
        ]
    )

    await safe_edit_text(
        callback.message,
        f"⏰ <b>Время напоминания</b>\n\n"
        f"Текущее время: <b>{current_time}</b>\n\n"
        f"Выбери время, в которое ты хочешь получать напоминания",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("set_reminder_"))
@require_role(UserRole.CLIENT)
async def set_reminder_handler(callback: CallbackQuery):
    """Set reminder time"""
    hour = callback.data.split("_")[-1]
    reminder_time = f"{hour}:00"

    success = await user_service.update_reminder_time(
        callback.from_user.id, reminder_time
    )

    if success:
        user = await user_service.get_user(callback.from_user.id)
        bonus_balance = user.get("bonus_balance", 0)
        keyboard = get_client_profile_keyboard()

        await safe_edit_text(
            callback.message,
            f"⏰ <b>Время напоминания обновлено!</b>\n\n"
            f"Теперь ты будешь получать напоминания в <b>{reminder_time}</b>\n\n"
            f"👤 <b>Мой профиль</b>\n\n"
            f"Имя: {user['full_name']}\n"
            f"Телефон: {user.get('phone', 'Не указано')}\n"
            f"Записей: {user.get('visit_count', 0)}\n"
            f"💰 Бонусные баллы: <b>{bonus_balance}</b>\n\n"
            f"Уведомления: {'✅ Включены' if user.get('is_subscribed') else '❌ Отключены'}",
            reply_markup=keyboard,
        )
    else:
        await callback.answer(
            "❌ Ошибка при обновлении времени напоминания", show_alert=True
        )
