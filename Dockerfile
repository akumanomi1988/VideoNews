# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed by some Python packages
# (e.g., for image processing or other libraries you might add later)
# For now, this can be minimal. ffmpeg might be needed by news_video_processor.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
# Be specific to avoid copying unnecessary files/folders like .git, .idea, etc.
# Consider a .dockerignore file if the project root has many such items.
COPY bot/ /app/bot/
COPY scripts/ /app/scripts/
COPY Resources/ /app/Resources/
COPY telegram_bot.py .
COPY news_video_processor.py .
COPY pipeline_config.json .
# If settings.json is still used by some parts (e.g. NewsProcessor called by VideoService), copy it too.
# Or ensure NewsProcessor is configured to not need it if possible.
# For now, let's assume settings.example.json might be a template for a config.json used by NewsProcessor
COPY settings.example.json /app/config.json 
# The above line assumes 'config.json' is the name NewsProcessor expects.
# This should align with how NewsProcessor is instantiated in VideoService.

# Command to run the application
CMD ["python", "telegram_bot.py"]
