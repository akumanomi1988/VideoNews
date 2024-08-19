import g4f
import random
import uuid
import configparser

def generate_article_and_phrases(topic):
    language = load_language()
    prompt = f"Generate a 200-word article about {topic} in {language}."
    api_key = load_g4f_api_key()
    
    article = g4f.GPT(api_key).generate(prompt)
    
    # Splitting article into 10 short phrases
    sentences = article.split('. ')
    short_phrases = random.sample(sentences, min(10, len(sentences)))
    
    return article, short_phrases

def load_g4f_api_key():
    # Loading GPT API key from config file
    config = configparser.ConfigParser()
    config.read('settings.config')
    return config['GPTConfig']['API_KEY']

def load_language():
    config = configparser.ConfigParser()
    config.read('settings.config')
    return config['LanguageSettings']['LANGUAGE']