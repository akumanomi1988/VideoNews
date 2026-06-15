import re

class SRTProcessor:
    def __init__(self, input_file, max_duration=2.0, max_words=5, pause_threshold=0.3):
        """
        Procesador de subtítulos SRT para agrupar palabras en frases con mejor fluidez.
        
        :param input_file: Archivo SRT de entrada (será sobrescrito).
        :param max_duration: Máximo tiempo en segundos por frase.
        :param max_words: Máximo número de palabras por frase.
        :param pause_threshold: Tiempo de pausa mínima (segundos) para permitir grupos más largos.
        """
        self.input_file = input_file
        self.max_duration = max_duration
        self.max_words = max_words
        self.pause_threshold = pause_threshold

    def parse_srt(self):
        """Lee el archivo SRT en memoria y extrae los tiempos y palabras."""
        pattern = re.compile(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.+)")
        subtitles = []

        with open(self.input_file, "r", encoding="utf-8") as file:
            content = file.read()

        matches = pattern.findall(content)
        for index, start, end, text in matches:
            subtitles.append({
                "index": int(index),
                "start": self.srt_time_to_seconds(start),
                "end": self.srt_time_to_seconds(end),
                "text": text
            })
        
        return subtitles

    def srt_time_to_seconds(self, time_str):
        """Convierte un tiempo SRT a segundos."""
        h, m, s, ms = map(int, re.split("[:,]", time_str))
        return h * 3600 + m * 60 + s + ms / 1000

    def seconds_to_srt_time(self, seconds):
        """Convierte segundos a formato SRT."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    def is_natural_break(self, text):
        """Verifica si una palabra es un punto de pausa natural."""
        return text.endswith((".", ",", "!", "?"))

    def group_subtitles(self, subtitles):
        """Agrupa palabras en frases con mejor sincronización y fluidez."""
        grouped = []
        temp_group = []
        group_start = None
        last_end = None

        for sub in subtitles:
            if not temp_group:
                temp_group.append(sub)
                group_start = sub["start"]
                last_end = sub["end"]
            else:
                pause = sub["start"] - last_end
                last_end = sub["end"]

                if pause > self.pause_threshold and self.is_natural_break(temp_group[-1]["text"]):
                    grouped.append(temp_group)
                    temp_group = [sub]
                    group_start = sub["start"]
                else:
                    if (sub["end"] - group_start > self.max_duration) or (len(temp_group) >= self.max_words):
                        grouped.append(temp_group)
                        temp_group = [sub]
                        group_start = sub["start"]
                    else:
                        temp_group.append(sub)

        if temp_group:
            grouped.append(temp_group)

        return grouped

    def write_srt(self, grouped_subtitles):
        """Sobrescribe el archivo SRT original con las frases agrupadas."""
        with open(self.input_file, "w", encoding="utf-8") as file:
            index = 1
            for group in grouped_subtitles:
                start_time = self.seconds_to_srt_time(group[0]["start"])
                end_time = self.seconds_to_srt_time(group[-1]["end"])
                text = " ".join(sub["text"] for sub in group)

                file.write(f"{index}\n{start_time} --> {end_time}\n{text}\n\n")
                index += 1

    def process(self):
        """Ejecuta todo el proceso en el mismo archivo."""
        subtitles = self.parse_srt()
        grouped_subtitles = self.group_subtitles(subtitles)
        self.write_srt(grouped_subtitles)

# # Uso:
# input_srt = "scripts\MediaManagers\word_level_subtitles.srt"

# # Configuración: Máximo 2 segundos por frase, 5 palabras por frase, y pausas de 0.3 seg
# processor = SRTProcessor(input_srt, max_duration=2.0, max_words=5, pause_threshold=0.3)
# processor.process()

# print(f"Archivo sobrescrito: {input_srt}")
