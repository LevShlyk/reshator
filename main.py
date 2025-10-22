import os
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    filters,
)
from deepseek_client import DeepSeekClient  # ваш класс

# Константы состояний разговора
CHOOSING, TYPING = range(2)

# Меню кнопок
MENU = [
    [KeyboardButton("Решить уравнение")],
    [KeyboardButton("Вычислить процент")],
    [KeyboardButton("Найти площадь круга")],
    [KeyboardButton("Своя задача")]
]
MENU_MARKUP = ReplyKeyboardMarkup(MENU, resize_keyboard=True, one_time_keyboard=True)

# Инициализация DeepSeekClient
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
deepseek = DeepSeekClient(api_key=DEEPSEEK_API_KEY)


# Асинхронная функция вызова DeepSeek
async def call_deepseek(prompt: str) -> str:
    try:
        return await deepseek.simple_chat(prompt)
    except Exception as e:
        return f"Ошибка при запросе к DeepSeek: {e}"


# Точка входа — приветственное меню
async def entry_point(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Выбери действие:", reply_markup=MENU_MARKUP)
    return CHOOSING


# Обработка выбора пользователя
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    context.user_data['choice'] = choice

    if choice == "Решить уравнение":
        await update.message.reply_text("Введите уравнение, например: 3x + 5 = 11")
    elif choice == "Вычислить процент":
        await update.message.reply_text("Введите два числа через пробел: число и процент, например: 200 15")
    elif choice == "Найти площадь круга":
        await update.message.reply_text("Введите радиус круга, например: 5")
    elif choice == "Своя задача":
        await update.message.reply_text("Напишите текст задачи (в одно сообщение).")
    else:
        await update.message.reply_text("Не понял выбор. Попробуй ещё раз.", reply_markup=MENU_MARKUP)
        return CHOOSING

    return TYPING


# Обработка ввода данных и вызов нейросети
async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = context.user_data.get('choice', '')
    user_text = update.message.text.strip()

    # Формируем промт для DeepSeek
    if choice == "Решить уравнение":
        prompt = f"Реши уравнение «{user_text}» и подробно опиши шаги для ученика 1–9 класса. Включи проверку ответа."
    elif choice == "Вычислить процент":
        parts = user_text.split()
        if len(parts) != 2:
            await update.message.reply_text("Ошибка: введите два числа через пробел, например: 200 15")
            return TYPING
        prompt = f"Вычисли {parts[1]}% от {parts[0]}. Поясни шаги для ученика 1–9 класса."
    elif choice == "Найти площадь круга":
        prompt = f"Найди площадь круга с радиусом {user_text}. Покажи формулу, подставь значения, объясни шаги."
    else:
        prompt = f"Реши задачу: «{user_text}». Объясни подробно шаги, чтобы понял ученик 1–9 класса."

    await update.message.reply_text("Ищу решение... (запрос к нейросети)")
    answer = await call_deepseek(prompt)

    # Отправляем длинный ответ частями
    max_len = 4000
    for i in range(0, len(answer), max_len):
        await update.message.reply_text(answer[i:i + max_len])

    await update.message.reply_text("Что ещё хотите сделать?", reply_markup=MENU_MARKUP)
    return CHOOSING


# Команда /cancel — завершение разговора
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Разговор завершён. Напишите любое сообщение, чтобы начать заново.",
                                    reply_markup=MENU_MARKUP)
    return ConversationHandler.END


# Запуск бота
def main():
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
        print("Ошибка: установите TELEGRAM_BOT_TOKEN и DEEPSEEK_API_KEY в переменные окружения.")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", entry_point), MessageHandler(filters.TEXT & ~filters.COMMAND, entry_point)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choice)],
            TYPING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    print("Бот запущен. Напишите /start в Telegram, чтобы начать.")
    app.run_polling()


if __name__ == '__main__':
    main()
