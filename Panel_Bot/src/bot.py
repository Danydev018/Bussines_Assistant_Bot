import os
import datetime
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
from shared_storage import get_all_chats, get_messages, marcar_atendido, marcar_seguimiento, archivar_chat, save_respuesta, get_summary_by_status, get_daily_attended_chats_count, get_pending_chats_count, postpone_chat, get_current_queue_positions, get_admin_setting, save_admin_setting, save_contact_recommendation

# --- Contactos recomendados ---
CONTACTS_FILE = os.path.join(os.path.dirname(__file__), 'contactos_recomendados.json')

def load_contacts():
    if not os.path.exists(CONTACTS_FILE):
        return []
    with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_contacts(contacts):
    with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(contacts, f, ensure_ascii=False, indent=2)

async def add_contact_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    context.user_data['adding_contact_for'] = user_id
    await update.callback_query.edit_message_text(
        "Por favor, ingresa el nombre del contacto recomendado:")

async def handle_add_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Paso 1: nombre
    if 'adding_contact_for' in context.user_data and 'adding_contact_name' not in context.user_data:
        context.user_data['adding_contact_name'] = update.message.text.strip()
        await update.message.reply_text("Ahora ingresa el número de teléfono del contacto (solo dígitos, sin espacios ni guiones):")
        return True
    # Paso 2: teléfono
    elif 'adding_contact_for' in context.user_data and 'adding_contact_name' in context.user_data:
        nombre = context.user_data['adding_contact_name']
        telefono = update.message.text.strip()
        if not telefono.isdigit():
            await update.message.reply_text("El número debe contener solo dígitos. Intenta de nuevo:")
            return True
        contacts = load_contacts()
        contacts.append({'nombre': nombre, 'telefono': telefono})
        save_contacts(contacts)
        user_id = context.user_data['adding_contact_for']
        await update.message.reply_text(f"Contacto guardado: {nombre} ({telefono})\n¿Quieres compartirlo ahora?", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Compartir", callback_data=f"compartir_contacto_{len(contacts)-1}_{user_id}"),
             InlineKeyboardButton("❌ Cancelar", callback_data=f"ver_{user_id}")]
        ]))
        context.user_data.pop('adding_contact_for', None)
        context.user_data.pop('adding_contact_name', None)
        return True
    return False

async def compartir_contacto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    # data: compartir_contacto_{idx}_{user_id}
    parts = data.split('_')
    idx = int(parts[2])
    user_id = parts[3]
    contacts = load_contacts()
    if idx < 0 or idx >= len(contacts):
        await query.edit_message_text("❌ Contacto no encontrado.")
        return
    contacto = contacts[idx]
    nombre = contacto['nombre']
    telefono = contacto['telefono']
    print(f"[DEBUG Panel_Bot] Guardando recomendación para user_id={user_id}, nombre={nombre}, telefono={telefono}")
    # Guardar la recomendación como un mensaje pendiente, igual que la funcionalidad de Responder
    try:
        mensaje = f"🤝 Te recomendamos contactar a: <b>{nombre}</b>\n📞 <code>{telefono}</code>"
        # Usar la misma función que Responder para que el User_Bot lo procese igual
        save_respuesta(user_id, mensaje)
        print(f"[DEBUG Panel_Bot] Recomendación guardada como mensaje pendiente para user_id={user_id}")
        await query.edit_message_text(f"✅ Contacto recomendado guardado para el usuario {user_id}. Será enviado por el User_Bot.")
        # Volver al panel del chat atendido después del feedback, llamando directamente con user_id
        await ver_mensajes_callback(update, context, user_id_override=user_id)
    except Exception as e:
        print(f"[DEBUG Panel_Bot] Error al guardar la recomendación: {e}")
        await query.edit_message_text(f"❌ Error al guardar la recomendación: {e}")

async def recomendar_contacto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.data.replace("recomendar_contacto_", "")
    contacts = load_contacts()
    keyboard = []
    for idx, c in enumerate(contacts):
        keyboard.append([
            InlineKeyboardButton(f"{c['nombre']} ({c['telefono']})", callback_data=f"compartir_contacto_{idx}_{user_id}"),
            InlineKeyboardButton("🗑️ Eliminar", callback_data=f"eliminar_contacto_{idx}_{user_id}")
        ])
    keyboard.append([InlineKeyboardButton("➕ Nuevo contacto", callback_data=f"nuevo_contacto_{user_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Volver", callback_data=f"ver_{user_id}")])
    await query.edit_message_text(
        "Selecciona un contacto para recomendar, eliminar o agrega uno nuevo:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def eliminar_contacto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    # data: eliminar_contacto_{idx}_{user_id}
    parts = data.split('_')
    idx = int(parts[2])
    user_id = parts[3]
    contacts = load_contacts()
    if idx < 0 or idx >= len(contacts):
        await query.edit_message_text("❌ Contacto no encontrado.")
        return
    contacto = contacts.pop(idx)
    save_contacts(contacts)
    # Volver a mostrar la lista de contactos inmediatamente después de eliminar
    await recomendar_contacto_callback(update, context)

async def nuevo_contacto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.data.replace("nuevo_contacto_", "")
    await add_contact_start(update, context, user_id)

load_dotenv()

ADMIN_ID = int(os.getenv('ADMIN_ID'))
TOKEN_BOTFATHER = os.getenv("TOKEN_BOTFATHER")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu bot de administración. Usa /chats para ver las conversaciones.")

async def recordatorio_chats_pendientes(context: ContextTypes.DEFAULT_TYPE):
    if get_admin_setting('vacation_mode_active') == 'True':
        return

    chats_data = get_all_chats(include_archived=True)
    if not chats_data:
        return

    ahora = datetime.datetime.now()
    chats_pendientes_para_recordar = []

    for user_id, mensajes in chats_data.items():
        if any(m['estado'] == 'pendiente' for m in mensajes):
            ultimo_mensaje = max(mensajes, key=lambda m: datetime.datetime.fromisoformat(m['timestamp']))
            postpone_until_str = ultimo_mensaje.get('postpone_until')
            if postpone_until_str:
                postpone_until_dt = datetime.datetime.fromisoformat(postpone_until_str)
                if ahora < postpone_until_dt:
                    continue
            if ahora - datetime.datetime.fromisoformat(ultimo_mensaje['timestamp']) > datetime.timedelta(hours=1):
                chats_pendientes_para_recordar.append(user_id)

    if chats_pendientes_para_recordar:
        msg = "🔔 *Recordatorio de Chats Pendientes* 🔔\n\nLos siguientes chats llevan más de 1 hora sin ser atendidos (o su posposición ha terminado):\n"
        for user_id in chats_pendientes_para_recordar:
            msg += f"- Usuario `{user_id}`\n"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="Markdown")

def _build_summary_message():
    summary_by_status = get_summary_by_status()
    daily_attended = get_daily_attended_chats_count()
    pending_count = get_pending_chats_count()

    msg = "<b>📊 Resumen de Chats</b>\n\n"
    msg += "<b>Por Estado:</b>\n"
    for status, count in summary_by_status.items():
        msg += f"• <b>{status.capitalize()}</b>: {count} chats\n"

    msg += f"\n<b>Atendidos Hoy:</b> {daily_attended} chats\n"
    msg += f"<b>Pendientes en Cola:</b> {pending_count} chats\n"
    return msg

async def chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message_to_edit = query.message
    else:
        message_to_edit = update.message

    current_filter = context.user_data.get('chat_filter', 'pendiente')
    chats = get_all_chats(estado_filtro=current_filter)
    chats = {uid: msgs for uid, msgs in chats.items() if msgs}

    msg = ""
    keyboard = []
    queue_positions = get_current_queue_positions()


    # Botones de filtro y resumen con emojis y mejor agrupados
    filter_buttons = [
        InlineKeyboardButton("🟢 Pendientes", callback_data="filter_pendiente"),
        InlineKeyboardButton("🟡 Seguimiento", callback_data="filter_seguimiento"),
        InlineKeyboardButton("🔵 Atendidos", callback_data="filter_atendido"),
        InlineKeyboardButton("🗄️ Archivados", callback_data="filter_archivado")
    ]
    keyboard.append(filter_buttons[:2])
    keyboard.append(filter_buttons[2:])
    keyboard.append([
        InlineKeyboardButton("📊 Resumen", callback_data="show_resumen"),
        InlineKeyboardButton("🏖️ Descanso", callback_data="modo_descanso_toggle")
    ])

    # Chats listados con formato profesional
    if not chats:
        msg = f"❌ <b>No hay chats registrados con estado</b> <code>{current_filter}</code>\n\n" + _build_summary_message()
    else:
        msg = f"<b>👥 Chats registrados</b> <i>(Filtrado por: {current_filter.capitalize()})</i>\n" + "─"*12 + "\n"
        for user_id, mensajes in chats.items():
            last = mensajes[-1]
            estado = last.get('estado', 'desconocido').capitalize()
            categoria = last.get('categoria', 'otros').capitalize()
            current_position = queue_positions.get(user_id, '-')
            nombre = last.get('nombre', '')
            nombre_str = f"<b>{nombre}</b>\n" if nombre else ""
            msg += (
                f"👤 {nombre_str}<code>{user_id}</code>\n"
                f"📨 <b>{len(mensajes)}</b> mensajes\n"
                f"🏷️ {categoria}   📌 <b>{estado}</b>\n"
                f"⏳ Posición: <b>{current_position}</b>\n"
                + "─"*12 + "\n"
            )
            # Mostrar la posición en la cola debajo del texto del botón
            pos_str = f"Posición: {current_position}" if current_position != '-' else "Sin posición"
            keyboard.append([
                InlineKeyboardButton(f"💬 Ver mensajes\n{pos_str}", callback_data=f"ver_{user_id}")
            ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    new_msg = msg
    new_reply_markup = reply_markup

    current_message_text = None
    current_reply_markup = None
    if update.callback_query and message_to_edit:
        current_message_text = message_to_edit.text
        current_reply_markup = message_to_edit.reply_markup

    if (current_message_text != new_msg or str(current_reply_markup) != str(new_reply_markup)):
        if update.callback_query:
            await message_to_edit.edit_text(new_msg, parse_mode="HTML", reply_markup=new_reply_markup)
        else:
            await message_to_edit.reply_text(new_msg, parse_mode="HTML", reply_markup=new_reply_markup)
    elif not update.callback_query:
        await message_to_edit.reply_text(new_msg, parse_mode="HTML", reply_markup=new_reply_markup)

async def ver_mensajes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_override=None):
    query = update.callback_query
    await query.answer()
    if user_id_override is not None:
        user_id = user_id_override
    else:
        user_id = query.data.replace("ver_", "")
    mensajes = get_messages(user_id, include_archived=True)
    if not mensajes:
        await query.edit_message_text(f"No hay mensajes para el usuario {user_id}.")
        return

    msg = f"<b>📨 Mensajes de</b> <code>{user_id}</code>\n" + "─"*12 + "\n"
    for m in mensajes:
        fecha = m.get('timestamp', '')
        turno = m.get('turno', '')
        estado = m.get('estado', '').capitalize()
        texto = m.get('text', '')
        msg += (
            f"🕒 <i>{fecha}</i>\n"
            f"🔖 Turno: <b>{turno}</b>\n"
            f"📌 Estado: <b>{estado}</b>\n"
            f"<pre>{texto}</pre>\n"
            + "─"*12 + "\n"
        )
    keyboard = [
        [
            InlineKeyboardButton("✅ Atendido", callback_data=f"atendido_{user_id}"),
            InlineKeyboardButton("🔄 Seguimiento", callback_data=f"seguimiento_{user_id}")
        ],
        [
            InlineKeyboardButton("🗄️ Archivar", callback_data=f"archivar_{user_id}"),
            InlineKeyboardButton("✉️ Responder", callback_data=f"responder_{user_id}")
        ],
        [
            InlineKeyboardButton("⏰ Posponer", callback_data=f"posponer_opciones_{user_id}"),
            InlineKeyboardButton("📇 Recomendar contacto", callback_data=f"recomendar_contacto_{user_id}")
        ],
        [
            InlineKeyboardButton("🔙 Volver al panel", callback_data="volver_panel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=reply_markup)

async def gestion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = data.split("_")[-1]

    if data.startswith("atendido_"):
        marcar_atendido(user_id)
        await query.answer(f"Chat con {user_id} marcado como atendido.")
        await chats(update, context)
    elif data.startswith("seguimiento_"):
        marcar_seguimiento(user_id)
        await query.answer(f"Chat con {user_id} marcado para seguimiento.")
        await chats(update, context)
    elif data.startswith("archivar_"):
        user_id = data.replace("archivar_", "")
        archivar_chat(user_id)
        await query.answer(f"Chat con {user_id} archivado.")
        await chats(update, context)
    elif data.startswith("responder_"):
        context.user_data['responder_a'] = user_id
        await query.edit_message_text(f"✉️ Ahora escribe el mensaje que deseas enviar a `{user_id}`. Cuando lo envíes, se reenviará automáticamente.", parse_mode="Markdown")
    elif data.startswith("posponer_opciones_"):
        await show_postpone_options_callback(update, context, user_id)
    elif data.startswith("posponer_fijo_"):
        hours = int(data.split("_")[-2])
        await postpone_fixed_hours_callback(update, context, user_id, hours)
    elif data.startswith("posponer_custom_"):
        await ask_custom_postpone_hours_callback(update, context, user_id)
    elif data == "modo_descanso_toggle":
        await toggle_modo_descanso(update, context)
    elif data == "terminar_descanso_confirm":
        await confirm_end_vacation(update, context)
    elif data == "redefinir_horas":
        await ask_new_vacation_duration(update, context)
    elif data == "redefinir_mensaje":
        await ask_new_vacation_message(update, context)
    elif data == "volver_panel":
        await chats(update, context)

async def toggle_modo_descanso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    vacation_mode_active = get_admin_setting('vacation_mode_active') == 'True'

    if vacation_mode_active:
        vacation_message = get_admin_setting('vacation_mode_message') or "No establecido"
        vacation_end_time_str = get_admin_setting('vacation_mode_end_time')
        end_time_msg = "No definida"
        if vacation_end_time_str:
            try:
                end_time_dt = datetime.datetime.fromisoformat(vacation_end_time_str)
                end_time_msg = f"hasta el {end_time_dt.strftime('%Y-%m-%d %H:%M')}"
            except ValueError:
                end_time_msg = "inválida"

        keyboard = [
            [InlineKeyboardButton("Redefinir Horas", callback_data="redefinir_horas")],
            [InlineKeyboardButton("Redefinir Mensaje", callback_data="redefinir_mensaje")],
            [InlineKeyboardButton("Terminar Descanso Ahora", callback_data="terminar_descanso_confirm")],
            [InlineKeyboardButton("🔙 Volver al Panel", callback_data="volver_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🏖️ *Modo Descanso Activo* ({end_time_msg})\n"
            f"*Mensaje Actual:* _{vacation_message}_\n\n"
            "Selecciona una opción:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await ask_initial_vacation_duration(update, context)

async def ask_initial_vacation_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['setting_vacation_mode'] = True
    await query.edit_message_text("Por favor, ingresa la duración de tu descanso en horas (ej: `24` para 24 horas).")

async def ask_new_vacation_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['redefining_vacation_duration'] = True
    await query.edit_message_text("Por favor, ingresa la nueva duración del descanso en horas.")

async def ask_new_vacation_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['redefining_vacation_message'] = True
    await query.edit_message_text("Por favor, ingresa el nuevo mensaje de descanso.")

async def ask_vacation_message(update: Update, context: ContextTypes.DEFAULT_TYPE, duration):
    context.user_data['vacation_duration'] = duration
    await update.message.reply_text("Ahora, ingresa el mensaje personalizado que verán los usuarios durante tu descanso.")

async def set_vacation_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, duration, message):
    end_time = datetime.datetime.now() + datetime.timedelta(hours=duration)
    save_admin_setting('vacation_mode_active', 'True')
    save_admin_setting('vacation_mode_end_time', end_time.isoformat())
    save_admin_setting('vacation_mode_message', message)
    await update.message.reply_text(f"✅ Modo Descanso activado hasta {end_time.strftime('%Y-%m-%d %H:%M')}. Mensaje: '{message}'")
    context.user_data.pop('setting_vacation_mode', None)
    context.user_data.pop('vacation_duration', None)
    await chats(update, context)

async def confirm_end_vacation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    save_admin_setting('vacation_mode_active', 'False')
    save_admin_setting('vacation_mode_end_time', '')
    save_admin_setting('vacation_mode_message', '')
    await query.edit_message_text("✅ Modo Descanso terminado. Notificaciones reactivadas.")
    await chats(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.is_bot:
        return

    text = update.message.text
    responder_a = context.user_data.get('responder_a')
    redefining_duration = context.user_data.get('redefining_vacation_duration')
    redefining_message = context.user_data.get('redefining_vacation_message')
    setting_vacation_mode = context.user_data.get('setting_vacation_mode')
    vacation_duration = context.user_data.get('vacation_duration')
    waiting_for_custom_hours_user_id = context.user_data.get('waiting_for_custom_hours')

    # --- Añadir contacto recomendado ---
    handled = await handle_add_contact(update, context)
    if handled:
        return

    if redefining_duration:
        try:
            duration = int(text)
            if duration <= 0:
                raise ValueError("La duración debe ser un número positivo.")
            end_time = datetime.datetime.now() + datetime.timedelta(hours=duration)
            save_admin_setting('vacation_mode_end_time', end_time.isoformat())
            await update.message.reply_text(f"✅ Duración del descanso actualizada a {duration} horas.")
            context.user_data.pop('redefining_vacation_duration', None)
            await chats(update, context)
        except ValueError:
            await update.message.reply_text("❌ Por favor, ingresa un número válido de horas.")
        return
    elif redefining_message:
        save_admin_setting('vacation_mode_message', text)
        await update.message.reply_text("✅ Mensaje de descanso actualizado.")
        context.user_data.pop('redefining_vacation_message', None)
        await chats(update, context)
        return
    elif waiting_for_custom_hours_user_id:
        try:
            hours = int(text)
            if hours <= 0:
                raise ValueError("Las horas deben ser un número positivo.")
            postpone_chat(waiting_for_custom_hours_user_id, hours)
            await update.message.reply_text(f"✅ Chat con {waiting_for_custom_hours_user_id} pospuesto por {hours} hora(s).")
            context.user_data.pop('waiting_for_custom_hours', None)
            await chats(update, context)
        except ValueError:
            await update.message.reply_text("❌ Por favor, ingresa un número válido de horas.")
        finally:
            context.user_data.pop('waiting_for_custom_hours', None)
        return
    elif setting_vacation_mode and not vacation_duration:
        try:
            duration = int(text)
            if duration <= 0:
                raise ValueError("La duración debe ser un número positivo.")
            await ask_vacation_message(update, context, duration)
        except ValueError:
            await update.message.reply_text("❌ Por favor, ingresa un número válido de horas para la duración del descanso.")
        return
    elif setting_vacation_mode and vacation_duration:
        await set_vacation_mode(update, context, vacation_duration, text)
        return

    if responder_a:
        try:
            save_respuesta(responder_a, text)
            await chats(update, context)
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
        return

    context.user_data['chat_filter'] = filter_state
    await chats(update, context)

async def resumen_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = _build_summary_message()
    await update.message.reply_text(msg, parse_mode="HTML")

async def show_resumen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = _build_summary_message()
    current_reply_markup = query.message.reply_markup
    await query.edit_message_text(msg, parse_mode="HTML", reply_markup=current_reply_markup)

async def show_postpone_options_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("1 hora", callback_data=f"posponer_fijo_1_{user_id}"),
         InlineKeyboardButton("3 horas", callback_data=f"posponer_fijo_3_{user_id}")],
        [InlineKeyboardButton("24 horas", callback_data=f"posponer_fijo_24_{user_id}"),
         InlineKeyboardButton("Personalizado", callback_data=f"posponer_custom_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Selecciona por cuánto tiempo deseas posponer el chat de `{user_id}`:", reply_markup=reply_markup, parse_mode="Markdown")

async def postpone_fixed_hours_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, hours):
    query = update.callback_query
    postpone_chat(user_id, hours)
    await query.answer(f"Chat con {user_id} pospuesto por {hours} hora(s).")
    await chats(update, context)

async def ask_custom_postpone_hours_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    query = update.callback_query
    context.user_data['waiting_for_custom_hours'] = user_id
    await query.edit_message_text(f"Por favor, ingresa el número de horas para posponer el chat de `{user_id}`:", parse_mode="Markdown")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN_BOTFATHER).build()
    job_queue = app.job_queue
    job_queue.run_repeating(recordatorio_chats_pendientes, interval=3600, first=10)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chats", chats))
    app.add_handler(CommandHandler("resumen", resumen_chats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(ver_mensajes_callback, pattern=r"^ver_.*?$"))
    app.add_handler(CallbackQueryHandler(gestion_callback, pattern=r"^(atendido_|seguimiento_|archivar_|responder_|posponer_opciones_|posponer_fijo_|posponer_custom_).*?$"))
    app.add_handler(CallbackQueryHandler(filter_chats_callback, pattern=r"^filter_.*?$"))
    app.add_handler(CallbackQueryHandler(show_resumen_callback, pattern=r"^show_resumen$"))
    app.add_handler(CallbackQueryHandler(toggle_modo_descanso, pattern=r"^modo_descanso_toggle$"))
    app.add_handler(CallbackQueryHandler(confirm_end_vacation, pattern=r"^terminar_descanso_confirm$"))
    app.add_handler(CallbackQueryHandler(ask_new_vacation_duration, pattern=r"^redefinir_horas$"))
    app.add_handler(CallbackQueryHandler(ask_new_vacation_message, pattern=r"^redefinir_mensaje$"))
    app.add_handler(CallbackQueryHandler(chats, pattern=r"^volver_panel$"))
    # Contactos recomendados
    app.add_handler(CallbackQueryHandler(recomendar_contacto_callback, pattern=r"^recomendar_contacto_.*$"))
    app.add_handler(CallbackQueryHandler(compartir_contacto_callback, pattern=r"^compartir_contacto_.*$"))
    app.add_handler(CallbackQueryHandler(nuevo_contacto_callback, pattern=r"^nuevo_contacto_.*$"))
    app.add_handler(CallbackQueryHandler(eliminar_contacto_callback, pattern=r"^eliminar_contacto_.*$"))

    app.run_polling(allowed_updates=Update.ALL_TYPES)