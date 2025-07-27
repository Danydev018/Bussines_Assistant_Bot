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
        text TEXT NOT NULL,
        turno INTEGER NOT NULL,
        estado TEXT NOT NULL DEFAULT 'pendiente',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')
conn.commit()
conn.close()


def get_next_turno():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT MAX(turno) FROM messages WHERE estado = "pendiente"')
    result = c.fetchone()
    conn.close()
    return (result[0] or 0) + 1

def save_message(user_id, text):
    turno = get_next_turno()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO messages (user_id, text, turno, estado) VALUES (?, ?, ?, ?)', (str(user_id), text, turno, 'pendiente'))
    conn.commit()
    conn.close()


def get_messages(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, text, turno, estado, timestamp FROM messages WHERE user_id = ? ORDER BY id', (str(user_id),))
    rows = c.fetchall()
    conn.close()
    return [
        {
            'id': row[0],
            'text': row[1],
            'turno': row[2],
            'estado': row[3],
            'timestamp': row[4]
        }
        for row in rows
    ]


def get_all_chats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id, id, text, turno, estado, timestamp FROM messages ORDER BY id')
    rows = c.fetchall()
    conn.close()
    chats = {}
    for user_id, id_, text, turno, estado, timestamp in rows:
        chats.setdefault(user_id, []).append({
            'id': id_,
            'text': text,
            'turno': turno,
            'estado': estado,
            'timestamp': timestamp
        })
    return chats

# --- Funciones de gestión de estado ---
def marcar_atendido(user_id):
    """Marca todos los mensajes de un usuario como atendidos."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE messages SET estado = "atendido" WHERE user_id = ?', (str(user_id),))
    conn.commit()
    conn.close()

def eliminar_mensajes(user_id):
    """Elimina todos los mensajes de un usuario."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM messages WHERE user_id = ?', (str(user_id),))
    conn.commit()
    conn.close()
