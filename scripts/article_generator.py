import g4f
import random
import configparser
import json
import random

class ArticleGenerator:
    def __init__(self, config_file='settings.config'):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.language = self.load_language()
        self.model = self.load_model()

    def load_language(self):
        return self.config['LanguageSettings']['LANGUAGE']

    def load_model(self):
        return self.config['GPTModelSettings']['MODEL']



    def generate_article_and_phrases(self, topic):
        # Construcción del mensaje para la generación
        prompt_template = (
            f"Eres un experto redactor de noticias sensacionalistas. A partir del titular que te proporcionaré y el idioma que te indique, genera un resultado en formato JSON con la siguiente estructura:\n\n"
            f"{{\n"
            f'  "title": "{topic}",  // El titular de la noticia que te proporcionaré, que quiero que devuelvas taducido\n'
            f'  "description": "",  // Una breve descripción del titular (resumen).\n'
            f'  "article": "",  // Un artículo completo de entre 200 y 250 palabras, escrito en un tono extremadamente sensacionalista, con giros narrativos y recursos dramáticos que mantengan al lector intrigado hasta el final.\n'
            f'  "image_descriptions": [  // Una lista de 25 descripciones breves y específicas que se puedan usar para encontrar imágenes relacionadas en Pexels.\n'
            f'    "description1",\n'
            f'    "description2",\n'
            f'    ...\n'
            f'  ]\n'
            f'}}\n\n'
            f"Parámetros:\n"
            f'- Idioma: "{self.language}"\n'
            f'- Titular: "{topic}"\n\n'
            f"Instrucciones adicionales:\n"
            f"- El idioma del contenido debe ser el que te especifique en el parámetro 'idioma'.\n"
            f"- El JSON debe estar completamente estructurado y correctamente formateado, sin excepciones. NO DENTRO DE UN BLOQUE DE CODIGO DE MARKDOWN."
            f"- Si no cumples alguna de estas condiciones SERÁS DESPEDIDO"
        )

        # formatted_prompt = prompt_template.format(idioma=self.language, titular=topic)
        messages = [{"role": "system", "content": prompt_template}]
        
        # Utiliza g4f con el modelo especificado y el mensaje construido
        response = g4f.ChatCompletion.create(model=self.model, messages=messages)

        # Obtener el contenido generado del JSON
        # content = response['choices'][0]['message']['content']
        content = response.strip()
        try:
            # Parsear el contenido como JSON
            content = content.replace('\n', '').replace('\r', '')
            response_json = json.loads(content)
            
            # Obtener el artículo y las descripciones de imágenes
            article = response_json.get('article', '')
            image_descriptions = response_json.get('image_descriptions', [])
            description = response_json.get('description', '')
            title = response_json.get('title', '')
            # Limitar el número de frases cortas a 10 si hay más
            short_phrases = random.sample(image_descriptions, min(10, len(image_descriptions)))

            return article, short_phrases, title, description

        except json.JSONDecodeError:
            # Manejo de errores si el contenido no es un JSON válido
            print("Error: The response is not in valid JSON format.")
            return None, []

