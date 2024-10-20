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
        # prompt_template = (
        #     'You are a creative and engaging news writer. Based on the headline and language I provide, '
        #     'generate a JSON with the following structure:\n\n'
        #     '{\n'
        #     '  "title": "",  // Write a concise and appealing headline (max 50 chars) that entices viewers to watch the video\n'
        #     '  "description": "",  // Write a brief summary that highlights key points and encourages the audience to view the video for more details\n'
        #     '  "article": "",  // Write, in specified Language in parameters, a 100-word news article that provides a balanced overview, drawing attention to why watching the video is essential to understand the full story\n'
        #     '  "image_descriptions": [  // Create 10 brief image descriptions, in English, focusing on objects, places, or materials that visually support the headline.\n'
        #     '    "description1",  // Example: "A skyline of a major city at dawn, symbolizing new beginnings"\n'
        #     '    "description2",\n'
        #     '    ...\n'
        #     '  ],\n'
        #     '  "tags": [  // Generate 10 relevant hashtags tailored for a YouTube video based on the headline. Each tag must be in its own element.\n'
        #     '    "#tag1",\n'
        #     '    "#tag2",\n'
        #     '    ...\n'
        #     '  ]\n'
        #     '}\n\n'
        #     'Parameters:\n'
        #     '- Language: [' + self.language + ']\n'
        #     '- Headline: [' + topic + ']\n\n'
        #     'Ensure the output is a fully structured and correctly formatted JSON.'
        # )
        # prompt_template = (
        #     'Hey, I have got something interesting for you. I need your help crafting a response with the following structure:'
        #     '{'
        #     '  "title": "",  // Write a short, catchy headline (max 50 characters) that makes people think, "Wait, could this be true?"'
        #     '  "description": "",  // Write a brief summary that teases key points, but keeps the real juicy details hidden. You want to intrigue them, just enough to make them curious and watch the video for the full story.'
        #     '  "article": "",  // Write a concise (100 words), highly informative news article with a slightly humorous, conspiratorial tone. Present all the key details of the event clearly, engaging the reader with wit and curiosity. Keep it factual but hint at underlying mysteries or hidden motives. The goal is to deliver the news while hinting at bigger implications or secrets, with no fluff. End by inviting readers to share their thoughts or theories in the comments.'
        #     '  "image_descriptions": [  // Write 10 detailed image descriptions in English, closely related to the scenes and key points discussed in the article. Each description should provide enough detail to help the audience visualize the moment clearly.'
        #     '    "description1",  // Example: "A group of people standing around a large conference table, looking at charts and discussing the next big move."'
        #     '    "description2",'
        #     '    ...'
        #     '  ],'
        #     '  "tags": [  // Generate 10-15 of the most relevant and widely used hashtags related to the topic, optimized for YouTube. Ensure each tag is relevant and frequently used in the community to maximize reach.'
        #     '    "#tag1",'
        #     '    "#tag2",'
        #     '    ...'
        #     '  ],'
        #     '  "cover_text": "",  // Generate a catchy, clickbait headline in less than 5 words in the specified Language. This should be attention-grabbing and mysterious enough to make users click immediately.'
        #     '}'
        #     'Parameters:'
        #     '- Language: [' + self.language + ']'
        #     '- Topic: [' + topic + ']'
        #     'Make sure the output is in a fully structured JSON format, no markdown, and keep that air of curiosity alive throughout. Lets make them think twice, shall we?'
        # )
        prompt_template = (
            'Hey, I have got something interesting for you. I need your help crafting a response with the following structure:'
            '{'
            '  "title": "",  // Write a short, catchy headline (max 50 characters) in ' + self.language + ', that makes people think, "Wait, could this be true?"'
            '  "description": "",  // Write a brief summary in ' + self.language + ',that teases key points but keeps the real juicy details hidden. You want to intrigue them just enough to make them curious and watch the video for the full story.'
            '  "article": "",  // Write a concise (100 words) in ' + self.language + ', highly informative news article in the specified Language with a slightly humorous, conspiratorial tone. Present all the key details of the event clearly, engaging the reader with wit and curiosity. Keep it factual but hint at underlying mysteries or hidden motives. The goal is to deliver the news while hinting at bigger implications or secrets, with no fluff. End by inviting readers to share their thoughts or theories in the comments.'
            '  "image_descriptions": [  // Write 10 detailed image descriptions in English, closely related to the scenes and key points discussed in the article. Each description should provide enough detail to help the audience visualize the moment clearly, incorporating elements of mystery or curiosity.'
            '    "description1",  // Example: "A group of people standing around a large conference table, looking at charts and discussing the next big move."'
            '    "description2",'
            '    ...'
            '  ],'
            '  "tags": [  // Generate 10-15 of the most relevant and widely used hashtags related to the topic in English, optimized for YouTube. Ensure each tag is relevant, frequently used in the community, and reflects trending topics or current events to maximize reach.'
            '    "#tag1",'
            '    "#tag2",'
            '    ...'
            '  ],'
            '  "cover_text": "",  // Generate a catchy, short, clickbait headline in less than 5 words in ' + self.language + ' This should be attention-grabbing and mysterious enough to make users click immediately.'
            '}'
            'Parameters:'
            '- Language: [' + self.language + ']'
            '- Topic: [' + topic + ']'
            'Make sure the output is in a fully structured JSON format, no markdown, and keep that air of curiosity alive throughout. this is mandatory!'
        )

        # prompt_template = (
        #     'Hey, I have got something interesting for you. I need your help crafting a response with the following structure:'
        #     '{'
        #     '  "title": "",  // Write a short, catchy headline (max 50 characters) that makes people think, "Wait, could this be true?"'
        #     '  "description": "",  // Write a brief summary that teases key points, but keeps the real juicy details hidden. You want to intrigue them, just enough to make them curious and watch the video for the full story.'
        #     '  "article": "",  // Write a concise (100 words), information-packed news article in a slightly humorous, conspiratorial tone. Present all the key details of the event, but make sure to keep the reader engaged with a sprinkle of wit and curiosity. Keep it factual but hint at underlying mysteries or potential secrets. The goal is to entertain while informing, so avoid empty fluff and focus on delivering the story clearly. Invite readers to share their thoughts on what might be "really" going on in the comments.' 
        #     '  "image_descriptions": [  // Write 10 detailed image descriptions in English, closely related to the scenes and key points discussed in the article. Each description should provide enough detail to help the audience clearly visualize the moment."'
        #     '    "description1",  // Example: "A group of people standing around a large conference table, looking at charts and discussing the next big move."'
        #     '    "description2",'
        #     '    ...'
        #     '  ],'
        #     '  "tags": [  // Generate 10-15 of the most popular and widely used hashtags related to the topic, optimized for YouTube. Each tag must be relevant to the topic and frequently used in the community.'
        #     '    "#tag1",'
        #     '    "#tag2",'
        #     '    ...'
        #     '  ]'
        #     '}'
        #     'Parameters:'
        #     '- Language: [' + self.language + ']'
        #     '- Topic: [' + topic + ']'
        #     'Make sure the output is in a fully structured JSON format, no markdown, and keep that air of curiosity alive throughout. Lets make them think twice, shall we?'
        # )
        # prompt_template = (
        #     'Hey, it’s me, your go-to narrator. Listen, I’ve got something to tell you, and I’d love to hear what you think. '
        #     'Based on the topic I’m about to show you, let’s create a JSON with the following structure:\n\n'
        #     '{\n'
        #     '  "title": "",  // A catchy, straight-to-the-point headline (max 50 characters), the kind that makes you think "Wait, could this be real?"\n'
        #     '  "description": "",  // A short summary that gives away just enough key points to spark curiosity but keeps the best stuff hidden… You know, just enough to make you want to watch the video and see for yourself.\n'
        #     '  "article": "",  // A 100-word article, written in the language specified in the parameters, that gives a solid overview but leaves that lingering question. Because, of course, to really get it, you’ve gotta watch the video.\n'
        #     '  "image_descriptions": [  // I need 10 short image descriptions (in English) of things, places, or objects that visually support the headline. What can we show that makes people think, "Is there more going on here?"\n'
        #     '    "description1",  // Example: "A city skyline at dusk, as if something is hiding beneath the surface."\n'
        #     '    "description2",\n'
        #     '    ...\n'
        #     '  ],\n'
        #     '  "tags": [  // Finally, I need 10 perfect hashtags for this YouTube video, based on the topic. Each one in its own element, and let’s make them thought-provoking, like "Is this really happening?"\n'
        #     '    "#tag1",\n'
        #     '    "#tag2",\n'
        #     '    ...\n'
        #     '  ]\n'
        #     '}\n\n'
        #     'Parameters:\n'
        #     '- Language: [' + self.language + ']\n'
        #     '- Topic: [' + topic + ']\n\n'
        #     'Oh, and make sure the output is a well-structured JSON. We don’t want to miss any important details, right?'
        # )


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
                cover_text = response_json.get('cover_text', '')
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

                return article, short_phrases, title, description, tags, cover_text

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

    def generate_article_and_phrases_long(self, topic):
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

        # Generar el título
        title_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "title": ""  // Write a compelling headline (max 50 chars)\n'
            '}\n'
            'Ensure the output is a properly formatted JSON object, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        title_json = self._generate_json_element(title_prompt)
        title = title_json.get('title', '')

        # Generar la descripción
        description_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "description": ""  // Write a summary that gives viewers a glimpse of key points\n'
            '}\n'
            'Ensure the output is a properly formatted JSON object, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        description_json = self._generate_json_element(description_prompt)
        description = description_json.get('description', '')

        # Generar el artículo (más de 1000 palabras)
        article_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "article": ""  // Write a detailed and comprehensive article of at least 100 words\n'
            '}\n'
            'Ensure the output is a properly formatted JSON object, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        article_json = self._generate_json_element(article_prompt)
        article = article_json.get('article', '')

        # Generar descripciones de imágenes
        image_descriptions_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "image_descriptions": []  // Create 20 concise image descriptions\n'
            '}\n'
            'Ensure the output is a properly formatted JSON object, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        image_descriptions_json = self._generate_json_element(image_descriptions_prompt)
        image_descriptions = image_descriptions_json.get('image_descriptions', [])

        # Generar etiquetas
        tags_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "tags": []  // Generate 10-15 relevant hashtags\n'
            '}\n'
            'Ensure the output is a properly formatted JSON object, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        tags_json = self._generate_json_element(tags_prompt)
        tags = tags_json.get('tags', [])

        # Limitar el número de frases cortas a 10 si hay más
        short_phrases = random.sample(image_descriptions, min(10, len(image_descriptions)))

        print(Fore.GREEN + "Article and phrases generated successfully.")

        # Crear el JSON completo
        response_json = {
            "title": title,
            "description": description,
            "article": article,
            "image_descriptions": image_descriptions,
            "tags": tags
        }

        # Guardar el JSON en el archivo
        try:
            os.makedirs(folder_path, exist_ok=True)  # Crear la carpeta si no existe
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(response_json, f, ensure_ascii=False, indent=4)
            print(f"JSON guardado correctamente en {file_path}")
        except Exception as e:
            print(f"Error al guardar el archivo JSON: {e}")

        return article, short_phrases, title, description, tags


    
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

    #     # Construct the prompt for article generation
    #     prompt_template = (
    #         'You are a creative and engaging news writer, with a knack for interweaving factual scientific theories and slightly conspiratorial ideas. '
    #         'Based on the headline and language I provide, generate a JSON with the following structure:\n\n'
    #         '{\n'
    #         '  "title": "",  // Write a compelling headline (max 50 chars) that catches attention and hints at deeper layers in the story\n'
    #         '  "description": "",  // Write a summary that gives viewers a glimpse of key points, and subtly suggests there is more than meets the eye\n'
    #         '  "article": "",  // Write a detailed article (at least 600 words, preferably much longer) that presents the facts, but skillfully interlaces scientific theories and slight conspiratorial ideas. Be careful to maintain a tone that is entertaining yet supported by real scientific or historical context. Avoid overt bias, but be playful with interpretations.\n'
    #         '  "image_descriptions": [  // Create 20 concise image descriptions in English, focusing on visuals that amplify the story\'s mystery or intrigue. Avoid depicting people or animals unless directly related to the headline. Include objects, materials, or scenes that evoke a deeper meaning. One description should be for a captivating cover image\n'
    #         '    "description1",  // Example: "Shadowy city under red sky, hinting at global power shifts."\n'
    #         '    "description2",\n'
    #         '    ...\n'
    #         '  ],\n'
    #         '  "tags": [  // Generate 5 relevant hashtags tailored for a YouTube video based on the headline. Focus on elements of intrigue, mystery, and scientific curiosity.\n'
    #         '    "#tag1",\n'
    #         '    "#tag2",\n'
    #         '    ...\n'
    #         '  ]\n'
    #         '}\n\n'
    #         'Parameters:\n'
    #         '- Language: [' + self.language + ']\n'
    #         '- Headline: [' + topic + ']\n\n'
    #         'Ensure the output is a fully structured and correctly formatted JSON. Make sure the article blends factual information with subtle but scientifically grounded conspiracy theories to keep the readers hooked.'
    #     )


    #     messages = [{"role": "system", "content": prompt_template}]
        
    #     retries = 5  # Número máximo de reintentos
    #     for attempt in range(retries):
    #         # Use g4f to create a chat completion using the specified model and constructed message
    #         response = g4f.ChatCompletion.create(model=self.model, messages=messages)
            
    #         try:
    #             # Intentar procesar la respuesta como JSON
    #             start_index = response.find('{')
    #             end_index = response.rfind('}')
    #             content = response[start_index:end_index + 1]
    #             response_json = json.loads(content)  # Intentar cargar el JSON

    #             # Si el JSON es válido, extraer los campos necesarios
    #             article = response_json.get('article', '')
    #             image_descriptions = response_json.get('image_descriptions', [])
    #             description = response_json.get('description', '')
    #             title = response_json.get('title', '')
    #             tags = response_json.get('tags', [])

    #             # Limitar el número de frases cortas a 10 si hay más
    #             short_phrases = random.sample(image_descriptions, min(10, len(image_descriptions)))

    #             print(Fore.GREEN + "Article and phrases generated successfully.")

    #             # Guardar el JSON en el archivo
    #             try:
    #                 os.makedirs(folder_path, exist_ok=True)  # Crear la carpeta si no existe
    #                 with open(file_path, 'w', encoding='utf-8') as f:
    #                     json.dump(response_json, f, ensure_ascii=False, indent=4)
    #                 print(f"JSON guardado correctamente en {file_path}")
    #             except Exception as e:
    #                 print(f"Error al guardar el archivo JSON: {e}")

    #             return article, short_phrases, title, description, tags

    #         except json.JSONDecodeError:
    #             # Si el JSON es inválido, imprimir el error y reintentar
    #             print(Fore.RED + f"Error: The response is not in valid JSON format (attempt {attempt + 1}/{retries}).")
    #             print(Fore.RED + content)

    #             # Esperar 1 segundo antes del próximo intento
    #             if attempt < retries - 1:
    #                 time.sleep(1)  # Espera antes de reintentar
    #             else:
    #                 print(Fore.RED + "Max retries reached. Could not generate a valid JSON response.")
        
    #     return None, [], "", "", []
    
    def generate_video_script_and_podcast(self, headlines):
        """
        Generates a structured JSON with articles, image descriptions, and then a podcast-style voice-over script 
        for the provided headlines, in the language specified by the 'self.language' attribute.

        Parameters:
            headlines (list of str): A list of news headlines.

        Returns:
            dict: A dictionary containing the video presentation, articles, image descriptions, podcast script, and hashtags for each headline.
        """
        print(Fore.CYAN + f"Generating video script and podcast for {len(headlines)} headlines...")

        # Unique GUID for file storage
        file_guid = str(uuid.uuid4())
        folder_path = '.temp'
        file_path = os.path.join(folder_path, f'{file_guid}_video_script.json')

        # Initialize the structure to store results for all headlines
        result_data = {}

        # Prompt templates for generating articles and podcast scripts
        prompt_template_articles = (
            'You are a sensationalist news writer. Based on the headlines I provide, generate a JSON with the following structure:\n\n'
            '{\n'
            '  "headline": "",  // Write a compelling short headline (max 10 words)\n'
            '  "description": "",  // Write a concise summary of the headline (50 words)\n'
            '  "article": "",  // Write a 100-word article that grabs attention and summarizes the key points, with a twist at the end.\n'
            '  "image_descriptions": [  // Create 5 image descriptions, including one for the cover and 4 related to the story.\n'
            '    "description1",  // Example: "A furious, crazed news anchor bursting out of the TV screen in an energetic pose."\n'
            '    "description2",  // Additional 4 scene-related descriptions.\n'
            '    ...\n'
            '  ],\n'
            '  "tags": [  // Generate 10 relevant and popular hashtags for news videos.\n'
            '    "#tag1",\n'
            '    "#tag2",\n'
            '    ...\n'
            '  ]\n'
            '}\n\n'
            'Parameters:\n'
            '- Language: [' + self.language + ']\n'
            '- Headlines: [].\n\n'
            'Ensure the output is a fully structured and correctly formatted JSON for each headline.'
        )

        prompt_template_podcast = (
            'You are a scriptwriter for a news podcast. Based on the headline and article provided, generate a voice-over script that sounds natural '
            'when read aloud by a single speaker. Ensure the tone is engaging and easy to follow. Use conversational language without unnecessary elements. '
            'No stage directions or non-spoken details are needed. Return the result in plain text without formatting.'
        )

        # Generate content for each headline
        for index, headline in enumerate(headlines):
            print(Fore.CYAN + f"Processing headline {index + 1}/{len(headlines)}: {headline}")

            # Messages for generating articles, images, and hashtags
            article_messages = [{"role": "system", "content": prompt_template_articles}, {"role": "user", "content": headline}]
            podcast_messages = [{"role": "system", "content": prompt_template_podcast}, {"role": "user", "content": headline}]

            # Retry mechanism in case of failed requests
            retries = 5

            for attempt in range(retries):
                try:
                    # Request 1: Generate article, title, description, image descriptions, and tags
                    article_response = g4f.ChatCompletion.create(model=self.model, messages=article_messages)
                    start_index = article_response.find('{')
                    end_index = article_response.rfind('}')
                    article_content = article_response[start_index:end_index + 1]
                    article_json = json.loads(article_content)  # Attempt to parse the JSON response

                    # Request 2: Generate podcast script
                    podcast_response = g4f.ChatCompletion.create(model=self.model, messages=podcast_messages)

                    # Combine both results
                    result_data[headline] = {
                        "headline": article_json.get('headline', ''),
                        "description": article_json.get('description', ''),
                        "article": article_json.get('article', ''),
                        "image_descriptions": article_json.get('image_descriptions', []),
                        "tags": article_json.get('tags', []),
                        "podcast_script": podcast_response.strip()  # Clean up podcast response
                    }

                    print(Fore.GREEN + f"Successfully generated content for headline {index + 1}")

                    # Save intermediate results to a file
                    try:
                        os.makedirs(folder_path, exist_ok=True)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(result_data, f, ensure_ascii=False, indent=4)
                        print(Fore.GREEN + f"Intermediate JSON saved at {file_path}")
                    except Exception as e:
                        print(Fore.RED + f"Error saving the JSON file: {e}")

                    break  # Exit retry loop on success

                except (json.JSONDecodeError, ValueError) as e:
                    print(Fore.RED + f"Error processing headline {headline}: {e} (attempt {attempt + 1}/{retries})")
                    if attempt < retries - 1:
                        time.sleep(1)  # Wait before retrying
                    else:
                        print(Fore.RED + f"Max retries reached for headline: {headline}. Skipping...")

        return result_data
