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
        prompt = f"""
            Based on the following headline, write an article designed to be listened to rather than read. 
            The language should be natural, engaging, and highly compelling for the listener, with a sensationalist style that keeps their attention at all times. 
            Use effective hooks, intense emotions, and unexpected twists to captivate the listener from start to finish. 
            The article should flow continuously without headings or sections, creating a seamless and immersive narrative.

            Format your response exclusively as JSON with the following structure. Do not include any markdown or code blocks. The JSON should be a single line with no additional line breaks:

            {{
                "article": "The generated text here.",
                "image_descriptions": [
                    "Short phrase 1 describing an image.",
                    "Short phrase 2 describing an image.",
                    "Short phrase 3 describing an image.",
                    "Short phrase 4 describing an image.",
                    "Short phrase 5 describing an image.",
                    "Short phrase 6 describing an image.",
                    "Short phrase 7 describing an image.",
                    "Short phrase 8 describing an image.",
                    "Short phrase 9 describing an image.",
                    "Short phrase 10 describing an image."
                ]
            }}

            Headline: {topic}

            Language: {self.language}
            """


        messages = [{"role": "system", "content": prompt}]
        
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

            # Limitar el número de frases cortas a 10 si hay más
            short_phrases = random.sample(image_descriptions, min(10, len(image_descriptions)))

            return article, short_phrases

        except json.JSONDecodeError:
            # Manejo de errores si el contenido no es un JSON válido
            print("Error: The response is not in valid JSON format.")
            return None, []

