import os
import uuid
import json
import random
from PIL import Image
import g4f
from colorama import Fore, Style, init
import time
# Initialize Colorama
init(autoreset=True)

class ArticleGenerator:
    def __init__(self, language, model, image_model):
        """
        Initializes the ArticleGenerator with the specified language, GPT model, and image generation model.

        Parameters:
            language (str): The language in which to generate the articles.
            model (str): The GPT model to use for article generation.
            image_model (str): The model to use for image generation.
        """
        self.language = language
        self.model = model
        self.image_model = image_model


    def generate_article_and_phrases_short(self, topic):
        """
        Generates an article and related phrases based on the provided topic.

        Parameters:
            topic (str): The topic for which the article and phrases should be generated.

        Returns:
            tuple: A tuple containing the generated article, short phrases, title, description, and tags.
        """
        print(Fore.CYAN + f"Generating article and phrases for topic: {topic}")
        # Generar un GUID único
        file_guid = str(uuid.uuid4())

        # Definir la ruta de la carpeta .temp y el archivo
        folder_path = '.temp'
        file_path = os.path.join(folder_path, f'{file_guid}.json')

        # Construct the prompt for article generation
        prompt_template = (
            'You are a sensationalist news writer. Based on the headline and language I provide, '
            'generate a JSON with the following structure:\n\n'
            '{\n'
            '  "title": "",  // Write a compelling short headline (max 50 chars)\n'
            '  "description": "",  // Write a concise summary of the headline\n'
            '  "article": "",  // Write, in specified Language in parameters, a 100-word news article that immediately grabs attention, '
            'summarizes the key points, and ends with an unexpected twist or fact.\n'
            '  "image_descriptions": [  // Create 10 brief image descriptions, in English, avoiding people or animals unless directly related to the headline. '
            'Include objects, materials, or relevant scenes. Make sure one description is for the cover image.\n'
            '    "description1",  // Example: "A pile of raw materials symbolizing the rise of new industries"\n'
            '    "description2",\n'
            '    ...\n'
            '  ],\n'
            '  "tags": [  // Generate 10 relevant hashtags tailored for a YouTube video based on the headline. Each tag must be in its own element.\n'
            '    "#tag1",\n'
            '    "#tag2",\n'
            '    ...\n'
            '  ]\n'
            '}\n\n'
            'Parameters:\n'
            '- Language: [' + self.language + ']\n'
            '- Headline: [' + topic + ']\n\n'
            'Ensure the output is a fully structured and correctly formatted JSON.'
        )

        messages = [{"role": "system", "content": prompt_template}]
        
        retries = 5  # Número máximo de reintentos
        for attempt in range(retries):
            # Use g4f to create a chat completion using the specified model and constructed message
            response = g4f.ChatCompletion.create(model=self.model, messages=messages)
            
            try:
                # Intentar procesar la respuesta como JSON
                start_index = response.find('{')
                end_index = response.rfind('}')
                content = response[start_index:end_index + 1]
                response_json = json.loads(content)  # Intentar cargar el JSON

                # Si el JSON es válido, extraer los campos necesarios
                article = response_json.get('article', '')
                image_descriptions = response_json.get('image_descriptions', [])
                description = response_json.get('description', '')
                title = response_json.get('title', '')
                tags = response_json.get('tags', [])

                # Limitar el número de frases cortas a 10 si hay más
                short_phrases = random.sample(image_descriptions, min(10, len(image_descriptions)))

                print(Fore.GREEN + "Article and phrases generated successfully.")

                # Guardar el JSON en el archivo
                try:
                    os.makedirs(folder_path, exist_ok=True)  # Crear la carpeta si no existe
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(response_json, f, ensure_ascii=False, indent=4)
                    print(f"JSON guardado correctamente en {file_path}")
                except Exception as e:
                    print(f"Error al guardar el archivo JSON: {e}")

                return article, short_phrases, title, description, tags

            except json.JSONDecodeError:
                # Si el JSON es inválido, imprimir el error y reintentar
                print(Fore.RED + f"Error: The response is not in valid JSON format (attempt {attempt + 1}/{retries}).")
                print(Fore.RED + content)

                # Esperar 1 segundo antes del próximo intento
                if attempt < retries - 1:
                    time.sleep(1)  # Espera antes de reintentar
                else:
                    print(Fore.RED + "Max retries reached. Could not generate a valid JSON response.")
        
        return None, [], "", "", []
