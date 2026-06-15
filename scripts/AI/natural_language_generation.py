import re
import os
import uuid
import json
import random
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from colorama import Fore, Style, init

from scripts.DataFetcher.news_extractor import NewsExtractor, ArticleData
from scripts.utils.app_logger import trace

init(autoreset=True)


class LLMProvider:
    """Handles multi-provider LLM requests with fallback (Ollama -> Groq -> Azure placeholder)"""

    def __init__(self, providers=None):
        self.logger = logging.getLogger(__name__)
        self._clients = []
        if providers:
            for p in providers:
                self._add_provider(p)

    def _add_provider(self, config: dict):
        ptype = config.get("type", "").lower()
        model = config.get("model", "")
        try:
            if ptype == "ollama":
                import ollama as _ollama
                endpoint = config.get("endpoint", "http://localhost:11434")
                client = _ollama.Client(host=endpoint)
                self._clients.append(("ollama", model, client, config))
                self.logger.info("Ollama provider ready (%s @ %s)", model, endpoint)

            elif ptype == "groq":
                from groq import Groq as _Groq
                api_key = config.get("api_key", "")
                if not api_key:
                    self.logger.warning("Groq provider skipped: no api_key")
                    return
                client = _Groq(api_key=api_key)
                self._clients.append(("groq", model, client, config))
                self.logger.info("Groq provider ready (%s)", model)

            elif ptype == "azure":
                from openai import OpenAI as _OpenAI
                endpoint = config.get("endpoint", "")
                api_key = config.get("api_key", "")
                if not endpoint or not api_key:
                    self.logger.warning("Azure provider skipped: missing endpoint or api_key")
                    return
                client = _OpenAI(base_url=endpoint, api_key=api_key)
                self._clients.append(("azure", model, client, config))
                self.logger.info("Azure provider ready (%s @ %s)", model, endpoint)

            else:
                self.logger.warning("Unknown provider type: %s", ptype)

        except ImportError as e:
            self.logger.warning("Provider %s not available: %s", ptype, e)

    @property
    def available(self) -> bool:
        return len(self._clients) > 0

    def complete(self, prompt: str, **kwargs) -> str:
        """Try each provider in order until one succeeds."""
        last_error = None
        for provider_type, model, client, cfg in self._clients:
            try:
                timeout = cfg.get("timeout", 60)
                if provider_type == "ollama":
                    resp = client.chat(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        options={"num_predict": kwargs.get("max_tokens", 8192)},
                        format="json",
                        timeout=timeout,
                    )
                    return resp["message"]["content"]

                elif provider_type == "groq":
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=kwargs.get("temperature", 0.7),
                        max_tokens=kwargs.get("max_tokens", 8192),
                        response_format={"type": "json_object"},
                        timeout=timeout,
                    )
                    return resp.choices[0].message.content

                elif provider_type == "azure":
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=kwargs.get("temperature", 0.7),
                        max_tokens=kwargs.get("max_tokens", 8192),
                        timeout=timeout,
                    )
                    return resp.choices[0].message.content

            except Exception as e:
                last_error = e
                self.logger.warning("%s failed (model=%s): %s", provider_type, model, e)
                continue

        raise RuntimeError(f"All LLM providers failed: {last_error}")


class Chatbot:
    @trace()
    def __init__(self, language, model, providers=None):
        """
        Initializes the Chatbot with language, model, and optional multi-provider config.

        Parameters:
            language (str): The language in which to generate the articles.
            model (str): Legacy model name (kept for backward compat).
            providers (list): List of provider dicts. If None, defaults to Ollama.
        """
        self.language = language
        self.model = model
        self.logger = logging.getLogger(__name__)
        self.llm = LLMProvider(providers or [
            {"type": "ollama", "model": "nemotron-3-super:cloud"},
        ])
        self.standard_rules = ('Your output must be a valid JSON object with double quotes for both keys and string values. Ensure proper nesting, avoid trailing commas, and escape special characters when necessary.'
                               'Ensure everything you say is factual and accurate, including years, numbers, and names.'
                               )
        self.ideology = 'Advocating for the transformation of existing structures toward a more just and equitable system'
        self.tone = 'Adapt the tone of the narration based on the nature of the news: if it is serious or tragic, use a somber, reflective style with a dramatic touch to heighten the impact. If the news is light or has humorous potential, adopt a colloquial, street-style, or even profane tone to make it more entertaining and relatable. For topics involving elites, scandals, or high-society situations, use a sarcastic or posh tone to emphasize the irony. If the news carries a mysterious vibe, employ a conspiratorial style with subtle insinuations and unexpected twists to sow controlled doubts.'
        self.numbers_as_words = (
            "IMPORTANT: All numbers, quantities, percentages, dates, and statistics "
            "MUST be written out fully as words in the spoken language. "
            "For example: write 'tres mil' instead of '3000', "
            "'veintiocho por ciento' instead of '28%', "
            "'dos mil veinticuatro' instead of '2024', "
            "'ciento treinta y cinco millones' instead of '135M'. "
            "This is critical because the text is converted to speech and "
            "digits sound unnatural when read aloud."
        )
        self.hook_rules = (
            "The narration MUST open with a direct hook addressed to the viewer "
            "using the second person ('tú' / 'te') to grab attention immediately. "
            "Examples of hooks: '¿Sabías que...?', 'Esto te va a enfadar...', "
            "'No te imaginas lo que pasó con...', 'Si creías que... te equivocas.', "
            "'Quédate hasta el final porque esto te interesa.', "
            "'Hay algo que no te están contando sobre...'. "
            "The tone must be controversial, provocative, and challenge common beliefs. "
            "Question power structures, expose hypocrisy, and present unexpected angles "
            "that make the viewer stop scrolling and watch the entire video. "
            "Every sentence should build tension or curiosity. "
            "Avoid bland or neutral statements — aim for opinions that spark debate."
        )
        self.spanish_spain_rules = (
            "IMPORTANTE: Escribe en español de España (no de Latinoamérica). "
            "Usa vocabulario, expresiones y pronunciación propias de España. "
            "Ejemplos: 'coche' (no 'carro'/'auto'), 'ordenador' (no 'computadora'), "
            "'móvil' (no 'celular'), 'vale' (no 'ok'), 'tío/tía' (no 'wey/güey'), "
            "'joder' (no 'carajo'), 'guay' (no 'chido/bacán'), "
            "'echar un vistazo' (no 'dar un vistazo'). "
            "Usa 'vosotros' para la segunda persona del plural. "
            "La redacción debe sonar natural para un hablante nativo de España. "
        )
        self.cta_rules = (
            "IMPORTANTE: Incluye obligatoriamente llamadas a la acción (CTA) naturales "
            "a lo largo de la narración y sobre todo al final. Ejemplos de CTAs: "
            "'Si te ha gustado, dale a like y suscríbete al canal para no perderte nada.' "
            "'No olvides compartir este vídeo con tus amigos.' "
            "'Activa la campanita para enterarte de todas las novedades.' "
            "'Déjame en los comentarios qué opinas sobre este tema.' "
            "'Suscríbete para más contenido como este.' "
            "'Compártelo si crees que más gente debería saber esto.' "
        )

    @trace()
    def generate_title(self, topic):
        title_prompt = (
            'Generate a response that must be a fully structured JSON object with the following format:\n'
            '{'
            '  "title": ""  // Create a highly engaging and SEO-optimized YouTube news title '
            'that incorporates relevant keywords to attract viewers and boost search rankings. '
            'The title should be highly clickable, a maximum of 80 characters, avoid URLs, capitalize the most important words, '
            'and include relevant emojis to increase engagement.'
            ' It should clearly indicate that the content is news-related, '
            'either by specifying the topic (e.g., Economy, Politics, Tech) or using words like "Breaking," "Latest," or "Report".'
            '}'
            f'{self.standard_rules}'
            f'Parameters:\n'
            f'- **Language of the title must be: [{self.language}]**\n'
            f'- Headline: [{topic}]\n'
        )

        print(Fore.BLUE + 'Generating Title...')
        title_json = self._generate_json_element(title_prompt)
        return title_json.get('title', '')
    
    @trace()
    def generate_description(self, topic):
        description_prompt = (
            'You are a creative and engaging news writer. Based on the headline and language I provide, '
            'generate a response that must be a fully structured JSON object with the following format:\n'
            '{\n'
            '  "description": ""  // Write a brief, SEO-optimized video description in ' + self.language + ' that highlights key points while keeping the most intriguing details hidden.'
                                     ' Maximum 1000 characters. Use relevant keywords to enhance search visibility and create curiosity, enticing viewers to watch the video for the full story.'
            '}\n'
            f'{self.standard_rules}'
            f'Parameters:\n'
            f'- **Languageof the article must be: [{self.language}]**\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'description')
        description_json = self._generate_json_element(description_prompt)
        return description_json.get('description', '')

    @trace()
    def generate_short_article(self, topic, source="", length=50, accept_labels =False):
        """
        Generates a short article based on the given topic.
        """
        print(Fore.BLUE + 'Generating YouTube narration')
        source_line = f'The news comes from {source}.' if source else ''
        narration_prompt = (
            "Generate a fully structured JSON object with the following format:\n"
            "{\n"
            '  "article": ""  // Write a fast-paced, news-bulletin style YouTube Shorts narration in ' + self.language + ' about the topic.\n'
            "}\n\n"
            "STRUCTURE (strict order):\n"
            "1. HOOK (first 5-8 seconds — ~40-50 words): Open with a direct spoken hook addressed to the viewer.\n"
            '   Examples: "¿Te has enterado de lo que ha pasado con...?" / "Pues resulta que..." / "Acabo de leer en [actual news source] que..."\n'
            f"   {source_line}\n"
            "   Mention specifically where you read/heard this to make it organic.\n"
            "2. EXPLAIN (main body — ~70-100 words): Actually explain WHAT the news is about.\n"
            "   Give key facts: what happened, who is involved, why it matters, contexto relevante.\n"
            "   Desarrolla la noticia con detalles concretos, datos y fuentes.\n"
            "3. CTA natural a mitad del vídeo — ~15-20 words): "
            "Haz una pausa natural para pedir like o suscripción de forma orgánica.\n"
            "   Ejemplo: 'Si te está gustando el vídeo, no te olvides de darle a like y suscribirte.'\n"
            "4. CLOSE (final ~20-30 words): Cierre con resumen impactante y CTA final.\n"
            "   Incluye: resumen provocador + llamado a la acción final.\n"
            "   Ejemplos: 'Esto apenas comienza, así que ya sabes: like, suscríbete y comparte.' "
            "/ 'Y tú, ¿qué opinas? Te leo en los comentarios.'\n\n"
            f"5. {self.hook_rules}\n"
            f"6. {self.numbers_as_words}\n"
            f"7. {self.spanish_spain_rules}\n"
            f"8. {self.cta_rules}\n"
            "9. The TOTAL article must be between 180 and 250 words — desarrolla bien la noticia pero sin relleno.\n"
            "10. Write conversationally, as if telling a friend something shocking you just read.\n"
            "11. La narrativa debe tener ritmo: sube y baja la intensidad para mantener la atención.\n"
            f"Parameters:\n"
            f"- Language: [{self.language}]\n"
            f"- Topic: [{topic}]\n"
            f"- Tone: fast news bulletin, urgent but not alarmist.\n"
            f"{self.standard_rules}\n"
        )
        narration_json = self._generate_json_element(narration_prompt)
        return narration_json.get('article', '')

    @trace()
    def generate_full_article(self, topic, length=150):
        """
        Generates a full-length article and a short summary based on the given topic.
        Returns a tuple of (full_article, short_summary).
        """
        print(Fore.BLUE + 'Generating full-length YouTube narration')
        full_prompt = (
            "Generate a fully structured JSON object with the following format:\n"
            "{\n"
            '  "full_article": "",  // Write a detailed, in-depth news narration in ' + self.language + ' about the topic. Cover key details, background context, and implications.'
            '  "short_summary": ""  // Write a brief 3-4 sentence summary of the key points.'
            "}\n\n"
            "Instructions:\n"
            "1. The full article must be comprehensive, well-structured, and suitable for a long-form video of 3-5 minutes.\n"
            "2. STRUCTURE (strict order):\n"
            "   a) INTRO HOOK (~60-80 words): Gancho inicial directo al espectador que enganche desde el primer segundo.\n"
            "      Presenta el tema de forma provocadora y promete revelar información clave.\n"
            "   b) CONTEXTO (~80-100 words): Explica los antecedentes necesarios para entender la noticia.\n"
            "      Por qué está pasando, qué llevó a esta situación, quiénes son los actores principales.\n"
            "   c) DESARROLLO (~150-200 words): El núcleo de la noticia con datos, cifras, declaraciones.\n"
            "      Desglosa la información de forma clara pero impactante. Incluye detalles exclusivos.\n"
            "   d) IMPLICACIONES (~60-80 words): Qué significa esto para el futuro, quién sale ganando y perdiendo.\n"
            "   e) CIERRE + CTA (~40-50 words): Resumen provocador + llamado a la acción (like, suscríbete, comentario).\n"
            "3. Incluye una CTA natural a mitad del vídeo y otra al final, obligatoriamente.\n"
            "4. The total article should be between 500 and 700 words — desarrollo profundo pero dinámico.\n"
            "5. Escribe con ritmo narrativo: alterna frases cortas impactantes con explicaciones más detalladas.\n"
            "6. Incluye preguntas retóricas al espectador para mantener su atención.\n"
            "7. La short_summary debe capturar la esencia en 3-4 frases impactantes.\n"
            f"8. {self.hook_rules}\n"
            f"9. {self.numbers_as_words}\n"
            f"10. {self.spanish_spain_rules}\n"
            f"11. {self.cta_rules}\n"
            f"Parameters:\n"
            f"- Language: [{self.language}]\n"
            f"- Topic: [{topic}]\n"
            f"- Tone: periodístico, provocador, con ritmo narrativo.\n"
            f"{self.standard_rules}\n"
        )
        print(Fore.BLUE + 'Full article')
        article_json = self._generate_json_element(full_prompt)
        return article_json.get('full_article', ''), article_json.get('short_summary', '')
    
    def generate_conclusion_from_text(self, article_text):
        conclusion_prompt = (
            "Generate a fully structured JSON object with the following format:\n"
            "{\n"
            '  "article": "" // Write a 50-100 word conclusion that offers a personal opinion on the issue from a liberal-progressive perspective.\n'
            "}\n\n"
            "Instructions:\n"
            "1. The conclusion must be a personal perspective; begin with a phrase such as 'In my view...' or its equivalent to clearly indicate that it is your opinion.\n"
            "2. Highlight systemic injustices and question power structures while hinting at future implications.\n"
            "3. Conclude with one final, thought-provoking rhetorical question that implies deeper systemic issues.\n"
            "4. Be provocative and controversial — challenge the reader's assumptions and leave them thinking.\n\n"
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

    def generate_image_descriptions(self, text, count=10):
        """
        Genera descripciones de imágenes basadas en un texto narrativo.
        
        Args:
            text (str): Texto narrativo del que extraer las imágenes (noticia, etc.).
            count (int): Número de descripciones de imágenes a generar.
            
        Returns:
            list: Lista de descripciones breves y concretas.
        """
        image_descriptions_prompt = (
            'You are a visual storyteller specializing in news content. Based on the given news narrative, '
            'extract the most relevant visual elements directly related to the story. '
            'Each description MUST be SPECIFICALLY tied to the actual news content — '
            'people mentioned, locations described, events referenced, objects of relevance. '
            'Generate a structured JSON object in the following format:\n'
            '{\n'
            '  "image_descriptions": ["", "", "..."]  // Generate ' + str(count) + ' image descriptions. '
            'Each description should be detailed and concrete, describing what is seen in the image as if it were a real photograph. '
            'CRITICAL: Tie every description to specific elements from the news story. '
            'Avoid generic phrases like "a person" — instead say "a Spanish businessman in a suit" or '
            '"a scientist in a lab coat holding a vaccine vial" based on what the article says. '
            'Include relevant settings from the story (e.g., "outside the European Parliament in Brussels", '
            '"in an office in Madrid", "in the middle of a flooded street"). '
            'Each description must be usable as a text-to-image prompt for AI image generation.\n'
            '}\n\n'
            'Parameters:\n'
            '- News narrative text: """' + text + '"""'
        )

        print(Fore.BLUE + 'Generating image descriptions...')
        image_descriptions_json = self._generate_json_element(image_descriptions_prompt)
        return image_descriptions_json.get('image_descriptions', [])

    def generate_scene_descriptions(self, text, count=10):
        """Generate scene/visual descriptions from narrative text for media prompts."""
        prompt = (
            'You are a visual director for news videos. Based on the news narrative text, '
            'extract the most relevant visual scenes that are DIRECTLY related to the story. '
            'Each scene must be SPECIFIC to the news content — not generic stock footage prompts. '
            'Generate a structured JSON object:\n'
            '{\n'
            '  "scenes": ["", "", "..."]  // Generate ' + str(count) + ' detailed visual scene descriptions '
            'suitable for searching stock video footage. Each description should be a concrete visual scene '
            'tied to elements from the news story (e.g., if the story is about Amazon deforestation, '
            'describe "aerial view of burning Amazon rainforest with smoke plumes rising" instead of '
            'just "a forest"). Include specific people, locations, objects, and actions from the story.\n'
            '}\n\n'
            'Parameters:\n'
            '- News narrative text: """' + text + '"""'
        )
        print(Fore.BLUE + 'Generating scene descriptions...')
        scenes_json = self._generate_json_element(prompt)
        return scenes_json.get('scenes', [])

    def summarize_news_from_url(self, url):
        extractor = NewsExtractor()
        article = extractor.extract_article(url)
        
        if article is None:
            return []

        summary_prompt = (
            'You are a creative writer. Based on the article text I provide, generate a response that must be a fully structured JSON object with the following format: '
            '{'
            '  "summary": "" // Write a brief summary of the news article in English, highlighting the main points and key details. The summary should be concise and informative, providing a clear overview of the article\'s content.'
            '}'
            f"{self.standard_rules}\n"
            f'Parameters:\n'
            f'- Article Text: [{article.text}]'
        )
        print(Fore.BLUE + f'Summary')
        summary_json = self._generate_json_element(summary_prompt)
        return summary_json.get('summary', '')

    def generate_tags(self, topic):
        tags_prompt = (
            'generate a response that must be a fully structured JSON object with the following format:'
            '{'
            '  "tags": ["","",""...] // Provide a list of exactly 20 of the most effective and widely used tags for this topic in English, optimized for YouTube SEO. Focus on including both single words and multi-word phrases that are highly relevant. Do NOT use the "#" symbol.'
            '}'
            f"{self.standard_rules}\n"
            f'Parameters:\n'
            f'- Language: [{self.language}]\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'tags')
        tags_json = self._generate_json_element(tags_prompt)
        return tags_json.get('tags', [])

    def generate_cover(self, topic):
        cover_prompt = (
            "You are an expert headline writer with a focus on clarity, precision, and SEO for news covers. "
            "Your task is to create a **very brief (max 5-6 words), clear, and informative** phrase "
            "based on the provided headline and language. Avoid generic or vague expressions. "
            "Prioritize delivering **the core information or main impact** of the topic without exaggeration.\n"
            "The output must be a **fully structured JSON object** in the following format:\n"
            "{\n"
            '  "cover": ""  // A specific, concise, and descriptive phrase in ' + self.language + ' that captures the key subject or event.\n'
            "}\n"
            f"Parameters:\n"
            f"- Language: [{self.language}]\n"
            f"- Headline: [{topic}]\n"
            "Avoid filler words, drama, or ambiguity. Focus on **accuracy and direct value**."
        )

        print(Fore.BLUE + f'cover')
        cover_json = self._generate_json_element(cover_prompt)
        return cover_json.get('cover', '')
    
    def enhance_prompt(self, topic):
        cover_prompt = (
            "You are a professional clickbait headline writer specializing in news covers. "
            "Your task is to generate a **highly engaging, curiosity-inducing, and dramatic** short phrase, "
            "based on the headline and language provided. The phrase should feel like a **movie title** and be **no longer than 5 words**.\n"
            "The output must be a **fully structured JSON object** in the following format:\n"
            "{\n"
            '  "cover": ""  // A gripping, clickbait phrase in ' + self.language + ', focusing on the main person or impact of the event.\n'
            "}\n"
            f"Parameters:\n"
            f"- Language: [{self.language}]\n"
            f"- Headline: [{topic}]\n"
            "Make it **bold, shocking, and impossible to ignore**."
        )

        print(Fore.BLUE + f'cover')
        cover_json = self._generate_json_element(cover_prompt)
        return cover_json.get('cover', '')

    def generate_cover_image(self, topic):
        cover_image_prompt = (
            'Describe an image for a YouTube thumbnail cover that includes all key elements from the news '
            'in a single, cohesive description string perfect for AI image generation:\n'
            '{\n'
            '  "coverImage": "" // Describe in english, the scene for the cover image. CRITICAL: Include the main person '
            '(a man or woman conveying emotions relevant to the news topic, with specific facial expression), '
            'a background setting DIRECTLY related to the news topic, and visual elements that tell the story '
            'at a glance. Make it dramatic, visually striking, and newsworthy. '
            'Avoid generic backgrounds — tie it to the specific news location or context.\n'
            '}\n'
            f"{self.standard_rules}\n"
            f'Parameters:\n'
            f'- Headline: [{topic}]\n'
        )
        print(Fore.BLUE + f'coverImage')
        cover_image_json = self._generate_json_element(cover_image_prompt)
        return cover_image_json.get('coverImage', '')


    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract a JSON object from text, trying multiple strategies."""
        text = text.strip()
        # Strategy 1: try to parse the whole response as JSON
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # Strategy 2: find outermost { ... } skipping braces inside strings
        start = text.find('{')
        if start != -1:
            depth = 0
            in_string = False
            escape = False
            for i in range(start, len(text)):
                ch = text[i]
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]

        # Strategy 3: find outermost [ ... ] skipping brackets inside strings
        start = text.find('[')
        if start != -1:
            depth = 0
            in_string = False
            escape = False
            for i in range(start, len(text)):
                ch = text[i]
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]

        return None

    def _generate_json_element(self, prompt_template, clean: bool = True):
        """
        Helper function to generate a single JSON element based on the provided prompt.
        Tries each LLM provider (Ollama -> Groq -> Azure) until one succeeds.
        """
        if not self.llm.available:
            self.logger.error("No LLM providers available.")
            return None

        retries = 2
        for attempt in range(retries):
            try:
                response = self.llm.complete(prompt_template, max_tokens=8192)

                content = self._extract_json(response)
                if content is None:
                    self.logger.warning("No valid JSON object found in response")
                    raise json.JSONDecodeError("No JSON object found", response, 0)

                if clean:
                    content = self.clean_and_load_json(content)
                    return content
                return json.loads(content)

            except (json.JSONDecodeError, ValueError) as e:
                snippet = response[:200] if attempt < retries - 1 else ""
                self.logger.warning("JSON error (attempt %d/%d): %s", attempt + 1, retries, e)
                if snippet:
                    self.logger.debug("Response: %s...", snippet)

            except Exception as e:
                self.logger.error("LLM error (attempt %d/%d): %s", attempt + 1, retries, e)

            if attempt < retries - 1:
                time.sleep(2)

        self.logger.error("Max retries reached. Could not generate valid JSON.")
        return {}

    def clean_and_load_json(self, json_string: str):
        """
        Cleans a given JSON string to remove unwanted characters and make it valid for parsing.
        Accepts both double-quoted and single-quoted string values (via ast.literal_eval).
        
        :param json_string: A string containing JSON data.
        :return: A Python dictionary parsed from the cleaned JSON string.
        :raises ValueError: If the cleaned string is still not valid JSON.
        """
        import ast
        try:
            # Safe print - handle Unicode errors on Windows console
            try:
                print(Fore.BLUE, json_string)
            except (UnicodeEncodeError, UnicodeError):
                print(Fore.BLUE + "[JSON output suppressed - Unicode encoding issue]")

            json_string = re.sub(r'[\x00-\x1F\x7F]', '', json_string)
            json_string = json_string.strip()
            json_string = re.sub(r',\s*([}\]])', r'\1', json_string)
            json_string = re.sub(r'(?<=\{|,)(\s*)([a-zA-Z0-9_]+)(\s*):', r'"\2":', json_string)

            # Try ast.literal_eval first (handles both ' and " strings, arrays, nested)
            try:
                json_dict = ast.literal_eval(json_string)
                return json_dict
            except (ValueError, SyntaxError):
                pass

            # Fallback to json.loads for strict JSON
            json_dict = json.loads(json_string)
            return json_dict
        except (json.JSONDecodeError, ValueError) as e:
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

    @trace()
    def generate_article_and_phrases_short(self, topic):
        """
        Generates an article and related phrases based on the provided topic.

        Parameters:
            topic (str or dict): The topic for which the article and phrases should be generated.
                                 Can be a string (title only) or dict with 'title' and optional 'source'.

        Returns:
            tuple: A tuple containing the generated article, short phrases, title, description, tags, cover, and cover image.
        """
        if isinstance(topic, dict):
            topic_title = topic.get('title', '')
            topic_source = topic.get('source', '')
        else:
            topic_title = str(topic)
            topic_source = ''
        print(Fore.CYAN + f"Generating article and phrases for topic: {topic_title}")

        # Generate a unique GUID
        file_guid = str(uuid.uuid4())
        folder_path = '.temp'
        file_path = os.path.join(folder_path, f'{file_guid}.json')

        article = self.generate_short_article(topic_title, source=topic_source)

        # Parallelize independent LLM calls
        results = {}
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_map = {
                executor.submit(self.generate_title, article): 'title',
                executor.submit(self.generate_description, article): 'description',
                executor.submit(self.generate_image_descriptions, article, 20): 'image_descriptions',
                executor.submit(self.generate_tags, article): 'tags',
                executor.submit(self.generate_cover, article): 'cover',
                executor.submit(self.generate_cover_image, article): 'cover_image',
            }
            for future in as_completed(future_map):
                key = future_map[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    print(Fore.RED + f"Error generating {key}: {e}")
                    results[key] = '' if key != 'image_descriptions' else []

        title = results.get('title', '')
        description = results.get('description', '')
        image_descriptions = results.get('image_descriptions', [])
        tags = results.get('tags', [])
        cover = results.get('cover', '')
        cover_image = results.get('cover_image', '')

        # Limit the number of short phrases to 10 if more are present
        short_phrases = random.sample(image_descriptions, min(20, len(image_descriptions)))

        print(Fore.GREEN + "Article and phrases generated successfully.")

        # Create the complete JSON response
        response_json = {
            "title": title,
            "description": description,
            "article": article,
            "image_descriptions": image_descriptions,
            "tags": tags,
            "cover": cover,
            "cover_image": cover_image,
            "source": topic_source
        }

        # Save the JSON to a file
        self.save_json(file_path, response_json)

        return article, short_phrases, title, description, tags, cover, cover_image
    
    @trace()
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

        article, short = self.generate_full_article(topic)

        # Parallelize independent LLM calls
        results = {}
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_map = {
                executor.submit(self.generate_title, short): 'title',
                executor.submit(self.generate_description, short): 'description',
                executor.submit(self.generate_image_descriptions, short, 40): 'image_descriptions',
                executor.submit(self.generate_tags, short): 'tags',
                executor.submit(self.generate_cover, short): 'cover',
                executor.submit(self.generate_cover_image, short): 'cover_image',
            }
            for future in as_completed(future_map):
                key = future_map[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    print(Fore.RED + f"Error generating {key}: {e}")
                    results[key] = '' if key != 'image_descriptions' else []

        title = results.get('title', '')
        description = results.get('description', '')
        image_descriptions = results.get('image_descriptions', [])
        tags = results.get('tags', [])
        cover = results.get('cover', '')
        cover_image = results.get('cover_image', '')

        # Limit the number of short phrases to 10 if more are present
        short_phrases = random.sample(image_descriptions, min(40, len(image_descriptions)))

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


    