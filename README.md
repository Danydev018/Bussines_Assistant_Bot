# Asistente de Negocios con Telegram

Este proyecto es un sistema de asistente de negocios que utiliza bots de Telegram para gestionar conversaciones con clientes o usuarios.

## Descripción

El sistema está compuesto por dos bots principales:

- **User_Bot**: Un "userbot" de Telethon que actúa como el punto de contacto principal para los usuarios. Se encarga de recibir mensajes, guardarlos y enviar respuestas automáticas.
- **Panel_Bot**: Un bot de `python-telegram-bot` que funciona como un panel de administración. Permite a un administrador ver las conversaciones, gestionarlas y enviar respuestas a través del `User_Bot`.

Ambos bots se comunican de forma indirecta a través de una base de datos SQLite compartida (`shared_messages.db`).


## Instalación y prueba en otra computadora

Sigue estos pasos para instalar y probar el asistente en un entorno nuevo:

1. **Clona el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd Bussines_Assistant_Bot
   ```

2. **Crea un entorno virtual de Python:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura las variables de entorno:**
   - Copia el archivo `.env.example` a `.env`.
   - Edita el archivo `.env` y coloca tus credenciales de Telegram:
     - `TOKEN_BOTFATHER`: Token del bot de administración (Panel_Bot).
     - `ADMIN_ID`: Tu ID de usuario de Telegram.
     - `API_ID` y `API_HASH`: Credenciales de la API de Telegram ([my.telegram.org](https://my.telegram.org)).

5. **(Opcional) Base de datos:**
   - Si usas SQLite, asegúrate de que el archivo `shared_messages.db` esté presente. Si no existe, se creará automáticamente al iniciar los bots.

6. **Inicia ambos bots en terminales separadas:**
   ```bash
   python3 User_Bot/src/bot/user_bot.py
   ```
   ```bash
   python3 Panel_Bot/src/bot.py
   ```

7. **Prueba la interacción:**
   - Escribe a tu bot de usuario en Telegram y verifica que responde.
   - Ingresa al panel de administración (Panel_Bot) y verifica que puedes ver y gestionar los mensajes.

---

## Configuración avanzada

Si necesitas personalizar la configuración, revisa y ajusta las variables del archivo `.env` según tus necesidades.

## Uso

Para iniciar los bots, ejecuta los siguientes comandos en dos terminales diferentes:

```bash
python3 User_Bot/src/bot/user_bot.py
```

```bash
python3 Panel_Bot/src/bot.py
```

### Interacción con el User_Bot (para Clientes)

Además de los botones que el bot te pueda mostrar, puedes interactuar con el User_Bot usando los siguientes comandos de texto:

- Para **consultar tu turno**, simplemente escribe: `turno`
- Para **cancelar tu turno**, simplemente escribe: `cancelar`