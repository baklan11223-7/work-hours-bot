import os
from datetime import datetime
import telebot
from flask import Flask, request

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 440544791  # твій Telegram ID

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_data = {}

positions = {
    "Бродильщик": 143,
    "Старший зміни": 143,
    "Кегомийка": 110,
    "Цех бутилки": 110
}

def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Внести зміну")
    markup.add("Мій звіт")
    return markup

def position_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for pos in positions:
        markup.add(pos)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Введіть прізвище та ім'я:")
    user_data[message.chat.id] = {"step": "name"}

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text

    if chat_id not in user_data:
        user_data[chat_id] = {}

    step = user_data[chat_id].get("step")

    if step == "name":
        user_data[chat_id]["name"] = text
        user_data[chat_id]["step"] = None
        bot.send_message(chat_id, "Готово ✅", reply_markup=main_keyboard())

    elif text == "Внести зміну":
        bot.send_message(chat_id, "Виберіть посаду:", reply_markup=position_keyboard())
        user_data[chat_id]["step"] = "position"

    elif step == "position" and text in positions:
        user_data[chat_id]["position"] = text
        user_data[chat_id]["rate"] = positions[text]
        user_data[chat_id]["step"] = "start_time"
        bot.send_message(chat_id, "Введіть час початку (наприклад 08:00):")

    elif step == "start_time":
        user_data[chat_id]["start"] = text
        user_data[chat_id]["step"] = "end_time"
        bot.send_message(chat_id, "Введіть час завершення (наприклад 18:00):")

    elif step == "end_time":
        user_data[chat_id]["end"] = text
        user_data[chat_id]["step"] = "break"
        bot.send_message(chat_id, "Скільки хвилин була перерва? (наприклад 30):")

    elif step == "break":
        try:
            break_minutes = int(text)
            start_time = datetime.strptime(user_data[chat_id]["start"], "%H:%M")
            end_time = datetime.strptime(user_data[chat_id]["end"], "%H:%M")

            worked_minutes = (end_time - start_time).seconds / 60
            worked_hours = (worked_minutes - break_minutes) / 60

            rate = user_data[chat_id]["rate"]
            total = round(worked_hours * rate, 2)

            name = user_data[chat_id]["name"]
            position = user_data[chat_id]["position"]

            result = f"""
📋 Звіт
👤 {name}
🏷 {position}
⏰ {user_data[chat_id]["start"]} - {user_data[chat_id]["end"]}
🍽 Перерва: {break_minutes} хв
🕒 Годин: {round(worked_hours,2)}
💰 Зароблено: {total} грн
"""

            bot.send_message(chat_id, result, reply_markup=main_keyboard())
            bot.send_message(ADMIN_ID, "НОВА ЗМІНА:\n" + result)

            user_data[chat_id]["step"] = None

        except:
            bot.send_message(chat_id, "Помилка формату. Спробуйте ще раз.")

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

@app.route("/")
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=os.environ.get("RENDER_EXTERNAL_URL") + "/" + TOKEN)
    return "Webhook set!"

if name == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
