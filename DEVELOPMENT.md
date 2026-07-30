# Документация разработчика

## Архитектура

Проект использует чистую архитектуру с разделением на слои:

```
Telegram API
    ↓
Handlers (обработка команд)
    ↓
Services (бизнес-логика)
    ↓
Repositories (CRUD операции)
    ↓
MongoDB
```

## Структура проекта

### `config/`
Конфигурация и настройки
- `settings.py` - Pydantic Settings для .env файла

### `database/`
Работа с MongoDB
- `mongo.py` - подключение к БД (singleton pattern)
- `migrations.py` - создание индексов при старте

### `models/`
Pydantic модели для валидации
- `user.py` - модели пользователя
- `schedule.py` - модели расписания
- `appointment.py` - модели записи
- `notification.py` - модели уведомлений

### `repositories/`
Data Access Layer - операции с БД
- `base.py` - базовый класс с CRUD методами
- `user_repo.py` - операции с пользователями
- `schedule_repo.py` - операции с расписанием
- `time_slot_repo.py` - операции с временными слотами
- `appointment_repo.py` - операции с записями
- `notification_repo.py` - операции с уведомлениями

### `services/`
Бизнес-логика (без зависимости от Telegram)
- `user_service.py` - управление пользователями
- `schedule_service.py` - управление расписанием
- `appointment_service.py` - управление записями
- `notification_service.py` - отправка уведомлений
- `reminder_service.py` - напоминания

### `handlers/`
Telegram обработчики (роутеры)
- `user_handlers.py` - регистрация, старт, меню
- `barber_handlers.py` - управление расписанием
- `client_handlers.py` - запись и отмена

### `tasks/`
Фоновые задачи (APScheduler)
- `scheduler.py` - управление планировщиком

### `enums/`
Перечисления
- `user_role.py` - BARBER, CLIENT
- `appointment_status.py` - BOOKED, COMPLETED, CANCELLED
- `time_slot_status.py` - AVAILABLE, BOOKED, LOCKED
- `notification_type.py` - типы уведомлений

### `utils/`
Вспомогательные функции
- `logger.py` - логирование
- `date_time.py` - работа с датами и временем
- `validators.py` - валидация данных
- `decorators.py` - декораторы для обработчиков

## Как разрабатывать новые функции

### 1. Добавить новый обработчик команды

**Файл:** `src/handlers/client_handlers.py`

```python
from aiogram import Router, F
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(F.data == "my_action")
async def my_handler(callback: CallbackQuery):
    """Обработчик для кнопки"""
    await callback.message.edit_text("Привет!")
```

### 2. Добавить новый метод сервиса

**Файл:** `src/services/user_service.py`

```python
async def my_new_method(self, param1: str) -> bool:
    """Новый метод сервиса"""
    # Бизнес-логика тут
    user = await self.user_repo.find_by_telephone(param1)
    return user is not None
```

### 3. Добавить новый метод repository

**Файл:** `src/repositories/user_repo.py`

```python
async def find_by_telephone(self, phone: str):
    """Поиск пользователя по телефону"""
    return await self.find_one({"phone": phone})
```

### 4. Добавить фоновую задачу

**Файл:** `src/tasks/scheduler.py`

```python
scheduler.add_job(
    my_job,
    CronTrigger(hour=14, minute=30),  # каждый день в 14:30
    id="my_job",
    args=[notification_service]
)

async def my_job(notification_service):
    """Фоновая задача"""
    logger.info("Job executed!")
```

## Тестирование

### Запуск тестов

```bash
pytest tests/
```

### Написание теста

**Файл:** `tests/unit/test_services.py`

```python
import pytest
from src.services import UserService

@pytest.mark.asyncio
async def test_register_user():
    service = UserService()
    user_id = await service.register_user(
        telegram_id=123456789,
        full_name="Test User",
        role=UserRole.CLIENT
    )
    assert user_id is not None
```

## Кодирование

### Стиль кода

Код должен соответствовать PEP 8:

```bash
# Проверка стиля
black src/
flake8 src/

# Сортировка импортов
isort src/
```

### Типизация

Все функции должны иметь типы:

```python
async def my_function(name: str, count: int = 10) -> List[str]:
    """Описание функции"""
    return [name] * count
```

### Документация

Краткие docstring для функций:

```python
async def book_appointment(self, time_slot_id: str, client_id: str) -> Optional[Dict]:
    """Book an appointment for a client on a time slot."""
    # реализация
```

## Лучшие практики

### 1. Обработка ошибок

Всегда обрабатывайте ошибки с логированием:

```python
try:
    result = await service.do_something()
except Exception as e:
    logger.error(f"Failed to do something: {e}", exc_info=True)
    return None
```

### 2. Валидация входных данных

Используйте Pydantic модели:

```python
from src.models import UserCreate

class MyHandler:
    async def handle(self, data: dict):
        # Автоматическая валидация
        user = UserCreate(**data)
        # Теперь user.full_name гарантировано валидна
```

### 3. Логирование

Логируйте важные операции:

```python
logger.info(f"Created user {user_id}")
logger.warning(f"Invalid phone: {phone}")
logger.error(f"Database error: {e}")
```

### 4. Асинхронность

Всегда используйте `async/await`:

```python
# ✅ Правильно
async def my_handler(self):
    user = await self.user_repo.find_by_id(user_id)

# ❌ Неправильно
def my_handler(self):
    user = await self.user_repo.find_by_id(user_id)  # SyntaxError!
```

## Добавление новых моделей БД

Когда нужна новая коллекция в MongoDB:

1. **Создайте Pydantic модель** в `src/models/`
2. **Создайте Repository** в `src/repositories/`
3. **Добавьте индексы** в `src/database/migrations.py`
4. **Создайте Service** в `src/services/`

Пример для новой коллекции `reviews`:

```python
# 1. models/review.py
class ReviewCreate(BaseModel):
    appointment_id: str
    rating: int
    comment: str

# 2. repositories/review_repo.py
class ReviewRepository(BaseRepository):
    def __init__(self):
        super().__init__("reviews")
    
    async def create_review(self, appointment_id: str, rating: int, comment: str):
        return await self.create({
            "appointment_id": ObjectId(appointment_id),
            "rating": rating,
            "comment": comment,
            "created_at": datetime.utcnow()
        })

# 3. database/migrations.py
db.reviews.create_index("appointment_id", unique=True)

# 4. services/review_service.py
class ReviewService:
    def __init__(self):
        self.review_repo = ReviewRepository()
    
    async def create_review(self, ...):
        ...
```

## Отладка

### Активация DEBUG режима

```env
LOG_LEVEL=DEBUG
```

### Просмотр логов

```bash
tail -f bot.log
```

### Отладка в Python

```python
import pdb

async def my_handler():
    pdb.set_trace()  # Остановка выполнения
    # теперь можете инспектировать переменные
```

## CI/CD

### GitHub Actions

Проект готов для настройки GitHub Actions:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest tests/
```

## Контакт

Вопросы разработчику: slizh00717@gmail.com
