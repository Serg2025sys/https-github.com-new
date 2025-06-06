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
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
ADMIN_ID = 466868254

if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не задано!")
if not WEBHOOK_URL:
    raise RuntimeError("❌ WEBHOOK_URL не задано!")

# 📦 Зберігаємо дані
user_message_map = {}
known_users = set()
user_phonebook = {}

# 📝 Зберегти контакт у CSV
def save_contact_to_csv(user_id, username, full_name, phone):
    file_exists = os.path.isfile("contacts.csv")
    rows = []
    if file_exists:
        with open("contacts.csv", "r", newline='', encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

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

# ✅ /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Бот працює через Webhook!")

# 📤 /export
async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        with open("contacts.csv", "rb") as f:
            await update.message.reply_document(InputFile(f), filename="contacts.csv")
    except FileNotFoundError:
        await update.message.reply_text("❌ Файл ще не створено.")

# 📥 Вхідне повідомлення
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    user_id = user.id
    known_users.add(user_id)

    phone = user_phonebook.get(user_id, "📵 номер не надано")
    user_display = f"@{user.username}" if user.username else user.full_name
    caption = f"📩 Від {user_display} (ID: {user_id})\n📱 Телефон: {phone}"

    keyboard = [
        [
            InlineKeyboardButton("❤️", callback_data=f"react_{user_id}_{msg.message_id}_heart"),
            InlineKeyboardButton("👍", callback_data=f"react_{user_id}_{msg.message_id}_like"),
            InlineKeyboardButton("😂", callback_data=f"react_{user_id}_{msg.message_id}_lol"),
        ],
        [
            InlineKeyboardButton("🤝", callback_data=f"react_{user_id}_{msg.message_id}_handshake"),
            InlineKeyboardButton("🔥", callback_data=f"react_{user_id}_{msg.message_id}_fire"),
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if msg.photo:
        file = msg.photo[-1].file_id
        sent = await context.bot.send_photo(chat_id=ADMIN_ID, photo=file, caption=caption, reply_markup=markup)
    elif msg.video:
        sent = await context.bot.send_video(chat_id=ADMIN_ID, video=msg.video.file_id, caption=caption, reply_markup=markup)
    elif msg.text:
        sent = await context.bot.send_message(chat_id=ADMIN_ID, text=f"{caption}:\n\n{msg.text}", reply_markup=markup)
    else:
        sent = await context.bot.send_message(chat_id=ADMIN_ID, text=f"{caption} — невідомий тип повідомлення.", reply_markup=markup)

    user_message_map[sent.message_id] = (user_id, msg.message_id)

    if user_id not in user_phonebook:
        button = KeyboardButton("📲 Надіслати номер", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True, one_time_keyboard=True)
        await msg.reply_text("Будь ласка, поділіться своїм номером телефону:", reply_markup=reply_markup)

# ☎️ Контакт
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact: Contact = update.message.contact
    user_id = contact.user_id or update.effective_user.id
    phone = contact.phone_number

    user_phonebook[user_id] = phone
    save_contact_to_csv(
        user_id=user_id,
        username=update.effective_user.username,
        full_name=update.effective_user.full_name or "",
        phone=phone
    )

    await update.message.reply_text("✅ Номер збережено. Дякуємо!")
    display = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.full_name
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📥 {display} надіслав номер: {phone}")

# 🔁 Відповідь/розсилка
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    reply = update.message.reply_to_message
    if reply:
        user_data = user_message_map.get(reply.message_id)
        if not user_data:
            await update.message.reply_text("❌ Не знайдено отримувача.")
            return

        user_id, user_msg_id = user_data
        if update.message.text:
            await context.bot.send_message(chat_id=user_id, text=update.message.text, reply_to_message_id=user
