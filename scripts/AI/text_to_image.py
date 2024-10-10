import uuid
from enum import Enum
from huggingface_hub import InferenceClient
import os
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Enum for aspect ratios: LANDSCAPE (16:9) and PORTRAIT (9:16)
class AspectRatio(Enum):
    LANDSCAPE = (1920, 1080)
    PORTRAIT = (1080, 1920)

# Enum for style presets that define the artistic style and look of the image
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
    YOUTUBE_THUMBNAIL = "An eye-catching composition featuring high contrast and bold colors. The image includes intense close-ups of objects, symbols, or dynamic scenes related to the news topic, designed to evoke curiosity and engagement. The background incorporates abstract elements (like charts or icons) that add a sense of action and excitement. The overall design is tailored for maximum clickbait appeal, ensuring it stands out in feeds without any text or overly dramatic portrayals of individuals."


class FluxImageGenerator:
    def __init__(self, token=None, output_dir="output_images"):
        # Initialize the Hugging Face Inference Client with the provided token
        self.client = InferenceClient(token=token)
        # Set output directory, creating it if it doesn't exist
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    @staticmethod
    def getImagePresets():
        return {preset.name: preset.value for preset in StylePreset}
    
    def generate_image(self, custom_prompt, style_preset, aspect_ratio, model="black-forest-labs/FLUX.1-schnell"):
        try:
            # Get the dimensions based on the selected aspect ratio
            width, height = aspect_ratio.value
            # Build the final prompt by combining the custom user prompt and the style preset
            prompt = f"{custom_prompt}. {style_preset.value}"

            print(Fore.BLUE + f"Image prompt \t ::-> {prompt}")
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
            print(Fore.GREEN + f"Image generated successfully and saved to {output_path}.")
            return output_path
        except Exception as e:
            print(Fore.RED + f"Error: {e}")
            return None
