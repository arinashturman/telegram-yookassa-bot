from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from yookassa import Configuration, Payment
import uuid
import asyncio
import os

# Настройки ЮKassa
Configuration.account_id = os.getenv("YOOKASSA_ACCOUNT_ID", "твой_id")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY", "твой_secret_key")

BOT_TOKEN = os.getenv("BOT_TOKEN", "твой_telegram_token")

# FastAPI
app = FastAPI()

# Telegram Application
telegram_app = Application.builder().token(BOT_TOKEN).build()

# Создание платежной ссылки
def create_payment_link(amount_rub: int, description: str, return_url: str, telegram_user_id: int) -> str:
    payment = Payment.create({
        "amount": {
            "value": f"{amount_rub}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url
        },
        "capture": True,
        "description": description,
        "metadata": {
            "telegram_user_id": telegram_user_id
        }
    }, idempotence_key=str(uuid.uuid4()))
    return payment.confirmation.confirmation_url

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Привет! Здесь я собрала свои авторские видеоуроки 💆‍♀️\n\n"
        "Выбери интересующий урок и начни заботу о себе прямо сейчас ✨"
    )
    keyboard = [[InlineKeyboardButton("Смотреть уроки", callback_data="show_lessons")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_lessons":
        text = "*Список доступных уроков✨*\n▫️ТЕЙПЫ ПРОТИВ ОТЁКОВ"
        keyboard = [[InlineKeyboardButton("Выбрать урок ✅", callback_data="lesson_1")]]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "lesson_1":
        caption = "*Что тебя ждёт в уроке?*\n\n" \
                  "✔️ Подготовка кожи\n✔️ Аппликация\n✔️ Нанесение\n✔️ Эффект\n\n" \
                  "*Стоимость:* 1000 рублей."
        keyboard = [
            [InlineKeyboardButton("Оплатить ✅", callback_data="pay")],
            [InlineKeyboardButton("↩️ Назад", callback_data="show_lessons")]
        ]
        await query.message.reply_photo(
            photo=open("lesson1.jpg", "rb"),
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif query.data == "pay":
        url = create_payment_link(
            amount_rub=1000,
            description="Урок: Тейпы против отёков",
            return_url="https://t.me/natural_face_bot",
            telegram_user_id=query.from_user.id
        )
        await query.message.reply_text(f"🔗 Ссылка для оплаты:\n{url}", disable_web_page_preview=True)

# Регистрируем хендлеры
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button_handler))

# Запускаем Telegram-бот как фон задачу
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(telegram_app.run_polling())

# ЮKassa Webhook
@app.post("/yookassa/webhook")
async def handle_webhook(request: Request):
    payload = await request.json()
    print("Webhook от ЮKassa:", payload)
    return {"status": "ok"}