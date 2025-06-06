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

# 🔑 Дані
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # https://your-render-name.onrender.com
ADMIN_ID = 466868254

user_message_map = {}
known_users = set()
user_phonebook = {}

# ✅ Функції (залиш ті самі: save_contact_to_csv, handle_contact, handle_user_message, export_csv, handle_admin_reply, handle_reaction_callback)

# 🌐 AIOHTTP хендлер для Telegram webhook
async def handle_webhook(request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response(text="ok")

# ▶️ Запуск
async def main():
    global application
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("export", export_csv))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(~filters.User(user_id=ADMIN_ID), handle_user_message))
    application.add_handler(MessageHandler(filters.User(user_id=ADMIN_ID), handle_admin_reply))
    application.add_handler(CallbackQueryHandler(handle_reaction_callback))

    # Реєструємо webhook
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")

    # HTTP-сервер
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=port)
    await site.start()

    print(f"🚀 Webhook активовано на {WEBHOOK_URL}/webhook")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
