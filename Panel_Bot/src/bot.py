import os
import datetime
from telegram import Update
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
from shared_storage import get_all_chats, get_messages, marcar_atendido, archivar_chat, save_respuesta

load_dotenv()

ADMIN_ID = int(os.getenv('ADMIN_ID'))
TOKEN_BOTFATHER = os.getenv("TOKEN_BOTFATHER")

async def recordatorio_chats_pendientes(context: ContextTypes.DEFAULT_TYPE):
    chats = get_all_chats()
    if not chats:
        return

    ahora = datetime.datetime.now()
    chats_pendientes = []
    for user_id, mensajes in chats.items():
        if any(m['estado'] == 'pendiente' for m in mensajes):
            ultimo_mensaje = max(mensajes, key=lambda m: datetime.datetime.fromisoformat(m['timestamp']))
            if ahora - datetime.datetime.fromisoformat(ultimo_mensaje['timestamp']) > datetime.timedelta(hours=1):
                chats_pendientes.append(user_id)

    if chats_pendientes:
        msg = "🔔 *Recordatorio de Chats Pendientes* 🔔\n\nLos siguientes chats llevan más de 1 hora sin ser atendidos:\n"
        for user_id in chats_pendientes:
            msg += f"- Usuario `{user_id}`\n"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="Markdown")

async def chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chats = get_all_chats()
    chats = {uid: msgs for uid, msgs in chats.items() if msgs}
    if not chats:
        await update.message.reply_text("No hay chats registrados.")
        return
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    msg = "*Chats registrados:*\n"
    keyboard = []
    for user_id, mensajes in chats.items():
        turnos = [m['turno'] for m in mensajes if m['estado'] == 'pendiente']
        estado = 'pendiente' if any(m['estado'] == 'pendiente' for m in mensajes) else 'atendido'
        turno = min(turnos) if turnos else '-'
        categoria = mensajes[-1].get('categoria', 'otros') # Obtener la categoría del último mensaje
        msg += f"\nUsuario `{user_id}`: {len(mensajes)} mensajes | Turno: {turno} | Estado: {estado} | Cat: {categoria}"
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
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    msg = f"*Mensajes de {user_id}:*\n\n"
    for m in mensajes:
        msg += (f"- [{m['timestamp']}] Turno: {m['turno']} | Estado: {m['estado']}\n  {m['text']}\n")
    keyboard = [
        [
            InlineKeyboardButton("✅ Marcar como atendido", callback_data=f"atendido_{user_id}"),
            InlineKeyboardButton("🗄️ Archivar Chat", callback_data=f"archivar_{user_id}")
        ],
        [
            InlineKeyboardButton("✉️ Responder", callback_data=f"responder_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def gestion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("atendido_"):
        user_id = data.replace("atendido_", "")
        marcar_atendido(user_id)
        await query.edit_message_text(f"✅ Chat de {user_id} marcado como atendido.")
    elif data.startswith("archivar_"):
        user_id = data.replace("archivar_", "")
        archivar_chat(user_id)
        await query.edit_message_text(f"🗄️ Chat de {user_id} archivado.")
    elif data.startswith("responder_"):
        user_id = data.replace("responder_", "")
        context.user_data['responder_a'] = user_id
        await query.edit_message_text(f"✉️ Ahora escribe el mensaje que deseas enviar a `{user_id}`. Cuando lo envíes, se reenviará automáticamente.", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.is_bot:
        return
    responder_a = context.user_data.get('responder_a')
    text = update.message.text
    if responder_a:
        try:
            save_respuesta(responder_a, text)
            await update.message.reply_text(f"✅ Mensaje para `{responder_a}` guardado en la base de datos para ser enviado.", parse_mode="Markdown")
        except Exception as e:
            print(f"[DEBUG Panel_Bot] Error al guardar respuesta: {e}")
            await update.message.reply_text(f"❌ Error al guardar la respuesta: {e}")
        context.user_data['responder_a'] = None
        return

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot de administración. Usa /chats para ver las conversaciones.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN_BOTFATHER).build()
    job_queue = app.job_queue
    job_queue.run_repeating(recordatorio_chats_pendientes, interval=3600, first=10)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chats", chats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(ver_mensajes_callback, pattern=r"^ver_.*?"))
    app.add_handler(CallbackQueryHandler(gestion_callback, pattern=r"^(atendido_|archivar_|responder_).*?"))

    app.run_polling(allowed_updates=Update.ALL_TYPES)
