from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from yookassa import Configuration, Payment
from fastapi import FastAPI, Request
import asyncio
import uuid
import logging
from threading import Thread

# Настройки логов
logging.basicConfig(level=logging.INFO)

# Настройки ЮKassa
Configuration.account_id = '1111202'
Configuration.secret_key = 'live_ZH5lu2pWuE-NviXGnfdE3N4acMupaT8GcB8rbUHTPdY'

# Telegram токен
TOKEN = "7945507873:AAFzT8i4DNdkNrvgQMd6mYQ8KhpL71Ngp1U"

# FastAPI приложение
fastapi_app = FastAPI()

# Telegram-приложение
app = ApplicationBuilder().token(TOKEN).build()

# --- Создание платежной ссылки ---
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

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Приветствую тебя! Здесь я собрала свои авторские видеоуроки, которые можно повторять дома: просто, удобно и эффективно 💆‍♀️\n\n"
        "Видеоуроки придут тебе сразу же в этот бот, после оплаты. "
        "Выбери интересующий урок и начни заботу о себе прямо сейчас ✨"
    )
    keyboard = [
        [InlineKeyboardButton("Смотреть уроки", callback_data="show_lessons")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

# --- Обработка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_lessons":
        text = "*Список доступных уроков✨*\n\n▫️ТЕЙПЫ ПРОТИВ ОТЁКОВ"
        keyboard = [
            [InlineKeyboardButton("Выбрать урок ✅", callback_data="lesson_1")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")

    elif query.data == "lesson_1":
        photo_path = "lesson1.jpg"
        caption = "*Что тебя ждёт в уроке?*\n\n" \
                  "✔️ Подготовка кожи к тейпированию\n" \
                  "✔️ Меры осторожности и как сделать тест на аллергию\n" \
                  "✔️ Как вырезать аппликацию от отёков\n" \
                  "✔️ Правильная техника нанесения тейпов\n" \
                  "✔️ Сколько носить тейпы, чтобы был эффект\n" \
                  "Как аккуратно снять аппликацию, не повредив кожу\n\n" \
                  "🎥 Только практика и ничего лишнего. Подойдёт даже тем, кто никогда не делал тейпирование.\n\n" \
                  "*Стоимость:* 1000 рублей."
        keyboard = [
            [InlineKeyboardButton("Оплатить ✅", callback_data="pay")],
            [InlineKeyboardButton("↩️ Назад к списку", callback_data="show_lessons")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_photo(
            photo=open(photo_path, "rb"),
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    elif query.data == "pay":
        payment_url = create_payment_link(
            amount_rub=1000,
            description="Урок: Тейпы против отёков",
            return_url="https://t.me/natural_face_bot",
            telegram_user_id=query.from_user.id
        )
        await query.message.reply_text(
            f"🔗 Вот ваша ссылка для оплаты:\n{payment_url}",
            disable_web_page_preview=True
        )

# --- Webhook для ЮKassa ---
@fastapi_app.post("/webhook")

async def handle_yookassa_webhook(request: Request):
    data = await request.json()
    logging.info(f"Webhook получен: {data}")

    event = data.get("event")
    object_data = data.get("object", {})
    metadata = object_data.get("metadata", {})

    if event == "payment.succeeded":
        telegram_user_id = metadata.get("telegram_user_id")
        if telegram_user_id:
            try:
                await app.bot.send_message(
                    chat_id=telegram_user_id,
                    text="🎉 Оплата прошла успешно! Вот ваш видеоурок:\n[Ваша ссылка на урок или вложение]"
                )
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения пользователю: {e}")

    return {"status": "ok"}

# --- Запуск Telegram-бота в отдельном потоке ---
def run_telegram_bot():
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

telegram_thread = Thread(target=run_telegram_bot)
telegram_thread.start()