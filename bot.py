import telebot
from telebot import types
import os
import sqlite3
from datetime import datetime, timedelta

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 440544791

# ---------- DATABASE ----------

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    full_name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    hourly_rate REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date TEXT,
    position_id INTEGER,
    start_time TEXT,
    end_time TEXT,
    lunch_minutes INTEGER,
    total_hours REAL,
    total_money REAL
)
""")

conn.commit()

# ---------- DEFAULT POSITIONS ----------

default_positions = {
    "Бродильщик": 143,
    "Старший зміни": 143,
    "Кегомийка": 110,
    "Цех бутилки": 110
}

for name, rate in default_positions.items():
    cursor.execute("INSERT OR IGNORE INTO positions (name, hourly_rate) VALUES (?, ?)", (name, rate))
conn.commit()

# ---------- STATES ----------

user_states = {}

# ---------- START ----------

@bot.message_handler(commands=['start'])
def start(message):
    cursor.execute("SELECT * FROM users WHERE telegram_id=?", (message.chat.id,))
    user = cursor.fetchone()

    if not user:
        bot.send_message(message.chat.id, "Введіть прізвище та ім'я:")
        user_states[message.chat.id] = {"step": "register"}
    else:
        show_main_menu(message.chat.id)

# ---------- MAIN MENU ----------

def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📝 Нова зміна", "📊 Тижневий звіт")
    if chat_id == ADMIN_ID:
        markup.add("⚙ Управління ставками")
    bot.send_message(chat_id, "Оберіть дію:", reply_markup=markup)

# ---------- TEXT HANDLER ----------

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.chat.id
    text = message.text

    if user_id in user_states:
        step = user_states[user_id]["step"]

        if step == "register":
            cursor.execute("INSERT INTO users (telegram_id, full_name) VALUES (?, ?)", (user_id, text))
            conn.commit()
            show_main_menu(user_id)

        elif step == "start_time":
            user_states[user_id]["start_time"] = text
            bot.send_message(user_id, "Введіть час завершення (HH:MM):")
            user_states[user_id]["step"] = "end_time"

        elif step == "end_time":
            user_states[user_id]["end_time"] = text
            bot.send_message(user_id, "Скільки хвилин тривав обід?")
            user_states[user_id]["step"] = "lunch"

        elif step == "lunch":
            save_shift(user_id, int(text))
            show_main_menu(user_id)

        elif step == "change_rate":
            position = user_states[user_id]["position"]
            cursor.execute("UPDATE positions SET hourly_rate=? WHERE name=?", (float(text), position))
            conn.commit()
            bot.send_message(user_id, "Ставку оновлено.")
            show_main_menu(user_id)

    elif text == "📝 Нова зміна":
        choose_date(user_id)

    elif text == "📊 Тижневий звіт":
        weekly_report(user_id)

    elif text == "⚙ Управління ставками" and user_id == ADMIN_ID:
        manage_rates(user_id)

# ---------- DATE SELECTION ----------

def choose_date(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime("%d.%m.%Y")
        markup.add(date)
    bot.send_message(chat_id, "Оберіть дату:", reply_markup=markup)
    user_states[chat_id] = {"step": "choose_position"}

@bot.message_handler(func=lambda message: "." in message.text and len(message.text) == 10)
def handle_date(message):
    user_id = message.chat.id
    if user_id in user_states:

       user_states[user_id]["date"] = message.text
       choose_position(user_id)

# ---------- POSITION ----------

def choose_position(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cursor.execute("SELECT name FROM positions")
    positions = cursor.fetchall()
    for p in positions:
        markup.add(p[0])
    bot.send_message(chat_id, "Оберіть посаду:", reply_markup=markup)
    user_states[chat_id]["step"] = "position"

@bot.message_handler(func=lambda message: True)
def handle_position(message):
    user_id = message.chat.id
    if user_id in user_states and user_states[user_id]["step"] == "position":
        user_states[user_id]["position"] = message.text
        bot.send_message(user_id, "Введіть час початку (HH:MM):")
        user_states[user_id]["step"] = "start_time"

# ---------- SAVE SHIFT ----------

def save_shift(user_id, lunch):
    data = user_states[user_id]
    start = datetime.strptime(data["start_time"], "%H:%M")
    end = datetime.strptime(data["end_time"], "%H:%M")

    hours = (end - start).seconds / 3600 - (lunch / 60)

    cursor.execute("SELECT id, hourly_rate FROM positions WHERE name=?", (data["position"],))
    position = cursor.fetchone()

    total = hours * position[1]

    cursor.execute("SELECT id FROM users WHERE telegram_id=?", (user_id,))
    user = cursor.fetchone()

    cursor.execute("""
    INSERT OR REPLACE INTO shifts (user_id, date, position_id, start_time, end_time, lunch_minutes, total_hours, total_money)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user[0], data["date"], position[0], data["start_time"], data["end_time"], lunch, hours, total))

    conn.commit()

    bot.send_message(user_id, f"Зміна збережена.\nГодини: {round(hours,2)}\nДо виплати: {round(total,2)} грн")

    if user_id != ADMIN_ID:
        cursor.execute("SELECT full_name FROM users WHERE telegram_id=?", (user_id,))
        name = cursor.fetchone()[0]
        bot.send_message(ADMIN_ID, f"🔔 Нова/Оновлена зміна\n{name}\n{data['date']}\n{data['position']}\n{data['start_time']}-{data['end_time']}\nОбід: {lunch} хв\nСума: {round(total,2)} грн")

# ---------- WEEKLY REPORT ----------

def weekly_report(user_id):
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    cursor.execute("""
    SELECT SUM(total_hours), SUM(total_money)
    FROM shifts
    WHERE user_id=(SELECT id FROM users WHERE telegram_id=?)
    AND date >= ?
    """, (user_id, week_ago.strftime("%d.%m.%Y")))

    result = cursor.fetchone()
    hours = result[0] if result[0] else 0
    money = result[1] if result[1] else 0

    bot.send_message(user_id, f"Тижневий звіт:\nГодини: {round(hours,2)}\nСума: {round(money,2)} грн")

# ---------- ADMIN RATES ----------

def manage_rates(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cursor.execute("SELECT name FROM positions")
    positions = cursor.fetchall()
    for p in positions:
        markup.add(p[0])
    bot.send_message(chat_id, "Оберіть посаду для зміни ставки:", reply_markup=markup)
    user_states[chat_id] = {"step": "admin_select"}

@bot.message_handler(func=lambda message: True)
def admin_select(message):
    user_id = message.chat.id
    if user_id == ADMIN_ID and user_id in user_states and user_states[user_id]["step"] == "admin_select":
        user_states[user_id]["position"] = message.text
        bot.send_message(user_id, "Введіть нову погодинну ставку:")
        user_states[user_id]["step"] = "change_rate"

from flask import Flask, request

app = Flask(__name__)

WEBHOOK_PATH = f"/{TOKEN}"
WEBHOOK_URL = f"https://work-hours-bot.onrender.com{WEBHOOK_PATH}"

bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

@app.route("/")
def index():
    return "Bot is running"

if name == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
