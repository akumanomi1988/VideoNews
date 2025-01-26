import re
import os
import uuid
import json
import random
from PIL import Image
import g4f
from colorama import Fore, Style, init
import time

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

    def generate_title(self, topic):
        title_prompt = (
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{'
            '  "title": ""  //Create a highly engaging and SEO-optimized YouTube title that incorporates relevant keywords to attract viewers and boost search rankings. The title should be a maximum of 80 characters, capitalize the most important words, and include relevant emojis.'
            '}'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
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
            '  "description": ""  // Write a brief, SEO-optimized video description in ' + self.language + ' that highlights key points while keeping the most intriguing details hidden. Use relevant keywords to enhance search visibility and create curiosity, enticing viewers to watch the video for the full story.'
            '}\n'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
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
                '  "article": "" // Write a factual and informative summary of the following news article in ' + self.language + ' with a serious and professional tone. Present the key details of the event clearly and concisely, ensuring the summary is around ' + str(length) + ' words long. Focus on delivering the facts objectively, without unnecessary opinions or emotions, maintaining a formal style typical of traditional news reports. Emphasize clarity and precision to ensure the narrative is engaging while adhering to the word limit'
                '}\n'
                'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
                'Ensure everything you say is truth. years, numbers and people.\n'
                f'Parameters:\n'
                f'- Language: [{self.language}]\n'
                f'- Article Text: [{article_text}]\n'
            )
        else:
            # If the topic is not a URL, proceed with the original prompt
            article_prompt = (
                'generate a response that must be a fully structured JSON object with the following format:\n'
                '{\n'
                '  "article": "" // Write a factual and informative news article in ' + self.language + ' with a serious and professional tone. Present the key details of the event clearly and concisely, ensuring the article is around ' + str(length) + ' words long. Focus on delivering the facts objectively, without unnecessary opinions or emotions, maintaining a formal style typical of traditional news reports. Emphasize clarity and precision to ensure the narrative is engaging while adhering to the word limit'
                '}\n'
                'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
                'Ensure everything you say is truth. years, numbers and people.\n'
                f'Parameters:\n'
                f'- Language: [{self.language}]\n'
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
            '  "article": "" // Write a brief, captivating introduction in ' + self.language + ' about the topic I provided. The introduction should be intriguing, hinting at something larger and more significant to come later. It should build anticipation while setting the scene in a serious and professional tone. The length of the introduction should be short, but impactful. Avoid giving away too much information upfront.\n'
            '}\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
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
            '  "article": "" // Write an in-depth and detailed development of the news article in ' + self.language + ' about the topic I provided. The content should focus on the central events, providing all relevant details and context. The tone should remain serious and objective, and the article should include an exploration of the main details, stakeholders, and any expert opinions. The development should not be too short but should fit within a single response, aiming for a detailed exploration of the topic.\n'
            '}\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
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
            '  "article": "" // Write a brief conclusion or resolution in ' + self.language + ' that sums up the key takeaways from the news article about the topic provided. The conclusion should give a final perspective on the issue, hinting at possible future implications or developments. It should be succinct yet thought-provoking, bringing the article to a close without adding new details.\n'
            '}\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
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
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "article": "" // Write a brief, captivating introduction in ' + self.language + ' about the following news article text. The introduction should be intriguing, hinting at something larger and more significant to come later. It should build anticipation while setting the scene in a serious and professional tone. The length of the introduction should be short, but impactful. Avoid giving away too much information upfront.\n'
            '}\n'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Article Text: [{article_text}]\n'
        )
        print(Fore.BLUE + f'Article: Introduction')
        intro_json = self._generate_json_element(intro_prompt)
        return intro_json.get('article', '')

    def generate_development_from_text(self, article_text):
        development_prompt = (
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "article": "" // Write an in-depth and detailed development of the following news article text in ' + self.language + '. The content should focus on the central events, providing all relevant details and context. The tone should remain serious and objective, and the article should include an exploration of the main details, stakeholders, and any expert opinions. The development should be around 500  words long, aiming for a detailed exploration of the topic.\n'
            '}\n'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Article Text: [{article_text}]\n'
        )
        print(Fore.BLUE + f'Article: Body')
        development_json = self._generate_json_element(development_prompt)
        return development_json.get('article', '')

    def generate_conclusion_from_text(self, article_text):
        conclusion_prompt = (
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "article": "" // Write a brief conclusion or resolution in ' + self.language + ' that sums up the key takeaways from the following news article text. The conclusion should give a final perspective on the issue, hinting at possible future implications or developments. It should be succinct yet thought-provoking, bringing the article to a close without adding new details.\n'
            '}\n'
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting.\n'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Article Text: [{article_text}]\n'
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
            'Your output must be a **properly formatted JSON object**, containing exactly 10 single-sentence image descriptions in a list, without any additional formatting, markdown, or commentary.'
            f'Parameters:\n'
            f'- Headline: [{topic}]'
        )
        print(Fore.BLUE + f'image descriptions')
        image_descriptions_json = self._generate_json_element(image_descriptions_prompt)
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
            'Your output must be a **properly formatted JSON object**, containing a single summary string, without any additional formatting, markdown, or commentary.'
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
            'Ensure the output is a **properly formatted JSON object**, without markdown or extra formatting. Use VidIQs insights on current trends, search volumes, and competitive score to select the best possible hashtags for reach and engagement.'
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'tags')
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
            'Your output must be a **properly formatted JSON object**, without markdown or extra formatting.'
            f'Parameters:\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'coverImage')
        cover_image_json = self._generate_json_element(cover_image_prompt)
        return cover_image_json.get('coverImage', '')


    def _generate_json_element(self, prompt_template):
        """
        Helper function to generate a single JSON element based on the provided prompt.
        """
        messages = [{"role": "system", "content": prompt_template}]
        
        retries = 10  # Número máximo de reintentos
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
                print(Fore.RED + response)

                if attempt < retries - 1:
                    time.sleep(1)  # Espera antes de reintentar
                else:
                    print(Fore.RED + "Max retries reached. Could not generate a valid JSON response.")
        
        return None
    
    def save_json(self, file_path, data):
        """Saves JSON data to a file."""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create the folder if it doesn't exist
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"JSON saved successfully at {file_path}")
        except Exception as e:
            print(f"Error saving JSON file: {e}")

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


    