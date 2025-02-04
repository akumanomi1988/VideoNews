import re
import os
import uuid
import json
import random
from PIL import Image
import g4f
from colorama import Fore, Style, init
import time
from g4f.client import Client

from scripts.DataFetcher.news_extractor import NewsExtractor
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
        self.standard_rules = ('Your output must be a properly formatted JSON object, using double quotes for keys and single quotes for values. Ensure proper nesting, avoid trailing commas, and escape special characters when necessary.'
                               'Ensure everything you say is factual and accurate, including years, numbers, and names.'
                               )
        self.ideology = 'Highlight systemic inequalities, corporate power abuses, and marginalized group impacts.'
        self.tone = 'Serious but with a *controlled conspiratorial undertone*—raise questions about hidden interests without direct accusations.'

    def generate_title(self, topic):
        title_prompt = (
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{'
            '  "title": ""  //Create a highly engaging and SEO-optimized YouTube title that incorporates relevant keywords to attract viewers and boost search rankings.'
                            ' The title should be a maximum of 60 characters, capitalize the most important words, and include relevant emojis.'
            '}'
            f'{self.standard_rules}'
            f'Parameters:\n'
            f'- **Language of the article must be: [{self.language}]**\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'title')
        title_json = self._generate_json_element(title_prompt)
        return title_json.get('title', '')

    def generate_description(self, topic):
        description_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "description": ""  // Write a brief, SEO-optimized video description in ' + self.language + ' that highlights key points while keeping the most intriguing details hidden.'
                                    ' Use relevant keywords to enhance search visibility and create curiosity, enticing viewers to watch the video for the full story.'
            '}\n'
            f'{self.standard_rules}'
            f'Parameters:\n'
            f'- **Languageof the article must be: [{self.language}]**\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'description')
        description_json = self._generate_json_element(description_prompt)
        return description_json.get('description', '')

    def generate_short_article(self, topic, length=100):
        def is_url(string):
            # Simple regex to check if the string is a URL
            return re.match(r'^(?:http|ftp)s?://', string) is not None

        if is_url(topic):
            # If the topic is a URL, use NewsExtractor to extract the article text
            extractor = NewsExtractor()
            article_text = extractor.extract_article(topic)
            article_prompt = (
                'generate a response that must be a fully structured JSON object with the following format:\n'
                '{\n'
                '  "article": "" // Write a factual and informative summary of the following news article in ' + self.language + ' with a serious and professional tone.'
                                    ' As a narrator text.'
                                    ' Present the key details of the event clearly and concisely, ensuring the summary is around ' + str(length) + ' words long.'
                '}\n'
                f'{self.standard_rules}'
                f'- Ideological framing: {self.ideology}'
                f'- Tone: {self.tone}'
                f'Parameters:'
                f'- **Languageof the article must be: [{self.language}]**\n'
                f'- Article Text: [{article_text}]'
            )
        else:
            # If the topic is not a URL, proceed with the original prompt
            article_prompt = (
                'generate a response that must be a fully structured JSON object with the following format:\n'
                '{\n'
                '  "article": "" // Write a factual and informative news article in ' + self.language + ' with a serious and professional tone. Present the key details of the event clearly and concisely, ensuring the article is around ' + str(length) + ' words long. Focus on delivering the facts objectively, without unnecessary opinions or emotions, maintaining a formal style typical of traditional news reports. Emphasize clarity and precision to ensure the narrative is engaging while adhering to the word limit'
                '}\n'
                f'{self.standard_rules}'
                f'- Ideological framing: {self.ideology}'
                f'- Tone: {self.tone}'
                f'Parameters:\n'
                f'- **Languageof the article must be: [{self.language}]**\n'
                f'- Headline: [{topic}]\n'
            )

        print(Fore.BLUE + f'article')
        article_json = self._generate_json_element(article_prompt)
        return article_json.get('article', '')
    
    def generate_introduction(self, topic):
        # Genera una introducción breve pero intrigante
        intro_prompt = (
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "article": "" // Write a brief, captivating introduction in ' + self.language + ' about the topic I provided.'
                            ' The introduction should be intriguing, hinting at something larger and more significant to come later.'
                            ' It should build anticipation while setting the scene in a serious and professional tone.'
                            ' The length of the introduction should be short, but impactful.'
                            ' Avoid giving away too much information upfront.'
            '}\n'
            f'{self.standard_rules}'
            f'- Ideological framing: {self.ideology}'
            f'- Tone: {self.tone}'
            f'Parameters:\n'
            f'- **Language of the article must be: [{self.language}]**\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'Article: Introduction')
        intro_json = self._generate_json_element(intro_prompt)
        return intro_json.get('article', '')

    def generate_development(self, topic):
        # Genera el desarrollo extenso de la noticia
        development_prompt = (
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "article": "" // Write an in-depth and detailed development of the news article in ' + self.language + ' about the topic I provided.'
                                ' Speak as a professional narrator.'
                                ' The content should focus on the central events, providing all relevant details and context.'
                                ' The tone should remain serious and objective, and the article should include an exploration of the main details, stakeholders, and any expert opinions.'
                                ' The development should not be too short but should fit within a single response, aiming for a detailed exploration of the topic.'
            '}\n'
            f'{self.standard_rules}'
            f'- Ideological framing: {self.ideology}'
            f'- Tone: {self.tone}'
            f'Parameters:\n'
            f'- **Language of the article must be: [{self.language}]**\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'Article: Body')
        development_json = self._generate_json_element(development_prompt)
        return development_json.get('article', '')

    def generate_conclusion(self, topic):
        # Genera una conclusión o desenlace corto
        conclusion_prompt = (
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "article": "" // Write a brief conclusion or resolution in ' + self.language + ' that sums up the key takeaways from the news article about the topic provided.'
                            ' The conclusion should give a final perspective on the issue, hinting at possible future implications or developments.'
                            ' It should be succinct yet thought-provoking, bringing the article to a close without adding new details.\n'
            '}\n'
            f'{self.standard_rules}'
            f'- Ideological framing: {self.ideology}'
            f'- Tone: {self.tone}'
            f'Parameters:\n'
            f'- **Language of the article must be: [{self.language}]**\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'Article: Conclusion')
        conclusion_json = self._generate_json_element(conclusion_prompt)
        return conclusion_json.get('article', '')


    def generate_full_article(self, topic):
        def is_url(string):
            return re.match(r'^(?:http|ftp)s?://', string) is not None

        if is_url(topic):
            extractor = NewsExtractor()
            article_text = extractor.extract_article(topic)
            intro = self.generate_introduction_from_text(article_text)
            development = self.generate_development_from_text(article_text)
            conclusion = self.generate_conclusion_from_text(article_text)
        else:
            intro = self.generate_introduction(topic)
            development = self.generate_development(topic)
            conclusion = self.generate_conclusion(topic)
        
        full_article = intro + " " + development + " " + conclusion
        return full_article , intro
    
    def generate_introduction_from_text(self, article_text):
        intro_prompt = (
            "Generate a fully structured JSON object with the following format:\n"
            "{\n"
            f'  "article": "" // Craft a 30-50 word video introduction in {self.language} that includes: '
            "1) A provocative hook starting with 'Did you know...?' or a similar phrase; "
            "2) A scandalous teaser using conspiratorial language; "
            "3) A rhetorical question hinting at systemic implications; "
            "4) A compelling call to action. "
            "5) Don't use emojis."
            "Incorporate urgency markers (exclamation points), write numbers in words, and imply hidden truths. "
            "Structure the introduction as follows: [SHOCKING HOOK] + [ALLURING TEASER] + [SUSPENSEFUL PAUSE] + [ENGAGEMENT COMMAND]. "
            "Example: 'What if I told you that...? [X revelation] Who else is involved? Don't miss the full investigation!'\n"
            "}\n"
            f'{self.standard_rules}'
            f'- Ideological framing: {self.ideology}'
            f'- Tone: {self.tone}'
            'Rules:\n'
            '- Start with question-like structure\n'
            '- Use 2-3 short sentences max\n'
            '- Include 1 emoji (context-appropriate) if language allows\n'
            '- End with platform-specific CTA: "Suscríbete/Dale like" (ES) or "Smash subscribe" (EN)\n'
            f'Parameters:\n'
            f'- Language of article must be : [{self.language}]\n'
            f'- Article Text: [{article_text}]\n'
        )
        print(Fore.BLUE + f'Article: Introduction')
        intro_json = self._generate_json_element(intro_prompt)
        return intro_json.get('article', '')

    def generate_development_from_text(self, article_text):
        development_prompt = (
            "Generate a fully structured JSON object with the following format:\n"
            "{\n"
            '  "article": "" // Write a 500-word continuous narrative analysis for voiceover using the news article provided\n'
            "}\n\n"
            "Instructions:\n"
            "1. Create cohesive prose blending these elements organically:\n"
            "   - Historical context and background\n"
            "   - Chronological event sequence (numbers as words)\n"
            "   - Contrast between elite vs. marginalized stakeholders\n"
            "   - Systemic analysis through liberal-progressive lens\n"
            "   - Future implications\n"
            "2. Seamlessly integrate:\n"
            "   - 3+ contrasts between official claims and factual outcomes\n"
            "   - 2+ expert quotes (real or contextualized)\n"
            "   - 1 historical parallel\n"
            "   - 2-3 rhetorical questions with conspiratorial subtext\n"
            "3. Use narrative devices for flow:\n"
            "   - Logical transitions ('Yet...', 'This pattern recalls...', 'Paradoxically...')\n"
            "   - Embedded chronology without section breaks\n"
            "   - Data integration without bullet points\n\n"
            "Formatting Rules:\n"
            "- All numerical values written as words\n"
            "- Maintain serious tone with journalistic gravity\n"
            "- Avoid explicit section headers\n"
            "- The text must be an interpretation of the provided content; you need to change it enough to avoid copyright infringement.\n"
            f"- Ideological Perspective: {self.ideology}\n\n"
            "Parameters:\n"
            f"- Language: {self.language}\n"
            f"- Source Article: {article_text}\n"
            f"{self.standard_rules}"
        )
        print(Fore.BLUE + f'Article: Body')
        development_json = self._generate_json_element(development_prompt)
        return development_json.get('article', '')

    def generate_conclusion_from_text(self, article_text):
        conclusion_prompt = (
            "Generate a fully structured JSON object with the following format:\n"
            "{\n"
            '  "article": "" // Write a 50-100 word conclusion that offers a personal opinion on the issue from a liberal-progressive perspective.\n'
            "}\n\n"
            "Instructions:\n"
            "1. The conclusion must be a personal perspective; begin with a phrase such as 'In my view...' or its equivalent to clearly indicate that it is your opinion.\n"
            "2. Highlight systemic injustices and question power structures while hinting at future implications.\n"
            "3. Conclude with one final, thought-provoking rhetorical question that implies deeper systemic issues.\n\n"
            "Formatting Requirements:\n"
            "- Use a serious tone with a slightly conspiratorial undertone (e.g., 'It is striking that...').\n"
            "- All numbers must be written in words (e.g., 'two hundred million' instead of '200M').\n"
            "- Maintain the ideological framing by critiquing elites and emphasizing the impact on marginalized groups.\n\n"
            f"{self.standard_rules}\n"
            f"- Ideological Framing: {self.ideology}\n"
            f"- Tone: {self.tone}\n\n"
            f"Parameters:\n"
            f"- Language of article must be : [{self.language}]\n"
            f"- Article Text: [{article_text}]\n"
            "Ensure the output is a properly formatted JSON object without any markdown or extra formatting.\n"
        )

        print(Fore.BLUE + f'Article: Conclusion')
        conclusion_json = self._generate_json_element(conclusion_prompt)
        return conclusion_json.get('article', '')

    def generate_image_descriptions(self, topic, count=10):
        image_descriptions_prompt = (
            'You are a creative writer. Based on the headline I provide, generate a response that must be a fully structured JSON object with the following format: '
            '{'
            '  "image_descriptions": ["","",""...]  // Write ' + str(count) + ' detailed image descriptions in English, closely related to the scenes and key points discussed in the article. Each description should be one sentence long and provide enough vivid detail to help the audience visualize the moment clearly, as if it were a scene from a graphic novel. Each scene should reflect elements of mystery, suspense, or cosmic intrigue to engage the readers imagination.'
            '}'
            f"{self.standard_rules}\n"
            f'Parameters:\n'
            f'- Headline: [{topic}]'
        )
        print(Fore.BLUE + f'image descriptions')
        image_descriptions_json = self._generate_json_element(image_descriptions_prompt,False)
        return image_descriptions_json.get('image_descriptions', [])
    def summarize_news_from_url(self, url):
        extractor = NewsExtractor()
        article_text = extractor.extract_article(url)
        
        if article_text is None:
            return []

        summary_prompt = (
            'You are a creative writer. Based on the article text I provide, generate a response that must be a fully structured JSON object with the following format: '
            '{'
            '  "summary": "" // Write a brief summary of the news article in English, highlighting the main points and key details. The summary should be concise and informative, providing a clear overview of the article\'s content.'
            '}'
            f"{self.standard_rules}\n"
            f'Parameters:\n'
            f'- Article Text: [{article_text}]'
        )
        print(Fore.BLUE + f'Summary')
        summary_json = self._generate_json_element(summary_prompt)
        return summary_json.get('summary', '')

    def generate_tags(self, topic):
        tags_prompt = (
            'generate a response that must be a fully structured JSON object with the following format:'
            '{'
            '  "tags": ["","",""...] // Provide a list of exactly 20 of the most effective and widely used tags for this topic. Tags should be optimized for YouTube and based on trending keywords and current community interests, incorporating single words and multi-word phrases that will maximize visibility and engagement. Each hashtag should be carefully researched to ensure relevance, without using the "#" symbol.'#// Generate 20 of the most relevant and widely used hashtags related to the topic in English, optimized for YouTube. Each hashtag should be effective for SEO, capturing trending topics and current events to maximize reach. Focus on including both single words and multi-word phrases that are highly relevant and frequently used in the community, without the "#" symbol, to enhance visibility and engagement.'
            '}'
            f"{self.standard_rules}\n"
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'tags')
        tags_json = self._generate_json_element(tags_prompt,False)
        return tags_json.get('tags', [])

    def generate_cover(self, topic):
        cover_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "cover": "" // Generate a short, attention-grabbing phrase in ' + self.language + ', focusing on the main character or affected person. It must contain a **maximum of 5 words** and evoke curiosity.\n'
            '}\n'
            f"{self.standard_rules}\n"
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'cover')
        cover_json = self._generate_json_element(cover_prompt)
        return cover_json.get('cover', '')
    
    

    def generate_cover_image(self, topic):
        cover_image_prompt = (
            'Describe an image for a cover that includes all key elements in a single, cohesive description string:\n'
            '{\n'
            '  "coverImage": "" // Describe in english, the scene for the cover image, combining elements such as the main person (a man or woman conveying emotions relevant to the news topic), '
            'background setting related to the topic, and any additional details that evoke the intended emotions.\n'
            '}\n'
            f"{self.standard_rules}\n"
            f'Parameters:\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'coverImage')
        cover_image_json = self._generate_json_element(cover_image_prompt)
        return cover_image_json.get('coverImage', '')


    
    def _generate_json_element(self, prompt_template, clean:bool = True):
        """
        Helper function to generate a single JSON element based on the provided prompt.
        """
        retries = 10  # Número máximo de reintentos
        for attempt in range(retries):
            try:
                # Nueva solicitud a GPT en cada intento
                client = Client()
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "assistant", "content": prompt_template}],
                    response_format="json",
                )
                response = response.choices[0].message.content
                print(Fore.YELLOW + f"Response (Intento {attempt + 1}): {response}")

                # Extraer contenido JSON de la respuesta
                start_index = response.find('{')
                end_index = response.rfind('}')
                content = response[start_index:end_index + 1]

                # Intentar limpiar y cargar el JSON
                if clean :
                    content = self.clean_and_load_json(content)
                    return content  # Retorna el JSON si es válido
                return json.loads(content)  # Retorna el JSON si es válido

            except (json.JSONDecodeError, ValueError) as e:
                # Captura errores en la conversión y en clean_and_load_json
                print(Fore.RED + f"Error al procesar JSON (intento {attempt + 1}/{retries}): {e}")
                print(Fore.RED + f"Respuesta defectuosa: {response}")

            except Exception as e:
                # Captura cualquier otro error inesperado
                print(Fore.RED + f"Error inesperado en la generación de JSON: {e} (intento {attempt + 1}/{retries})")

            # Esperar antes de volver a intentar
            if attempt < retries - 1:
                time.sleep(2)  # Espera antes de reintentar con una nueva solicitud

        print(Fore.RED + "Se alcanzó el número máximo de reintentos. No se pudo generar un JSON válido.")
        return None

    def clean_and_load_json(self, json_string: str):
        """
        Cleans a given JSON string to remove unwanted characters and make it valid for JSON parsing.
        Replaces double quotes in values with single quotes while keeping JSON structure intact.
        
        :param json_string: A string containing JSON data.
        :return: A Python dictionary parsed from the cleaned JSON string.
        :raises ValueError: If the cleaned string is still not valid JSON.
        """
        try:
            print(Fore.BLUE, json_string)
            # Remove non-printable characters except for accented characters and other Unicode characters
            json_string = re.sub(r'[\x00-\x1F\x7F]', '', json_string)
            
            # Strip unnecessary whitespace
            json_string = json_string.strip()
            
            # Remove trailing commas in JSON objects and arrays
            json_string = re.sub(r',\s*([}\]])', r'\1', json_string)
            
            # Ensure all keys are properly quoted
            json_string = re.sub(r'(?<=\{|,)(\s*)([a-zA-Z0-9_]+)(\s*):', r'"\2":', json_string)
            
            # Contar las comillas dobles
            quote_count = json_string.count('"')
            if quote_count > 4:
                # Encontrar todas las posiciones de las comillas
                indices = [i for i, c in enumerate(json_string) if c == '"']
                # Mantener las primeras 3 y la última
                if len(indices) >= 4:
                    keep_indices = set(indices[:3] + [indices[-1]])
                    chars = list(json_string)
                    for i in indices:
                        if i not in keep_indices:
                            chars[i] = "'"  # Reemplazar comillas intermedias
                    json_string = ''.join(chars)
            
            # Convert JSON string to dictionary to manipulate values safely
            json_dict = json.loads(json_string)
            
            return json_dict
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON after cleaning: {e}\n{json_string}")
    def save_json(self, file_path, data):
        """Saves JSON data to a file."""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create the folder if it doesn't exist
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"JSON saved successfully at {file_path}")
        except Exception as e:
            print(f"Error saving JSON file: {e} ")

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

        article = self.generate_short_article(topic)  # Specify article length here
        title = self.generate_title(article)
        description = self.generate_description(article)
        image_descriptions = self.generate_image_descriptions(article, count=10)  # Specify number of image descriptions here
        tags = self.generate_tags(article)
        cover = self.generate_cover(article)
        cover_image = self.generate_cover_image(article)

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

        article , short = self.generate_full_article(topic)
        title = self.generate_title(short)
        description = self.generate_description(short)
        image_descriptions = self.generate_image_descriptions(short, count=20)  # Specify number of image descriptions here
        tags = self.generate_tags(short)
        cover = self.generate_cover(short)
        cover_image = self.generate_cover_image(short)

        # Limit the number of short phrases to 10 if more are present
        short_phrases = random.sample(image_descriptions, min(20, len(image_descriptions)))

        print(Fore.GREEN + "Long article and phrases generated successfully.")

        # Create the complete JSON response
        response_json = {
            "title": title,
            "description": description,
            "article": article.replace('\n', ''),
            "image_descriptions": image_descriptions,
            "tags": tags,
            "cover": cover,
            "cover_image": cover_image
        }

        # Save the JSON to a file
        self.save_json(file_path, response_json)

        return article.replace('\n', ''), short_phrases, title, description, tags, cover, cover_image


    