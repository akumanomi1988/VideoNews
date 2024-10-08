import os
from colorama import init, Fore
from PIL import Image

# Initialize colorama
init(autoreset=True)

class ImageManager:
    """Handles image operations, including resizing and compression."""

    @staticmethod
    def reduce_image_size(image_path, max_size_kb, reduction_percentage):
        """
        Reduces the size of an image if its weight exceeds the given maximum size.

        :param image_path: Path to the image file.
        :param max_size_kb: Maximum allowed image size in kilobytes (kB).
        :param reduction_percentage: Percentage to reduce the image size by on each iteration.
        """
        # Get the current image size in kB
        current_size_kb = os.path.getsize(image_path) / 1024.0

        # Open the image
        image = Image.open(image_path)

        # Loop to reduce the size until the image is within the allowed size limit
        while current_size_kb > max_size_kb:
            # Get the current dimensions of the image
            width, height = image.size

            # Apply the reduction percentage to the current dimensions
            new_width = int(width * (1 - reduction_percentage / 100.0))
            new_height = int(height * (1 - reduction_percentage / 100.0))
            
            # Resize the image
            image = image.resize((new_width, new_height))
            
            # Overwrite the original image
            image.save(image_path, optimize=True, quality=85)
            
            # Update the current size in kB after saving the image
            current_size_kb = os.path.getsize(image_path) / 1024.0
            
            # Display status update with colorama
            print(f"{Fore.YELLOW}Resized to: {new_width}x{new_height}, weight: {current_size_kb:.2f} kB")

        print(f"{Fore.GREEN}Reduction complete! Image is within the size limit.")

