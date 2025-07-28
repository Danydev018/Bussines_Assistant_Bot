# Asistente de Negocios con Telegram

Este proyecto es un sistema de asistente de negocios que utiliza bots de Telegram para gestionar conversaciones con clientes o usuarios.

## Descripción

El sistema está compuesto por dos bots principales:

- **User_Bot**: Un "userbot" de Telethon que actúa como el punto de contacto principal para los usuarios. Se encarga de recibir mensajes, guardarlos y enviar respuestas automáticas.
- **Panel_Bot**: Un bot de `python-telegram-bot` que funciona como un panel de administración. Permite a un administrador ver las conversaciones, gestionarlas y enviar respuestas a través del `User_Bot`.

Ambos bots se comunican de forma indirecta a través de una base de datos SQLite compartida (`shared_messages.db`).

## Configuración

1.  **Clona el repositorio.**
2.  **Crea un entorno virtual:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Crea un archivo `.env`** a partir del archivo `.env.example` y completa las variables de entorno:
    - `TOKEN_BOTFATHER`: El token de tu bot de Telegram (el que usas para el panel de administración).
    - `ADMIN_ID`: Tu ID de usuario de Telegram.
    - `API_ID` y `API_HASH`: Tus credenciales de la API de Telegram (puedes obtenerlas en [my.telegram.org](https://my.telegram.org)).

## Uso

Para iniciar los bots, ejecuta los siguientes comandos en dos terminales diferentes:

```bash
python3 User_Bot/src/bot/user_bot.py
```

```bash
python3 Panel_Bot/src/bot.py
```
