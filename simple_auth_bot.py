"""
Упрощенный Telegram Bot для авторизации аккаунтов
Только вход в аккаунты с сохранением и подписями
"""

import asyncio
import json
import os
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

ACCOUNTS_FILE = 'saved_accounts.json'

# Хранилище данных пользователей
user_sessions = {}

class AccountManager:
    """Управление сохраненными аккаунтами"""
    
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
    def save_account(user_id: int, phone: str, label: str = None):
        """Сохранить аккаунт с подписью"""
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
        
        # Проверяем, есть ли уже такой номер
        existing = next((acc for acc in data[user_key] if acc['phone'] == phone), None)
        
        if existing:
            # Обновляем подпись
            existing['label'] = label or phone
            existing['updated'] = datetime.now().isoformat()
        else:
            # Добавляем новый
            data[user_key].append({
                'phone': phone,
                'label': label or phone,
                'created': datetime.now().isoformat(),
                'updated': datetime.now().isoformat()
            })
        
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
                if user_key in data:
                    data[user_key] = [acc for acc in data[user_key] if acc['phone'] != phone]
                    
                    # Удаляем файлы сессии
                    session_file = f'session_{phone.replace("+", "")}.session'
                    for ext in ['', '-journal']:
                        try:
                            if os.path.exists(session_file + ext):
                                os.remove(session_file + ext)
                        except:
                            pass
                    
                    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    return True
            except:
                pass
        return False

def get_session(user_id: int) -> dict:
    """Получить сессию пользователя"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'state': 'main',
            'phone': None,
            'client': None,
            'label': None
        }
    return user_sessions[user_id]

def delete_session_file(phone: str):
    """Удалить файл сессии для нового входа"""
    session_name = f'session_{phone.replace("+", "")}'
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
    user_id = user.id
    
    accounts = AccountManager.load_accounts(user_id)
    
    keyboard = []
    
    if accounts:
        keyboard.append([InlineKeyboardButton("📱 Мои аккаунты", callback_data="list_accounts")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить аккаунт", callback_data="add_account")])
    keyboard.append([InlineKeyboardButton("ℹ️ Информация", callback_data="info")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
🔐 <b>Telegram Auth Manager</b>

Привет, {user.first_name}!

Этот бот помогает управлять авторизациями в Telegram аккаунтах.

<b>Возможности:</b>
✅ Вход в аккаунты с новым кодом
✅ Сохранение аккаунтов с подписями
✅ Управление несколькими аккаунтами
✅ Повторная отправка кода

Сохранено аккаунтов: <b>{len(accounts)}</b>
"""
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список аккаунтов"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    accounts = AccountManager.load_accounts(user_id)
    
    if not accounts:
        await query.message.edit_text(
            "❌ У тебя нет сохраненных аккаунтов.\n\nДобавь первый!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ Добавить", callback_data="add_account")
            ], [
                InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")
            ]])
        )
        return
    
    text = "<b>📱 Твои аккаунты</b>\n\n"
    keyboard = []
    
    for i, acc in enumerate(accounts, 1):
        label = acc.get('label', acc['phone'])
        phone = acc['phone']
        text += f"{i}. <b>{label}</b>\n   📞 {phone}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"🔐 {label}", callback_data=f"login:{phone}")
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить еще", callback_data="add_account")])
    keyboard.append([InlineKeyboardButton("🗑 Удалить аккаунт", callback_data="delete_menu")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def add_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления аккаунта"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_session(user_id)
    session['state'] = 'waiting_phone'
    
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="back_to_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
<b>➕ Добавление аккаунта</b>

Введи номер телефона с кодом страны.

<b>Примеры:</b>
• <code>+79123456789</code>
• <code>+380991234567</code>
• <code>+77011234567</code>

После авторизации ты сможешь добавить подпись для аккаунта.
"""
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка номера телефона"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if session['state'] != 'waiting_phone':
        return
    
    phone = update.message.text.strip()
    
    if not phone.startswith('+'):
        await update.message.reply_text("❌ Номер должен начинаться с '+'\nПопробуй еще раз:")
        return
    
    session['phone'] = phone
    session['state'] = 'waiting_code'
    
    # Удаляем старую сессию для нового кода
    delete_session_file(phone)
    
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
        
        session['client'] = client
        
        keyboard = [
            [InlineKeyboardButton("🔄 Отправить заново", callback_data="resend_code")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_auth")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Код отправлен на <code>{phone}</code>\n\n"
            "📱 Введи код из Telegram:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка: {e}\n\n"
            "Проверь правильность номера и попробуй еще раз."
        )
        session['state'] = 'main'

async def resend_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повторная отправка кода"""
    query = update.callback_query
    await query.answer("Отправляю новый код...")
    
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if session['state'] != 'waiting_code' or not session['client']:
        await query.message.reply_text("❌ Ошибка: нет активной сессии")
        return
    
    try:
        # Удаляем старую сессию
        delete_session_file(session['phone'])
        
        # Переподключаемся
        await session['client'].disconnect()
        
        proxy = (socks.SOCKS5, DEFAULT_PROXY_ADDR, DEFAULT_PROXY_PORT)
        client = TelegramClient(
            f'session_{session["phone"].replace("+", "")}',
            DEFAULT_API_ID,
            DEFAULT_API_HASH,
            proxy=proxy,
            connection_retries=10,
            retry_delay=5,
            timeout=30
        )
        
        await client.connect()
        await client.send_code_request(session['phone'])
        session['client'] = client
        
        await query.message.reply_text(
            f"✅ Новый код отправлен на <code>{session['phone']}</code>\n\n"
            "📱 Введи код:",
            parse_mode='HTML'
        )
    except Exception as e:
        await query.message.reply_text(f"❌ Ошибка: {e}")

async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кода авторизации"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if session['state'] != 'waiting_code':
        return
    
    code = update.message.text.strip()
    client = session['client']
    phone = session['phone']
    
    try:
        await client.sign_in(phone, code)
        
        # Успешная авторизация - спрашиваем подпись
        session['state'] = 'waiting_label'
        
        keyboard = [[InlineKeyboardButton("⏭ Пропустить", callback_data="skip_label")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✅ <b>Успешно авторизован!</b>\n\n"
            "Теперь можешь добавить подпись для этого аккаунта.\n"
            "Например: <i>Рабочий</i>, <i>Личный</i>, <i>Запасной</i>\n\n"
            "Введи подпись или нажми 'Пропустить':",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except SessionPasswordNeededError:
        session['state'] = 'waiting_2fa'
        await update.message.reply_text(
            "🔐 У тебя включена двухфакторная аутентификация.\n\n"
            "Введи пароль от Telegram:"
        )
    except PhoneCodeInvalidError:
        keyboard = [[InlineKeyboardButton("🔄 Отправить заново", callback_data="resend_code")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ Неверный код!\n\nПопробуй еще раз или получи новый:",
            reply_markup=reply_markup
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def handle_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пароля 2FA"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if session['state'] != 'waiting_2fa':
        return
    
    password = update.message.text.strip()
    client = session['client']
    
    try:
        await client.sign_in(password=password)
        
        session['state'] = 'waiting_label'
        
        keyboard = [[InlineKeyboardButton("⏭ Пропустить", callback_data="skip_label")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "✅ <b>Успешно авторизован!</b>\n\n"
            "Добавь подпись для аккаунта или нажми 'Пропустить':",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Неверный пароль: {e}\n\nПопробуй еще раз:")

async def handle_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подписи аккаунта"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if session['state'] != 'waiting_label':
        return
    
    label = update.message.text.strip()
    phone = session['phone']
    
    # Сохраняем аккаунт с подписью
    AccountManager.save_account(user_id, phone, label)
    
    # Отключаемся от клиента
    if session['client']:
        try:
            await session['client'].disconnect()
        except:
            pass
    
    session['state'] = 'main'
    session['client'] = None
    
    keyboard = [[InlineKeyboardButton("📱 Мои аккаунты", callback_data="list_accounts")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎉 Аккаунт <b>{phone}</b> сохранен с подписью: <b>{label}</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def skip_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропустить добавление подписи"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    phone = session['phone']
    
    # Сохраняем без подписи
    AccountManager.save_account(user_id, phone, phone)
    
    if session['client']:
        try:
            await session['client'].disconnect()
        except:
            pass
    
    session['state'] = 'main'
    session['client'] = None
    
    keyboard = [[InlineKeyboardButton("📱 Мои аккаунты", callback_data="list_accounts")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        f"✅ Аккаунт <b>{phone}</b> сохранен!",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def login_to_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход в сохраненный аккаунт"""
    query = update.callback_query
    await query.answer()
    
    phone = query.data.split(':')[1]
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    session['phone'] = phone
    session['state'] = 'waiting_code'
    
    # Удаляем старую сессию для нового кода
    delete_session_file(phone)
    
    await query.message.edit_text("⏳ Подключаюсь к Telegram...")
    
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
        
        session['client'] = client
        
        keyboard = [
            [InlineKeyboardButton("🔄 Отправить заново", callback_data="resend_code")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_auth")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(
            f"✅ Код отправлен на <code>{phone}</code>\n\n"
            "📱 Введи код из Telegram:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        await query.message.edit_text(f"❌ Ошибка: {e}")

async def delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню удаления аккаунтов"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    accounts = AccountManager.load_accounts(user_id)
    
    if not accounts:
        await query.message.edit_text("❌ Нет аккаунтов для удаления")
        return
    
    text = "<b>🗑 Удаление аккаунта</b>\n\nВыбери аккаунт для удаления:\n\n"
    keyboard = []
    
    for acc in accounts:
        label = acc.get('label', acc['phone'])
        phone = acc['phone']
        text += f"• {label} ({phone})\n"
        keyboard.append([
            InlineKeyboardButton(f"❌ {label}", callback_data=f"delete:{phone}")
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="list_accounts")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить аккаунт"""
    query = update.callback_query
    
    phone = query.data.split(':')[1]
    user_id = update.effective_user.id
    
    if AccountManager.remove_account(user_id, phone):
        await query.answer("✅ Аккаунт удален!")
        await list_accounts(update, context)
    else:
        await query.answer("❌ Ошибка удаления")

async def cancel_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена авторизации"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if session['client']:
        try:
            await session['client'].disconnect()
        except:
            pass
    
    session['state'] = 'main'
    session['client'] = None
    
    await query.message.reply_text("❌ Авторизация отменена")
    await start(update, context)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о боте"""
    query = update.callback_query
    await query.answer()
    
    text = """
<b>ℹ️ Информация</b>

<b>Что делает этот бот:</b>
• Помогает авторизоваться в Telegram аккаунтах
• Сохраняет аккаунты с подписями
• Каждый раз присылает новый код
• Поддерживает 2FA

<b>Как использовать:</b>
1. Нажми "➕ Добавить аккаунт"
2. Введи номер телефона
3. Введи код из Telegram
4. Добавь подпись (необязательно)

<b>Технические детали:</b>
• API: Стандартный Telegram API
• Прокси: SOCKS5 (автоматически)
• Безопасность: Данные хранятся локально

<b>Команды:</b>
/start - Главное меню
/help - Помощь
"""
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок"""
    query = update.callback_query
    data = query.data
    
    if data == "back_to_start":
        await start(update, context)
    elif data == "list_accounts":
        await list_accounts(update, context)
    elif data == "add_account":
        await add_account_start(update, context)
    elif data.startswith("login:"):
        await login_to_account(update, context)
    elif data == "delete_menu":
        await delete_menu(update, context)
    elif data.startswith("delete:"):
        await delete_account(update, context)
    elif data == "resend_code":
        await resend_code(update, context)
    elif data == "cancel_auth":
        await cancel_auth(update, context)
    elif data == "skip_label":
        await skip_label(update, context)
    elif data == "info":
        await info(update, context)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщений"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    state = session.get('state', 'main')
    
    if state == 'waiting_phone':
        await handle_phone(update, context)
    elif state == 'waiting_code':
        await handle_code(update, context)
    elif state == 'waiting_2fa':
        await handle_2fa(update, context)
    elif state == 'waiting_label':
        await handle_label(update, context)

def main():
    """Запуск бота"""
    print("🤖 Запуск Simple Auth Bot...")
    
    # Читаем токен
    BOT_TOKEN = None
    if os.path.exists('bot_token.txt'):
        with open('bot_token.txt', 'r') as f:
            BOT_TOKEN = f.read().strip()
    
    if not BOT_TOKEN:
        BOT_TOKEN = input("Введи токен бота: ").strip()
        with open('bot_token.txt', 'w') as f:
            f.write(BOT_TOKEN)
    
    print("✅ Токен загружен")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("✅ Бот запущен!\n")
    print("💡 Для деплоя на сервер используй:")
    print("   - Railway.app")
    print("   - Render.com")
    print("   - Heroku")
    print("   - PythonAnywhere\n")
    
    # Запускаем
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
