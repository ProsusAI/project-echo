# Use an official Python runtime as a parent image
FROM public.ecr.aws/docker/library/python:3.11-slim

# Install ffmpeg, yt-dlp, dumb-init, Chromium, and libmagic
RUN apt-get update && \
    apt-get install -y ffmpeg dumb-init chromium curl libmagic1 && \
    curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# Install npm and Node.js properly
RUN apt-get update && \
    apt-get install -y curl software-properties-common && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port FastAPI is running on
EXPOSE 8000

# Python buffer size
ENV PYTHONUNBUFFERED=1

# Define the command to run the application
CMD ["dumb-init", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
