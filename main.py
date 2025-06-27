import os
import uuid
import logging
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from yookassa import Configuration, Payment

# ───── Логирование ───── #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ───── Загрузка переменных среды ───── #
def load_env():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    YOOKASSA_ACCOUNT_ID = os.getenv("YOOKASSA_ACCOUNT_ID")
    YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

    if not all([BOT_TOKEN, YOOKASSA_ACCOUNT_ID, YOOKASSA_SECRET_KEY]):
        raise RuntimeError("❌ Отсутствуют переменные среды: BOT_TOKEN, YOOKASSA_ACCOUNT_ID или YOOKASSA_SECRET_KEY")

    Configuration.account_id = YOOKASSA_ACCOUNT_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY
    return BOT_TOKEN

# ───── Инициализация ───── #
BOT_TOKEN = load_env()
telegram_app = Application.builder().token(BOT_TOKEN).build()
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    await telegram_app.initialize()
    logger.info("✅ Telegram bot initialized.")

# ───── Webhook ───── #
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error("Ошибка в webhook: %s", e)
    return {"ok": True}

# ───── Команда /start ───── #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Смотреть уроки", callback_data="show_lessons")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Здесь я собрала свои авторские видеоуроки 💆‍♀️\n\n"
        "Выбери интересующий урок и начни заботу о себе прямо сейчас ✨",
        reply_markup=reply_markup
    )

# ───── Обработка кнопок ───── #
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
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
            with open("lesson1.jpg", "rb") as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )

        elif query.data == "pay":
            url = create_payment_link(
                amount_rub=1000,
                description="Урок: Тейпы против отёков",
                return_url="https://t.me/natural_face_bot",  # 👈 Подставлен юзернейм
                telegram_user_id=query.from_user.id
            )
            await query.message.reply_text(f"🔗 Ссылка для оплаты:\n{url}", disable_web_page_preview=True)

    except Exception as e:
        logger.error("❌ Ошибка при обработке кнопки: %s", e)
        await query.message.reply_text("Произошла ошибка. Попробуйте позже.")

# ───── Создание платёжной ссылки ───── #
def create_payment_link(amount_rub, description, return_url, telegram_user_id):
    payment = Payment.create({
        "amount": {
            "value": f"{amount_rub:.2f}",
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
    }, idempotency_key=str(uuid.uuid4()))
    return payment.confirmation.confirmation_url

# ───── Регистрация хендлеров ───── #
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button_handler))