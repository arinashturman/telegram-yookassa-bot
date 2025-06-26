import os
import uuid
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from yookassa import Configuration, Payment

app = FastAPI()

# Загружаем переменные среды
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOOKASSA_ACCOUNT_ID = os.getenv("YOOKASSA_ACCOUNT_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

# Настраиваем ЮKassa
Configuration.account_id = YOOKASSA_ACCOUNT_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

# Создаём Telegram приложение
telegram_app = Application.builder().token(BOT_TOKEN).build()

# Создаём FastAPI endpoint для Telegram Webhook
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

# Обработчик /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Смотреть уроки", callback_data="show_lessons")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Здесь я собрала свои авторские видеоуроки 💆‍♀️\n\n"
        "Выбери интересующий урок и начни заботу о себе прямо сейчас ✨",
        reply_markup=reply_markup
    )

# Обработчик кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_lessons":
        keyboard = [[InlineKeyboardButton("Выбрать урок ✅", callback_data="lesson_1")]]
        await query.message.reply_text(
            "*Список доступных уроков✨*\n▫️ТЕЙПЫ ПРОТИВ ОТЁКОВ",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif query.data == "lesson_1":
        caption = (
            "*Что тебя ждёт в уроке?*\n\n"
            "✔️ Подготовка кожи\n✔️ Аппликация\n✔️ Нанесение\n✔️ Эффект\n\n"
            "*Стоимость:* 1000 рублей."
        )
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
        payment_url = create_payment_link(
            amount_rub=1000,
            description="Урок: Тейпы против отёков",
            return_url="https://t.me/ИМЯ_ТВОЕГО_БОТА",
            telegram_user_id=query.from_user.id
        )
        await query.message.reply_text(
            f"🔗 Ссылка для оплаты:\n{payment_url}",
            disable_web_page_preview=True
        )

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

# Добавляем обработчики
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button_handler))

# При старте приложения регистрируем Webhook
@app.on_event("startup")
async def on_startup():
    await telegram_app.initialize()
    webhook_url = "https://telegram-yookassa-bot.onrender.com/webhook"
    await telegram_app.bot.set_webhook(webhook_url)
    await telegram_app.start()
    print("Webhook установлен:", webhook_url)

@app.on_event("shutdown")
async def on_shutdown():
    await telegram_app.stop()