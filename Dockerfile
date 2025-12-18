FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    util-linux \
    ntfs-3g \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (Added Pillow and Numpy for AI)
RUN pip install --no-cache-dir fastapi uvicorn python-multipart jinja2 Pillow numpy

COPY . .

EXPOSE 8000
CMD ["python", "server.py"]
