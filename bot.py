import telebot
from telebot import apihelper
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import TOKEN
from extensions import CurrencyConverter, APIException

bot = telebot.TeleBot(TOKEN)

# Словарь состояний пользователей
user_data = {}

# Доступные валюты (только коды)
available_currencies = ['USD', 'EUR', 'RUB']


def get_currency_keyboard():
    """Возвращает клавиатуру с кнопками USD, EUR, RUB"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for code in available_currencies:
        keyboard.add(KeyboardButton(code))
    return keyboard


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'step': 1, 'base': None, 'quote': None, 'amount': None}
    keyboard = get_currency_keyboard()
    bot.send_message(
        chat_id,
        "Привет! Я помогу перевести одну валюту в другую.\n"
        "Доступны: USD, EUR, RUB.\n\n"
        "Выберите валюту, цену которой хотите узнать:",
        reply_markup=keyboard
    )


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(
        message,
        "Использование:\n"
        "1. Напишите /start\n"
        "2. Выбирайте валюты на кнопках (USD, EUR, RUB)\n"
        "3. Введите число\n\n"
        "Команды:\n"
        "/start – начать конвертацию\n"
        "/values – показать доступные валюты\n"
        "/help – эта справка"
    )


@bot.message_handler(commands=['values'])
def values_command(message):
    currencies = "\n".join([f"- {code}" for code in available_currencies])
    bot.reply_to(message, f"Доступные валюты:\n{currencies}")


@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip().upper()  # Приводим к верхнему регистру

    if chat_id not in user_data:
        bot.send_message(chat_id, "Пожалуйста, начните с команды /start")
        return

    state = user_data[chat_id]

    # Шаг 1: выбор валюты, которую переводим (base)
    if state['step'] == 1:
        if text not in available_currencies:
            bot.send_message(
                chat_id,
                f"Ошибка: '{text}' не является доступной валютой.\n"
                f"Доступны: {', '.join(available_currencies)}\n"
                "Выберите валюту из кнопок:",
                reply_markup=get_currency_keyboard()
            )
            return
        state['base'] = text
        state['step'] = 2
        bot.send_message(
            chat_id,
            f"Вы выбрали: {text}\n"
            "Теперь выберите валюту, в которой нужно узнать цену:",
            reply_markup=get_currency_keyboard()
        )

    # Шаг 2: выбор валюты, в которую переводим (quote)
    elif state['step'] == 2:
        if text not in available_currencies:
            bot.send_message(
                chat_id,
                f"Ошибка: '{text}' не является доступной валютой.\n"
                f"Доступны: {', '.join(available_currencies)}\n"
                "Выберите валюту из кнопок:",
                reply_markup=get_currency_keyboard()
            )
            return
        if text == state['base']:
            bot.send_message(
                chat_id,
                "Ошибка: нельзя переводить валюту саму в себя.\n"
                "Выберите другую валюту:",
                reply_markup=get_currency_keyboard()
            )
            return
        state['quote'] = text
        state['step'] = 3
        bot.send_message(
            chat_id,
            f"Вы выбрали: {text}\n"
            "Теперь введите количество валюты, которую необходимо перевести (число больше нуля):",
            reply_markup=ReplyKeyboardRemove()
        )

    # Шаг 3: ввод количества
    elif state['step'] == 3:
        try:
            amount = float(text)
        except ValueError:
            bot.send_message(
                chat_id,
                "Ошибка: количество должно быть числом (например, 100 или 50.5).\n"
                "Попробуйте ещё раз:",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        if amount <= 0:
            bot.send_message(
                chat_id,
                "Ошибка: количество должно быть больше нуля.\n"
                "Попробуйте ещё раз:",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        state['amount'] = amount

        base_code = state['base']
        quote_code = state['quote']

        try:
            result = CurrencyConverter.get_price(base_code, quote_code, amount)
            bot.send_message(
                chat_id,
                f"{amount} {base_code} = {result} {quote_code}",
                reply_markup=ReplyKeyboardRemove()
            )
        except APIException as e:
            bot.send_message(chat_id, f"Ошибка: {e}", reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            bot.send_message(chat_id, f"Непредвиденная ошибка: {e}", reply_markup=ReplyKeyboardRemove())

        del user_data[chat_id]
        bot.send_message(
            chat_id,
            "Конвертация завершена. Если хотите перевести другую валюту, введите /start",
            reply_markup=ReplyKeyboardRemove()
        )


if __name__ == '__main__':
    # Настройка HTTP/HTTPS прокси
    apihelper.proxy = {'https': 'http://185.11.134.227:8443'}

    print("Бот запущен...")
    bot.infinity_polling()