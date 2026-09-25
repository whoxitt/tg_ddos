"""
Telegram Bot для управления автоотправкой сообщений
Красивый интерфейс с кнопками и удобным управлением
"""

import asyncio
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import socks

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
DEFAULT_API_ID = 94575
DEFAULT_API_HASH = 'a3406de8d171bb422bb6ddf3bbd800e2'
DEFAULT_PROXY_ADDR = '127.0.0.1'
DEFAULT_PROXY_PORT = 16960

ACCOUNTS_FILE = 'bot_accounts.json'
MESSAGES_FILE = 'bot_messages.json'

# Хранилище данных пользователей
user_data_storage: Dict[int, dict] = {}

class AccountStorage:
    """Класс для работы с сохраненными аккаунтами"""
    
    @staticmethod
    def load_accounts(user_id: int) -> list:
        """Загрузить аккаунты пользователя"""
        if os.path.exists(ACCOUNTS_FILE):
            try:
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get(str(user_id), [])
            except:
                return []
        return []
    
    @staticmethod
    def save_account(user_id: int, phone: str):
        """Сохранить аккаунт"""
        data = {}
        if os.path.exists(ACCOUNTS_FILE):
            try:
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                pass
        
        user_key = str(user_id)
        if user_key not in data:
            data[user_key] = []
        
        if phone not in data[user_key]:
            data[user_key].append(phone)
            
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def remove_account(user_id: int, phone: str):
        """Удалить аккаунт"""
        if os.path.exists(ACCOUNTS_FILE):
            try:
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                user_key = str(user_id)
                if user_key in data and phone in data[user_key]:
                    data[user_key].remove(phone)
                    
                    # Удаляем файл сессии
                    session_file = f'session_{phone.replace("+", "")}.session'
                    if os.path.exists(session_file):
                        os.remove(session_file)
                    
                    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            except:
                pass

class MessageStorage:
    """Класс для работы с сообщениями"""
    
    @staticmethod
    def save_messages(user_id: int, messages: list):
        """Сохранить сообщения пользователя"""
        data = {}
        if os.path.exists(MESSAGES_FILE):
            try:
                with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                pass
        
        data[str(user_id)] = messages
        
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def load_messages(user_id: int) -> list:
        """Загрузить сообщения пользователя"""
        if os.path.exists(MESSAGES_FILE):
            try:
                with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get(str(user_id), [])
            except:
                return []
        return []

def get_user_data(user_id: int) -> dict:
    """Получить данные пользователя"""
    if user_id not in user_data_storage:
        user_data_storage[user_id] = {
            'state': 'main',
            'phone': None,
            'client': None,
            'selected_chat': None,
            'messages': [],
            'interval': 10,
            'limit_type': None,
            'limit_value': None,
            'sending_task': None
        }
    return user_data_storage[user_id]

def delete_session_file(phone: str):
    """Удалить файл сессии"""
    session_name = 'session_' + phone.replace('+', '')
    for ext in ['.session', '.session-journal']:
        file_path = session_name + ext
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("📱 Мои аккаунты", callback_data="accounts")],
        [InlineKeyboardButton("➕ Добавить аккаунт", callback_data="add_account")],
        [InlineKeyboardButton("📝 Мои сообщения", callback_data="view_messages")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🚀 <b>Telegram Auto Sender Bot</b>

Привет, {user.first_name}!

Я помогу тебе автоматически отправлять сообщения в Telegram чаты от твоего аккаунта.

<b>Возможности:</b>
✅ Управление несколькими аккаунтами
✅ Сохранение сообщений
✅ Гибкие настройки отправки
✅ Статистика в реальном времени
✅ Простой и понятный интерфейс

Выбери действие:
"""
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def accounts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню аккаунтов"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    accounts = AccountStorage.load_accounts(user_id)
    
    keyboard = []
    
    if accounts:
        for phone in accounts:
            keyboard.append([InlineKeyboardButton(f"📱 {phone}", callback_data=f"select_account:{phone}")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить новый", callback_data="add_account")])
    
    if accounts:
        keyboard.append([InlineKeyboardButton("🗑 Удалить аккаунт", callback_data="delete_account_menu")])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "<b>📱 Твои аккаунты</b>\n\n"
    if accounts:
        text += "Выбери аккаунт для работы:"
    else:
        text += "У тебя пока нет добавленных аккаунтов.\nДобавь первый аккаунт!"
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def add_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления аккаунта"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    user_data['state'] = 'waiting_phone'
    
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
<b>➕ Добавление аккаунта</b>

Введи номер телефона с кодом страны.

<b>Примеры:</b>
• +79123456789
• +380991234567
• +77011234567

Отправь номер телефона:
"""
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введенного номера телефона"""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if user_data['state'] != 'waiting_phone':
        return
    
    phone = update.message.text.strip()
    
    if not phone.startswith('+'):
        await update.message.reply_text(
            "❌ Номер должен начинаться с '+'.\nПопробуй еще раз:"
        )
        return
    
    user_data['phone'] = phone
    user_data['state'] = 'waiting_code'
    
    # Удаляем старую сессию
    delete_session_file(phone)
    
    # Создаем клиент и отправляем код
    await update.message.reply_text("⏳ Подключаюсь к Telegram...")
    
    try:
        proxy = (socks.SOCKS5, DEFAULT_PROXY_ADDR, DEFAULT_PROXY_PORT)
        client = TelegramClient(
            f'session_{phone.replace("+", "")}',
            DEFAULT_API_ID,
            DEFAULT_API_HASH,
            proxy=proxy,
            connection_retries=10,
            retry_delay=5,
            timeout=30
        )
        
        await client.connect()
        await client.send_code_request(phone)
        
        user_data['client'] = client
        
        keyboard = [
            [InlineKeyboardButton("🔄 Отправить код заново", callback_data="resend_code")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_auth")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Код отправлен на <b>{phone}</b>\n\n"
            "Введи код из Telegram:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка подключения: {e}\n\n"
            "Проверь:\n"
            "• Правильность номера\n"
            "• Прокси на 127.0.0.1:16960\n"
            "• Интернет соединение"
        )
        user_data['state'] = 'main'

async def resend_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повторная отправка кода"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if user_data['state'] != 'waiting_code' or not user_data['client']:
        await query.message.reply_text("❌ Ошибка: нет активной сессии")
        return
    
    try:
        await user_data['client'].send_code_request(user_data['phone'])
        await query.message.reply_text(
            f"✅ Новый код отправлен на <b>{user_data['phone']}</b>\n\n"
            "Введи код из Telegram:",
            parse_mode='HTML'
        )
    except Exception as e:
        await query.message.reply_text(f"❌ Ошибка: {e}")

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кода авторизации"""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if user_data['state'] != 'waiting_code':
        return
    
    code = update.message.text.strip()
    client = user_data['client']
    phone = user_data['phone']
    
    if not client:
        await update.message.reply_text("❌ Ошибка: нет активной сессии")
        return
    
    try:
        await client.sign_in(phone, code)
        
        # Сохраняем аккаунт
        AccountStorage.save_account(user_id, phone)
        
        await update.message.reply_text("✅ <b>Успешно авторизован!</b>", parse_mode='HTML')
        
        # Сбрасываем состояние
        user_data['state'] = 'main'
        user_data['client'] = None
        
        # Показываем главное меню
        await asyncio.sleep(1)
        
        keyboard = [
            [InlineKeyboardButton("📱 Мои аккаунты", callback_data="accounts")],
            [InlineKeyboardButton("📝 Мои сообщения", callback_data="view_messages")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎉 Аккаунт <b>{phone}</b> добавлен!\n\nЧто дальше?",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except SessionPasswordNeededError:
        user_data['state'] = 'waiting_2fa'
        await update.message.reply_text(
            "🔐 У тебя включена двухфакторная аутентификация.\n\n"
            "Введи пароль от Telegram:"
        )
    except PhoneCodeInvalidError:
        keyboard = [[InlineKeyboardButton("🔄 Отправить код заново", callback_data="resend_code")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ Неверный код!\n\nПопробуй еще раз:",
            reply_markup=reply_markup
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка авторизации: {e}")
        user_data['state'] = 'main'

async def handle_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пароля 2FA"""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if user_data['state'] != 'waiting_2fa':
        return
    
    password = update.message.text.strip()
    client = user_data['client']
    phone = user_data['phone']
    
    try:
        await client.sign_in(password=password)
        
        # Сохраняем аккаунт
        AccountStorage.save_account(user_id, phone)
        
        await update.message.reply_text("✅ <b>Успешно авторизован!</b>", parse_mode='HTML')
        
        user_data['state'] = 'main'
        user_data['client'] = None
        
        keyboard = [
            [InlineKeyboardButton("📱 Мои аккаунты", callback_data="accounts")],
            [InlineKeyboardButton("📝 Мои сообщения", callback_data="view_messages")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎉 Аккаунт <b>{phone}</b> добавлен!\n\nЧто дальше?",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Неверный пароль: {e}\n\nПопробуй еще раз:")

async def cancel_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена авторизации"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if user_data['client']:
        try:
            await user_data['client'].disconnect()
        except:
            pass
    
    user_data['state'] = 'main'
    user_data['client'] = None
    user_data['phone'] = None
    
    await query.message.reply_text("❌ Авторизация отменена")
    await start(update, context)

async def select_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор аккаунта для работы"""
    query = update.callback_query
    await query.answer()
    
    phone = query.data.split(':')[1]
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    user_data['phone'] = phone
    
    keyboard = [
        [InlineKeyboardButton("📤 Начать отправку", callback_data="start_sending")],
        [InlineKeyboardButton("◀️ Назад", callback_data="accounts")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        f"✅ Выбран аккаунт: <b>{phone}</b>\n\n"
        "Что будем делать?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    query = update.callback_query
    if query:
        await query.answer()
    
    text = """
<b>ℹ️ Помощь</b>

<b>Как использовать бота:</b>

1️⃣ <b>Добавь аккаунт</b>
   • Нажми "➕ Добавить аккаунт"
   • Введи номер телефона
   • Введи код из Telegram

2️⃣ <b>Настрой сообщения</b>
   • Нажми "📝 Мои сообщения"
   • Добавь сообщения для отправки

3️⃣ <b>Начни отправку</b>
   • Выбери аккаунт
   • Нажми "📤 Начать отправку"
   • Настрой параметры

<b>⚙️ Технические детали:</b>
• Прокси: SOCKS5 127.0.0.1:16960
• API: стандартный Telegram API
• Рекомендуемый интервал: 10+ секунд

<b>⚠️ Важно:</b>
• Не злоупотребляй отправкой
• Соблюдай правила Telegram
• Используй только для личных целей
"""
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def view_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр сохраненных сообщений"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    messages = MessageStorage.load_messages(user_id)
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить сообщения", callback_data="add_messages")],
    ]
    
    if messages:
        keyboard.append([InlineKeyboardButton("🗑 Очистить все", callback_data="clear_messages")])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "<b>📝 Твои сообщения</b>\n\n"
    
    if messages:
        text += f"Всего сообщений: <b>{len(messages)}</b>\n\n"
        for i, msg in enumerate(messages[:10], 1):
            preview = msg[:50] + '...' if len(msg) > 50 else msg
            text += f"{i}. {preview}\n"
        
        if len(messages) > 10:
            text += f"\n... и еще {len(messages) - 10}"
    else:
        text += "У тебя пока нет сохраненных сообщений."
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def add_messages_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления сообщений"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    user_data['state'] = 'adding_messages'
    user_data['temp_messages'] = []
    
    keyboard = [[InlineKeyboardButton("✅ Завершить", callback_data="finish_adding_messages")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
<b>➕ Добавление сообщений</b>

Отправляй сообщения по одному.
Каждое новое сообщение = новое сообщение для отправки.

Когда закончишь, нажми "✅ Завершить"
"""
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нового сообщения"""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if user_data['state'] != 'adding_messages':
        return
    
    message_text = update.message.text.strip()
    
    if not message_text:
        return
    
    if 'temp_messages' not in user_data:
        user_data['temp_messages'] = []
    
    user_data['temp_messages'].append(message_text)
    
    await update.message.reply_text(
        f"✅ Добавлено! Всего: <b>{len(user_data['temp_messages'])}</b>\n\n"
        "Отправь еще или нажми «✅ Завершить»",
        parse_mode='HTML'
    )

async def finish_adding_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение добавления сообщений"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if 'temp_messages' in user_data and user_data['temp_messages']:
        MessageStorage.save_messages(user_id, user_data['temp_messages'])
        count = len(user_data['temp_messages'])
        
        user_data['messages'] = user_data['temp_messages']
        user_data['temp_messages'] = []
        user_data['state'] = 'main'
        
        keyboard = [[InlineKeyboardButton("◀️ Вернуться к сообщениям", callback_data="view_messages")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            f"✅ Сохранено <b>{count}</b> сообщений!",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await query.message.edit_text("❌ Ты не добавил ни одного сообщения!")

async def clear_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистка всех сообщений"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    MessageStorage.save_messages(user_id, [])
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="view_messages")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "✅ Все сообщения удалены!",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок"""
    query = update.callback_query
    data = query.data
    
    if data == "accounts":
        await accounts_menu(update, context)
    elif data == "add_account":
        await add_account_start(update, context)
    elif data == "back_to_main":
        await start(update, context)
    elif data.startswith("select_account:"):
        await select_account(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data == "view_messages":
        await view_messages(update, context)
    elif data == "add_messages":
        await add_messages_start(update, context)
    elif data == "finish_adding_messages":
        await finish_adding_messages(update, context)
    elif data == "clear_messages":
        await clear_messages(update, context)
    elif data == "resend_code":
        await resend_code(update, context)
    elif data == "cancel_auth":
        await cancel_auth(update, context)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    state = user_data.get('state', 'main')
    
    if state == 'waiting_phone':
        await handle_phone(update, context)
    elif state == 'waiting_code':
        await handle_code(update, context)
    elif state == 'waiting_2fa':
        await handle_2fa(update, context)
    elif state == 'adding_messages':
        await handle_new_message(update, context)

def main():
    """Запуск бота"""
    print("🤖 Запуск Telegram Bot...")
    
    # Пытаемся прочитать токен из файла
    BOT_TOKEN = None
    if os.path.exists('bot_token.txt'):
        try:
            with open('bot_token.txt', 'r', encoding='utf-8') as f:
                BOT_TOKEN = f.read().strip()
            print("✅ Токен загружен из файла bot_token.txt")
        except:
            pass
    
    # Если токена нет, спрашиваем
    if not BOT_TOKEN:
        print("\n⚠️  ВАЖНО: Вставь токен бота!")
        print("Получить токен: https://t.me/BotFather\n")
        BOT_TOKEN = input("Введи токен бота: ").strip()
        
        if not BOT_TOKEN:
            print("❌ Токен не введен!")
            return
        
        # Сохраняем токен в файл
        try:
            with open('bot_token.txt', 'w', encoding='utf-8') as f:
                f.write(BOT_TOKEN)
            print("✅ Токен сохранен в bot_token.txt")
        except:
            pass
    
    # Создаем приложение БЕЗ прокси (Bot API обычно доступен напрямую)
    print(f"🔧 Подключение к Telegram Bot API...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Запускаем бота с настройками для прокси
    print("✅ Бот запущен!\n")
    print("💡 Найди бота в Telegram и отправь /start\n")
    
    # Используем polling с увеличенными таймаутами для прокси
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        pool_timeout=30,
        connect_timeout=30,
        read_timeout=30,
        write_timeout=30
    )

if __name__ == '__main__':
    main()
