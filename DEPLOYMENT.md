# Деплой и запуск Barber Bot

## Локальный запуск (разработка)

### Требования
- Python 3.10+
- MongoDB (локально или Atlas)
- Telegram Bot Token

### 1. Подготовка окружения

```bash
# Клонируйте репозиторий
git clone <repo-url>
cd TelegramBot

# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt
```

### 2. Установка переменных окружения

Экспортируйте переменные окружения в вашей shell:

```bash
# Обязательные
export TELEGRAM_BOT_TOKEN="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"

# Опциональные (используются значения по умолчанию)
export MONGODB_URI="mongodb://localhost:27017"
export DATABASE_NAME="barber_bot"
export TIMEZONE="Europe/Moscow"
export LOG_LEVEL="INFO"
```

Или создайте скрипт `setup_env.sh`:
```bash
#!/bin/bash
export TELEGRAM_BOT_TOKEN="your_token_here"
export MONGODB_URI="mongodb://localhost:27017"
export DATABASE_NAME="barber_bot"
export TIMEZONE="Europe/Moscow"
export LOG_LEVEL="INFO"

python -m src.main
```

И запустите:
```bash
chmod +x setup_env.sh
./setup_env.sh
```

### 3. Запуск MongoDB (локально)

**Вариант 1: Docker Compose (рекомендуется)**
```bash
docker-compose up -d mongodb
```

**Вариант 2: Локальная установка**
```bash
# На macOS (Homebrew)
brew services start mongodb-community

# На Linux (Ubuntu)
sudo systemctl start mongodb

# На Windows
# Установите MongoDB Community Edition и запустите через Services
```

### 4. Запуск бота

```bash
python -m src.main
```

Вывод должен показать:
```
Starting Barber Bot...
Connected to MongoDB: barber_bot
Database initialized
Scheduler started with jobs
Bot started and listening for messages...
```

## Docker деплой (продакшин)

### 1. Запуск с Docker Compose

```bash
# Экспортируйте переменные окружения
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export DATABASE_NAME="barber_bot"
export TIMEZONE="Europe/Moscow"
export LOG_LEVEL="INFO"

# Запустите контейнеры
docker-compose up -d
```

Или установите переменные при запуске:
```bash
TELEGRAM_BOT_TOKEN="your_token" docker-compose up -d
```

### 2. Проверка логов

```bash
# Логи бота
docker-compose logs -f bot

# Логи MongoDB
docker-compose logs -f mongodb
```

### 3. Остановка

```bash
docker-compose down
```

## Деплой на VPS/Сервер

### 1. Установите на сервере

```bash
# SSH на сервер
ssh user@your-server.com

# Клонируйте репозиторий
git clone <repo-url>
cd TelegramBot

# Установите Docker и Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установите Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Настройка

```bash
# Скопируйте .env.example
cp .env.example .env

# Редактируйте .env с вашими параметрами
nano .env
```

### 3. Запуск

```bash
# Запустите контейнеры в фоне
docker-compose up -d

# Проверьте статус
docker-compose ps
```

### 4. Автоматический перезапуск при перезагрузке сервера

```bash
# Docker контейнеры установлены с restart policy "unless-stopped"
# поэтому они автоматически перезапускаются
```

## Обновление кода

```bash
# Остановите контейнеры
docker-compose down

# Обновите код
git pull origin main

# Пересоберите image
docker-compose build

# Запустите снова
docker-compose up -d
```

## Мониторинг и логирование

### Просмотр логов в реальном времени

```bash
# Все логи
docker-compose logs -f

# Только бота
docker-compose logs -f bot

# Последние 100 строк
docker-compose logs -n 100 bot
```

### Логи в контейнере

```bash
# Сначала посмотрите логи MongoDB
docker-compose logs mongodb

# Проверьте статус контейнеров
docker-compose ps
```

## Тестирование бота

1. Найдите вашего бота в Telegram (@BotFather дал вам URL)
2. Отправьте `/start`
3. Пройдите регистрацию
4. Протестируйте функционал

## Решение проблем

### Бот не запускается

```bash
# Проверьте Telegram token
echo $TELEGRAM_BOT_TOKEN

# Проверьте подключение к MongoDB
docker-compose logs mongodb

# Проверьте логи бота
docker-compose logs bot
```

### MongoDB не запускается

```bash
# Проверьте порт 27017
sudo lsof -i :27017

# Проверьте volume
docker volume ls | grep barber
```

### Медленная работа

```bash
# Проверьте индексы в MongoDB
docker-compose exec mongodb mongosh

# В mongosh:
use barber_bot
db.users.getIndexes()
db.appointments.getIndexes()
```

## Резервное копирование БД

### Резервная копия MongoDB

```bash
# Экспорт данных
docker-compose exec mongodb mongodump --out /backup

# Копирование на хост
docker cp telegram_bot_mongodb:/backup ./mongodb_backup
```

### Восстановление из резервной копии

```bash
# Копирование на контейнер
docker cp ./mongodb_backup telegram_bot_mongodb:/restore

# Восстановление в контейнере
docker-compose exec mongodb mongorestore /restore
```

## Масштабирование

На данный момент бот запускается в одном контейнере. Для масштабирования на несколько экземпляров нужно:

1. Перенести `APScheduler` на отдельный сервис
2. Использовать Celery + Redis для фоновых задач
3. Установить load balancer

## Продакшин чек-лист

- [ ] `.env` файл настроен правильно
- [ ] TELEGRAM_BOT_TOKEN заполнен
- [ ] MONGODB_URI указывает на production MongoDB
- [ ] LOG_LEVEL установлено на INFO (не DEBUG)
- [ ] Резервное копирование настроено
- [ ] Мониторинг настроен
- [ ] SSL/TLS настроено (если требуется)
- [ ] Добавлены права доступа для пользователей MongoDB
- [ ] Тестирование завершено

## Контакт и поддержка

При возникновении проблем, обращайтесь:
- Email: slizh00717@gmail.com
