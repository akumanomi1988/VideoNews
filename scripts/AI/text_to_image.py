from time import sleep
import uuid
import base64
import ssl
import socket
from urllib.parse import urlsplit
from enum import Enum
import os
from colorama import Fore, init
import requests

init(autoreset=True)


class AspectRatio(Enum):
    # MAI image endpoints require each edge >=768 and cap the pixel count at
    # 1,048,576 for the currently configured deployment. These are near-exact
    # platform ratios within that budget.
    LANDSCAPE = (1365, 768)
    PORTRAIT = (768, 1365)
    SHORTS = (768, 1365)


class StylePreset(Enum):
    NONE = "NO TEXT."
    NEWSPHERE_CINEMATIC = (
        "NewSphere Cinematic: editorial film-still craft, believable materials and anatomy, "
        "purposeful visual hierarchy, layered depth and a coherent photographic treatment. "
        "Honor the scene's specific action, location, viewpoint and lighting. Use navy, cyan "
        "and warm amber as restrained connecting accents, not an obligatory dark-blue wash. "
        "Preserve daylight, environmental color and the subject's natural textures when specified. "
        "Do not add offices, monitors, holograms, robots or decorative technology unless the scene "
        "explicitly calls for them. Reserve unobtrusive caption-safe space within the environment, "
        "not a blank band. No generated text, logos, watermarks or documentary implications."
    )
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
    YOUTUBE_THUMBNAIL = (
        "Editorial YouTube thumbnail with one topic-specific focal idea, a clear silhouette, "
        "purposeful visual contrast and readable composition at small size. Follow the supplied "
        "subject and truth boundaries; do not add unrelated people, seductive poses or clickbait "
        "objects. Reserve natural negative space for deterministic title composition. "
        "No generated lettering, logos, watermarks or false documentary claims."
    )
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
    def __init__(self, output_dir="output_images", model="black-forest-labs/FLUX.1-schnell",
                 azure_endpoint=None, azure_api_key=None, azure_model="MAI-Image-2e"):
        self.model = model
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.azure_endpoint = azure_endpoint
        self.azure_api_key = azure_api_key
        self.azure_model = azure_model
        self.azure_limiter = RateLimiter(max_calls=20, period=60.0)
        self._azure_dead = not self.azure_endpoint or not self.azure_api_key
        self.last_generation_info = {}

    @staticmethod
    def getImagePresets():
        return {preset.name: preset.value for preset in StylePreset}

    def preflight(self):
        """Check Azure configuration and TLS reachability without generating or billing."""
        if not self.azure_endpoint or not self.azure_api_key:
            raise RuntimeError("Azure image generation requires an endpoint and API key")
        parsed = urlsplit(self.azure_endpoint)
        if parsed.scheme != "https" or not parsed.hostname:
            raise RuntimeError("Azure image endpoint must be an HTTPS URL")
        try:
            with socket.create_connection((parsed.hostname, parsed.port or 443), timeout=8) as sock:
                with ssl.create_default_context().wrap_socket(sock, server_hostname=parsed.hostname):
                    pass
        except (OSError, ssl.SSLError) as exc:
            raise RuntimeError("Azure image endpoint is not reachable over verified TLS") from exc
        return {"provider": "Azure MAI", "configured": True,
                "tls_reachable": True, "model": self.azure_model}

    def generate_image(self, custom_prompt, style_preset: StylePreset, aspect_ratio: AspectRatio,
                       max_attempts: int | None = None):
        if style_preset == StylePreset.NONE:
            final_prompt = custom_prompt
        else:
            final_prompt = f"{custom_prompt}. with this style -> {style_preset.value}"

        width, height = aspect_ratio.value
        print(Fore.BLUE + f"Image prompt\t ::-> {final_prompt}")
        self.preflight()
        attempts = max_attempts if max_attempts is not None else int(
            os.getenv("VIDEO_IMAGE_MAX_ATTEMPTS_PER_SCENE", "2"))
        if not 1 <= attempts <= 4:
            raise ValueError("VIDEO_IMAGE_MAX_ATTEMPTS_PER_SCENE must be from 1 to 4")
        last_error = None
        for attempt in range(attempts):
            try:
                return self._generate_with_azure(final_prompt, width, height)
            except requests.HTTPError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else 0
                if status not in (408, 429) and status < 500:
                    raise RuntimeError(f"Azure image provider rejected the request (HTTP {status})") from exc
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
            if attempt + 1 < attempts:
                sleep(min(2 ** attempt, 8))
        raise RuntimeError(
            f"Azure image generation failed after {attempts} bounded attempt(s): "
            f"{type(last_error).__name__ if last_error else 'provider error'}"
        ) from last_error

    def _generate_with_azure(self, prompt, width, height):
        self.azure_limiter.acquire()
        max_pixels = 1_048_576
        min_edge = 768
        if width < min_edge or height < min_edge or width * height > max_pixels:
            raise ValueError("Requested image dimensions exceed the configured MAI pixel limits")
        resp = requests.post(
            self.azure_endpoint,
            headers={"Content-Type": "application/json", "api-key": self.azure_api_key},
            json={"prompt": prompt, "width": width, "height": height,
                  "n": 1, "model": self.azure_model},
            timeout=(15, 180),
        )
        resp.raise_for_status()
        data = resp.json()
        outputs = data.get("data") if isinstance(data, dict) else None
        encoded = outputs[0].get("b64_json") if outputs and isinstance(outputs[0], dict) else None
        if not isinstance(encoded, str) or len(encoded) > 80 * 1024 * 1024:
            raise RuntimeError("Azure image provider returned no valid bounded PNG payload")
        try:
            img_bytes = base64.b64decode(encoded, validate=True)
            from io import BytesIO
            from PIL import Image
            with Image.open(BytesIO(img_bytes)) as image:
                if image.format != "PNG":
                    raise ValueError("provider output is not PNG")
                image.verify()
        except Exception as exc:
            raise RuntimeError("Azure image provider returned a corrupt or unsupported image") from exc

        output_path = os.path.join(self.output_dir, f"azure_{uuid.uuid4()}.png")
        with open(output_path, "wb") as f:
            f.write(img_bytes)
        usage = data.get("usage") if isinstance(data, dict) else None
        info = {"provider": "Azure MAI", "model": self.azure_model,
                "requested_width": width, "requested_height": height, "usage": usage}
        if isinstance(usage, dict):
            cost = usage.get("cost_usd")
            if isinstance(cost, (int, float)) and cost >= 0:
                info["cost_usd"] = float(cost)
        self.last_generation_info = info
        print(Fore.GREEN + f"Azure image saved to {output_path}")
        return output_path
