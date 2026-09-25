# 🚀 Запуск бота на Render.com

## Шаг 1: Создай GitHub репозиторий

1. Зайди на https://github.com
2. Нажми "New repository"
3. Название: `telegram-auth-bot`
4. Public
5. Create repository

## Шаг 2: Загрузи файлы на GitHub

Загрузи эти файлы в репозиторий:
- `bot.py`
- `requirements.txt`
- `Procfile`
- `runtime.txt`

## Шаг 3: Деплой на Render

1. Зайди на https://render.com
2. Войди через GitHub
3. Нажми "New" → "Web Service"
4. Выбери репозиторий `telegram-auth-bot`
5. Настройки:
   - **Name**: telegram-auth-bot
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: Free

6. **Добавь переменную окружения**:
   - Нажми "Environment"
   - Добавь:
     - Key: `BOT_TOKEN`
     - Value: `8733879858:AAHUHpKjyQqDRp0irVDxE7LzV-5x9w2EmGM`

7. Нажми "Create Web Service"

## ✅ Готово!

Бот будет работать 24/7 бесплатно!

---

## 📝 Список файлов:

```
telegram-auth-bot/
├── bot.py              # Основной файл бота
├── requirements.txt    # Зависимости
├── Procfile           # Команда запуска
└── runtime.txt        # Версия Python
```

---

## ⚠️ Важно:

- Бот работает БЕЗ прокси (прокси не нужен на сервере)
- Используется стандартный Telegram API
- Все данные сохраняются в файлы

---

## 🔧 Проблемы?

Если бот не запускается:
1. Проверь токен в Environment Variables
2. Проверь логи в Render Dashboard
3. Убедись что все файлы загружены

