"""
Telegram Auto Message Sender
Отправляет сообщения в чат от вашего аккаунта с заданными интервалами
"""

import asyncio
import time
from telethon import TelegramClient
from telethon.tl.types import InputPeerChat, InputPeerChannel
from datetime import datetime, timedelta

# Цвета для консоли
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class TelegramAutoSender:
    def __init__(self):
        self.client = None
        self.api_id = None
        self.api_hash = None
        self.phone = None
        
    async def setup(self):
        """Настройка подключения к Telegram"""
        print(f"\n{Colors.BLUE}=== Настройка Telegram Auto Sender ==={Colors.RESET}\n")
        
        print("Для работы нужны API credentials от Telegram:")
        print("1. Перейдите на https://my.telegram.org")
        print("2. Войдите в свой аккаунт")
        print("3. Перейдите в 'API development tools'")
        print("4. Создайте приложение и получите api_id и api_hash\n")
        
        self.api_id = input("Введите ваш API ID: ").strip()
        self.api_hash = input("Введите ваш API HASH: ").strip()
        self.phone = input("Введите ваш номер телефона (с кодом страны, например +79123456789): ").strip()
        
        # Создаем клиент
        self.client = TelegramClient('session_' + self.phone, self.api_id, self.api_hash)
        
        print(f"\n{Colors.YELLOW}Подключение к Telegram...{Colors.RESET}")
        await self.client.start(phone=self.phone)
        print(f"{Colors.GREEN}✓ Успешно подключено!{Colors.RESET}\n")
        
    async def get_chat(self):
        """Выбор чата для отправки сообщений"""
        print(f"\n{Colors.BLUE}=== Выбор чата ==={Colors.RESET}\n")
        
        # Получаем список диалогов
        dialogs = await self.client.get_dialogs(limit=50)
        
        print("Доступные чаты:")
        for i, dialog in enumerate(dialogs, 1):
            chat_type = "Группа" if dialog.is_group else "Канал" if dialog.is_channel else "Личный"
            print(f"{i}. {dialog.name} ({chat_type})")
        
        while True:
            try:
                choice = int(input(f"\nВыберите номер чата (1-{len(dialogs)}): "))
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
        print(f"\n{Colors.BLUE}=== Ввод сообщений ==={Colors.RESET}\n")
        print("Введите сообщения, которые нужно отправить.")
        print("Каждое сообщение на новой строке.")
        print("Когда закончите, введите 'СТОП' на новой строке.\n")
        
        messages = []
        counter = 1
        
        while True:
            msg = input(f"Сообщение {counter}: ")
            if msg.strip().upper() == 'СТОП':
                break
            if msg.strip():
                messages.append(msg.strip())
                counter += 1
        
        print(f"\n{Colors.GREEN}✓ Добавлено {len(messages)} сообщений{Colors.RESET}")
        return messages
    
    async def get_sending_params(self, total_messages):
        """Настройка параметров отправки"""
        print(f"\n{Colors.BLUE}=== Настройка отправки ==={Colors.RESET}\n")
        print(f"Всего сообщений: {total_messages}")
        
        interval = int(input("\nИнтервал между сообщениями (в секундах, рекомендуется 10): ") or "10")
        
        print("\nВыберите режим:")
        print("1. По времени (указать часы работы)")
        print("2. По количеству сообщений")
        print("3. Отправить все сообщения")
        
        mode = input("\nВыберите режим (1/2/3): ").strip()
        
        limit_type = None
        limit_value = None
        
        if mode == '1':
            hours = float(input("Сколько часов должна работать программа? "))
            limit_type = 'time'
            limit_value = hours
            print(f"{Colors.YELLOW}Режим: по времени ({hours} ч.){Colors.RESET}")
        elif mode == '2':
            count = int(input("Сколько сообщений отправить? "))
            limit_type = 'count'
            limit_value = min(count, total_messages)
            print(f"{Colors.YELLOW}Режим: по количеству ({limit_value} сообщений){Colors.RESET}")
        else:
            limit_type = 'all'
            limit_value = total_messages
            print(f"{Colors.YELLOW}Режим: все сообщения ({total_messages} шт.){Colors.RESET}")
        
        return interval, limit_type, limit_value
    
    async def send_messages(self, chat, messages, interval, limit_type, limit_value):
        """Отправка сообщений"""
        print(f"\n{Colors.BLUE}=== Начало отправки ==={Colors.RESET}\n")
        
        start_time = datetime.now()
        end_time = None
        
        if limit_type == 'time':
            end_time = start_time + timedelta(hours=limit_value)
            print(f"Начало: {start_time.strftime('%H:%M:%S')}")
            print(f"Окончание: {end_time.strftime('%H:%M:%S')}")
        
        sent_count = 0
        message_index = 0
        
        try:
            while True:
                # Проверка условий остановки
                if limit_type == 'time':
                    if datetime.now() >= end_time:
                        print(f"\n{Colors.GREEN}✓ Время истекло. Отправка завершена.{Colors.RESET}")
                        break
                elif limit_type == 'count' or limit_type == 'all':
                    if sent_count >= limit_value:
                        print(f"\n{Colors.GREEN}✓ Достигнут лимит сообщений. Отправка завершена.{Colors.RESET}")
                        break
                
                # Отправка сообщения
                message_text = messages[message_index % len(messages)]
                
                try:
                    await self.client.send_message(chat, message_text)
                    sent_count += 1
                    message_index += 1
                    
                    current_time = datetime.now().strftime('%H:%M:%S')
                    print(f"[{current_time}] {Colors.GREEN}✓{Colors.RESET} Отправлено #{sent_count}: {message_text[:50]}{'...' if len(message_text) > 50 else ''}")
                    
                    # Информация о прогрессе
                    if limit_type == 'time':
                        remaining = (end_time - datetime.now()).total_seconds() / 3600
                        print(f"   Осталось времени: {remaining:.2f} ч.")
                    elif limit_type in ['count', 'all']:
                        print(f"   Прогресс: {sent_count}/{limit_value}")
                    
                except Exception as e:
                    print(f"{Colors.RED}✗ Ошибка отправки: {e}{Colors.RESET}")
                
                # Ожидание перед следующим сообщением
                if sent_count < limit_value or limit_type == 'time':
                    print(f"   Ожидание {interval} сек...\n")
                    await asyncio.sleep(interval)
                    
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Отправка прервана пользователем.{Colors.RESET}")
        
        # Статистика
        elapsed = datetime.now() - start_time
        print(f"\n{Colors.BLUE}=== Статистика ==={Colors.RESET}")
        print(f"Отправлено сообщений: {sent_count}")
        print(f"Затрачено времени: {elapsed}")
        print(f"Средняя скорость: {sent_count / (elapsed.total_seconds() / 60):.2f} сообщений/мин")
    
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
            
            print(f"\n{Colors.YELLOW}Начать отправку? (да/нет): {Colors.RESET}", end='')
            confirm = input().strip().lower()
            
            if confirm in ['да', 'yes', 'y', 'д']:
                await self.send_messages(chat, messages, interval, limit_type, limit_value)
            else:
                print(f"{Colors.YELLOW}Отправка отменена.{Colors.RESET}")
                
        finally:
            if self.client:
                await self.client.disconnect()
                print(f"\n{Colors.BLUE}Отключено от Telegram.{Colors.RESET}")

async def main():
    sender = TelegramAutoSender()
    await sender.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Программа завершена.{Colors.RESET}")
