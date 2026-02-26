import telebot
import os
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

data = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привіт! Введи зміну у форматі:\n08:00-18:00 0.5 150\n(початок-кінець обід ставка)")

@bot.message_handler(func=lambda message: True)
def handle_shift(message):
    try:
        parts = message.text.split()
        time_part = parts[0]
        lunch = float(parts[1])
        rate = float(parts[2])

        start_time, end_time = time_part.split('-')

        fmt = "%H:%M"
        start_dt = datetime.strptime(start_time, fmt)
        end_dt = datetime.strptime(end_time, fmt)

        hours = (end_dt - start_dt).seconds / 3600 - lunch
        salary = hours * rate

        user_id = message.chat.id

        if user_id not in data:
            data[user_id] = 0

        data[user_id] += salary

        bot.send_message(message.chat.id, f"Відпрацьовано: {hours} год\nЗароблено: {salary} грн\nЗагалом: {data[user_id]} грн")

    except:
        bot.send_message(message.chat.id, "Помилка формату.\nПриклад:\n08:00-18:00 0.5 150")

bot.infinity_polling()
