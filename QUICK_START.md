# 🚀 Быстрый старт

## За 5 минут до готового бота

### 1. Получение необходимых параметров

**Telegram Bot Token:**
- Откройте Telegram
- Найдите @BotFather
- Выполните `/start` → `/newbot`
- Скопируйте токен

**Chat ID барбера (для уведомлений):**
- Отправьте боту `/start`
- Посмотрите логи консоли: `User /start command - chat_id: XXXXXXX`
- Это значение `BARBER_CHAT_ID`

Экспортируйте переменные окружения:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export MONGODB_URI="mongodb://localhost:27017"
export DATABASE_NAME="barber_bot"
export TIMEZONE="Europe/Moscow"
export LOG_LEVEL="INFO"
```

Или создайте файл `run.sh`:
```bash
#!/bin/bash
export TELEGRAM_BOT_TOKEN="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
export BARBER_CHAT_ID="987654321"  # Получите из логов /start
export MONGODB_URI="mongodb://localhost:27017"
export DATABASE_NAME="barber_bot"
export TIMEZONE="Europe/Moscow"
export LOG_LEVEL="INFO"

python -m src.main
```

Запустите:
```bash
chmod +x run.sh
./run.sh
```

### 2. Установка зависимостей

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
```

### 3. Запуск MongoDB (выберите один вариант)

**Вариант A: Docker (легче всего)**
```bash
docker run -d -p 27017:27017 --name mongo mongo:7.0
```

**Вариант B: Docker Compose**
```bash
docker-compose up -d mongodb
```

**Вариант C: Локальная установка**
- [MongoDB Community Edition](https://www.mongodb.com/try/download/community)

### 4. Запуск бота

```bash
python -m src.main
```

✅ Бот готов! Откройте Telegram и найдите вашего бота.

---

## Что это дает вам?

### Основной функционал

| Роль | Функции |
|------|---------|
| **Барбер** | ✂️ Создание расписания<br>📅 Публикация времени<br>📊 Управление записями<br>🔔 Уведомления о клиентах |
| **Клиент** | 📅 Просмотр свободных мест<br>✂️ Запись на стрижку<br>⏰ Напоминания в 09:00<br>❌ Отмена записи |

### Технические возможности

- ✅ Telegram Bot API (aiogram 3.x)
- ✅ MongoDB для хранения данных
- ✅ Автоматические напоминания (APScheduler)
- ✅ Полная система уведомлений
- ✅ Pydantic валидация
- ✅ Чистая архитектура (репозитории, сервисы)
- ✅ Docker для деплоя

---

## Структура

```
src/
├── config/          # Конфигурация
├── database/        # MongoDB
├── models/          # Pydantic модели
├── repositories/    # CRUD операции
├── services/        # Бизнес-логика
├── handlers/        # Telegram команды
├── tasks/           # Фоновые задачи
├── enums/           # Перерахунки
└── utils/           # Помощники
```

---

## Тестирование бота

1. Откройте Telegram и найдите вашего бота
2. Отправьте `/start`
3. Выберите роль (Барбер / Клиент)
4. Заполните профиль

### Как барбер:
- Перейдите в меню → "Создать расписание"
- Укажите дату, время работы и длительность сеанса
- Опубликуйте расписание

### Как клиент:
- Перейдите в меню → "Записаться"
- Выберите дату и время
- Подтвердите запись

---

## Главные команды

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация нового пользователя |
| `/menu` | Главное меню |
| `/help` | Справка |

---

## Файлы документации

- **README.md** - Полное описание проекта
- **DEVELOPMENT.md** - Для разработчиков
- **DEPLOYMENT.md** - Как запустить в продакшене
- **QUICK_START.md** - Этот файл 😊

---

## Что дальше?

### Добавить функции:
1. Откройте `src/services/` для бизнес-логики
2. Добавьте новый метод в сервис
3. Создайте обработчик в `src/handlers/`
4. Протестируйте через Telegram

### Примеры расширений:
- 💳 Интеграция платежей
- ⭐ Система рейтингов
- 📞 SMS напоминания
- 📊 Статистика барбера
- 🔐 Авторизация администратора

### Изменить дизайн:
- Сообщения: `src/handlers/*.py`
- Кнопки: `src/handlers/*.py` (InlineKeyboardMarkup)
- Часовой пояс: `.env` (TIMEZONE)

---

## Проблемы?

### Бот не запускается?
```bash
# Проверьте токен
echo $TELEGRAM_BOT_TOKEN

# Проверьте логи
tail -f bot.log
```

### MongoDB не запускается?
```bash
# Проверьте порт
lsof -i :27017
```

### Ошибка при импорте?
```bash
# Переустановите зависимости
pip install -r requirements.txt --force-reinstall
```

---

## Архитектура (для разработчиков)

```
Telegram User
    ↓
Handler (команда)
    ↓
Service (логика)
    ↓
Repository (БД)
    ↓
MongoDB
```

Каждый слой отвечает за свое:
- **Handlers** - только Telegram
- **Services** - бизнес-логика
- **Repositories** - работа с БД
- **Models** - валидация данных

---

## Конфигурация в .env

```env
# Обязательно
TELEGRAM_BOT_TOKEN=ваш_токен_здесь

# Опционально (по умолчанию уже установлено)
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=barber_bot
TIMEZONE=Europe/Kyiv
LOG_LEVEL=INFO
```

---

## Версии

- Python 3.10+
- aiogram 3.8.0
- MongoDB 7.0
- Pydantic 2.7.1

---

## Лицензия

MIT - используйте как хотите!

---

## Контакт

Email: slizh00717@gmail.com

Приятной разработки! ✨
