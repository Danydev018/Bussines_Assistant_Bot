import os
import sys
import asyncio
import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
import requests
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent.parent))
from shared_storage import save_message, get_pending_respuestas, mark_respuesta_sent, get_all_chats, get_user_status, get_user_position, cancel_turn, get_admin_setting, get_contact_recommendation, mark_contact_recommendation_sent

load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION = 'userbot_session'
TOKEN_BOTFATHER = os.getenv('TOKEN_BOTFATHER')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

client = TelegramClient(SESSION, API_ID, API_HASH)

notified_users = set()

def enviar_al_botfather(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN_BOTFATHER}/sendMessage"
    payload = {
        "chat_id": ADMIN_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

async def consultar_turno_action(event, user_id):
    position = get_user_position(user_id)
    if position:
        await event.reply(f"Estás en la posición #{position} de la fila.")
    else:
        await event.reply("No tienes un turno pendiente en este momento.")

async def cancelar_turno_action(event, user_id):
    cancel_turn(user_id)
    await event.reply("Tu turno ha sido cancelado y tu chat archivado.")

@client.on(events.NewMessage(incoming=True))
async def handler(event):

    print(f"[DEBUG User_Bot] Nuevo mensaje recibido. event.is_private={event.is_private}")
    if not event.is_private:
        print("[DEBUG User_Bot] Mensaje ignorado: no es privado.")
        return
    sender = await event.get_sender()
    if sender.is_self or getattr(sender, 'bot', False):
        print("[DEBUG User_Bot] Mensaje ignorado: es de self o bot.")
        return

    user_id = str(sender.id)
    user_status = get_user_status(user_id)
    text = event.text.lower().strip()

    # --- Enviar recomendación de contacto si existe ---
    rec = get_contact_recommendation(user_id)
    print(f"[DEBUG User_Bot] Buscando recomendación para user_id={user_id}. Resultado: {rec}")
    if rec:
        try:
            print(f"[DEBUG User_Bot] Enviando recomendación a {user_id}: nombre={rec['nombre']}, telefono={rec['telefono']}")
            await event.reply(
                f"🤝 Para resolver tu problematica Te recomendamos contactar a:\n<b>{rec['nombre']}</b>\n📞 <code>{rec['telefono']}</code>",
                parse_mode="HTML"
            )
            mark_contact_recommendation_sent(user_id)
            print(f"[DEBUG User_Bot] Recomendación marcada como enviada para {user_id}")
        except Exception as e:
            print(f"[DEBUG User_Bot] Error al enviar recomendación de contacto a {user_id}: {e}")

    buttons = [
        [Button.inline("Consultar mi Turno", data=b"consultar_turno")],
        [Button.inline("Cancelar mi Turno", data=b"cancelar_turno")]
    ]

    vacation_mode_active = get_admin_setting('vacation_mode_active') == 'True'
    vacation_message = get_admin_setting('vacation_mode_message')

    response_text = ""

    if text == "turno":
        await consultar_turno_action(event, user_id)
        return
    elif text == "cancelar":
        await cancelar_turno_action(event, user_id)
        return
    elif user_status in ["pendiente", "seguimiento"]:
        response_text = "Puedes consultar o cancelar tu turno:"
    else:
        save_message(user_id, event.text)
        response_text = "¡Gracias por tu mensaje! Te responderé pronto. Puedes consultar tu turno escribiendo `turno` o cancelarlo escribiendo `cancelar`."

    if vacation_mode_active and vacation_message:
        response_text += f"\n\n*Mensaje del Administrador:* {vacation_message}"

    await event.reply(response_text, buttons=buttons)

@client.on(events.CallbackQuery(data=b"consultar_turno"))
async def consultar_turno_callback(event):
    user_id = str(event.sender_id)
    await event.answer("", alert=False) # Dismiss the loading indicator
    await consultar_turno_action(event, user_id)

@client.on(events.CallbackQuery(data=b"cancelar_turno"))
async def cancelar_turno_callback(event):
    user_id = str(event.sender_id)
    await event.answer("", alert=False) # Dismiss the loading indicator
    await cancelar_turno_action(event, user_id)

async def loop_notificaciones():
    while True:
        vacation_mode_active = get_admin_setting('vacation_mode_active') == 'True'
        if vacation_mode_active:
            print("Modo descanso activo en User_Bot. Notificaciones de turno deshabilitadas.")
            await asyncio.sleep(1800) # Esperar 30 minutos antes de volver a chequear
            continue

        chats = get_all_chats()
        if not chats:
            await asyncio.sleep(1800)
            continue

        ahora = datetime.datetime.now()
        usuarios_pendientes = []
        for user_id, mensajes in chats.items():
            if any(m['estado'] == 'pendiente' for m in mensajes):
                ultimo_mensaje = max(mensajes, key=lambda m: datetime.datetime.fromisoformat(m['timestamp']))
                postpone_until_str = ultimo_mensaje.get('postpone_until')
                if postpone_until_str:
                    postpone_until_dt = datetime.datetime.fromisoformat(postpone_until_str)
                    if ahora < postpone_until_dt:
                        continue  # El chat está pospuesto
                
                primer_turno = min(m['turno'] for m in mensajes if m['estado'] == 'pendiente')
                usuarios_pendientes.append((user_id, primer_turno))

        usuarios_pendientes.sort(key=lambda x: x[1])

        for i, (user_id, turno) in enumerate(usuarios_pendientes[:3]):
            if user_id not in notified_users:
                try:
                    await client.send_message(int(user_id), f"¡Hola! Estás en la posición {i + 1} de la fila.")
                    notified_users.add(user_id)
                    print(f"Notificación de turno enviada a {user_id}")
                except Exception as e:
                    print(f"Error al notificar a {user_id}: {e}")
        
        current_pending_ids = {user_id for user_id, _ in usuarios_pendientes}
        notified_users.intersection_update(current_pending_ids)

        await asyncio.sleep(1800) # Notificar cada 30 minutos

async def loop_respuestas():
    print("Userbot iniciado y esperando respuestas para enviar...")
    while True:
        respuestas = get_pending_respuestas()
        for respuesta in respuestas:
            try:
                await client.send_message(
                    int(respuesta['user_id_destino']),
                    respuesta['texto_respuesta'],
                    parse_mode='HTML'
                )
                mark_respuesta_sent(respuesta['id'])
                print(f"Respuesta enviada a {respuesta['user_id_destino']}")
            except Exception as e:
                print(f"Error al enviar respuesta a {respuesta['user_id_destino']}: {e}")
        await asyncio.sleep(5)

if __name__ == "__main__":
    with client:
        client.loop.create_task(loop_respuestas())
        client.loop.create_task(loop_notificaciones())
        client.run_until_disconnected()

