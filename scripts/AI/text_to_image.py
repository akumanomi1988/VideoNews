from time import sleep
import uuid
from enum import Enum
from huggingface_hub import InferenceClient
import os
from colorama import Fore, init
import random
from g4f.client import Client
import requests

# Initialize colorama
init(autoreset=True)

class AspectRatio(Enum):
    LANDSCAPE = (1920, 1080)
    PORTRAIT = (1080, 1920)

class StylePreset(Enum):
    NONE = ""
    VINTAGE = "NO TEXT. Sepia tones with retro cars and vintage architecture, enhanced with a grainy effect, shot with a 35mm film camera for an authentic nostalgic feel."
    MINIMALIST = "NO TEXT. Clean and uncluttered design featuring geometric forms and soft pastel tones, illuminated by high-key lighting in a studio shot that emphasizes simplicity."
    NATURE_SCENE = "A breathtaking landscape showcasing majestic mountains and serene lakes, captured with a DSLR using natural lighting for a wide dynamic range that highlights the beauty of nature."
    ANIME = "NO TEXT. Inspired by Studio Ghibli, featuring vibrant colors and expressive characters, with cell shading and dynamic perspectives that bring the scene to life."
    COMIC_STORYTELLER = "NO TEXT. Bold lines and vibrant panels create a captivating comic book aesthetic, with speech bubbles and close-ups in a medium shot that tell a dynamic visual story."
    PHOTOREALISTIC = "NO TEXT. Hyper-realistic portrayal captured on a full-frame DSLR, emphasizing crisp details and balanced lighting to create an image that feels lifelike."
    IMPRESSIONIST = "NO TEXT. Soft brushstrokes and muted colors portray a wide landscape, capturing the impression of natural light to evoke emotion and tranquility."
    SURREALIST = "NO TEXT. Dreamlike elements with warped shapes and juxtaposed objects, illuminated by ethereal light and captured with a macro lens to enhance surreal qualities."
    ABSTRACT = "NO TEXT. Non-representational imagery featuring vibrant splashes of color and sharp contrasts, captured in close-up macro shots to create visual intrigue."
    REALISM = "NO TEXT. Faithful depiction of scenes with natural colors, medium shot, and balanced light that emphasize fine details for an authentic look."
    YOUTUBE_THUMBNAIL = "An impressively seductive woman with a surprised expression and a slight smile gazes directly at the camera, her enchanting eyes drawing the viewer in. The shot is a half-height close-up, capturing her captivating features and alluring presence. The location is a random, unspecified backdrop that does not distract from her beauty, allowing her charm to take center stage. The focus is on her expression, highlighting the playful yet enticing allure she exudes"

class FluxImageGenerator:
    def __init__(self, token=None, output_dir="output_images", model="black-forest-labs/FLUX.1-schnell"):
        self.hf_client = InferenceClient(token=token) if token else None
        self.g4f_client = Client()
        self.model = model
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    @staticmethod
    def getImagePresets():
        return {preset.name: preset.value for preset in StylePreset}
    
    def generate_image(self, custom_prompt, style_preset: StylePreset, aspect_ratio: AspectRatio):
        # Construir el prompt final
        if style_preset == StylePreset.YOUTUBE_THUMBNAIL:
            final_prompt = style_preset.value
        elif style_preset == StylePreset.NONE:
            final_prompt = custom_prompt
        else:
            final_prompt = f"{custom_prompt}. with this style -> {style_preset.value}"

        width, height = aspect_ratio.value
        print(Fore.BLUE + f"Image prompt\t ::-> {final_prompt}")

        # Sistema de reintentos con fallback
        while True:
            # Intentar con Hugging Face 3 veces
            for _ in range(3):
                image_path = self._generate_with_huggingface(final_prompt, width, height)
                if image_path:
                    return image_path
                sleep(10)  # Esperar entre intentos

            # Fallback a g4f si Hugging Face falla
            image_path = self._generate_with_g4f(final_prompt)
            if image_path:
                return image_path
            sleep(10)  # Esperar antes de reiniciar el ciclo

    def _generate_with_huggingface(self, prompt, width, height):
        if not self.hf_client:
            return None
            
        try:
            image = self.hf_client.text_to_image(
                prompt,
                model=self.model,
                height=height,
                width=width,
                seed=random.randint(0, 2**32 - 1)
            )
            
            output_path = os.path.join(self.output_dir, f"hf_{uuid.uuid4()}.png")
            image.save(output_path)
            print(Fore.GREEN + f"Hugging Face image saved to {output_path}")
            return output_path
        except Exception as e:
            print(Fore.RED + f"Hugging Face Error: {str(e)}")
            return None

    def _generate_with_g4f(self, prompt):
        try:
            response = self.g4f_client.images.generate(
                model="flux",
                prompt=prompt,
                response_format="url"
            )
            
            if not response.data:
                return None

            image_url = response.data[0].url
            image_data = requests.get(image_url).content
            
            output_path = os.path.join(self.output_dir, f"g4f_{uuid.uuid4()}.png")
            with open(output_path, 'wb') as f:
                f.write(image_data)
                
            print(Fore.GREEN + f"g4f image saved to {output_path}")
            return output_path
        except Exception as e:
            print(Fore.RED + f"g4f Error: {str(e)}")
            return None