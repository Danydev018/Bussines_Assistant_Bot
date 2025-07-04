
# Este archivo solo debe ser usado por el user_bot para ESCRIBIR.
# El panel_bot debe importar solo get_messages/get_all_chats desde shared_storage.py para LEER.
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent.parent))
from shared_storage import get_messages, get_all_chats, save_message

# save_message solo debe ser usado por el user_bot
def save_message(user_id, text):
    from .shared_storage import save_message as shared_save_message
    shared_save_message(user_id, text)
