"""
Telegram Auto Message Sender (Упрощенная версия с сохранением номеров)
Отправляет сообщения в чат от вашего аккаунта с заданными интервалами
"""

import asyncio
import time
import json
import os
from telethon import TelegramClient
from telethon.tl.types import InputPeerChat, InputPeerChannel
from datetime import datetime, timedelta

# Цвета для консоли
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'

# Публичные API credentials для тестирования
DEFAULT_API_ID = 94575
DEFAULT_API_HASH = 'a3406de8d171bb422bb6ddf3bbd800e2'

# Настройки прокси по умолчанию
DEFAULT_PROXY_TYPE = 'SOCKS5'
DEFAULT_PROXY_ADDR = '127.0.0.1'
DEFAULT_PROXY_PORT = 16960

# Файл для сохранения номеров
PHONES_FILE = 'saved_phones.json'

class PhoneStorage:
    """Класс для работы с сохраненными номерами"""
    
    @staticmethod
    def load_phones():
        """Загрузить сохраненные номера"""
        if os.path.exists(PHONES_FILE):
            try:
                with open(PHONES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    @staticmethod
    def save_phone(phone):
        """Сохранить новый номер"""
        phones = PhoneStorage.load_phones()
        if phone not in phones:
            phones.append(phone)
            with open(PHONES_FILE, 'w', encoding='utf-8') as f:
                json.dump(phones, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def remove_phone(phone):
        """Удалить номер из сохраненных"""
        phones = PhoneStorage.load_phones()
        if phone in phones:
            phones.remove(phone)
            with open(PHONES_FILE, 'w', encoding='utf-8') as f:
                json.dump(phones, f, ensure_ascii=False, indent=2)

class TelegramAutoSender:
    def __init__(self):
        self.client = None
        self.api_id = DEFAULT_API_ID
        self.api_hash = DEFAULT_API_HASH
        self.phone = None
        
    def delete_session_file(self, phone):
        """Удаление файла сессии для получения нового кода"""
        session_name = 'session_' + phone.replace('+', '')
        session_file = session_name + '.session'
        session_journal = session_name + '.session-journal'
        
        # Удаляем файлы сессии если они существуют
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                print(f"{Colors.GREEN}✓ Старая сессия удалена{Colors.RESET}")
            except:
                pass
        
        if os.path.exists(session_journal):
            try:
                os.remove(session_journal)
            except:
                pass
    
    async def select_or_add_phone(self):
        """Выбор существующего номера или добавление нового"""
        phones = PhoneStorage.load_phones()
        
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.CYAN}{'  ВЫБОР НОМЕРА ТЕЛЕФОНА':^60}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        
        if phones:
            print(f"{Colors.GREEN}Сохраненные номера:{Colors.RESET}\n")
            for i, phone in enumerate(phones, 1):
                print(f"  {Colors.YELLOW}{i}.{Colors.RESET} {phone}")
            
            print(f"\n  {Colors.YELLOW}0.{Colors.RESET} {Colors.BLUE}Добавить новый номер{Colors.RESET}")
            print(f"  {Colors.YELLOW}d.{Colors.RESET} {Colors.RED}Удалить номер{Colors.RESET}")
            
            while True:
                choice = input(f"\n{Colors.CYAN}Выбор: {Colors.RESET}").strip().lower()
                
                if choice == 'd':
                    # Удаление номера
                    del_choice = input(f"{Colors.RED}Номер для удаления (1-{len(phones)}): {Colors.RESET}").strip()
                    try:
                        idx = int(del_choice) - 1
                        if 0 <= idx < len(phones):
                            phone_to_delete = phones[idx]
                            PhoneStorage.remove_phone(phone_to_delete)
                            # Также удаляем файл сессии
                            self.delete_session_file(phone_to_delete)
                            print(f"{Colors.GREEN}✓ Номер {phone_to_delete} удален{Colors.RESET}")
                            return await self.select_or_add_phone()  # Показываем меню заново
                        else:
                            print(f"{Colors.RED}Неверный номер!{Colors.RESET}")
                    except ValueError:
                        print(f"{Colors.RED}Введите число!{Colors.RESET}")
                    continue
                
                if choice == '0':
                    # Добавление нового номера
                    new_phone = input(f"\n{Colors.CYAN}Введите номер телефона (например, +79123456789): {Colors.RESET}").strip()
                    if new_phone:
                        PhoneStorage.save_phone(new_phone)
                        print(f"{Colors.GREEN}✓ Номер сохранен!{Colors.RESET}")
                        return new_phone
                    else:
                        print(f"{Colors.RED}Номер не может быть пустым!{Colors.RESET}")
                        continue
                
                # Выбор существующего номера
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(phones):
                        return phones[idx]
                    else:
                        print(f"{Colors.RED}Неверный номер! Выберите от 1 до {len(phones)}{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}Введите число, 0 или 'd'!{Colors.RESET}")
        else:
            # Если нет сохраненных номеров
            print(f"{Colors.YELLOW}У вас пока нет сохраненных номеров.{Colors.RESET}")
            new_phone = input(f"\n{Colors.CYAN}Введите номер телефона (например, +79123456789): {Colors.RESET}").strip()
            if new_phone:
                PhoneStorage.save_phone(new_phone)
                print(f"{Colors.GREEN}✓ Номер сохранен!{Colors.RESET}")
                return new_phone
            else:
                print(f"{Colors.RED}Номер не может быть пустым!{Colors.RESET}")
                return await self.select_or_add_phone()
        
    async def setup(self):
        """Настройка подключения к Telegram"""
        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.RESET}")
        print(f"{Colors.MAGENTA}{'  TELEGRAM AUTO SENDER':^60}{Colors.RESET}")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}")
        
        # Выбор или добавление номера
        self.phone = await self.select_or_add_phone()
        
        # Удаляем старую сессию, чтобы каждый раз приходил новый код
        print(f"\n{Colors.YELLOW}Удаление старой сессии для получения нового кода...{Colors.RESET}")
        self.delete_session_file(self.phone)
        
        print(f"\n{Colors.GREEN}✓ Выбран номер: {self.phone}{Colors.RESET}")
        print(f"{Colors.GREEN}✓ Используются стандартные API ключи{Colors.RESET}")
        print(f"{Colors.GREEN}✓ Прокси: SOCKS5 {DEFAULT_PROXY_ADDR}:{DEFAULT_PROXY_PORT}{Colors.RESET}")
        print(f"{Colors.GREEN}✓ При каждом входе будет приходить новый код{Colors.RESET}")
        
        # Настройка прокси SOCKS5
        import socks
        proxy = (socks.SOCKS5, DEFAULT_PROXY_ADDR, DEFAULT_PROXY_PORT)
        
        # Создаем клиент с настройками подключения
        self.client = TelegramClient(
            'session_' + self.phone.replace('+', ''), 
            self.api_id, 
            self.api_hash,
            proxy=proxy,
            connection_retries=10,
            retry_delay=5,
            timeout=30
        )
        
        print(f"\n{Colors.YELLOW}Подключение к Telegram...{Colors.RESET}")
        
        try:
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                # Отправляем код
                await self.client.send_code_request(self.phone)
                
                while True:
                    print(f"\n{Colors.CYAN}Код отправлен на {self.phone}{Colors.RESET}")
                    print(f"{Colors.YELLOW}Введите код из Telegram или 'заново' для повторной отправки{Colors.RESET}")
                    
                    code = input(f"{Colors.CYAN}Код: {Colors.RESET}").strip()
                    
                    if code.lower() == 'заново':
                        print(f"\n{Colors.YELLOW}Отправка нового кода...{Colors.RESET}")
                        await self.client.send_code_request(self.phone)
                        continue
                    
                    try:
                        await self.client.sign_in(self.phone, code)
                        break  # Успешная авторизация
                    except Exception as e:
                        error_str = str(e).lower()
                        
                        # Если включена двухфакторная аутентификация
                        if 'sessionpasswordneeded' in str(type(e).__name__).lower() or 'password' in error_str:
                            print(f"\n{Colors.YELLOW}У вас включена двухфакторная аутентификация (2FA){Colors.RESET}")
                            password = input(f'{Colors.CYAN}Введите пароль от Telegram: {Colors.RESET}')
                            await self.client.sign_in(password=password)
                            break
                        
                        # Неверный код
                        elif 'phone code invalid' in error_str or 'code invalid' in error_str:
                            print(f"{Colors.RED}✗ Неверный код! Попробуйте еще раз или введите 'заново'{Colors.RESET}")
                            continue
                        
                        else:
                            raise
            
            print(f"{Colors.GREEN}✓ Успешно подключено!{Colors.RESET}\n")
            
        except Exception as e:
            print(f"{Colors.RED}Ошибка подключения: {e}{Colors.RESET}")
            print(f"\n{Colors.YELLOW}Возможные решения:{Colors.RESET}")
            print("1. Проверьте правильность кода/пароля")
            print("2. Проверьте интернет-соединение и прокси")
            print("3. Попробуйте ввести 'заново' для получения нового кода")
            print("4. Проверьте что прокси запущен на 127.0.0.1:16960")
            raise
        
    async def get_chat(self):
        """Выбор чата для отправки сообщений"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.CYAN}{'  ВЫБОР ЧАТА':^60}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        
        # Получаем список диалогов
        dialogs = await self.client.get_dialogs(limit=50)
        
        print(f"{Colors.GREEN}Доступные чаты:{Colors.RESET}\n")
        for i, dialog in enumerate(dialogs, 1):
            chat_type = "👥 Группа" if dialog.is_group else "📢 Канал" if dialog.is_channel else "👤 Личный"
            print(f"  {Colors.YELLOW}{i:2d}.{Colors.RESET} {dialog.name} {Colors.BLUE}({chat_type}){Colors.RESET}")
        
        while True:
            try:
                choice = int(input(f"\n{Colors.CYAN}Выберите номер чата (1-{len(dialogs)}): {Colors.RESET}"))
                if 1 <= choice <= len(dialogs):
                    selected_chat = dialogs[choice - 1]
                    print(f"{Colors.GREEN}✓ Выбран чат: {selected_chat.name}{Colors.RESET}")
                    return selected_chat
                else:
                    print(f"{Colors.RED}Неверный номер. Попробуйте снова.{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}Введите число!{Colors.RESET}")
    
    async def input_messages(self):
        """Ввод сообщений для отправки"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.CYAN}{'  ВВОД СООБЩЕНИЙ':^60}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        
        print("Способы ввода сообщений:")
        print(f"  {Colors.YELLOW}1.{Colors.RESET} Ввести вручную (каждое на новой строке, в конце 'СТОП')")
        print(f"  {Colors.YELLOW}2.{Colors.RESET} Загрузить из файла messages.txt")
        
        choice = input(f"\n{Colors.CYAN}Выбор (1/2): {Colors.RESET}").strip()
        
        messages = []
        
        if choice == '2':
            try:
                with open('messages.txt', 'r', encoding='utf-8') as f:
                    messages = [line.strip() for line in f if line.strip()]
                print(f"{Colors.GREEN}✓ Загружено {len(messages)} сообщений из файла{Colors.RESET}")
            except FileNotFoundError:
                print(f"{Colors.YELLOW}Файл messages.txt не найден. Создайте его или используйте ручной ввод.{Colors.RESET}")
                print("Переключаюсь на ручной ввод...\n")
                choice = '1'
        
        if choice == '1':
            print(f"\n{Colors.YELLOW}Введите сообщения, каждое на новой строке.{Colors.RESET}")
            print(f"{Colors.YELLOW}Когда закончите, введите 'СТОП' на новой строке.{Colors.RESET}\n")
            
            counter = 1
            
            while True:
                msg = input(f"{Colors.CYAN}Сообщение {counter}: {Colors.RESET}")
                if msg.strip().upper() == 'СТОП':
                    break
                if msg.strip():
                    messages.append(msg.strip())
                    counter += 1
            
            print(f"\n{Colors.GREEN}✓ Добавлено {len(messages)} сообщений{Colors.RESET}")
        
        return messages
    
    async def get_sending_params(self, total_messages):
        """Настройка параметров отправки"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.CYAN}{'  НАСТРОЙКА ОТПРАВКИ':^60}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
        
        print(f"{Colors.GREEN}Всего сообщений: {total_messages}{Colors.RESET}")
        
        interval = int(input(f"\n{Colors.CYAN}Интервал между сообщениями в секундах (рекомендуется 10): {Colors.RESET}") or "10")
        
        print(f"\n{Colors.YELLOW}Выберите режим:{Colors.RESET}")
        print(f"  {Colors.YELLOW}1.{Colors.RESET} По времени (указать часы работы)")
        print(f"  {Colors.YELLOW}2.{Colors.RESET} По количеству сообщений")
        print(f"  {Colors.YELLOW}3.{Colors.RESET} Отправить все сообщения")
        
        mode = input(f"\n{Colors.CYAN}Выберите режим (1/2/3): {Colors.RESET}").strip()
        
        limit_type = None
        limit_value = None
        
        if mode == '1':
            hours = float(input(f"{Colors.CYAN}Сколько часов должна работать программа? {Colors.RESET}"))
            limit_type = 'time'
            limit_value = hours
            print(f"{Colors.GREEN}✓ Режим: по времени ({hours} ч.){Colors.RESET}")
        elif mode == '2':
            count = int(input(f"{Colors.CYAN}Сколько сообщений отправить? {Colors.RESET}"))
            limit_type = 'count'
            limit_value = count
            print(f"{Colors.GREEN}✓ Режим: по количеству ({limit_value} сообщений){Colors.RESET}")
        else:
            limit_type = 'all'
            limit_value = total_messages
            print(f"{Colors.GREEN}✓ Режим: все сообщения ({total_messages} шт.){Colors.RESET}")
        
        return interval, limit_type, limit_value
    
    async def send_messages(self, chat, messages, interval, limit_type, limit_value):
        """Отправка сообщений"""
        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.RESET}")
        print(f"{Colors.MAGENTA}{'  НАЧАЛО ОТПРАВКИ':^60}{Colors.RESET}")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.RESET}\n")
        
        start_time = datetime.now()
        end_time = None
        
        if limit_type == 'time':
            end_time = start_time + timedelta(hours=limit_value)
            print(f"{Colors.CYAN}Начало:    {start_time.strftime('%H:%M:%S')}{Colors.RESET}")
            print(f"{Colors.CYAN}Окончание: {end_time.strftime('%H:%M:%S')}{Colors.RESET}\n")
        
        sent_count = 0
        message_index = 0
        
        try:
            while True:
                # Проверка условий остановки
                if limit_type == 'time':
                    if datetime.now() >= end_time:
                        print(f"\n{Colors.GREEN}{'='*60}{Colors.RESET}")
                        print(f"{Colors.GREEN}✓ Время истекло. Отправка завершена.{Colors.RESET}")
                        print(f"{Colors.GREEN}{'='*60}{Colors.RESET}")
                        break
                elif limit_type == 'count' or limit_type == 'all':
                    if sent_count >= limit_value:
                        print(f"\n{Colors.GREEN}{'='*60}{Colors.RESET}")
                        print(f"{Colors.GREEN}✓ Достигнут лимит сообщений. Отправка завершена.{Colors.RESET}")
                        print(f"{Colors.GREEN}{'='*60}{Colors.RESET}")
                        break
                
                # Отправка сообщения
                message_text = messages[message_index % len(messages)]
                
                try:
                    await self.client.send_message(chat, message_text)
                    sent_count += 1
                    message_index += 1
                    
                    current_time = datetime.now().strftime('%H:%M:%S')
                    msg_preview = message_text[:50] + ('...' if len(message_text) > 50 else '')
                    print(f"[{current_time}] {Colors.GREEN}✓{Colors.RESET} Отправлено #{sent_count}: {msg_preview}")
                    
                    # Информация о прогрессе
                    if limit_type == 'time':
                        remaining = (end_time - datetime.now()).total_seconds() / 3600
                        print(f"   {Colors.YELLOW}Осталось времени: {remaining:.2f} ч.{Colors.RESET}")
                    elif limit_type in ['count', 'all']:
                        percent = (sent_count / limit_value) * 100
                        print(f"   {Colors.YELLOW}Прогресс: {sent_count}/{limit_value} ({percent:.1f}%){Colors.RESET}")
                    
                except Exception as e:
                    print(f"{Colors.RED}✗ Ошибка отправки: {e}{Colors.RESET}")
                
                # Ожидание перед следующим сообщением
                if sent_count < limit_value or (limit_type == 'time' and datetime.now() < end_time):
                    print(f"   {Colors.BLUE}Ожидание {interval} сек...{Colors.RESET}\n")
                    await asyncio.sleep(interval)
                    
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}{'='*60}{Colors.RESET}")
            print(f"{Colors.YELLOW}Отправка прервана пользователем.{Colors.RESET}")
            print(f"{Colors.YELLOW}{'='*60}{Colors.RESET}")
        
        # Статистика
        elapsed = datetime.now() - start_time
        hours = int(elapsed.total_seconds() // 3600)
        minutes = int((elapsed.total_seconds() % 3600) // 60)
        seconds = int(elapsed.total_seconds() % 60)
        
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.CYAN}{'  СТАТИСТИКА':^60}{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"\n{Colors.GREEN}Отправлено сообщений: {sent_count}{Colors.RESET}")
        print(f"{Colors.GREEN}Затрачено времени:    {hours:02d}:{minutes:02d}:{seconds:02d}{Colors.RESET}")
        if elapsed.total_seconds() > 0:
            print(f"{Colors.GREEN}Средняя скорость:     {sent_count / (elapsed.total_seconds() / 60):.2f} сообщений/мин{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    async def run(self):
        """Основной запуск программы"""
        try:
            await self.setup()
            chat = await self.get_chat()
            messages = await self.input_messages()
            
            if not messages:
                print(f"{Colors.RED}Нет сообщений для отправки!{Colors.RESET}")
                return
            
            interval, limit_type, limit_value = await self.get_sending_params(len(messages))
            
            print(f"\n{Colors.YELLOW}{'='*60}{Colors.RESET}")
            print(f"{Colors.YELLOW}Начать отправку? (да/нет): {Colors.RESET}", end='')
            confirm = input().strip().lower()
            
            if confirm in ['да', 'yes', 'y', 'д']:
                await self.send_messages(chat, messages, interval, limit_type, limit_value)
            else:
                print(f"{Colors.YELLOW}Отправка отменена.{Colors.RESET}")
                
        finally:
            if self.client:
                await self.client.disconnect()
                print(f"{Colors.BLUE}Отключено от Telegram.{Colors.RESET}")

async def main():
    sender = TelegramAutoSender()
    await sender.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Программа завершена.{Colors.RESET}")
