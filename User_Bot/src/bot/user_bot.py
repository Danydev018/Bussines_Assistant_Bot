import os
import sys
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
import requests
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent.parent))
from shared_storage import save_message, get_pending_respuestas, mark_respuesta_sent, get_all_chats

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

@client.on(events.NewMessage(incoming=True))
async def handler(event):
    if not event.is_private:
        return
    sender = await event.get_sender()
    if sender.is_self or getattr(sender, 'bot', False):
        return
    save_message(sender.id, event.text)
    await event.reply("¡Gracias por tu mensaje! Te responderé pronto.")

async def loop_notificaciones():
    while True:
        chats = get_all_chats()
        if not chats:
            await asyncio.sleep(60)
            continue

        # Obtener solo los usuarios con estado pendiente
        usuarios_pendientes = sorted([
            (user_id, min(m['turno'] for m in mensajes if m['estado'] == 'pendiente'))
            for user_id, mensajes in chats.items()
            if any(m['estado'] == 'pendiente' for m in mensajes)
        ], key=lambda x: x[1])

        for i, (user_id, turno) in enumerate(usuarios_pendientes[:3]):
            if user_id not in notified_users:
                try:
                    await client.send_message(int(user_id), f"¡Hola! Tu turno es el #{turno}. Estás en la posición {i + 1} de la fila.")
                    notified_users.add(user_id)
                    print(f"Notificación de turno enviada a {user_id}")
                except Exception as e:
                    print(f"Error al notificar a {user_id}: {e}")
        
        # Limpiar usuarios notificados que ya no están en la cola
        current_pending_ids = {user_id for user_id, _ in usuarios_pendientes}
        notified_users.intersection_update(current_pending_ids)

        await asyncio.sleep(300) # Notificar cada 5 minutos

async def loop_respuestas():
    print("Userbot iniciado y esperando respuestas para enviar...")
    while True:
        respuestas = get_pending_respuestas()
        for respuesta in respuestas:
            try:
                await client.send_message(int(respuesta['user_id_destino']), respuesta['texto_respuesta'])
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
