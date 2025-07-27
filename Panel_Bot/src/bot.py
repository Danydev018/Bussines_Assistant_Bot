import os
from telegram import Update
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler , ContextTypes, filters
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
from shared_storage import get_all_chats, get_messages, marcar_atendido, eliminar_mensajes

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
        # Mostrar el turno más bajo pendiente y estado general
        turnos = [m['turno'] for m in mensajes if m['estado'] == 'pendiente']
        estado = 'pendiente' if any(m['estado'] == 'pendiente' for m in mensajes) else 'atendido'
        turno = min(turnos) if turnos else '-'
        msg += f"\nUsuario `{user_id}`: {len(mensajes)} mensajes | Turno: {turno} | Estado: {estado}"
        keyboard.append([InlineKeyboardButton(f"Ver mensajes de {user_id}", callback_data=f"ver_{user_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def ver_mensajes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[DEBUG Panel_Bot] Entró a ver_mensajes_callback")
    query = update.callback_query
    await query.answer()
    user_id = query.data.replace("ver_", "")
    mensajes = get_messages(user_id)
    if not mensajes:
        await query.edit_message_text(f"No hay mensajes para el usuario {user_id}.")
        return
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    msg = f"*Mensajes de {user_id}:*\n\n"
    for m in mensajes:
        msg += (f"- [{m['timestamp']}] Turno: {m['turno']} | Estado: {m['estado']}\n  {m['text']}\n")
    # Botones para marcar como atendido, eliminar y responder
    keyboard = [
        [
            InlineKeyboardButton("✅ Marcar como atendido", callback_data=f"atendido_{user_id}"),
            InlineKeyboardButton("🗑️ Eliminar chat", callback_data=f"eliminar_{user_id}")
        ],
        [
            InlineKeyboardButton("✉️ Responder", callback_data=f"responder_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def gestion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[DEBUG Panel_Bot] Entró a gestion_callback con data: {update.callback_query.data}")
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("atendido_"):
        user_id = data.replace("atendido_", "")
        marcar_atendido(user_id)
        await query.edit_message_text(f"✅ Chat de {user_id} marcado como atendido.")
    elif data.startswith("eliminar_"):
        user_id = data.replace("eliminar_", "")
        eliminar_mensajes(user_id)
        await query.edit_message_text(f"🗑️ Chat de {user_id} eliminado de la base de datos.")
    elif data.startswith("responder_"):
        user_id = data.replace("responder_", "")
        context.user_data['responder_a'] = user_id
        # Feedback inmediato y claro
        await query.edit_message_text(f"✉️ Ahora escribe el mensaje que deseas enviar a `{user_id}`. Cuando lo envíes, se reenviará automáticamente.", parse_mode="Markdown")


# Obtener ruta absoluta del archivo de respuestas
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
RESPUESTAS_PATH = str(BASE_DIR / "User_Bot/src/bot/respuestas_pendientes.txt")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ignorar mensajes enviados por otros bots para evitar bucles
    if update.message.from_user.is_bot:
        return
    responder_a = context.user_data.get('responder_a')
    text = update.message.text
    if responder_a:
        try:
            # Crear archivo si no existe
            if not os.path.exists(RESPUESTAS_PATH):
                with open(RESPUESTAS_PATH, "w") as f:
                    pass
            with open(RESPUESTAS_PATH, "a") as f:
                f.write(f"{responder_a}|{text}\n")
            print(f"[DEBUG Panel_Bot] Mensaje escrito en {RESPUESTAS_PATH}: {responder_a}|{text}")
            await update.message.reply_text(f"✅ Mensaje enviado a `{responder_a}`: {text}", parse_mode="Markdown")
        except Exception as e:
            print(f"[DEBUG Panel_Bot] Error al escribir mensaje: {e}")
            await update.message.reply_text(f"❌ Error al enviar mensaje: {e}")
        context.user_data['responder_a'] = None
        return
    # Si no está respondiendo a nadie, ignorar o manejar otros comandos aquí
    # pass

load_dotenv()

TOKEN_BOTFATHER = os.getenv("TOKEN_BOTFATHER")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot. Escribe cualquier mensaje y lo guardaré para ti. Usa /inbox para ver tus mensajes.")



# show_inbox eliminado, ahora solo se usa /chats

from telegram.ext import CallbackQueryHandler
app = ApplicationBuilder().token(TOKEN_BOTFATHER).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("chats", chats))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Handler para ver mensajes
app.add_handler(CallbackQueryHandler(ver_mensajes_callback, pattern=r"^ver_.*"))
# Handler para gestión de estado y responder
app.add_handler(CallbackQueryHandler(gestion_callback, pattern=r"^(atendido_|eliminar_|responder_).*$"))

app.run_polling(allowed_updates=Update.ALL_TYPES)