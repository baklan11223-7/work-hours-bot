import telebot
from telebot import types
from datetime import datetime
import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 440544791  # твій Telegram ID

bot = telebot.TeleBot(TOKEN)

# ---- ТВОЇ ПОСАДИ ----
positions = {
    "Бродильний Цех (Бродильщик)": 143,
    "Кегомийний Цех (Старший зміни)": 143,
    "Кегомийний Цех (Кегомийщик)": 110,
    "Кегомийний Цех (Налив Бутилок)": 110
}

user_data = {}

# ---- КНОПКИ ----
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Внести зміну")
    markup.add("Мій звіт")
    markup.add("Забрати зарплату")
    return markup

def position_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for pos in positions:
        markup.add(pos)
    return markup

# ---- START ----
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {
            "name": None,
            "shifts": []
        }
        bot.send_message(chat_id, "Введіть прізвище та ім'я:")
        user_data[chat_id]["step"] = "name"
    else:
        bot.send_message(chat_id, "Оберіть дію:", reply_markup=main_keyboard())

# ---- ОСНОВНА ЛОГІКА ----
@bot.message_handler(func=lambda message: True)
def handle(message):
    chat_id = message.chat.id
    text = message.text

    if chat_id not in user_data:
        user_data[chat_id] = {"name": None, "shifts": []}

    step = user_data[chat_id].get("step")

    # ---- Введення ПІБ ----
    if step == "name":
        user_data[chat_id]["name"] = text
        user_data[chat_id]["step"] = None
        bot.send_message(chat_id, "Реєстрація завершена ✅", reply_markup=main_keyboard())
        return

    # ---- Внести зміну ----
    if text == "Внести зміну":
        bot.send_message(chat_id, "Оберіть посаду:", reply_markup=position_keyboard())
        user_data[chat_id]["step"] = "position"

    elif step == "position" and text in positions:
        user_data[chat_id]["position"] = text
        user_data[chat_id]["rate"] = positions[text]
        user_data[chat_id]["step"] = "date"
        bot.send_message(chat_id, "Введіть дату (формат: 2026-03-05)")

    elif step == "date":
        try:
            datetime.strptime(text, "%Y-%m-%d")
            user_data[chat_id]["date"] = text
            user_data[chat_id]["step"] = "hours"
            bot.send_message(chat_id, "Введіть кількість годин:")
        except:
            bot.send_message(chat_id, "Неправильний формат. Приклад: 2026-03-05")

    elif step == "hours":
        try:
            hours = float(text)
            rate = user_data[chat_id]["rate"]
            total = hours * rate

            shift = {
                "date": user_data[chat_id]["date"],
                "hours": hours,
                "rate": rate,
                "total": total
            }

            user_data[chat_id]["shifts"].append(shift)

            name = user_data[chat_id]["name"]

            bot.send_message(chat_id,
                             f"Зміна додана ✅\n"
                             f"Дата: {shift['date']}\n"
                             f"Години: {shift['hours']}\n"
                             f"Сума: {shift['total']} грн",
                             reply_markup=main_keyboard())

            bot.send_message(ADMIN_ID,
                             f"НОВА ЗМІНА\n"
                             f"ПІБ: {name}\n"
                             f"Дата: {shift['date']}\n"
                             f"Посада: {user_data[chat_id]['position']}\n"
                             f"Години: {shift['hours']}\n"
                             f"Сума: {shift['total']} грн")

            user_data[chat_id]["step"] = None
        except:
            bot.send_message(chat_id, "Введіть правильну кількість годин")

    # ---- Мій звіт ----
    elif text == "Мій звіт":
        now = datetime.now()
        month = now.month
        year = now.year

        total_month = 0

        for shift in user_data[chat_id]["shifts"]:
            shift_date = datetime.strptime(shift["date"], "%Y-%m-%d")
            
            if shift_date.month == month and shift_date.year == year:
                total_month += shift["total"]

        bot.send_message(chat_id, f"Зарплата за поточний місяць: {round(total_month,2)} грн")

    # ---- Забрати зарплату ----
    elif text == "Забрати зарплату":
        now = datetime.now()
        month = now.month
        year = now.year

        total_month = 0
        new_shifts = []

        for shift in user_data[chat_id]["shifts"]:
            shift_date = datetime.strptime(shift["date"], "%Y-%m-%d")
            if shift_date.month == month and shift_date.year == year:
                total_month += shift["total"]
            else:
                new_shifts.append(shift)

        if total_month == 0:
            bot.send_message(chat_id, "Немає нарахувань за цей місяць.")
        else:
            bot.send_message(chat_id, f"Зарплата {round(total_month,2)} грн видана ✅")
            user_data[chat_id]["shifts"] = new_shifts

    else:
        bot.send_message(chat_id, "Оберіть дію:", reply_markup=main_keyboard())

bot.polling()
