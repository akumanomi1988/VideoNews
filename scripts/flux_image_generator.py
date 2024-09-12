import uuid
from enum import Enum
from huggingface_hub import InferenceClient
import os

# Enum for aspect ratios: LANDSCAPE (16:9) and PORTRAIT (9:16)
class AspectRatio(Enum):
    LANDSCAPE = (1920, 1080)
    PORTRAIT = (1080, 1920)

# Enum for style presets that define the artistic style and look of the image
class StylePreset(Enum):
    FUTURISTIC_CITY = "NO TEXT.urban futuristic vibe with neon lights, wide-angle shot, deep depth of field"
    VINTAGE = "NO TEXT.sepia tones, retro cars, grainy effect, shot with 35mm film camera for authenticity"
    FANTASY_WORLD = "NO TEXT.epic fantasy with castles, dragons, soft lighting, shot with a cinematic lens"
    CYBERPUNK = "NO TEXT.neon cityscape, dark tones, aerial view, hyper-detailed, shot with wide-angle lens"
    MINIMALIST = "NO TEXT.clean design, geometric forms, soft pastel tones, high-key lighting, studio shot"
    NATURE_SCENE = "majestic mountains and serene lakes, DSLR shot, natural lighting, wide dynamic range"
    ANIME = "NO TEXT.Studio ghibli style, vibrant colors, expressive characters, cell shading, shot in dynamic perspectives"
    COMIC_STORYTELLER = "NO TEXT.bold lines, vibrant panels, speech bubbles, close-ups, medium shot"
    PHOTOREALISTIC = "NO TEXT.hyper-realistic, shot on full-frame DSLR, crisp details, balanced lighting"
    IMPRESSIONIST = "NO TEXT.soft brushstrokes, muted colors, wide landscape, impression of natural light"
    SURREALIST = "NO TEXT.dreamlike elements, warped shapes, juxtaposed objects, ethereal light, macro lens"
    ABSTRACT = "NO TEXT.non-representational, vibrant splashes of color, sharp contrasts, close-up, macro shot"
    REALISM = "NO TEXT.faithful depiction, natural colors, medium shot, balanced light, fine details"
    YOUTUBE_THUMBNAIL = "NO TEXT. High contrast, bold colors, dramatic lighting, intense close-ups of characters or objects, exaggerated dynamic poses, and focused expressions. No text. Designed for maximum visual impact, targeting clickbait-style engagement, with an emphasis on evoking curiosity and excitement."


class FluxImageGenerator:
    def __init__(self, token=None, output_dir="output_images"):
        # Initialize the Hugging Face Inference Client with the provided token
        self.client = InferenceClient(token=token)
        # Set output directory, creating it if it doesn't exist
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_image(self, custom_prompt, style_preset, aspect_ratio, model="black-forest-labs/FLUX.1-dev"):
        try:
            # Get the dimensions based on the selected aspect ratio
            width, height = aspect_ratio.value
            # Build the final prompt by combining the custom user prompt and the style preset
            prompt = f"{custom_prompt}, in {style_preset.value}"
            # Generate the image using the Hugging Face API
            image = self.client.text_to_image(
                prompt,
                model=model,
                height=height,
                width=width
            )
            # Define the output file path
            output_path = os.path.join(self.output_dir, f"{style_preset.name}_{uuid.uuid4()}.png")
            # Save the generated image to the specified output directory
            image.save(output_path)
            print(f"Image generated successfully and saved to {output_path}.")
            return output_path
        except Exception as e:
            print(f"Error: {e}")
            return None

