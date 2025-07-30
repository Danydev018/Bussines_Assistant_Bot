# --- Funciones para recomendaciones de contacto ---
def save_contact_recommendation(user_id, nombre, telefono):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS contact_recommendations (
            user_id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            telefono TEXT NOT NULL,
            enviado INTEGER DEFAULT 0
        )
    ''')
    c.execute('INSERT OR REPLACE INTO contact_recommendations (user_id, nombre, telefono, enviado) VALUES (?, ?, ?, 0)', (str(user_id), nombre, telefono))
    conn.commit()
    conn.close()

def get_contact_recommendation(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS contact_recommendations (
            user_id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            telefono TEXT NOT NULL,
            enviado INTEGER DEFAULT 0
        )
    ''')
    c.execute('SELECT nombre, telefono FROM contact_recommendations WHERE user_id=? AND enviado=0', (str(user_id),))
    row = c.fetchone()
    conn.close()
    if row:
        return {'nombre': row[0], 'telefono': row[1]}
    return None

def mark_contact_recommendation_sent(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE contact_recommendations SET enviado=1 WHERE user_id=?', (str(user_id),))
    conn.commit()
    conn.close()
import sqlite3
import pathlib
import datetime

# Ruta absoluta a la base de datos compartida
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
DB_PATH = str(PROJECT_ROOT / 'shared_messages.db')

CATEGORIAS = {
    'trabajo': ['reporte', 'oficina', 'reunión', 'trabajo', 'jefe'],
    'familia': ['mamá', 'papá', 'hermano', 'familia'],
    'amigos': ['fiesta', 'amigo', 'salida', 'birra'],
    'otros': []
}

def categorizar(mensaje):
    mensaje = mensaje.lower()
    for categoria, palabras in CATEGORIAS.items():
        if any(palabra in mensaje for palabra in palabras):
            return categoria
    return 'otros'

# --- Inicialización de la Base de Datos ---
def initialize_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Tabla de mensajes de clientes
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            text TEXT NOT NULL,
            turno INTEGER NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente', -- pendiente, atendido, seguimiento, archivado
            categoria TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_status_change_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            postpone_until DATETIME
        )
    ''')
    # Tabla de respuestas del administrador
    c.execute('''
        CREATE TABLE IF NOT EXISTS respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id_destino TEXT NOT NULL,
            texto_respuesta TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente' -- pendiente, enviado
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_settings (
            setting_name TEXT PRIMARY KEY,
            setting_value TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Llama a la inicialización al cargar el módulo
initialize_database()


# --- Funciones para la tabla 'messages' ---

def get_next_turno():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT MAX(turno) FROM messages WHERE estado = "pendiente"')
    result = c.fetchone()
    conn.close()
    return (result[0] or 0) + 1

def save_message(user_id, text):
    turno = get_next_turno()
    categoria = categorizar(text)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO messages (user_id, text, turno, estado, categoria, last_status_change_timestamp, postpone_until) VALUES (?, ?, ?, ?, ?, ?, ?)', (str(user_id), text, turno, 'pendiente', categoria, datetime.datetime.now().isoformat(), None))
    conn.commit()
    conn.close()


def get_messages(user_id, include_archived=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if include_archived:
        c.execute('SELECT id, text, turno, estado, categoria, timestamp, last_status_change_timestamp, postpone_until FROM messages WHERE user_id = ? ORDER BY id', (str(user_id),))
    else:
        c.execute('SELECT id, text, turno, estado, categoria, timestamp, last_status_change_timestamp, postpone_until FROM messages WHERE user_id = ? AND estado != "archivado" ORDER BY id', (str(user_id),))
    rows = c.fetchall()
    conn.close()
    return [
        {
            'id': row[0],
            'text': row[1],
            'turno': row[2],
            'estado': row[3],
            'categoria': row[4],
            'timestamp': row[5],
            'last_status_change_timestamp': row[6],
            'postpone_until': row[7]
        }
        for row in rows
    ]


def get_all_chats(estado_filtro=None, include_archived=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = 'SELECT user_id, id, text, turno, estado, categoria, timestamp, last_status_change_timestamp, postpone_until FROM messages'
    conditions = []
    params = []

    if estado_filtro:
        conditions.append('estado = ?')
        params.append(estado_filtro)
    elif not include_archived:
        conditions.append('estado != "archivado"')

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    query += ' ORDER BY id'

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    chats = {}
    for user_id, id_, text, turno, estado, categoria, timestamp, last_status_change_timestamp, postpone_until in rows:
        chats.setdefault(user_id, []).append({
            'id': id_,
            'text': text,
            'turno': turno,
            'estado': estado,
            'categoria': categoria,
            'timestamp': timestamp,
            'last_status_change_timestamp': last_status_change_timestamp,
            'postpone_until': postpone_until
        })
    return chats

# --- Funciones de gestión de estado ---
def _update_chat_status(user_id, new_status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE messages SET estado = ?, last_status_change_timestamp = ? WHERE user_id = ?', (new_status, datetime.datetime.now().isoformat(), str(user_id)))
    conn.commit()
    conn.close()

def marcar_atendido(user_id):
    """Marca todos los mensajes de un usuario como atendidos."""
    _update_chat_status(user_id, "atendido")

def marcar_seguimiento(user_id):
    """Marca todos los mensajes de un usuario como en seguimiento."""
    _update_chat_status(user_id, "seguimiento")

def archivar_chat(user_id):
    """Archiva todos los mensajes de un usuario."""
    _update_chat_status(user_id, "archivado")

def postpone_chat(user_id, hours):
    """Posponer un chat por un número de horas."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    postpone_time = (datetime.datetime.now() + datetime.timedelta(hours=hours)).isoformat()
    c.execute('UPDATE messages SET postpone_until = ? WHERE user_id = ?', (postpone_time, str(user_id)))
    conn.commit()
    conn.close()

def get_user_status(user_id):
    """Obtiene el estado más reciente de un usuario."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT estado FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1', (str(user_id),))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_user_position(user_id):
    """Calcula la posición en la cola de un usuario pendiente."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT user_id, MIN(turno) as primer_turno
        FROM messages
        WHERE estado = "pendiente"
        GROUP BY user_id
        ORDER BY primer_turno ASC
    ''')
    usuarios_pendientes = c.fetchall()
    conn.close()
    for i, (uid, _) in enumerate(usuarios_pendientes):
        if uid == str(user_id):
            return i + 1
    return None

def cancel_turn(user_id):
    """Cancela el turno de un usuario archivando su chat."""
    archivar_chat(user_id)

# --- Funciones de resumen ---
def get_summary_by_status():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT estado, COUNT(DISTINCT user_id) FROM messages GROUP BY estado')
    rows = c.fetchall()
    conn.close()
    return {estado: count for estado, count in rows}

def get_daily_attended_chats_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.date.today().isoformat()
    c.execute('SELECT COUNT(DISTINCT user_id) FROM messages WHERE estado = "atendido" AND DATE(last_status_change_timestamp) = ?', (today,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_pending_chats_count():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(DISTINCT user_id) FROM messages WHERE estado = "pendiente"')
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def get_current_queue_positions():
    """Devuelve un diccionario con user_id: posicion_en_cola para chats pendientes."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT user_id, MIN(turno) as primer_turno
        FROM messages
        WHERE estado = "pendiente"
        GROUP BY user_id
        ORDER BY primer_turno ASC
    ''')
    usuarios_pendientes = c.fetchall()
    conn.close()
    
    positions = {}
    for i, (user_id, _) in enumerate(usuarios_pendientes):
        positions[user_id] = i + 1
    return positions

# --- Funciones para la tabla 'respuestas' ---

def save_respuesta(user_id_destino, texto_respuesta):
    """Guarda una respuesta para ser enviada por el User_Bot."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO respuestas (user_id_destino, texto_respuesta, estado) VALUES (?, ?, ?)', (str(user_id_destino), texto_respuesta, 'pendiente'))
    conn.commit()
    conn.close()

def get_pending_respuestas():
    """Obtiene todas las respuestas pendientes de ser enviadas."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, user_id_destino, texto_respuesta FROM respuestas WHERE estado = "pendiente"')
    rows = c.fetchall()
    conn.close()
    return [
        {
            'id': row[0],
            'user_id_destino': row[1],
            'texto_respuesta': row[2]
        }
        for row in rows
    ]

def mark_respuesta_sent(respuesta_id):
    """Marca una respuesta como enviada."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE respuestas SET estado = "enviado" WHERE id = ?', (respuesta_id,))
    conn.commit()
    conn.close()

# --- Funciones para la tabla 'admin_settings' ---

def save_admin_setting(setting_name, setting_value):
    """Guarda o actualiza una configuración del administrador."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO admin_settings (setting_name, setting_value) VALUES (?, ?)', (setting_name, str(setting_value)))
    conn.commit()
    conn.close()

def get_admin_setting(setting_name):
    """Obtiene una configuración del administrador."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT setting_value FROM admin_settings WHERE setting_name = ?', (setting_name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None
