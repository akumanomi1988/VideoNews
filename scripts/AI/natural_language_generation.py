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

class Chatbot:
    def __init__(self, language, model):
        """
        Initializes the ArticleGenerator with the specified language, GPT model, and image generation model.

        Parameters:
            language (str): The language in which to generate the articles.
            model (str): The GPT model to use for article generation.
            image_model (str): The model to use for image generation.
        """
        self.language = language
        self.model = model

    def generate_title(self, topic):
        title_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "title": ""  // Create a highly engaging and SEO-optimized YouTube title that incorporates relevant keywords to attract viewers and boost search rankings."'
            '}\n'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        title_json = self._generate_json_element(title_prompt)
        return title_json.get('title', '')

    def generate_description(self, topic):
        description_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "description": ""  // Write a brief, SEO-optimized video description in ' + self.language + ' that highlights key points while keeping the most intriguing details hidden. Use relevant keywords to enhance search visibility and create curiosity, enticing viewers to watch the video for the full story.'
            '}\n'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        description_json = self._generate_json_element(description_prompt)
        return description_json.get('description', '')

    def generate_article(self, topic, length=120):
        article_prompt = (
            'You are a professional news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "article": "" // Write a factual and informative news article in ' + self.language + ' with a serious and professional tone. Present the key details of the event clearly and concisely, ensuring the article is approximately {length} words long. Focus on delivering the facts objectively, without unnecessary opinions or emotions, maintaining a formal style typical of traditional news reports. Emphasize clarity and precision to ensure the narrative is engaging while adhering to the word limit'
            '}\n'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        ).format(length=length)
        
        article_json = self._generate_json_element(article_prompt)
        return article_json.get('article', '')

    def generate_image_descriptions(self, topic, count=10):
        image_descriptions_prompt = (
            'You are a creative writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "image_descriptions": ["","",""...]  // Write {count} detailed image descriptions in English, closely related to the scenes and key points discussed in the article. Each description should provide enough detail to help the audience visualize the moment clearly, as if it were a scene from a graphic novel. Incorporate elements of mystery, suspense, or intrigue to engage the reader\'s imagination.'
            '}\n'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        ).format(count=count)
        
        image_descriptions_json = self._generate_json_element(image_descriptions_prompt)
        return image_descriptions_json.get('image_descriptions', [])

    def generate_tags(self, topic):
        tags_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "tags": [] // Generate 20 of the most relevant and widely used hashtags related to the topic in English, optimized for YouTube. Each hashtag should be effective for SEO, capturing trending topics and current events to maximize reach. Focus on including both single words and multi-word phrases that are highly relevant and frequently used in the community, without the "#" symbol, to enhance visibility and engagement.'
            '}\n'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        tags_json = self._generate_json_element(tags_prompt)
        return tags_json.get('tags', [])

    def generate_cover(self, topic):
        cover_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "cover": "" // Generate a short, attention-grabbing phrase in ' + self.language + ', focusing on the main character or affected person. It must contain a **maximum of 5 words** and evoke curiosity.\n'
            '}\n'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        cover_json = self._generate_json_element(cover_prompt)
        return cover_json.get('cover', '')
    
    

    def generate_cover_image(self, topic):
        cover_image_prompt = (
            'Describe an image for a cover that includes all key elements in a single, cohesive description string:\n'
            '{\n'
            '  "coverImage": "" // Describe the scene for the cover image, combining elements such as the main person (a man or woman conveying emotions relevant to the news topic), '
            'background setting related to the topic, and any additional details that evoke the intended emotions.\n'
            '}\n'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        cover_image_json = self._generate_json_element(cover_image_prompt)
        return cover_image_json.get('coverImage', '')


    def _generate_json_element(self, prompt_template):
        """
        Helper function to generate a single JSON element based on the provided prompt.
        """
        messages = [{"role": "system", "content": prompt_template}]
        
        retries = 5  # Número máximo de reintentos
        for attempt in range(retries):
            response = g4f.ChatCompletion.create(model=self.model, messages=messages)
            
            try:
                start_index = response.find('{')
                end_index = response.rfind('}')
                content = response[start_index:end_index + 1]
                response_json = json.loads(content)  # Intentar cargar el JSON

                return response_json

            except json.JSONDecodeError:
                print(Fore.RED + f"Error: The response is not in valid JSON format (attempt {attempt + 1}/{retries}).")
                print(Fore.RED + content)

                if attempt < retries - 1:
                    time.sleep(1)  # Espera antes de reintentar
                else:
                    print(Fore.RED + "Max retries reached. Could not generate a valid JSON response.")
        
        return None
    
    def generate_article_and_phrases_short(self, topic):
        """
        Generates an article and related phrases based on the provided topic.

        Parameters:
            topic (str): The topic for which the article and phrases should be generated.

        Returns:
            tuple: A tuple containing the generated article, short phrases, title, description, tags, cover, and cover image.
        """
        print(Fore.CYAN + f"Generating article and phrases for topic: {topic}")

        # Generate a unique GUID
        file_guid = str(uuid.uuid4())
        folder_path = '.temp'
        file_path = os.path.join(folder_path, f'{file_guid}.json')

        title = self.generate_title(topic)
        description = self.generate_description(topic)
        article = self.generate_article(topic, length=120)  # Specify article length here
        image_descriptions = self.generate_image_descriptions(topic, count=10)  # Specify number of image descriptions here
        tags = self.generate_tags(topic)
        cover = self.generate_cover(topic)
        cover_image = self.generate_cover_image(topic)

        # Limit the number of short phrases to 10 if more are present
        short_phrases = random.sample(image_descriptions, min(10, len(image_descriptions)))

        print(Fore.GREEN + "Article and phrases generated successfully.")

        # Create the complete JSON response
        response_json = {
            "title": title,
            "description": description,
            "article": article,
            "image_descriptions": image_descriptions,
            "tags": tags,
            "cover": cover,
            "cover_image": cover_image
        }

        # Save the JSON to a file
        self.save_json(file_path, response_json)

        return article, short_phrases, title, description, tags, cover, cover_image
    
    def generate_article_and_phrases_long(self, topic):
        """
        Generates a long article and related phrases based on the provided topic.

        Parameters:
            topic (str): The topic for which the article and phrases should be generated.

        Returns:
            tuple: A tuple containing the generated article, short phrases, title, description, tags, cover, and cover image.
        """
        print(Fore.CYAN + f"Generating long article and phrases for topic: {topic}")

        # Generate a unique GUID
        file_guid = str(uuid.uuid4())
        folder_path = '.temp'
        file_path = os.path.join(folder_path, f'{file_guid}.json')

        title = self.generate_title(topic)
        description = self.generate_description(topic)
        article = self.generate_article(topic, length=2000)  # Specify article length of 2000 words here
        image_descriptions = self.generate_image_descriptions(topic, count=20)  # Specify number of image descriptions here
        tags = self.generate_tags(topic)
        cover = self.generate_cover(topic)
        cover_image = self.generate_cover_image(topic)

        # Limit the number of short phrases to 10 if more are present
        short_phrases = random.sample(image_descriptions, min(20, len(image_descriptions)))

        print(Fore.GREEN + "Long article and phrases generated successfully.")

        # Create the complete JSON response
        response_json = {
            "title": title,
            "description": description,
            "article": article,
            "image_descriptions": image_descriptions,
            "tags": tags,
            "cover": cover,
            "cover_image": cover_image
        }

        # Save the JSON to a file
        self.save_json(file_path, response_json)

        return article, short_phrases, title, description, tags, cover, cover_image


    
    # def generate_video_script_and_podcast(self, headlines):
    #     """
    #     Generates a structured JSON with articles, image descriptions, and then a podcast-style voice-over script 
    #     for the provided headlines, in the language specified by the 'self.language' attribute.

    #     Parameters:
    #         headlines (list of str): A list of news headlines.

    #     Returns:
    #         dict: A dictionary containing the video presentation, articles, image descriptions, podcast script, and hashtags for each headline.
    #     """
    #     print(Fore.CYAN + f"Generating video script and podcast for {len(headlines)} headlines...")

    #     # Unique GUID for file storage
    #     file_guid = str(uuid.uuid4())
    #     folder_path = '.temp'
    #     file_path = os.path.join(folder_path, f'{file_guid}_video_script.json')

    #     # Initialize the structure to store results for all headlines
    #     result_data = {}

    #     # Prompt templates for generating articles and podcast scripts
    #     prompt_template_articles = (
    #         'You are a sensationalist news writer. Based on the headlines I provide, generate a JSON with the following structure:\n\n'
    #         '{\n'
    #         '  "headline": "",  // Write a compelling short headline (max 10 words)\n'
    #         '  "description": "",  // Write a concise summary of the headline (50 words)\n'
    #         '  "article": "",  // Write a 100-word article that grabs attention and summarizes the key points, with a twist at the end.\n'
    #         '  "image_descriptions": [  // Create 5 image descriptions, including one for the cover and 4 related to the story.\n'
    #         '    "description1",  // Example: "A furious, crazed news anchor bursting out of the TV screen in an energetic pose."\n'
    #         '    "description2",  // Additional 4 scene-related descriptions.\n'
    #         '    ...\n'
    #         '  ],\n'
    #         '  "tags": [  // Generate 10 relevant and popular hashtags for news videos.\n'
    #         '    "#tag1",\n'
    #         '    "#tag2",\n'
    #         '    ...\n'
    #         '  ]\n'
    #         '}\n\n'
    #         'Parameters:\n'
    #         '- Language: [' + self.language + ']\n'
    #         '- Headlines: [].\n\n'
    #         'Ensure the output is a fully structured and correctly formatted JSON for each headline.'
    #     )

    #     prompt_template_podcast = (
    #         'You are a scriptwriter for a news podcast. Based on the headline and article provided, generate a voice-over script that sounds natural '
    #         'when read aloud by a single speaker. Ensure the tone is engaging and easy to follow. Use conversational language without unnecessary elements. '
    #         'No stage directions or non-spoken details are needed. Return the result in plain text without formatting.'
    #     )

    #     # Generate content for each headline
    #     for index, headline in enumerate(headlines):
    #         print(Fore.CYAN + f"Processing headline {index + 1}/{len(headlines)}: {headline}")

    #         # Messages for generating articles, images, and hashtags
    #         article_messages = [{"role": "system", "content": prompt_template_articles}, {"role": "user", "content": headline}]
    #         podcast_messages = [{"role": "system", "content": prompt_template_podcast}, {"role": "user", "content": headline}]

    #         # Retry mechanism in case of failed requests
    #         retries = 5

    #         for attempt in range(retries):
    #             try:
    #                 # Request 1: Generate article, title, description, image descriptions, and tags
    #                 article_response = g4f.ChatCompletion.create(model=self.model, messages=article_messages)
    #                 start_index = article_response.find('{')
    #                 end_index = article_response.rfind('}')
    #                 article_content = article_response[start_index:end_index + 1]
    #                 article_json = json.loads(article_content)  # Attempt to parse the JSON response

    #                 # Request 2: Generate podcast script
    #                 podcast_response = g4f.ChatCompletion.create(model=self.model, messages=podcast_messages)

    #                 # Combine both results
    #                 result_data[headline] = {
    #                     "headline": article_json.get('headline', ''),
    #                     "description": article_json.get('description', ''),
    #                     "article": article_json.get('article', ''),
    #                     "image_descriptions": article_json.get('image_descriptions', []),
    #                     "tags": article_json.get('tags', []),
    #                     "podcast_script": podcast_response.strip()  # Clean up podcast response
    #                 }

    #                 print(Fore.GREEN + f"Successfully generated content for headline {index + 1}")

    #                 # Save intermediate results to a file
    #                 try:
    #                     os.makedirs(folder_path, exist_ok=True)
    #                     with open(file_path, 'w', encoding='utf-8') as f:
    #                         json.dump(result_data, f, ensure_ascii=False, indent=4)
    #                     print(Fore.GREEN + f"Intermediate JSON saved at {file_path}")
    #                 except Exception as e:
    #                     print(Fore.RED + f"Error saving the JSON file: {e}")

    #                 break  # Exit retry loop on success

    #             except (json.JSONDecodeError, ValueError) as e:
    #                 print(Fore.RED + f"Error processing headline {headline}: {e} (attempt {attempt + 1}/{retries})")
    #                 if attempt < retries - 1:
    #                     time.sleep(1)  # Wait before retrying
    #                 else:
    #                     print(Fore.RED + f"Max retries reached for headline: {headline}. Skipping...")

    #     return result_data

    # def generate_article_and_phrases_long(self, topic):
    #     """
    #     Generates an article and related phrases based on the provided topic.

    #     Parameters:
    #         topic (str): The topic for which the article and phrases should be generated.

    #     Returns:
    #         tuple: A tuple containing the generated article, short phrases, title, description, and tags.
    #     """
    #     print(Fore.CYAN + f"Generating article and phrases for topic: {topic}")
        
    #     # Generar un GUID único
    #     file_guid = str(uuid.uuid4())
    #     # Definir la ruta de la carpeta .temp y el archivo
    #     folder_path = '.temp'
    #     file_path = os.path.join(folder_path, f'{file_guid}.json')

    #     # Generar el título
    #     title_prompt = (
    #         'You are a creative and engaging news writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "title": ""  // Write a short, catchy headline (max 50 characters) in ' + self.language + ', that makes people think, "Wait, could this be true?"'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )
    #     title_json = self._generate_json_element(title_prompt)
    #     title = title_json.get('title', '')

    #     # Generar la descripción
    #     description_prompt = (
    #         'You are a creative and engaging news writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "description": ""  // Write a brief summary in ' + self.language + ',that teases key points but keeps the real juicy details hidden. You want to intrigue them just enough to make them curious and watch the video for the full story.'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )
    #     description_json = self._generate_json_element(description_prompt)
    #     description = description_json.get('description', '')
    #     article_prompt = (
    #         'You are a professional news writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "article": ""  // Write a factual and informative news article in ' + self.language + ' with a serious and professional tone **in more than 2000 words (10 paragraphs)**. Follow the structure of a news article without naming the parts: \n'
    #         '    - Introduction: Introduce the topic with a clear and concise paragraph that answers the 6 Ws (who, what, when, where, why, and how) and sets the stage for the rest of the article.\n'
    #         '    - Body: Develop the article using the inverted pyramid structure. Start with the most important information and provide details and context as you progress. Include background information and consequences of the event.\n'
    #         '    - Conclusion: Summarize the main points and provide a closing statement.\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )
    #     article_json = self._generate_json_element(article_prompt)
    #     article = article_json.get('article', '')

    #     # Generar descripciones de imágenes
    #     image_descriptions_prompt = (
    #         'You are a creative writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "image_descriptions": ["","",""...]  // Write 20 detailed image descriptions in English, closely related to the scenes and key points discussed in the article. Each description should provide enough detail to help the audience visualize the moment clearly, as if it were a scene from a graphic novel. Incorporate elements of mystery, suspense, or intrigue to engage the reader\'s imagination.'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #         )
    #     image_descriptions_json = self._generate_json_element(image_descriptions_prompt)
    #     image_descriptions = image_descriptions_json.get('image_descriptions', [])

    #     # Generar etiquetas
    #     tags_prompt = (
    #         'You are a creative and engaging news writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "tags": [] // Generate 5 of the most relevant and widely used hashtags in only one word, related to the topic in English, optimized for YouTube. Ensure each tag is relevant, frequently used in the community, and reflects trending topics or current events to maximize reach.'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )
    #     tags_json = self._generate_json_element(tags_prompt)
    #     tags = tags_json.get('tags', [])

    #     # Generar cover
    #     cover_prompt = (
    #         'You are a creative and engaging news writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "cover": "" // Generate a short, attention-grabbing phrase in ' + self.language + ', focusing on the main character or affected person. It must contain a **maximum of 5 words** and evoke curiosity.\n'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )
    #     cover_json = self._generate_json_element(cover_prompt)
    #     cover = cover_json.get('cover', '')

    #             # Generar cover
    #     cover_image_prompt = (
    #         'Describe an image for a cover that includes all key elements in a single, cohesive description string:\n'
    #         '{\n'
    #         '  "coverImage": "" // Describe the scene for the cover image, combining elements such as the main person (a man or woman conveying emotions relevant to the news topic), '
    #         'background setting related to the topic, and any additional details that evoke the intended emotions.\n'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )

    #     cover_image_json = self._generate_json_element(cover_image_prompt)
    #     cover_image = cover_image_json.get('coverImage', '')


    #     # Limitar el número de frases cortas a 10 si hay más
    #     short_phrases = random.sample(image_descriptions, min(10, len(image_descriptions)))

    #     print(Fore.GREEN + "Article and phrases generated successfully.")

    #     # Crear el JSON completo
    #     response_json = {
    #         "title": title,
    #         "description": description,
    #         "article": article,
    #         "image_descriptions": image_descriptions,
    #         "tags": tags,
    #         "cover": cover,
    #         "coverImage": cover_image
    #     }

    #     # Guardar el JSON en el archivo
    #     try:
    #         os.makedirs(folder_path, exist_ok=True)  # Crear la carpeta si no existe
    #         with open(file_path, 'w', encoding='utf-8') as f:
    #             json.dump(response_json, f, ensure_ascii=False, indent=4)
    #         print(f"JSON guardado correctamente en {file_path}")
    #     except Exception as e:
    #         print(f"Error al guardar el archivo JSON: {e}")

    #     return article, short_phrases, title, description, tags, cover ,cover_image

    # def generate_article_and_phrases_short(self, topic):
    #     """
    #     Generates an article and related phrases based on the provided topic.

    #     Parameters:
    #         topic (str): The topic for which the article and phrases should be generated.

    #     Returns:
    #         tuple: A tuple containing the generated article, short phrases, title, description, and tags.
    #     """
    #     print(Fore.CYAN + f"Generating article and phrases for topic: {topic}")
        
    #     # Generar un GUID único
    #     file_guid = str(uuid.uuid4())
    #     # Definir la ruta de la carpeta .temp y el archivo
    #     folder_path = '.temp'
    #     file_path = os.path.join(folder_path, f'{file_guid}.json')

    #     # Generar el título
    #     title_prompt = (
    #         'You are a creative and engaging news writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "title": ""  // Create a highly engaging and SEO-optimized YouTube title that incorporates relevant keywords to attract viewers and boost search rankings."'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )
    #     title_json = self._generate_json_element(title_prompt)
    #     title = title_json.get('title', '')

    #     # Generar la descripción
    #     description_prompt = (
    #         'You are a creative and engaging news writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "description": ""  // Write a brief, SEO-optimized video description in ' + self.language + ' that highlights key points while keeping the most intriguing details hidden. Use relevant keywords to enhance search visibility and create curiosity, enticing viewers to watch the video for the full story.'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )
    #     description_json = self._generate_json_element(description_prompt)
    #     description = description_json.get('description', '')
    #     article_prompt = (
    #         'You are a professional news writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "article": "" // Write a factual and informative news article in ' + self.language + ' with a serious and professional tone. Present the key details of the event clearly and concisely, ensuring the article is approximately 120 words long. Focus on delivering the facts objectively, without unnecessary opinions or emotions, maintaining a formal style typical of traditional news reports. Emphasize clarity and precision to ensure the narrative is engaging while adhering to the word limit'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )
    #     article_json = self._generate_json_element(article_prompt)
    #     article = article_json.get('article', '')

    #     # Generar descripciones de imágenes
    #     image_descriptions_prompt = (
    #         'You are a creative writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "image_descriptions": ["","",""...]  // Write 10 detailed image descriptions in English, closely related to the scenes and key points discussed in the article. Each description should provide enough detail to help the audience visualize the moment clearly, as if it were a scene from a graphic novel. Incorporate elements of mystery, suspense, or intrigue to engage the reader\'s imagination.'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #         )
    #     image_descriptions_json = self._generate_json_element(image_descriptions_prompt)
    #     image_descriptions = image_descriptions_json.get('image_descriptions', [])

    #     # Generar etiquetas
    #     tags_prompt = (
    #         'You are a creative and engaging news writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "tags": [] // Generate 20 of the most relevant and widely used hashtags related to the topic in English, optimized for YouTube. Each hashtag should be effective for SEO, capturing trending topics and current events to maximize reach. Focus on including both single words and multi-word phrases that are highly relevant and frequently used in the community, without the "#" symbol, to enhance visibility and engagement.'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )
    #     tags_json = self._generate_json_element(tags_prompt)
    #     tags = tags_json.get('tags', [])

    #     # Generar cover
    #     cover_prompt = (
    #         'You are a creative and engaging news writer. Based on the headline and language I provide, '
    #         'generate a response that must be a fully structured JSON object with the following format:\n'
    #         '{\n'
    #         '  "cover": "" // Generate a short, attention-grabbing phrase in ' + self.language + ', focusing on the main character or affected person. It must contain a **maximum of 5 words** and evoke curiosity.\n'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )
    #     cover_json = self._generate_json_element(cover_prompt)
    #     cover = cover_json.get('cover', '')

    #     cover_image_prompt = (
    #         'Describe an image for a cover that includes all key elements in a single, cohesive description string:\n'
    #         '{\n'
    #         '  "coverImage": "" // Describe the scene for the cover image, combining elements such as the main person (a man or woman conveying emotions relevant to the news topic), '
    #         'background setting related to the topic, and any additional details that evoke the intended emotions.\n'
    #         '}\n'
    #         'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
    #         f'Parameters:\n'
    #         f'- Language: [{self.language}]\n'
    #         f'- Headline: [{topic}]\n'
    #     )

    #     cover_image_json = self._generate_json_element(cover_image_prompt)
    #     cover_image = cover_image_json.get('coverImage', '')

    #     # Limitar el número de frases cortas a 10 si hay más
    #     short_phrases = random.sample(image_descriptions, min(10, len(image_descriptions)))

    #     print(Fore.GREEN + "Article and phrases generated successfully.")

    #     # Crear el JSON completo
    #     response_json = {
    #         "title": title,
    #         "description": description,
    #         "article": article,
    #         "image_descriptions": image_descriptions,
    #         "tags": tags,
    #         "cover": cover,
    #         "cover_image": cover_image
    #     }

    #     # Guardar el JSON en el archivo
    #     try:
    #         os.makedirs(folder_path, exist_ok=True)  # Crear la carpeta si no existe
    #         with open(file_path, 'w', encoding='utf-8') as f:
    #             json.dump(response_json, f, ensure_ascii=False, indent=4)
    #         print(f"JSON guardado correctamente en {file_path}")
    #     except Exception as e:
    #         print(f"Error al guardar el archivo JSON: {e}")

    #     return article, short_phrases, title, description, tags, cover,cover_image
    