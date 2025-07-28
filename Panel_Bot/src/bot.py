import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
from shared_storage import get_all_chats, get_messages, marcar_atendido, marcar_seguimiento, archivar_chat, save_respuesta, get_summary_by_status, get_daily_attended_chats_count, get_pending_chats_count

load_dotenv()

ADMIN_ID = int(os.getenv('ADMIN_ID'))
TOKEN_BOTFATHER = os.getenv("TOKEN_BOTFATHER")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot de administración. Usa /chats para ver las conversaciones.")

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

def _build_summary_message():
    summary_by_status = get_summary_by_status()
    daily_attended = get_daily_attended_chats_count()
    pending_count = get_pending_chats_count()

    msg = "*Resumen de Chats:*\n\n"
    msg += "*Por Estado:*\n"
    for status, count in summary_by_status.items():
        msg += f"- {status.capitalize()}: {count} chats\n"

    msg += f"\n*Atendidos Hoy:* {daily_attended} chats\n"
    msg += f"*Pendientes en Cola:* {pending_count} chats\n"
    return msg

async def chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Determinar si la llamada viene de un comando o de un callback
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message_to_edit = query.message
    else:
        message_to_edit = update.message

    # Obtener el filtro actual del usuario o establecer "pendiente" por defecto
    current_filter = context.user_data.get('chat_filter', 'pendiente')

    chats = get_all_chats(estado_filtro=current_filter)
    chats = {uid: msgs for uid, msgs in chats.items() if msgs}

    msg = "" # Inicializar msg aquí, se construirá condicionalmente
    keyboard = []

    if not chats:
        msg = f"*No hay chats registrados con estado '{current_filter}'.*\n\n" + _build_summary_message() # Mostrar mensaje específico y luego resumen
    else:
        msg = f"*Chats registrados (Filtrado por: {current_filter.capitalize()})*: \n"
        for user_id, mensajes in chats.items():
            turnos = [m['turno'] for m in mensajes if m['estado'] == 'pendiente']
            estado = mensajes[-1].get('estado', 'desconocido') # Obtener el estado del último mensaje
            turno = min(turnos) if turnos else '-'
            categoria = mensajes[-1].get('categoria', 'otros')
            msg += f"\nUsuario `{user_id}`: {len(mensajes)} mensajes | Turno: {turno} | Estado: {estado} | Cat: {categoria}"
            keyboard.append([InlineKeyboardButton(f"Ver mensajes de {user_id}", callback_data=f"ver_{user_id}")])
    
    # Botones de filtro (siempre se muestran)
    filter_buttons_row1 = [
        InlineKeyboardButton("Pendientes", callback_data="filter_pendiente"),
        InlineKeyboardButton("En Seguimiento", callback_data="filter_seguimiento")
    ]
    filter_buttons_row2 = [
        InlineKeyboardButton("Atendidos", callback_data="filter_atendido"),
        InlineKeyboardButton("Archivados", callback_data="filter_archivado")
    ]
    summary_button_row = [
        InlineKeyboardButton("Resumen", callback_data="show_resumen")
    ]
    keyboard.append(filter_buttons_row1)
    keyboard.append(filter_buttons_row2)
    keyboard.append(summary_button_row)

    reply_markup = InlineKeyboardMarkup(keyboard) # Asegurar que reply_markup siempre se define

    # Construir el nuevo mensaje y teclado
    new_msg = msg
    new_reply_markup = reply_markup

    # Obtener el mensaje actual para comparar
    current_message_text = None
    current_reply_markup = None
    if update.callback_query and message_to_edit:
        current_message_text = message_to_edit.text
        current_reply_markup = message_to_edit.reply_markup

    # Solo editar si el contenido o el teclado son diferentes
    if (current_message_text != new_msg or 
        str(current_reply_markup) != str(new_reply_markup)):
        if update.callback_query:
            await message_to_edit.edit_text(new_msg, parse_mode="Markdown", reply_markup=new_reply_markup)
        else:
            await message_to_edit.reply_text(new_msg, parse_mode="Markdown", reply_markup=new_reply_markup)
    elif not update.callback_query: # Si no es un callback, siempre responder al comando /chats
        await message_to_edit.reply_text(new_msg, parse_mode="Markdown", reply_markup=new_reply_markup)

async def ver_mensajes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.data.replace("ver_", "")
    mensajes = get_messages(user_id, include_archived=True)
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
            InlineKeyboardButton("🔄 En Seguimiento", callback_data=f"seguimiento_{user_id}")
        ],
        [
            InlineKeyboardButton("🗄️ Archivar Chat", callback_data=f"archivar_{user_id}"),
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
    elif data.startswith("seguimiento_"):
        user_id = data.replace("seguimiento_", "")
        marcar_seguimiento(user_id)
        await query.edit_message_text(f"🔄 Chat de {user_id} marcado como en seguimiento.")
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

async def filter_chats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    filter_state = query.data.replace("filter_", "")
    
    current_filter = context.user_data.get('chat_filter', 'pendiente')

    if current_filter == filter_state:
        # Si el filtro es el mismo, no hacer nada para evitar el error "Message is not modified"
        return

    context.user_data['chat_filter'] = filter_state
    await chats(update, context) # Volver a llamar a chats con el nuevo filtro

async def resumen_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Esta función es para el comando /resumen
    msg = _build_summary_message()
    await update.message.reply_text(msg, parse_mode="Markdown")

async def show_resumen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = _build_summary_message()
    
    # Obtener el reply_markup actual del mensaje para mantener los botones
    current_reply_markup = query.message.reply_markup

    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=current_reply_markup)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN_BOTFATHER).build()
    job_queue = app.job_queue
    job_queue.run_repeating(recordatorio_chats_pendientes, interval=3600, first=10)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chats", chats))
    app.add_handler(CommandHandler("resumen", resumen_chats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(ver_mensajes_callback, pattern=r"^ver_.*?$"))
    app.add_handler(CallbackQueryHandler(gestion_callback, pattern=r"^(atendido_|seguimiento_|archivar_|responder_).*?$"))
    app.add_handler(CallbackQueryHandler(filter_chats_callback, pattern=r"^filter_.*?$"))
    app.add_handler(CallbackQueryHandler(show_resumen_callback, pattern=r"^show_resumen$"))

    app.run_polling(allowed_updates=Update.ALL_TYPES)