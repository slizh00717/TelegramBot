# CI/CD Pipeline Documentation

## Overview

Этот проект использует GitHub Actions для автоматической проверки кода, тестирования и деплоя.

### Workflows

#### 1. **CI Workflow** (`.github/workflows/ci.yml`)
**Когда запускается:** При push в `main`/`develop` или создание PR

**Что проверяет:**
- ✅ **Ruff Linting** - проверка PEP 8 и других правил качества
- ✅ **Code Formatting** - проверка форматирования
- ✅ **Type Checking** - проверка типов с mypy
- ✅ **Security** - проверка безопасности с Bandit

---

#### 2. **Docker Workflow** (`.github/workflows/docker.yml`)
**Когда запускается:** При push в `main` или создание tag

**Что делает:**
- 🐳 Собирает Docker образ
- 📦 Пушит в GitHub Container Registry (ghcr.io)
- 🏷️ Автоматически тегирует версии

---

## Локальная разработка

### Установка инструментов

```bash
# Установить линтеры и type checker
pip install ruff mypy bandit

# Или установить из требований для разработки
pip install -r requirements-dev.txt
```

### Запуск проверок локально

```bash
# Проверка кода с Ruff
ruff check src/

# Форматирование с Ruff
ruff format src/

# Type checking
mypy src/ --ignore-missing-imports

# Security check
bandit -r src/ -ll
```

---

## Требования для запуска CI/CD

### GitHub Secrets (если используется Docker push)

Для автоматического пуша Docker образов в ghcr.io, используются встроенные GitHub secrets:
- `GITHUB_TOKEN` - автоматически предоставляется GitHub
- `GITHUB_ACTOR` - имя пользователя

**Ручная настройка не требуется** - GitHub Actions сам авторизуется!

---

## Deploy Варианты

### Вариант 1: Docker Compose (локальный/VPS)

```bash
# Скопировать env файл
cp env.sh.example env.sh
# Отредактировать env.sh с реальными credentials

# Запустить бота в Docker
docker-compose up -d
```

### Вариант 2: Kubernetes

```bash
# Создать ConfigMap с конфигурацией
kubectl create configmap bot-config --from-file=env.sh

# Применить Kubernetes manifests (нужно создать)
kubectl apply -f k8s/
```

### Вариант 3: GitHub Actions Deploy (опционально)

Можно добавить workflow для автоматического деплоя на VPS/Cloud:

```yaml
name: Deploy to VPS

on:
  push:
    branches: [ main ]
    
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/barber-bot
            git pull origin main
            docker-compose down
            docker-compose up -d
```

---

## Версионирование с Tags

Проект поддерживает автоматическое версионирование через git tags:

```bash
# Создать новый релиз
git tag v1.0.0
git push origin v1.0.0
```

После этого:
1. Docker образ будет собран и помечен как `v1.0.0`
2. Появится GitHub Release (если настроена)
3. Образ будет доступен в ghcr.io с тегом `v1.0.0`

---

## Мониторинг CI/CD

### GitHub Actions UI
- Перейти на вкладку "Actions" в репозитории
- Смотреть логи для каждого workflow
- Скачивать artifacts (если есть)

### Статус бейджи

Можно добавить бейджи в README.md:

```markdown
![CI Status](https://github.com/USERNAME/TelegramBot/workflows/CI%20-%20Lint%20%26%20Type%20Check/badge.svg)
![Docker Status](https://github.com/USERNAME/TelegramBot/workflows/Docker%20Build%20%26%20Push/badge.svg)
```

---

## Troubleshooting

### Workflow не запускается

1. Проверить, что workflow файл в `.github/workflows/`
2. Убедиться, что в репозитории включены Actions
3. Проверить права доступа (Settings → Actions)

### Docker push не работает

1. Убедиться, что `GITHUB_TOKEN` имеет права на `packages: write`
2. Проверить логи в GitHub Actions
3. Проверить, что Docker image собирается правильно

### Type check выводит ошибки

1. `# type: ignore` для игнорирования конкретной строки
2. `[[tool.mypy.overrides]]` в `pyproject.toml` для игнорирования модулей
3. Использовать `Optional` и `Union` для типов

---

## Лучшие практики

1. **Используйте Conventional Commits**
   ```
   feat: добавить новую функцию
   fix: исправить баг
   docs: обновить документацию
   ```

2. **Пишите type hints**
   ```python
   async def my_function(param: str) -> bool:
       pass
   ```

3. **Следуйте PEP 8**
   - Ruff автоматически проверяет это

4. **Держите образ маленьким**
   - Используйте multi-stage builds (уже используется)
   - Удаляйте ненужные файлы

---

## Полезные ссылки

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Ruff Documentation](https://github.com/astral-sh/ruff)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
