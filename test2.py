from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader


class Main:
    def __init__(self, config_file='settings.json'):
        """
        Inicializa la clase Main y configura el YoutubeMediaUploader.
        
        :param config_file: Ruta al archivo de configuración (por defecto 'settings.json').
        """
        self.config_file = config_file
        self.config = self.load_configuration()
        self.youtube_uploader = YoutubeMediaUploader(
            client_secrets_file=self.config['youtube']['credentials_file'],
            channel_description=""
        )

    def load_configuration(self):
        """
        Carga la configuración desde el archivo JSON.
        
        :return: Diccionario con la configuración cargada.
        """
        import json
        with open(self.config_file, 'r') as file:
            return json.load(file)
if __name__ == "__main__":
    # Inicializar la clase Main
    main = Main(config_file='settings.json')

    # Definir los datos para la subida del video
    output_file = ".temp/_Misterio_Inslito_en_Rincn_Tra.mp4"  # Ruta al archivo de video
    title = "⚽️ ¡Real Madrid vs Manchester City!🔥"  # Título del video
    cover = ".temp/NONE_9c7e7ab2-5c96-41d3-ae04-f2261a7b006b.png" # Ruta a la miniatura (thumbnail)
    description = "Descubre todos los detalles de la próxima batalla épica en la Champions League entre el Real Madrid y el Manchester City. Estos dos gigantes del fútbol, con una historia reciente llena de tensión y drama, se enfrentarán nuevamente para demostrar su supremacía. ¿Podrá el campeón actual, el Real Madrid, mantener su título, o el Manchester City, ganador de la edición 2023, sorprenderá a todos? ¡No te pierdas esta eliminatoria electrizante!"  # Descripción del video
    tags = [
        "ChampionsLeague",
        "RealMadrid",
        "ManchesterCity",
        "fútbol",
        "fútbolEuropeo",
        "eliminatorias",
        "deportes",
        "deportesEnVivo",
        "fútbolEnVivo",
        "titans",
        "batallaDeTitans",
        "supremacía",
        "fútbol2024",
        "fútbol2025",
        "fútbolEspañol",
        "fútbolIngles",
        "fútbolAmateur",
        "fútbolProfesional",
        "fútbolDeElite",
        "fútbolDeLiga",
        "fútbolDeChampions"
    ]  # Etiquetas para el video

    # Subir el video a YouTube
    youtube_response = main.youtube_uploader.upload(
        output_file,
        title=title,
        thumbnail_path=cover,
        description=description,
        tags=tags
    )

    # Mostrar la respuesta de YouTube
    print("Respuesta de YouTube:", youtube_response)