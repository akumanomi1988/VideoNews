from time import sleep, time
import uuid
import base64
from enum import Enum
from huggingface_hub import InferenceClient
import os
from colorama import Fore, init
import random
import requests

init(autoreset=True)


class AspectRatio(Enum):
    LANDSCAPE = (1024, 768)
    PORTRAIT = (768, 1024)


class StylePreset(Enum):
    NONE = "NO TEXT."
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
    YOUTUBE_THUMBNAIL = "Image without text. High-contrast, vibrant colors with a clean and focused composition. Sharp HD quality, ensuring crystal-clear details. A strikingly seductive woman with an expressive, engaging gaze, her slightly parted lips hinting at playful intrigue. Her captivating eyes lock onto the viewer, radiating confidence and allure. The shot is a half-height close-up, perfectly framing her elegant features. The background is softly blurred and neutral, ensuring no distractions while emphasizing her charm. Balanced lighting enhances her beauty, creating depth and warmth. The overall aesthetic is eye-catching, sophisticated, and irresistibly captivating."
    DISNEY = "NO TEXT. Whimsical, colorful characters with large expressive eyes and soft, rounded features. Magical backgrounds, fairy-tale atmosphere, and a warm, inviting color palette inspired by classic Disney animation."
    PIXAR = "NO TEXT. 3D animated style with vibrant colors, exaggerated expressions, and cinematic lighting. Playful and heartwarming, with a focus on storytelling and emotional depth, reminiscent of Pixar movies."
    KIDS_BOOK = "NO TEXT. Simple, playful illustrations with bold outlines and bright, cheerful colors. Friendly characters and imaginative scenes, as seen in classic children's picture books."
    CARTOON = "NO TEXT. Exaggerated, humorous characters with bold lines and flat colors. Dynamic poses and expressive faces, in the style of Saturday morning cartoons."
    PIXELART = "NO TEXT. Retro pixel art style with blocky, low-resolution graphics and a limited color palette. Nostalgic and playful, reminiscent of classic 8-bit and 16-bit video games."
    LEGO = "NO TEXT. 3D render of scenes and characters built entirely from LEGO bricks, with glossy plastic textures and playful construction."
    PAPER_CUTOUT = "NO TEXT. Collage style using layered paper cutouts, with visible textures and shadows, creating a handcrafted, tactile look."
    CLAYMATION = "NO TEXT. Stop-motion clay animation style, with soft, rounded shapes and visible fingerprints, giving a handmade, playful feel."
    STORYBOOK_WATERCOLOR = "NO TEXT. Gentle watercolor washes and soft pencil outlines, evoking the charm of classic children's storybook illustrations."
    CHIBI = "NO TEXT. Super-deformed, cute characters with oversized heads and eyes, tiny bodies, and bright, pastel colors, inspired by Japanese chibi art."
    DREAMWORKS = "NO TEXT. 3D animated style with expressive, slightly exaggerated characters, dynamic lighting, and a cinematic, adventurous atmosphere, inspired by DreamWorks Animation films."


from scripts.utils.rate_limiter import RateLimiter


class FluxImageGenerator:
    def __init__(self, token=None, output_dir="output_images", model="black-forest-labs/FLUX.1-schnell",
                 azure_endpoint=None, azure_api_key=None, azure_model="MAI-Image-2e"):
        self.hf_client = InferenceClient(token=token) if token else None
        self.model = model
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.azure_endpoint = azure_endpoint
        self.azure_api_key = azure_api_key
        self.azure_model = azure_model
        self.azure_limiter = RateLimiter(max_calls=20, period=60.0)
        self._hf_dead = self.hf_client is None
        self._azure_dead = not self.azure_endpoint or not self.azure_api_key

    @staticmethod
    def getImagePresets():
        return {preset.name: preset.value for preset in StylePreset}

    def generate_image(self, custom_prompt, style_preset: StylePreset, aspect_ratio: AspectRatio):
        if style_preset == StylePreset.YOUTUBE_THUMBNAIL:
            final_prompt = style_preset.value
        elif style_preset == StylePreset.NONE:
            final_prompt = custom_prompt
        else:
            final_prompt = f"{custom_prompt}. with this style -> {style_preset.value}"

        width, height = aspect_ratio.value
        print(Fore.BLUE + f"Image prompt\t ::-> {final_prompt}")

        for attempt in range(5):
            if not self._hf_dead:
                image_path = self._generate_with_huggingface(final_prompt, width, height)
                if image_path:
                    return image_path
                print(Fore.YELLOW + "HF failed, marking as dead for this generation")
                self._hf_dead = True

            if not self._azure_dead:
                image_path = self._generate_with_azure(final_prompt, width, height)
                if image_path:
                    return image_path
                print(Fore.YELLOW + "Azure failed, marking as dead for this generation")
                self._azure_dead = True

            if self._hf_dead and self._azure_dead:
                print(Fore.RED + "Both providers dead, skipping remaining attempts")
                break
            if attempt < 4:
                sleep(5)

        raise RuntimeError("All image generation attempts failed (HF + Azure)")

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

    def _generate_with_azure(self, prompt, width, height):
        if not self.azure_endpoint or not self.azure_api_key:
            return None

        try:
            self.azure_limiter.acquire()

            max_dim = 1024
            min_dim = 768
            if width > max_dim or height > max_dim:
                ratio = min(max_dim / width, max_dim / height)
                width = int(width * ratio)
                height = int(height * ratio)
            if width < min_dim or height < min_dim:
                ratio = max(min_dim / width, min_dim / height)
                width = int(width * ratio)
                height = int(height * ratio)

            resp = requests.post(
                self.azure_endpoint,
                headers={
                    "Content-Type": "application/json",
                    "api-key": self.azure_api_key,
                },
                json={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "n": 1,
                    "model": self.azure_model,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            b64 = data["data"][0]["b64_json"]
            img_bytes = base64.b64decode(b64)

            output_path = os.path.join(self.output_dir, f"azure_{uuid.uuid4()}.png")
            with open(output_path, "wb") as f:
                f.write(img_bytes)
            print(Fore.GREEN + f"Azure image saved to {output_path}")
            return output_path
        except Exception as e:
            print(Fore.RED + f"Azure Error: {str(e)}")
            return None
