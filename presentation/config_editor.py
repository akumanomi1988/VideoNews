import tkinter as tk
from tkinter import filedialog, messagebox
import configparser
import os

# Define la ruta del archivo de configuración y del archivo de ejemplo
CONFIG_FILE = 'settings.config'
EXAMPLE_FILE = 'settings.config.example'

class ConfigEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Configuración de la Aplicación")

        # Cargar configuración
        self.config = configparser.ConfigParser()
        if not os.path.exists(CONFIG_FILE):
            self.create_default_config()
        self.config.read(CONFIG_FILE)

        # Crear widgets
        self.create_widgets()

    def create_widgets(self):
        # Crear y colocar widgets para cada sección de la configuración

        # Temporary Directory
        tk.Label(self.root, text="Temporary Directory:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.temp_dir_entry = tk.Entry(self.root, width=50)
        self.temp_dir_entry.grid(row=0, column=1, padx=10, pady=5)
        self.temp_dir_entry.insert(0, self.config.get('settings', 'temp_dir', fallback='.temp'))

        # YouTube Credentials
        tk.Label(self.root, text="YouTube Credentials File:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.youtube_credentials_entry = tk.Entry(self.root, width=50)
        self.youtube_credentials_entry.grid(row=1, column=1, padx=10, pady=5)
        self.youtube_credentials_entry.insert(0, self.config.get('Youtube', 'youtube_credentials_file', fallback=''))

        # Pexels API Key
        tk.Label(self.root, text="Pexels API Key:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.pexels_api_key_entry = tk.Entry(self.root, width=50)
        self.pexels_api_key_entry.grid(row=2, column=1, padx=10, pady=5)
        self.pexels_api_key_entry.insert(0, self.config.get('Pexels', 'API_KEY', fallback=''))

        # NewsAPI Configuration
        tk.Label(self.root, text="NewsAPI API Key:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.news_api_key_entry = tk.Entry(self.root, width=50)
        self.news_api_key_entry.grid(row=3, column=1, padx=10, pady=5)
        self.news_api_key_entry.insert(0, self.config.get('NewsAPI', 'api_key', fallback=''))

        tk.Label(self.root, text="Country:").grid(row=4, column=0, padx=10, pady=5, sticky="e")
        self.country_entry = tk.Entry(self.root, width=50)
        self.country_entry.grid(row=4, column=1, padx=10, pady=5)
        self.country_entry.insert(0, self.config.get('NewsAPI', 'country', fallback='us'))

        tk.Label(self.root, text="Page Size:").grid(row=5, column=0, padx=10, pady=5, sticky="e")
        self.page_size_entry = tk.Entry(self.root, width=50)
        self.page_size_entry.grid(row=5, column=1, padx=10, pady=5)
        self.page_size_entry.insert(0, self.config.get('NewsAPI', 'page_size', fallback='5'))

        # Article Settings
        tk.Label(self.root, text="Model:").grid(row=6, column=0, padx=10, pady=5, sticky="e")
        self.model_entry = tk.Entry(self.root, width=50)
        self.model_entry.grid(row=6, column=1, padx=10, pady=5)
        self.model_entry.insert(0, self.config.get('ArticleSettings', 'MODEL', fallback='gpt-3.5-turbo'))

        tk.Label(self.root, text="Image Model:").grid(row=7, column=0, padx=10, pady=5, sticky="e")
        self.image_model_entry = tk.Entry(self.root, width=50)
        self.image_model_entry.grid(row=7, column=1, padx=10, pady=5)
        self.image_model_entry.insert(0, self.config.get('ArticleSettings', 'IMAGE_MODEL', fallback='gemini'))

        tk.Label(self.root, text="Language:").grid(row=8, column=0, padx=10, pady=5, sticky="e")
        self.language_entry = tk.Entry(self.root, width=50)
        self.language_entry.grid(row=8, column=1, padx=10, pady=5)
        self.language_entry.insert(0, self.config.get('ArticleSettings', 'LANGUAGE', fallback='spanish'))

        # Video Result
        tk.Label(self.root, text="Aspect Ratio:").grid(row=9, column=0, padx=10, pady=5, sticky="e")
        self.aspect_ratio_entry = tk.Entry(self.root, width=50)
        self.aspect_ratio_entry.grid(row=9, column=1, padx=10, pady=5)
        self.aspect_ratio_entry.insert(0, self.config.get('VideoResult', 'aspect_ratio', fallback='9:16'))

        tk.Label(self.root, text="Background Music:").grid(row=10, column=0, padx=10, pady=5, sticky="e")
        self.background_music_entry = tk.Entry(self.root, width=50)
        self.background_music_entry.grid(row=10, column=1, padx=10, pady=5)
        self.background_music_entry.insert(0, self.config.get('VideoResult', 'background_music', fallback=''))

        # Eleven Labs
        tk.Label(self.root, text="Eleven Labs API Key:").grid(row=11, column=0, padx=10, pady=5, sticky="e")
        self.elevenlabs_api_key_entry = tk.Entry(self.root, width=50)
        self.elevenlabs_api_key_entry.grid(row=11, column=1, padx=10, pady=5)
        self.elevenlabs_api_key_entry.insert(0, self.config.get('ElevenLabs', 'API_KEY', fallback=''))

        tk.Label(self.root, text="Model:").grid(row=12, column=0, padx=10, pady=5, sticky="e")
        self.elevenlabs_model_entry = tk.Entry(self.root, width=50)
        self.elevenlabs_model_entry.grid(row=12, column=1, padx=10, pady=5)
        self.elevenlabs_model_entry.insert(0, self.config.get('ElevenLabs', 'MODEL', fallback='eleven_multilingual_v2'))

        tk.Label(self.root, text="Voice:").grid(row=13, column=0, padx=10, pady=5, sticky="e")
        self.elevenlabs_voice_entry = tk.Entry(self.root, width=50)
        self.elevenlabs_voice_entry.grid(row=13, column=1, padx=10, pady=5)
        self.elevenlabs_voice_entry.insert(0, self.config.get('ElevenLabs', 'VOICE', fallback='gD1IexrzCvsXPHUuT0s3'))

        # Botones
        tk.Button(self.root, text="Guardar Configuración", command=self.save_config).grid(row=14, column=0, padx=10, pady=10)
        tk.Button(self.root, text="Run", command=self.run_application).grid(row=14, column=1, padx=10, pady=10)

    def create_default_config(self):
        """Crea un archivo de configuración por defecto basado en el archivo de ejemplo."""
        if os.path.exists(EXAMPLE_FILE):
            with open(EXAMPLE_FILE, 'r') as example_file:
                with open(CONFIG_FILE, 'w') as config_file:
                    config_file.write(example_file.read())
            print("Archivo de configuración creado a partir del archivo de ejemplo.")
        else:
            print("El archivo de ejemplo no se encontró.")

    def save_config(self):
        """Guarda la configuración en el archivo."""
        # Actualizar la configuración con los valores de la interfaz
        self.config['settings'] = {'temp_dir': self.temp_dir_entry.get()}
        self.config['Youtube'] = {'youtube_credentials_file': self.youtube_credentials_entry.get()}
        self.config['Pexels'] = {'API_KEY': self.pexels_api_key_entry.get()}
        self.config['NewsAPI'] = {
            'api_key': self.news_api_key_entry.get(),
            'country': self.country_entry.get(),
            'page_size': self.page_size_entry.get()
        }
        self.config['ArticleSettings'] = {
            'MODEL': self.model_entry.get(),
            'IMAGE_MODEL': self.image_model_entry.get(),
            'LANGUAGE': self.language_entry.get()
        }
        self.config['VideoResult'] = {
            'aspect_ratio': self.aspect_ratio_entry.get(),
            'background_music': self.background_music_entry.get()
        }
        self.config['ElevenLabs'] = {
            'API_KEY': self.elevenlabs_api_key_entry.get(),
            'MODEL': self.elevenlabs_model_entry.get(),
            'VOICE': self.elevenlabs_voice_entry.get()
        }

       
