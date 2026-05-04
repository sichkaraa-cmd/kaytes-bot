import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
MANAGER_CHAT_ID = os.environ["MANAGER_CHAT_ID"]

AGENTS = {
    "agent1": {"name": "Марина Соколова",  "address": "Технопарк, корп. 2, эт. 4"},
    "agent2": {"name": "Алексей Громов",   "address": "БЦ Северный, Ленинградский пр-т"},
    "agent3": {"name": "Ольга Петрова",    "address": "БЦ Москва-Сити, башня Восток"},
}

PRODUCTS = {
    "p1": {"name": "Горбуша 250г", "price": 490},
    "p2": {"name": "Кета 250г",    "price": 590},
    "p3": {"name": "Нерка 250г",   "price": 690},
}

STEP_QTY, STEP_CONTACT = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    agent_code = args[0] if args else None
    agent = AGENTS.get(agent_code)

    context.user_data.clear()
    context.user_data["agent_code"] = agent_code
    context.user_data["agent"] = agent

    if agent:
        header = (
            f"Привет! Заказ через агента: *{agent['name']}*\n"
            f"Адрес доставки: {agent['address']}\n\n"
        )
    else:
        header = "Привет! Оформляем заказ красной икры Кайтес.\n\n"

    keyboard = [
        [InlineKeyboardButton("Горбуша 250г — 490₽", callback_data="prod_p1")],
        [InlineKeyboardButton("Кета 250г — 590₽",    callback_data="prod_p2")],
        [InlineKeyboardButton("Нерка 250г — 690₽",   callback_data="prod_p3")],
    ]
    await update.message.reply_text(
        header + "Выберите вид икры:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def product_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_key = query.data.replace("prod_", "")
    product = PRODUCTS[prod_key]
    context.user_data["product"] = product

    keyboard = [
        [InlineKeyboardButton("1", callback_data="qty_1"),
         InlineKeyboardButton("2", callback_data="qty_2"),
         InlineKeyboardButton("3", callback_data="qty_3")],
        [InlineKeyboardButton("5", callback_data="qty_5"),
         InlineKeyboardButton("10", callback_data="qty_10")],
    ]
    await query.edit_message_text(
        f"Выбрано: *{product['name']}* — {product['price']}₽\n\nСколько плошек?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return STEP_QTY


async def qty_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    qty = int(query.data.replace("qty_", ""))
    product = context.user_data["product"]
    total = product["price"] * qty
    context.user_data["qty"] = qty
    context.user_data["total"] = total

    await query.edit_message_text(
        f"*{product['name']}* × {qty} шт = *{total}₽*\n\n"
        f"Напишите ваше имя и телефон (или @username в Telegram):",
        parse_mode="Markdown"
    )
    return STEP_CONTACT


async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.text
    product = context.user_data["product"]
    qty     = context.user_data["qty"]
    total   = context.user_data["total"]
    agent   = context.user_data.get("agent")
    now     = datetime.now().strftime("%d.%m.%Y %H:%M")

    if agent:
        delivery = f"Агент *{agent['name']}* свяжется с вами.\nАдрес: {agent['address']}"
    else:
        delivery = "Менеджер свяжется с вами для уточнения деталей."

    await update.message.reply_text(
        f"✅ *Заказ принят!*\n\n"
        f"{product['name']} × {qty} шт = {total}₽\n\n"
        f"{delivery}",
        parse_mode="Markdown"
    )

    if agent:
        agent_line = f"👤 Агент: {agent['name']}\n📍 Адрес: {agent['address']}"
    else:
        agent_line = "⚠️ Прямой заказ (без агента)"

    manager_msg = (
        f"🆕 *НОВЫЙ ЗАКАЗ* — {now}\n\n"
        f"{agent_line}\n\n"
        f"🐟 Товар: {product['name']}\n"
        f"📦 Кол-во: {qty} шт\n"
        f"💰 Сумма: {total}₽\n\n"
        f"📞 Контакт: {contact}"
    )
    await context.bot.send_message(
        chat_id=MANAGER_CHAT_ID,
        text=manager_msg,
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Заказ отменён. Напишите /start чтобы начать заново.")
    return ConversationHandler.END


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(product_chosen, pattern="^prod_")
        ],
        states={
            STEP_QTY: [
                CallbackQueryHandler(qty_chosen, pattern="^qty_")
            ],
            STEP_CONTACT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, contact_received)
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel)
        ],
        allow_reentry=True
    )

    app.add_handler(conv)

    print("Бот запущен.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
