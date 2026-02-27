import telebot
from telebot import types
from datetime import datetime
import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 4440544791

bot = telebot.TeleBot(TOKEN)

positions = {
    "Бродильний Цех (Бродильщик)": 143,
    "Кегомийний Цех (Старший зміни)": 143,
    "Кегомийний Цех (Кегомийщик)": 110,
    "Кегомийний Цех (Налив Бутилок)": 110,
}

user_data = {}

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Додати зміну")
    markup.add("Мій звіт")
    markup.add("Забрати зарплату")
    return markup

def position_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for p in positions:
        markup.add(p)
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {
            "name": None,
            "step": "register",
            "shifts": []
        }
        bot.send_message(chat_id, "Введіть Прізвище Імʼя:")
    else:
        bot.send_message(chat_id, "Меню:", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle(message):
    chat_id = message.chat.id
    text = message.text

    if chat_id not in user_data:
        user_data[chat_id] = {
            "name": None,
            "step": "register",
            "shifts": []
        }

    step = user_data[chat_id]["step"]

    if step == "register":
        user_data[chat_id]["name"] = text
        user_data[chat_id]["step"] = None
        bot.send_message(chat_id, "Реєстрація завершена ✅", reply_markup=main_keyboard())

    elif text == "Додати зміну":
        user_data[chat_id]["step"] = "position"
        bot.send_message(chat_id, "Оберіть посаду:", reply_markup=position_keyboard())

    elif step == "position" and text in positions:
        user_data[chat_id]["position"] = text
        user_data[chat_id]["rate"] = positions[text]
        user_data[chat_id]["step"] = "start_time"
        bot.send_message(chat_id, "Час початку роботи? (08:00)")

    elif step == "start_time":
        user_data[chat_id]["start_time"] = text
        user_data[chat_id]["step"] = "end_time"
        bot.send_message(chat_id, "Час завершення роботи? (18:00)")

    elif step == "end_time":
        user_data[chat_id]["end_time"] = text
        user_data[chat_id]["step"] = "break"
        bot.send_message(chat_id, "Обід (в хвилинах)?")

    elif step == "break":
        try:
            break_minutes = int(text)

            start = datetime.strptime(user_data[chat_id]["start_time"], "%H:%M")
            end = datetime.strptime(user_data[chat_id]["end_time"], "%H:%M")

            worked_minutes = (end - start).total_seconds() / 60 - break_minutes
            hours = round(worked_minutes / 60, 2)

            rate = user_data[chat_id]["rate"]
            total = round(hours * rate, 2)

            shift = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "month": datetime.now().month,
                "year": datetime.now().year,
                "position": user_data[chat_id]["position"],
                "hours": hours,
                "total": total
            }

            user_data[chat_id]["shifts"].append(shift)
            user_data[chat_id]["step"] = None

            bot.send_message(chat_id,
                             f"Зміна додана ✅\nГодини: {hours}\nСума: {total} грн",
                             reply_markup=main_keyboard())

            bot.send_message(ADMIN_ID,
                             f"Нова зміна:\n"
                             f"{user_data[chat_id]['name']}\n"
                             f"{shift['position']}\n"
                             f"{hours} год\n"
                             f"{total} грн")

        except:
            bot.send_message(chat_id, "Помилка формату часу.")

    elif text == "Мій звіт":
        total = sum(s["total"] for s in user_data[chat_id]["shifts"])
        bot.send_message(chat_id, f"Загальна сума: {total} грн")

    elif text == "Забрати зарплату":
        now = datetime.now()
        month = now.month
        year = now.year

        month_shifts = [
            s for s in user_data[chat_id]["shifts"]
            if s["month"] == month and s["year"] == year]

        total_month = sum(s["total"] for s in month_shifts)

        user_data[chat_id]["shifts"] = [
            s for s in user_data[chat_id]["shifts"]
            if not (s["month"] == month and s["year"] == year)
        ]

        bot.send_message(chat_id,
                         f"Зарплата за місяць: {total_month} грн\nОбнулено ✅")

    else:
        bot.send_message(chat_id, "Обери дію з меню.",
                         reply_markup=main_keyboard())

bot.infinity_polling()
