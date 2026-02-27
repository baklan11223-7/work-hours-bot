import os
from flask import Flask, request
import telebot
from telebot import types
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 4440544791

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

positions = {
    "Бродильний Цех (Бродильщик)": 143,
    "Кегомийний Цех (Старший зміни)": 143,
    "Кегомийний Цех (Кегомийщик)": 110,
    "Кегомийний Цех (Цех наливу СКЛА)": 110
}

user_data = {}


def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Додати зміну")
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
                "date": datetime.now(),
                "hours": hours,
                "total": total
            })

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
