import os
import telebot
from flask import Flask, request
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8603408375  # твій Telegram ID

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

positions = {
    "Бродильний Цех (Бродильщик)": 143,
    "Кегомийний Цех (Старший зміни)": 143,
    "Кегомийний Цех (Кегомийщик)": 110,
    "Кегомийний Цех (Налив Бутилок)": 110
}

user_data = {}


def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Внести зміну")
    markup.add("Мій звіт")
    markup.add("Забрати зарплату")
    return markup


def position_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for pos in positions:
        markup.add(pos)
    return markup


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {
        "name": None,
        "step": "name",
        "shifts": []
    }
    bot.send_message(chat_id, "Введи ім'я та прізвище:")


@bot.message_handler(func=lambda message: True)
def handle(message):
    chat_id = message.chat.id
    text = message.text

    if chat_id not in user_data:
        return

    step = user_data[chat_id]["step"]

    if step == "name":
        user_data[chat_id]["name"] = text
        user_data[chat_id]["step"] = None
        bot.send_message(chat_id, "Готово ✅", reply_markup=main_keyboard())

    elif text == "Внести зміну":
        user_data[chat_id]["step"] = "position"
        bot.send_message(chat_id, "Вибери посаду:", reply_markup=position_keyboard())

    elif step == "position" and text in positions:
        user_data[chat_id]["position"] = text
        user_data[chat_id]["rate"] = positions[text]
        user_data[chat_id]["step"] = "hours"
        bot.send_message(chat_id, "Скільки годин?")

    elif step == "hours":
        try:
            hours = float(text)
            rate = user_data[chat_id]["rate"]
            total = hours * rate

            shift = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "position": user_data[chat_id]["position"],
                "hours": hours,
                "total": total
            }

            user_data[chat_id]["shifts"].append(shift)
            user_data[chat_id]["step"] = None

            bot.send_message(chat_id, f"Зміна додана ✅\n{hours} год × {rate} грн = {total} грн", reply_markup=main_keyboard())

            # звіт адміну
            bot.send_message(
                ADMIN_ID,
                f"Нова зміна:\n"
                f"{user_data[chat_id]['name']}\n"
                f"{shift['position']}\n"
                f"{hours} год\n"
                f"{total} грн"
            )

        except:
            bot.send_message(chat_id, "Введи число.")

    elif text == "Мій звіт":
        total = sum(s["total"] for s in user_data[chat_id]["shifts"])
        bot.send_message(chat_id, f"Загальна сума: {total} грн")

    elif text == "Забрати зарплату":
        month = datetime.now().month
        year = datetime.now().year

        total_month = 0
        remaining_shifts = []

        for shift in user_data[chat_id]["shifts"]:
            shift_date = datetime.strptime(shift["date"], "%Y-%m-%d")

            if shift_date.month == month and shift_date.year == year:
                total_month += shift["total"]
            else:
                remaining_shifts.append(shift)

        user_data[chat_id]["shifts"] = remaining_shifts

        bot.send_message(chat_id, f"Зарплата за місяць: {round(total_month, 2)} грн\nОбнулено ✅")


# ---------- WEBHOOK ----------

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


@app.route("/")
def index():
    return "Bot is running"


if name == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=os.getenv("RENDER_EXTERNAL_URL") + "/" + TOKEN)
    app.run(host="0.0.0.0", port=10000)
