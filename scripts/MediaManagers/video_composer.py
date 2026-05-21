from moviepy.editor import VideoFileClip, CompositeVideoClip
import cv2
import numpy as np
import os
from typing import List


class VideoOverlayComposer:
    """
    Clase para superponer videos con fondo verde sobre un video base con transparencia.
    """

    def __init__(self, base_video_path: str, overlay_video_paths: List[str], 
                 output_path: str = "output_video.mp4"):
        """
        Inicializa el compositor de videos.

        Args:
            base_video_path (str): Ruta del video base.
            overlay_video_paths (List[str]): Lista de rutas de videos superpuestos.
            output_path (str): Ruta del archivo de salida.
        """
        self.base_video = VideoFileClip(base_video_path)
        self.overlay_videos = [VideoFileClip(path).resize(self.base_video.size) for path in overlay_video_paths]
        self.output_path = output_path
        self.green_lower = np.array([35, 50, 50])  # Rango inferior de verde en HSV
        self.green_upper = np.array([85, 255, 255])  # Rango superior de verde en HSV

    def remove_green_screen(self, clip: VideoFileClip) -> VideoFileClip:
        """
        Elimina el fondo verde de un clip dejando transparencia.

        Args:
            clip (VideoFileClip): Clip con fondo verde.

        Returns:
            VideoFileClip: Clip con fondo transparente.
        """
        def process_frame(frame):
            # Convertir de RGB a HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            mask = cv2.inRange(hsv, self.green_lower, self.green_upper)

            # Invertir la máscara para que el verde sea transparente (0) y lo demás opaco (255)
            mask = 255 - mask

            # Convertir máscara a valores entre 0 y 1 (formato que acepta MoviePy)
            mask = mask.astype(np.float32) / 255.0

            return mask

        # Crear la máscara a partir de la función process_frame
        mask_clip = clip.fl_image(process_frame)

        # Aplicar la máscara al video superpuesto
        return clip.set_mask(mask_clip)

    def calculate_positions(self) -> List[float]:
        """
        Calcula los tiempos de inicio de los videos superpuestos.

        Returns:
            List[float]: Lista de tiempos de inicio.
        """
        base_duration = self.base_video.duration
        num_overlays = len(self.overlay_videos)

        if num_overlays == 1:
            return [0]
        elif num_overlays == 2:
            return [0, base_duration / 2]

        interval = base_duration / num_overlays
        return [i * interval for i in range(num_overlays)]

    def compose_video(self):
        """
        Compone el video final con las superposiciones manteniendo la transparencia.
        """
        processed_overlays = [self.remove_green_screen(clip) for clip in self.overlay_videos]
        positions = self.calculate_positions()

        # Ajustar duración de superpuestos si es necesario
        for i, clip in enumerate(processed_overlays):
            max_duration = self.base_video.duration - positions[i]
            if clip.duration > max_duration:
                processed_overlays[i] = clip.subclip(0, max_duration)

        # Aplicar posiciones y tiempos de inicio
        overlay_clips = [
            clip.set_position(("center", "center")).set_start(pos)
            for clip, pos in zip(processed_overlays, positions)
        ]

        # Crear el video compuesto
        final_video = CompositeVideoClip([self.base_video] + overlay_clips)

        # Guardar el video final con transparencia
        final_video.write_videofile(
            self.output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            verbose=False
        )

        # Liberar memoria
        self.base_video.close()
        for clip in self.overlay_videos:
            clip.close()

    def __del__(self):
        """Limpieza al destruir la instancia."""
        if hasattr(self, 'base_video'):
            self.base_video.close()
        if hasattr(self, 'overlay_videos'):
            for clip in self.overlay_videos:
                clip.close()


if __name__ == "__main__":
    # Ruta del video base
    base_video = "C:/Users/mozot/source/repos/akumanomi1988/from_news_to_video_uploaded/Resources/Creencias y Futuro de Japón003.mp4"
    
    # Directorio de videos superpuestos
    directory = "C:/Users/mozot/source/repos/akumanomi1988/from_news_to_video_uploaded/Resources/Videos"
    
    # Obtener archivos de video en la carpeta
    overlay_videos = [
        os.path.join(directory, filename)
        for filename in os.listdir(directory)
        if filename.endswith((".mp4", ".avi", ".mov"))
    ]

    if not overlay_videos:
        print("No se encontraron videos superpuestos.")
    else:
        composer = VideoOverlayComposer(
            base_video_path=base_video,
            overlay_video_paths=overlay_videos,
            output_path="C:/Users/mozot/source/repos/akumanomi1988/from_news_to_video_uploaded/Resources/result_video.mp4"
        )

        try:
            composer.compose_video()
            print("¡Video compuesto exitosamente!")
        except Exception as e:
            print(f"Error al componer el video: {str(e)}")