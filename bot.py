import os
import logging
import csv
from aiohttp import web
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    KeyboardButton, ReplyKeyboardMarkup, Contact, InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# 🔧 Логи
logging.basicConfig(level=logging.INFO)

# 🔑 Дані з середовища
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Наприклад: https://your-bot-name.onrender.com
ADMIN_ID = 466868254

# 🛡 Перевірка токена й URL
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не задано в середовищі!")
if not WEBHOOK_URL:
    raise RuntimeError("❌ WEBHOOK_URL не задано в середовищі!")

# 📦 Пам’ять
user_message_map = {}
known_users = set()
user_phonebook = {}

# 📝 Зберегти контакт у CSV
def save_contact_to_csv(user_id: int, username: str, full_name: str, phone: str):
    file_exists = os.path.isfile("contacts.csv")
    rows = []
    if file_exists:
        with open("contacts.csv", "r", newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    updated = False
    for row in rows:
        if int(row["user_id"]) == user_id:
            row["username"] = username or ""
            row["full_name"] = full_name
            row["phone"] = phone
            updated = True
            break

    if not updated:
        rows.append({
            "user_id": user_id,
            "username": username or "",
            "full_name": full_name,
            "phone": phone
        })

    with open("contacts.csv", "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "username", "full_name", "phone"])
        writer.writeheader()
        writer.writerows(rows)

# ✅ /start для перевірки
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Бот працює через Webhook!")

# ... [Твій інший код: export_csv, handle_user_message, handle_contact, handle_admin_reply, handle_reaction_callback] ...
# (залиш без змін — він уже коректний)

# 🌐 AIOHTTP обробник Webhook
async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(text="ok")
    except Exception as e:
        logging.error(f"❌ Помилка обробки webhook: {e}")
        return web.Response(status=500)

# ▶️ Запуск
async def main():
    global application
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("export", export_csv))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(~filters.User(user_id=ADMIN_ID), handle_user_message))
    application.add_handler(MessageHandler(filters.User(user_id=ADMIN_ID), handle_admin_reply))
    application.add_handler(CallbackQueryHandler(handle_reaction_callback))

    # Webhook
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    logging.info(f"✅ Webhook встановлено на: {WEBHOOK_URL}/webhook")

    # AIOHTTP сервер
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=port)
    await site.start()

    logging.info(f"🚀 Сервер запущено на порту {port}")

if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"❌ Помилка запуску: {e}")
