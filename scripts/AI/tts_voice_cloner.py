import requests
import time
from pathlib import Path
from typing import Optional, Union

class TTSVoiceCloner:
    """Clase para clonar voz usando el modelo F5-Spanish de Hugging Face Spaces.
    
    Args:
        api_url (str): URL del espacio de Hugging Face (default: espacio oficial)
        timeout (int): Tiempo máximo de espera para respuestas (segundos)
        max_retries (int): Intentos máximos ante fallos de conexión
    """
    
    def __init__(
        self,
        api_url: str = "https://jpgallegoar-spanish-f5.hf.space",
        timeout: int = 60,
        max_retries: int = 3
    ):
        self.api_url = api_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._validate_api()

    def _validate_api(self) -> None:
        """Verifica que la API esté disponible."""
        try:
            response = requests.get(f"{self.api_url}/info", timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error conectando a la API: {str(e)}") from e

    def generate(
        self,
        audio_path: Union[str, Path],
        text: str,
        output_path: Optional[Union[str, Path]] = None
    ) -> bytes:
        """Genera audio clonado a partir de voz de referencia y texto.
        
        Args:
            audio_path: Ruta al audio de referencia (formato WAV recomendado)
            text: Texto a sintetizar en español
            output_path: Ruta opcional para guardar el audio resultante
            
        Returns:
            bytes: Audio generado en formato WAV
        """
        # Validar inputs
        audio_file = Path(audio_path)
        if not audio_file.is_file():
            raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")
        
        if not text.strip():
            raise ValueError("El texto de entrada no puede estar vacío")

        # Preparar payload para la API
        files = {"audio": audio_file.open("rb")}
        data = {"text": text.strip()}

        # Enviar petición con reintentos
        for _ in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.api_url}/run/predict",
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Procesar respuesta
                result = response.json()
                if "data" not in result:
                    raise ValueError("Respuesta de API inválida")
                
                audio_data = result["data"][0].get("name")
                if not audio_data:
                    raise ValueError("Audio no generado correctamente")
                
                # Descargar y guardar audio
                audio_response = requests.get(f"{self.api_url}/file/{audio_data}")
                audio_content = audio_response.content
                
                if output_path:
                    Path(output_path).write_bytes(audio_content)
                
                return audio_content
                
            except requests.exceptions.RequestException as e:
                time.sleep(2)
        
        raise ConnectionError(f"Fallo después de {self.max_retries} intentos")

    @property
    def supported_formats(self) -> tuple:
        """Formatos de audio soportados para entrada."""
        return (".wav", ".mp3", ".ogg")  # Basado en documentación del modelo :cite[6]:cite[9]