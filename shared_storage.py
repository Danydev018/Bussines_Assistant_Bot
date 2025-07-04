import sqlite3
import pathlib

# Ruta absoluta a la base de datos compartida
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
DB_PATH = str(PROJECT_ROOT / 'shared_messages.db')

# Inicializar la base de datos y la tabla si no existen
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        text TEXT NOT NULL
    )
''')
conn.commit()
conn.close()

def save_message(user_id, text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO messages (user_id, text) VALUES (?, ?)', (str(user_id), text))
    conn.commit()
    conn.close()

def get_messages(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT text FROM messages WHERE user_id = ? ORDER BY id', (str(user_id),))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_all_chats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id, text FROM messages ORDER BY id')
    rows = c.fetchall()
    conn.close()
    chats = {}
    for user_id, text in rows:
        chats.setdefault(user_id, []).append(text)
    return chats
