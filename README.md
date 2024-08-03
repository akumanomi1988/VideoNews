# Generador de Videos de Tendencias de Twitter

Este proyecto genera videos a partir de las tendencias de Twitter y los sube a YouTube Shorts y TikTok. Utiliza modelos de lenguaje para generar textos descriptivos y gTTS para crear audios en español de España.

## Requisitos

- Python 3.9+
- Claves de API para Twitter, Hugging Face, Pexels, YouTube, y TikTok

## Instalación de Python 3.9

1. Descarga la versión de Python 3.9 desde [python.org](https://www.python.org/downloads/release/python-390/).
2. Sigue las instrucciones de instalación específicas para tu sistema operativo.

## Descarga del Repositorio

1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/TwitterTrendsVideoGenerator.git
   cd TwitterTrendsVideoGenerator
   ```

## Instalación de Requerimientos

1. Crea y activa un entorno virtual:
   ```bash
   python3.9 -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Configuración

1. Renombra `config.py.example` a `config.py`:
   ```bash
   mv config.py.example config.py
   ```

2. Edita `config.py` con tus claves de API:
   ```python
   TWITTER_CONSUMER_KEY = 'tu_twitter_consumer_key'
   TWITTER_CONSUMER_SECRET = 'tu_twitter_consumer_secret'
   TWITTER_ACCESS_TOKEN = 'tu_twitter_access_token'
   TWITTER_ACCESS_TOKEN_SECRET = 'tu_twitter_access_token_secret'
   PEXELS_API_KEY = 'tu_pexels_api_key'
   YOUTUBE_API_KEY = 'tu_youtube_api_key'
   TIKTOK_API_KEY = 'tu_tiktok_api_key'
   ```

## Obtención de Claves API

### Twitter

1. Ve a [Twitter Developer](https://developer.twitter.com/en/apps) y crea una nueva aplicación.
2. Genera tus claves de `Consumer Key`, `Consumer Secret`, `Access Token`, y `Access Token Secret`.

### Hugging Face

1. Crea una cuenta en [Hugging Face](https://huggingface.co/).
2. Navega a [API Tokens](https://huggingface.co/settings/tokens) y genera un nuevo token.

### Pexels

1. Regístrate en [Pexels](https://www.pexels.com/api/).
2. Genera tu `API Key` desde el dashboard.

### YouTube

1. Ve a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un nuevo proyecto y habilita la API de YouTube Data v3.
3. Genera una clave de API desde la sección de credenciales.

### TikTok

1. Regístrate en [TikTok for Developers](https://developers.tiktok.com/).
2. Crea una aplicación y genera tu `API Key`.

## Ejecución

1. Ejecuta el script principal:
   ```bash
   python main.py
   ```

Este script:
- Obtendrá las tendencias actuales de Twitter.
- Generará un texto descriptivo usando un modelo de Hugging Face.
- Creará un archivo de audio usando gTTS.
- Generará un video combinando el texto y el audio.
- Subirá el video a YouTube Shorts y TikTok.

## Estructura del Proyecto

- `main.py`: Script principal que orquesta el flujo completo.
- `config.py`: Archivo de configuración para las claves de API.
- `src/`: Contiene módulos para manejar diferentes funcionalidades:
  - `twitter_api.py`: Obtiene tendencias de Twitter.
  - `text_generator.py`: Genera texto usando Hugging Face.
  - `audio_generator.py`: Genera audio usando gTTS.
  - `video_creator.py`: Crea el video usando moviepy.
  - `youtube_uploader.py`: Sube el video a YouTube Shorts.
  - `tiktok_uploader.py`: Sube el video a TikTok.
