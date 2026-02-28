import os
import json
from flask import Flask, request
import telebot
from telebot import types
from datetime import datetime
import sqlite3

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 4440544791

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    date TEXT,
    hours REAL,
    total REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS advances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    amount REAL
)
""")

conn.commit()

DATA_FILE = "users.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

positions = {
    "Бродильний Цех (Бродильщик)": 143,
    "Кегомийний Цех (Старший зміни)": 143,
    "Кегомийний Цех (Кегомийщик)": 110,
    "Кегомийний Цех (Цех наливу СКЛА)": 110
}

user_data = load_data()


def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Додати зміну")
    markup.row("📅 Змінити день")
    markup.row("📊 Мій звіт")
    markup.row("➖ Взяти аванс")
    markup.row("💰 Забрати зарплату")
    return markup


def position_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for pos in positions:
        markup.row(pos)
    return markup


@bot.message_handler(func=lambda message: True)
def handle(message):
    chat_id = message.chat.id
    text = message.text

    if chat_id not in user_data:
        user_data[chat_id] = {
            "name": None,
            "step": None,
            "position": None,
            "rate": 0,
            "start": None,
            "end": None,
            "selecte_day": datetime.now().day,
            "shifts": [],
            "advances": []
        }

    user = user_data[chat_id]
    step = user["step"]

    if text == "/start":
        user["step"] = "name"
        bot.send_message(chat_id, "Введіть Прізвище Імʼя:")
        return

    if step == "name":
        user["name"] = text
        user["step"] = None
        bot.send_message(chat_id, f"Вітаю, {text}", reply_markup=main_keyboard())
        return

    if text == "📅 Змінити день":
        user["step"] = "change_day"
        bot.send_message(chat_id, "Введіть день місяця (1–31):")
        return

    if step == "change_day":
        try:
            day = int(text)

            if 1 <= day <= 31:
                user["selected_day"] = day
                user["step"] = None
                bot.send_message(
                    chat_id,
                    f"День змінено на {day} число ✅",
                    reply_markup=main_keyboard()
                )
            else:
                bot.send_message(chat_id, "Введіть число від (1 до 31):")

        except Exception:
            bot.send_message(chat_id, "Введіть число")

        return
    if text == "➕ Додати зміну":
        user["step"] = "position"
        bot.send_message(chat_id, "Оберіть посаду:", reply_markup=position_keyboard())
        return

    if step == "position" and text in positions:
        user["position"] = text
        user["rate"] = positions[text]
        user["step"] = "start"
        bot.send_message(chat_id, "Час початку роботи? (08:00)")
        return

    if step == "start":
        user["start"] = text
        user["step"] = "end"
        bot.send_message(chat_id, "Час завершення роботи? (18:00)")
        return

    if step == "end":
        user["end"] = text
        user["step"] = "break"
        bot.send_message(chat_id, "Обід (в хвилинах)?")
        return

    if step == "break":
        try:
            break_minutes = int(text)

            start = datetime.strptime(user["start"], "%H:%M")
            end = datetime.strptime(user["end"], "%H:%M")

            worked_minutes = (end - start).total_seconds() / 60 - break_minutes
            hours = round(worked_minutes / 60, 2)
            total = round(hours * user["rate"], 2)

            user["shifts"].append({
                "date": f"{datetime.now().year}-{datetime.now().month:02d}-{user['selected_day']:02d}",
                "hours": hours,
                "total": total
            })
            
            save_data(user_data)

            user["step"] = None

            bot.send_message(
                chat_id,
                f"Зміна додана ✅\nГодини: {hours}\nСума: {total} грн",
                reply_markup=main_keyboard()
            )

            bot.send_message(
                ADMIN_ID,
                f"НОВА ЗМІНА:\n{user['name']}\n{user['position']}\n{hours} год\n{total} грн"
            )
        except:
            bot.send_message(chat_id, "Помилка формату часу.")
        return

    if text == "➖ Взяти аванс":
        user["step"] = "advance"
        bot.send_message(chat_id, "Введіть суму авансу:")
        return

    if step == "advance":
        try:
            amount = float(text)
            user["advances"].append({
                "date": datetime.now(),
                "amount": amount
            })
            user["step"] = None

            bot.send_message(chat_id, f"Аванс {amount} грн додано ✅", reply_markup=main_keyboard())

            bot.send_message(
                ADMIN_ID,
                f"АВАНС:\n{user['name']}\n{amount} грн"
            )
        except:
            bot.send_message(chat_id, "Введіть число.")
        return

    if text == "📊 Мій звіт":
        total = sum(s["total"] for s in user["shifts"])
        advance_total = sum(a["amount"] for a in user["advances"])
        to_pay = total - advance_total

        bot.send_message(
            chat_id,
            f"Нараховано: {total} грн\n"
            f"Аванс: {advance_total} грн\n"
            f"До виплати: {to_pay} грн"
        )
        return

    if text == "💰 Забрати зарплату":
        total = sum(s["total"] for s in user["shifts"])
        advance_total = sum(a["amount"] for a in user["advances"])
        to_pay = total - advance_total

        user["shifts"].clear()
        user["advances"].clear()

        bot.send_message(
            chat_id,
            f"Виплачено: {to_pay} грн\nОбнулено ✅",
            reply_markup=main_keyboard()
        )
        return

    bot.send_message(chat_id, "Обери дію з меню.", reply_markup=main_keyboard())


@app.route('/', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return '', 200


@app.route('/', methods=['GET'])
def index():
    return "Bot is running"


if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=os.getenv("RENDER_EXTERNAL_URL"))
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
