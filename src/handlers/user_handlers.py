from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from src.enums import UserRole
from src.services import UserService
from src.utils import logger, normalize_phone, validate_name, validate_phone

router = Router()
user_service = UserService()


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()


def get_menu_keyboard() -> ReplyKeyboardMarkup:
    """Create keyboard with menu button"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📋 Меню")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    """Handle /start command"""
    # Log chat ID for admin purposes
    logger.info(f"User /start command - chat_id: {message.chat.id}, user_id: {message.from_user.id}")

    # Extract referral code from start parameter if present
    referral_code = None
    if message.text and len(message.text.split()) > 1:
        referral_code = message.text.split()[1]

    user = await user_service.get_user(message.from_user.id)

    if user:
        await message.answer(
            f"👋 Привет, {user['full_name']}!\n\nТы уже зарегистрирован. Используй кнопку меню для навигации.",
            reply_markup=get_menu_keyboard(),
        )
    else:
        # Store referral code in state for later use during registration
        await state.update_data(referral_code=referral_code)

        # Create keyboard with Start button for new users
        start_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🚀 Начать регистрацию")]],
            resize_keyboard=True,
            one_time_keyboard=False,
        )

        await message.answer(
            "👋 Добро пожаловать в барбершоп бот!\n\nДавай зарегистрируемся. Нажми кнопку ниже:",
            reply_markup=start_keyboard,
        )


@router.message(F.text == "🚀 Начать регистрацию")
async def start_registration_handler(message: Message, state: FSMContext):
    """Handle registration start button"""
    user = await user_service.get_user(message.from_user.id)

    if user:
        await message.answer(
            f"👋 Привет, {user['full_name']}!\n\nТы уже зарегистрирован. Используй кнопку меню для навигации.",
            reply_markup=get_menu_keyboard(),
        )
    else:
        await message.answer("Укажи своё имя (минимум 2 символа):")
        await state.set_state(RegistrationStates.waiting_for_name)


@router.message(RegistrationStates.waiting_for_name, F.text)
async def process_name(message: Message, state: FSMContext):
    """Process user name during registration"""
    if not validate_name(message.text):
        await message.answer("❌ Имя должно быть минимум 2 символа. Попробуй ещё раз:")
        return

    await state.update_data(full_name=message.text)
    await message.answer(
        "Теперь введи свой номер телефона:\n\n"
        "Подходящие форматы:\n"
        "• +375XXXXXXXXX (с плюсом)\n"
        "• 375XXXXXXXXX (без плюса - добавится автоматически)\n"
        "• 0XXXXXXXXX (локальный формат)",
        reply_markup=get_menu_keyboard(),
    )
    await state.set_state(RegistrationStates.waiting_for_phone)


@router.message(RegistrationStates.waiting_for_phone, F.text)
async def process_phone(message: Message, state: FSMContext):
    """Process phone number during registration"""
    from src.config import settings

    if not validate_phone(message.text):
        await message.answer(
            "❌ Неверный формат телефона. Попробуй ещё раз:\n\n"
            "Подходящие форматы:\n"
            "• +375XXXXXXXXX (с плюсом)\n"
            "• 375XXXXXXXXX (без плюса)\n"
            "• 0XXXXXXXXX (локальный формат)"
        )
        return

    # Normalize phone number
    normalized_phone = normalize_phone(message.text)
    await state.update_data(phone=normalized_phone)

    # Automatically determine role based on chat_id
    role = UserRole.BARBER if message.chat.id == settings.barber_chat_id else UserRole.CLIENT
    username = message.from_user.username

    # Get referral code from state if present
    data = await state.get_data()
    referral_code = data.get("referral_code")

    try:
        user_id = await user_service.register_user(
            telegram_id=message.from_user.id,
            full_name=data["full_name"],
            role=role,
            phone=normalized_phone,
            username=username,
            referral_code_from=referral_code,
        )
    except ValueError as e:
        await message.answer(f"❌ Ошибка регистрации: {str(e)}")
        await state.clear()
        return

    if user_id:
        user = await user_service.get_user(message.from_user.id)

        await message.answer(
            f"✅ <b>Регистрация успешна!</b>\n\n👤 Имя: {user['full_name']}\n📞 Телефон: {normalized_phone}"
        )

        # Show menu with buttons
        if role == UserRole.BARBER:
            await show_barber_menu(message, user)
        else:
            await show_client_menu(message, user)

            # Show price hint for new clients
            await message.answer(
                "💡 <b>Совет:</b> Нажми на кнопку <b>💰 Прайс</b> в меню, чтобы увидеть стоимость услуг барбера!"
            )

        logger.info(f"User {message.from_user.id} registered as {role.value} with ID {user_id}")
    else:
        await message.answer("❌ Ошибка при регистрации. Попробуй /start")

    await state.clear()


@router.message(Command("menu"))
async def menu_handler(message: Message):
    """Show main menu"""
    user = await user_service.get_user(message.from_user.id)

    if not user:
        await message.answer("❌ Сначала зарегистрируйся через /start")
        return

    if user["role"] == UserRole.BARBER.value:
        await show_barber_menu(message, user)
    else:
        await show_client_menu(message, user)


@router.callback_query(F.data == "menu")
async def menu_callback_handler(callback: CallbackQuery):
    """Show main menu from callback"""
    user = await user_service.get_user(callback.from_user.id)

    if not user:
        await callback.message.edit_text("❌ Сначала зарегистрируйся через /start")
        return

    if user["role"] == UserRole.BARBER.value:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📅 Расписание", callback_data="barber_create_schedule"),
                    InlineKeyboardButton(text="📊 Записи", callback_data="barber_view_appointments"),
                ],
                [
                    InlineKeyboardButton(text="👥 Клиенты", callback_data="barber_view_clients"),
                    InlineKeyboardButton(text="⚙️ Профиль", callback_data="barber_profile"),
                ],
            ]
        )
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📅 Записаться", callback_data="client_book_appointment"),
                    InlineKeyboardButton(text="📊 Записи", callback_data="client_view_appointments"),
                ],
                [
                    InlineKeyboardButton(text="💰 Прайс", callback_data="client_view_price"),
                    InlineKeyboardButton(text="⚙️ Профиль", callback_data="client_profile"),
                ],
            ]
        )

    await callback.message.edit_text("Меню", reply_markup=keyboard)


async def show_barber_menu(message: Message, user):
    """Show menu for barber"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Расписание", callback_data="barber_create_schedule"),
                InlineKeyboardButton(text="📊 Записи", callback_data="barber_view_appointments"),
            ],
            [
                InlineKeyboardButton(text="👥 Клиенты", callback_data="barber_view_clients"),
                InlineKeyboardButton(text="🚫 Список", callback_data="barber_view_blacklist"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Профиль", callback_data="barber_profile"),
            ],
        ]
    )

    await message.answer("Меню", reply_markup=keyboard)


async def show_client_menu(message: Message, user):
    """Show menu for client"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Записаться", callback_data="client_book_appointment"),
                InlineKeyboardButton(text="📊 Записи", callback_data="client_view_appointments"),
            ],
            [
                InlineKeyboardButton(text="💰 Прайс", callback_data="client_view_price"),
                InlineKeyboardButton(text="⚙️ Профиль", callback_data="client_profile"),
            ],
        ]
    )

    await message.answer("Меню", reply_markup=keyboard)


@router.message(F.text == "📋 Меню")
async def menu_button_handler(message: Message):
    """Handle menu button"""
    user = await user_service.get_user(message.from_user.id)

    if not user:
        await message.answer("❌ Сначала зарегистрируйся через /start")
        return

    if user["role"] == UserRole.BARBER.value:
        await show_barber_menu(message, user)
    else:
        await show_client_menu(message, user)


@router.message(Command("help"))
async def help_handler(message: Message):
    """Show help"""
    await message.answer(
        "<b>Доступные команды:</b>\n\n"
        "/start - Регистрация\n"
        "/menu - Главное меню\n"
        "/help - Помощь\n\n"
        "<b>О боте:</b>\n"
        "Это бот для записи в барбершоп. "
        "Клиенты могут записываться на стрижку, "
        "а барберы могут управлять своим расписанием.",
        parse_mode="HTML",
    )
