import os
import sys
import time
from dotenv import load_dotenv
from telethon import TelegramClient, events
from collections import defaultdict
import requests
# Importar save_message del almacenamiento compartido del panel
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent.parent))
from shared_storage import save_message

load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SESSION = 'userbot_session'
TOKEN_BOTFATHER = os.getenv('TOKEN_BOTFATHER')
ADMIN_ID = int(os.getenv('ADMIN_ID')) # tu user_id de Telegram


PETICION_PATH = "ver_chats_request.txt"
# Usar la misma ruta absoluta que el Panel_Bot
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
RESPUESTAS_PATH = str(BASE_DIR / "src/bot/respuestas_pendientes.txt")

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
    # Solo responder y almacenar si es chat privado
    if not event.is_private:
        return
    sender = await event.get_sender()
    if sender.is_self or getattr(sender, 'bot', False):
        return
    categoria = categorizar(event.text or "")
    chats_categorizados[categoria].add(sender.id)
    ultimos_mensajes[sender.id] = event.text
    # Guardar mensaje en el archivo compartido
    save_message(sender.id, event.text)
    await event.reply("¡Gracias por tu mensaje! Te responderé pronto.")

def resumen_chats():
    msg = "**Chats agrupados por categoría:**\n"
    for categoria, user_ids in chats_categorizados.items():
        msg += f"\n*{categoria.upper()}*\n"
        for user_id in user_ids:
            last_msg = ultimos_mensajes.get(user_id, "")
            msg += f"- Usuario `{user_id}`: {last_msg[:30]}...\n"
    return msg


import asyncio
async def loop_peticion():
    print("Userbot iniciado y esperando peticiones del admin bot...")
    print(f"[DEBUG User_Bot] Esperando en ruta: {os.getcwd()}")
    print(f"[DEBUG User_Bot] RESPUESTAS_PATH: {RESPUESTAS_PATH}")
    while True:
        # Petición de resumen de chats
        if os.path.exists(PETICION_PATH):
            msg = resumen_chats()
            enviar_al_botfather(msg)
            os.remove(PETICION_PATH)
        # Revisión de respuestas pendientes
        if os.path.exists(RESPUESTAS_PATH):
            print(f"[DEBUG User_Bot] Revisando archivo de respuestas: {RESPUESTAS_PATH}")
            with open(RESPUESTAS_PATH, "r") as f:
                lines = f.readlines()
            print(f"[DEBUG User_Bot] Cantidad de líneas a procesar: {len(lines)}")
            pendientes = []
            for line in lines:
                try:
                    user_id, mensaje = line.strip().split("|", 1)
                    print(f"[DEBUG User_Bot] Reenviando a {user_id}: {mensaje}")
                    await client.send_message(int(user_id), mensaje)
                except Exception as e:
                    import traceback
                    print(f"[DEBUG User_Bot] Error al reenviar a {user_id}: {e}\n{traceback.format_exc()}")
                    pendientes.append(line)  # Si falla, lo dejamos pendiente
            # Sobrescribir archivo solo con los pendientes
            with open(RESPUESTAS_PATH, "w") as f:
                f.writelines(pendientes)
            print(f"[DEBUG User_Bot] Fin de revisión de respuestas pendientes")
        else:
            print(f"[DEBUG User_Bot] Archivo de respuestas NO existe: {RESPUESTAS_PATH}")
        await asyncio.sleep(2)

if __name__ == "__main__":
    with client:
        client.loop.create_task(loop_peticion())
        client.run_until_disconnected()