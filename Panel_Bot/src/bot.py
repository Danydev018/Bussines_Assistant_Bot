import os
from telegram import Update
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler , ContextTypes, filters
from storage import save_message, get_messages

load_dotenv()

TOKEN_BOTFATHER = os.getenv("TOKEN_BOTFATHER")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot. Escribe cualquier mensaje y lo guardaré para ti. Usa /inbox para ver tus mensajes.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    save_message(user_id, text)
    await update.message.reply_text("Mensaje guardado.")

async def show_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    msgs = get_messages(user_id)
    if not msgs:
        await update.message.reply_text("No tienes mensajes guardados.")
    else:
        await update.message.reply_text("Tus mensajes:\n" + "\n".join(msgs))

app = ApplicationBuilder().token(TOKEN_BOTFATHER).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("inbox", show_inbox))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling(allowed_updates=Update.ALL_TYPES)