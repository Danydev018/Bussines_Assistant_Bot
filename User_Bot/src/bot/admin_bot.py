import os
from telegram import Update
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

ADMIN_ID = int(os.getenv('ADMIN_ID')) # tu user_id de Telegram, solo tú puedes usar el comando
PETICION_PATH = "ver_chats_request.txt"

async def ver_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("No autorizado.")
        return
    # Escribe un archivo como señal
    with open(PETICION_PATH, "w") as f:
        f.write("1")
    await update.message.reply_text("Petición enviada al userbot. Espera la respuesta.")

if __name__ == "__main__":
    import os
    import sys

    TOKEN_BOTFATHER = os.getenv("TOKEN_BOTFATHER")
    if not TOKEN_BOTFATHER:
        print("Define la variable de entorno BOTFATHER_TOKEN con el token del bot.")
        sys.exit(1)

    app = ApplicationBuilder().token(TOKEN_BOTFATHER).build()
    app.add_handler(CommandHandler("ver_chats", ver_chats))
    print("Bot admin corriendo...")
    app.run_polling()