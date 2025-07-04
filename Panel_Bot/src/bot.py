import os
from telegram import Update
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler , ContextTypes, filters
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
from shared_storage import get_all_chats, get_messages

async def chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chats = get_all_chats()
    # Filtrar solo usuarios con mensajes no vacíos
    chats = {uid: msgs for uid, msgs in chats.items() if msgs}
    if not chats:
        await update.message.reply_text("No hay chats registrados.")
        return
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    msg = "*Chats registrados:*\n"
    keyboard = []
    for user_id, mensajes in chats.items():
        msg += f"\nUsuario `{user_id}`: {len(mensajes)} mensajes"
        keyboard.append([InlineKeyboardButton(f"Ver mensajes de {user_id}", callback_data=f"ver_{user_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def ver_mensajes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.data.replace("ver_", "")
    mensajes = get_messages(user_id)
    if not mensajes:
        await query.edit_message_text(f"No hay mensajes para el usuario {user_id}.")
        return
    msg = f"*Mensajes de {user_id}:*\n\n" + "\n".join(f"- {m}" for m in mensajes)
    await query.edit_message_text(msg, parse_mode="Markdown")

load_dotenv()

TOKEN_BOTFATHER = os.getenv("TOKEN_BOTFATHER")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot. Escribe cualquier mensaje y lo guardaré para ti. Usa /inbox para ver tus mensajes.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ignorar mensajes enviados por otros bots para evitar bucles
    if update.message.from_user.is_bot:
        return
    user_id = update.message.from_user.id
    text = update.message.text
    # save_message solo debe ser usado por el user_bot, no por el panel_bot
    # save_message(user_id, text)
    # Ya no respondemos automáticamente para evitar bucles
    pass


# show_inbox eliminado, ahora solo se usa /chats

from telegram.ext import CallbackQueryHandler
app = ApplicationBuilder().token(TOKEN_BOTFATHER).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("chats", chats))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(
    CallbackQueryHandler(ver_mensajes_callback, pattern=r"^ver_.*")
)

app.run_polling(allowed_updates=Update.ALL_TYPES)