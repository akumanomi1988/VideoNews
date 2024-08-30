import os
import json
import random
import requests
from PIL import Image
from io import BytesIO
import g4f
from g4f.client import Client
from colorama import Fore, Style, init

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

    def generate_article_and_phrases(self, topic):
        """
        Generates an article and related phrases based on the provided topic.

        Parameters:
            topic (str): The topic for which the article and phrases should be generated.

        Returns:
            tuple: A tuple containing the generated article, short phrases, title, description, and tags.
        """
        print(Fore.CYAN + f"Generating article and phrases for topic: {topic}")
        
        # Construct the prompt for article generation
        prompt_template = (
            f"You are an expert sensationalist news writer. Based on the headline I will provide and the language I will specify, "
            f"generate a result in JSON format with the following structure:\n\n"
            f"{{\n"
            f'  "title": "{topic}",  // The headline of the news that I will provide, which I want you to return translated\n'
            f'  "description": "",  // A brief description of the headline (summary).\n'
            f'  "article": "",  // A full 100-word article written in an extremely sensationalist tone, with narrative twists and dramatic elements that keep the reader intrigued until the end.\n'
            f'  "image_descriptions": [  // A list of 25 brief and specific descriptions that can be used to find related images on Pexels.\n'
            f'    "description1",\n'
            f'    "description2",\n'
            f'    ...\n'
            f'  ],\n'
            f'  "tags": [  // A list of 10 keywords to use for the video\'s SEO'
            f'    "tag1",\n'
            f'    "Tag2",\n'
            f'    ...\n'
            f'  ]\n'
            f'}}\n\n'
            f"Parameters:\n"
            f'- Language: "{self.language}"\n'
            f'- Headline: "{topic}"\n\n'
            f"Additional Instructions:\n"
            f"- The content language must be the one specified in the 'language' parameter.\n"
            f"- The JSON must be fully structured and correctly formatted, with no exceptions. NOT WITHIN A MARKDOWN CODE BLOCK."
            f"- If you fail to meet any of these conditions, YOU WILL BE FIRED."
        )

        messages = [{"role": "system", "content": prompt_template}]
        
        # Use g4f to create a chat completion using the specified model and constructed message
        response = g4f.ChatCompletion.create(model=self.model, messages=messages)
        # Get the generated content from the response
        content = response.strip().replace('```json', '').replace('```', '')
        try:
            # Parse the content as JSON
            content = content.replace('\n', '').replace('\r', '')
            response_json = json.loads(content)
            
            # Retrieve the article and image descriptions
            article = response_json.get('article', '')
            image_descriptions = response_json.get('image_descriptions', [])
            description = response_json.get('description', '')
            title = response_json.get('title', '')
            tags = response_json.get('tags', [])
            
            # Limit the number of short phrases to 10 if there are more
            short_phrases = random.sample(image_descriptions, min(10, len(image_descriptions)))

            print(Fore.GREEN + "Article and phrases generated successfully.")
            return article, short_phrases, title, description, tags

        except json.JSONDecodeError:
            # Handle errors if the content is not valid JSON
            print(Fore.RED + "Error: The response is not in valid JSON format.")
            print(Fore.RED + content)
            return None, [], "", "", []

    def generate_image(self, prompt, output_path):
        """
        Generates an image based on the provided prompt and saves it to the specified path.

        Parameters:
            prompt (str): The prompt for the image generation.
            output_path (str): The path where the generated image will be saved.
        """
        print(Fore.CYAN + f"Generating image for prompt: {prompt}")
        
        client = Client()
        response = client.images.generate(
            model=self.image_model,
            prompt=prompt,
            size="1024x1024"  # Adjust size if needed
        )

        image_url = response.data[0].url
        
        try:
            # Fetch the image from the URL
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            
            # Open the image and save it as JPEG
            image = Image.open(BytesIO(image_response.content))
            image = image.convert('RGB')
            image.save(output_path, 'JPEG')
            print(Fore.GREEN + f"Image saved to {output_path}")
        
        except requests.exceptions.RequestException as e:
            print(Fore.RED + f"Failed to fetch image from URL '{image_url}'. Error: {str(e)}")
        except OSError as e:
            print(Fore.RED + f"Failed to save image to '{output_path}'. Error: {str(e)}")
