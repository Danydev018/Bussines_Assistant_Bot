import os
from dotenv import load_dotenv
import time
from telethon import TelegramClient, events
from collections import defaultdict
import requests

load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION = 'userbot_session'
TOKEN_BOTFATHER = os.getenv('TOKEN_BOTFATHER')
ADMIN_ID =  os.getenv('ADMIN_ID') # tu user_id de Telegram
PETICION_PATH = "ver_chats_request.txt"

CATEGORIAS = {
    'trabajo': ['reporte', 'oficina', 'reunión', 'trabajo', 'jefe'],
    'familia': ['mamá', 'papá', 'hermano', 'familia'],
    'amigos': ['fiesta', 'amigo', 'salida', 'birra'],
    'otros': []
}

chats_categorizados = defaultdict(set)
ultimos_mensajes = {}

client = TelegramClient(SESSION, API_ID, API_HASH)

def categorizar(mensaje):
    mensaje = mensaje.lower()
    for categoria, palabras in CATEGORIAS.items():
        if any(palabra in mensaje for palabra in palabras):
            return categoria
    return 'otros'

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
    sender = await event.get_sender()
    if sender.is_self:
        return
    categoria = categorizar(event.text or "")
    chats_categorizados[categoria].add(sender.id)
    ultimos_mensajes[sender.id] = event.text
    await event.reply("¡Gracias por tu mensaje! Te responderé pronto.")

def resumen_chats():
    msg = "**Chats agrupados por categoría:**\n"
    for categoria, user_ids in chats_categorizados.items():
        msg += f"\n*{categoria.upper()}*\n"
        for user_id in user_ids:
            last_msg = ultimos_mensajes.get(user_id, "")
            msg += f"- Usuario `{user_id}`: {last_msg[:30]}...\n"
    return msg

def loop_peticion():
    print("Userbot iniciado y esperando peticiones del admin bot...")
    while True:
        if os.path.exists(PETICION_PATH):
            msg = resumen_chats()
            enviar_al_botfather(msg)
            os.remove(PETICION_PATH)
        time.sleep(2)

if __name__ == "__main__":
    with client:
        from threading import Thread
        t = Thread(target=loop_peticion, daemon=True)
        t.start()
        client.run_until_disconnected()