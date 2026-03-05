<div align="center">
  <img src="assets/banner.png" alt="Cerebro Local AI Banner" width="800">
  <h1>🧠 Cerebro Local AI</h1>
  <p><b>Tu Segundo Cerebro Digital Personal • Privado • Local • Inteligente</b></p>
  
  [![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
  [![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
</div>

---

**Cerebro Local AI** es un ecosistema diseñado para centralizar tu conocimiento de forma segura y privada. Combina la agilidad de un **Bot de Telegram** para la captura inmediata de pensamientos, enlaces y archivos, con un **Dashboard de Streamlit** para el análisis, búsqueda y visualización de tu base de datos personal.

## ✨ Características Principales

- 📱 **Captura Ubicua**: Envía mensajes, enlaces, fotos y PDFs desde cualquier lugar mediante Telegram.
- 🏷️ **Taxonomía de 3 Niveles**: Clasificación automática y jerárquica mediante hashtags:
  - **Nivel 1 (Proyectos)**: #LaAgencia #GreenHouse #Tesis
  - **Nivel 2 (Naturaleza)**: #Prompt #Novedades #Herramientas #Hacks
  - **Nivel 3 (Plataformas)**: Categorización específica (por ejemplo, #Notion #Notion #MetaAds).
- 🔒 **Privacidad Total**: Todo se almacena en una base de datos SQLite local. Tus datos nunca salen de tu control.
- 📊 **Dashboard Ejecutivo**: Visualización interactiva con métricas de productividad, galería de archivos y búsqueda global.
- 📂 **Gestión de Archivos**: Descarga automática y organización de multimedia enviada al bot.

## 🛠️ Stack Tecnológico

- **Core**: Python 3.x
- **Bot**: [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI)
- **Visualización**: [Streamlit](https://streamlit.io/)
- **Datos**: SQLite + Pandas
- **Entorno**: Python-dotenv para gestión de secretos

---

## 🚀 Guía de Inicio Rápido

### 1. Clonar y Preparar
```bash
git clone https://github.com/juandabermudeez/Cerebro_Local_AI.git
cd Cerebro_Local_AI
```

### 2. Instalar Dependencias
Se recomienda usar un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuración de Entorno
Crea un archivo `.env` en la raíz del proyecto (puedes usar `.env.example` como base):
```env
TELEGRAM_TOKEN=tu_token_de_bot_father
```

### 4. Lanzamiento
Para un funcionamiento completo, inicia ambos módulos:

- **Iniciar el Bot (Captura):**
  ```bash
  python bot.py
  ```

- **Iniciar el Dashboard (Visualización):**
  ```bash
  streamlit run dashboard.py
  ```

---

## 📁 Estructura del Proyecto

```text
├── assets/             # Recursos visuales del repositorio
├── bot.py              # Lógica de interacción con Telegram
├── dashboard.py        # Aplicación Streamlit principal
├── database.py         # Capa de abstracción de SQLite
├── documentos_locales/ # Almacenamiento local de PDFs (ignorado por Git)
├── fotos_locales/      # Almacenamiento local de imágenes (ignorado por Git)
├── .env.example        # Plantilla de configuración
└── requirements.txt    # Dependencias del proyecto
```

## 🤝 Contribuciones
¡Las contribuciones son bienvenidas! Si tienes ideas para mejorar la taxonomía o nuevas visualizaciones, no dudes en abrir un *Issue* o enviar un *Pull Request*.

---
<div align="center">
  <sub>Desarrollado con ❤️ para la gestión del conocimiento personal.</sub>
</div>
