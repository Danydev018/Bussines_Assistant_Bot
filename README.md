### 3. Obtener tu ADMIN_ID 👤
1. Abre Telegram y busca el bot `@userinfobot` o `@getmyid_bot`.
2. Inicia una conversación y escribe cualquier mensaje.
3. El bot te responderá con tu **ID de usuario**. Usa ese número como `ADMIN_ID` en el archivo `.env`.

# 🤖 Asistente de Negocios con Telegram


Este proyecto es un sistema de asistente de negocios que utiliza bots de Telegram para gestionar conversaciones con clientes o usuarios de manera eficiente y automatizada.


## 📝 Descripción


El sistema está compuesto por dos bots principales:

• **User_Bot** 🤝: Un "userbot" basado en Telethon que actúa como punto de contacto principal para los usuarios. Recibe mensajes, los almacena y envía respuestas automáticas.
• **Panel_Bot** 🛠️: Un bot construido con `python-telegram-bot` que funciona como panel de administración. Permite al administrador ver, gestionar y responder conversaciones a través del `User_Bot`.

Ambos bots se comunican de forma indirecta mediante una base de datos SQLite compartida (`shared_messages.db`).




## �️ Obtención de credenciales necesarias

Antes de instalar el asistente, necesitas crear tu bot en Telegram y obtener las credenciales de la API:

### 1. Crear un bot con BotFather 🤖
1. Abre Telegram y busca el usuario `@BotFather`.
2. Inicia una conversación y ejecuta el comando `/newbot`.
3. Sigue las instrucciones para asignar un nombre y un usuario único a tu bot.
4. Al finalizar, BotFather te dará un **Token**. Guárdalo, lo necesitarás como `TOKEN_BOTFATHER`.

### 2. Obtener API_ID y API_HASH de Telegram 🔑
1. Ve a [my.telegram.org](https://my.telegram.org) e inicia sesión con tu número de teléfono de Telegram.
2. Haz clic en "API development tools".
3. Completa el formulario para crear una nueva aplicación (puedes poner cualquier nombre y URL).
4. Al finalizar, se mostrarán tu **API_ID** y **API_HASH**. Guárdalos para el archivo `.env`.

---

Sigue estos pasos profesionales para instalar y poner en marcha el asistente en un entorno nuevo:

1️⃣ **Clona el repositorio**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd Bussines_Assistant_Bot
   ```

2️⃣ **Crea un entorno virtual de Python**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3️⃣ **Instala las dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4️⃣ **Configura las variables de entorno**
   - Copia el archivo `.env.example` a `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edita el archivo `.env` y completa los siguientes datos:
     - `TOKEN_BOTFATHER`: Token del bot de administración (Panel_Bot).
     - `ADMIN_ID`: Tu ID de usuario de Telegram.
     - `API_ID` y `API_HASH`: Credenciales de la API de Telegram ([my.telegram.org](https://my.telegram.org)).

5️⃣ **(Opcional) Base de datos**
   - Si usas SQLite, asegúrate de que el archivo `shared_messages.db` esté presente. Si no existe, se creará automáticamente al iniciar los bots.

6️⃣ **Inicia ambos bots en terminales separadas**
   - Terminal 1:
     ```bash
     python3 User_Bot/src/bot/user_bot.py
     ```
   - Terminal 2:
     ```bash
     python3 Panel_Bot/src/bot.py
     ```

7️⃣ **Verifica la interacción**
   - 💬 Escribe a tu bot de usuario en Telegram y verifica que responde.
   - 🛠️ Ingresa al panel de administración (Panel_Bot) y verifica que puedes ver y gestionar los mensajes.

---


## ⚙️ Configuración avanzada

Si necesitas personalizar la configuración, revisa y ajusta las variables del archivo `.env` según tus necesidades específicas.


## 🧑‍💼 Uso

Para iniciar los bots, ejecuta los siguientes comandos en dos terminales diferentes:

Terminal 1:
```bash
python3 User_Bot/src/bot/user_bot.py
```

Terminal 2:
```bash
python3 Panel_Bot/src/bot.py
```

### 💡 Interacción con el User_Bot (para Clientes)

Además de los botones que el bot te pueda mostrar, puedes interactuar con el User_Bot usando los siguientes comandos de texto:

- Para **consultar tu turno** 🕒, simplemente escribe: `turno`
- Para **cancelar tu turno** ❌, simplemente escribe: `cancelar`